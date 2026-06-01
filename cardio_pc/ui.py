from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .diagnosis import ModelConfig, load_config, run_diagnosis, save_config
from .features import StudyAnalysis, analyze_loaded_images
from .guidance import build_primary_care_guidance
from .imaging import SUPPORTED_EXTENSIONS, LoadedImage, load_files


class CardioConsultPCApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CardioConsult PC Cine - Gemma4 4B Edge")
        self.geometry("1180x760")
        self.minsize(960, 640)

        self.config_model: ModelConfig = load_config()
        self.file_paths: list[Path] = []
        self.loaded_images: list[LoadedImage] = []
        self.study: StudyAnalysis | None = None
        self.last_report = ""
        self.preview_image: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._refresh_model_status()

    def _build_ui(self) -> None:
        root = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(root, padding=8)
        right = ttk.Frame(root, padding=8)
        root.add(left, weight=1)
        root.add(right, weight=2)

        title = ttk.Label(left, text="输入文件", font=("Microsoft YaHei UI", 13, "bold"))
        title.pack(anchor=tk.W)

        button_row = ttk.Frame(left)
        button_row.pack(fill=tk.X, pady=(8, 8))
        ttk.Button(button_row, text="添加图像/动图/视频/DICOM", command=self.add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="清空", command=self.clear_files).pack(side=tk.LEFT)

        self.file_list = tk.Listbox(left, height=12)
        self.file_list.pack(fill=tk.BOTH, expand=False)
        self.file_list.bind("<<ListboxSelect>>", lambda _event: self.update_preview())

        ttk.Label(left, text="预览", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, pady=(12, 4))
        self.preview = ttk.Label(left, text="未选择图像", anchor=tk.CENTER)
        self.preview.pack(fill=tk.BOTH, expand=True)

        model_box = ttk.LabelFrame(left, text="离线 Gemma4 4B 设置", padding=8)
        model_box.pack(fill=tk.X, pady=(12, 0))
        self.model_var = tk.StringVar(value=self.config_model.model_path)
        self.llama_var = tk.StringVar(value=self.config_model.llama_exe)
        self.status_var = tk.StringVar(value="")

        ttk.Label(model_box, text="GGUF 模型").pack(anchor=tk.W)
        model_row = ttk.Frame(model_box)
        model_row.pack(fill=tk.X, pady=(2, 6))
        ttk.Entry(model_row, textvariable=self.model_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(model_row, text="选择", command=self.choose_model).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(model_box, text="llama-cli.exe").pack(anchor=tk.W)
        llama_row = ttk.Frame(model_box)
        llama_row.pack(fill=tk.X, pady=(2, 6))
        ttk.Entry(llama_row, textvariable=self.llama_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(llama_row, text="选择", command=self.choose_llama).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(model_box, text="保存设置", command=self.save_model_settings).pack(anchor=tk.E)
        ttk.Label(model_box, textvariable=self.status_var, wraplength=420).pack(anchor=tk.W, pady=(6, 0))

        run_row = ttk.Frame(right)
        run_row.pack(fill=tk.X)
        ttk.Button(run_row, text="开始离线分析", command=self.start_analysis).pack(side=tk.LEFT)
        ttk.Button(run_row, text="保存诊断文本", command=self.save_report).pack(side=tk.LEFT, padx=(8, 0))
        self.progress = ttk.Progressbar(run_row, mode="indeterminate")
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(16, 0))

        self.summary_var = tk.StringVar(value="等待输入。Cine 综合版支持静态图、动图、视频、多页 TIFF 和多帧 DICOM；输出格式与原 PC 版一致。")
        ttk.Label(right, textvariable=self.summary_var, wraplength=720).pack(anchor=tk.W, pady=(10, 8))

        guide_box = ttk.LabelFrame(right, text="基层/初学者辅助提示", padding=8)
        guide_box.pack(fill=tk.X, pady=(0, 8))
        self.guidance_var = tk.StringVar(value="完成分析后显示体位完整性、补扫建议和复核提示。")
        ttk.Label(guide_box, textvariable=self.guidance_var, wraplength=760).pack(anchor=tk.W)

        columns = ("file", "view", "phase", "chamber", "doppler")
        self.table = ttk.Treeview(right, columns=columns, show="headings", height=8)
        headings = {
            "file": "文件/帧",
            "view": "体位",
            "phase": "相位",
            "chamber": "腔室代理",
            "doppler": "Doppler",
        }
        for column, label in headings.items():
            self.table.heading(column, text=label)
            self.table.column(column, anchor=tk.W, width=120 if column != "file" else 240)
        self.table.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(right, text="疑似诊断输出", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W)
        self.output = tk.Text(right, wrap=tk.WORD, height=18, font=("Microsoft YaHei UI", 11))
        self.output.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def add_files(self) -> None:
        extensions = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        selected = filedialog.askopenfilenames(
            title="选择心脏超声图像、动图、视频或 DICOM/DCOM 文件",
            filetypes=[
                ("Supported ultrasound media", extensions),
                ("Raster / animated images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.heic *.heif *.gif *.apng"),
                ("DICOM", "*.dcm *.dicom *.dcom"),
                ("Video", "*.mp4 *.m4v *.mov *.avi *.mkv *.webm *.wmv *.mpg *.mpeg *.ts *.mts *.m2ts *.3gp *.cine"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return
        for item in selected:
            path = Path(item)
            if path not in self.file_paths:
                self.file_paths.append(path)
                self.file_list.insert(tk.END, str(path))

    def clear_files(self) -> None:
        self.file_paths.clear()
        self.loaded_images.clear()
        self.study = None
        self.last_report = ""
        self.file_list.delete(0, tk.END)
        self.table.delete(*self.table.get_children())
        self.output.delete("1.0", tk.END)
        self.preview.configure(text="未选择图像", image="")
        self.summary_var.set("等待输入。")
        self.guidance_var.set("完成分析后显示体位完整性、补扫建议和复核提示。")

    def choose_model(self) -> None:
        selected = filedialog.askopenfilename(title="选择 Gemma4 4B GGUF", filetypes=[("GGUF", "*.gguf"), ("All files", "*.*")])
        if selected:
            self.model_var.set(selected)
            self.save_model_settings()

    def choose_llama(self) -> None:
        selected = filedialog.askopenfilename(title="选择 llama-cli.exe", filetypes=[("llama-cli", "*.exe"), ("All files", "*.*")])
        if selected:
            self.llama_var.set(selected)
            self.save_model_settings()

    def save_model_settings(self) -> None:
        self.config_model.model_path = self.model_var.get().strip()
        self.config_model.llama_exe = self.llama_var.get().strip()
        save_config(self.config_model)
        self._refresh_model_status()

    def _refresh_model_status(self) -> None:
        self.status_var.set(self.config_model.status)

    def start_analysis(self) -> None:
        if not self.file_paths:
            messagebox.showwarning("缺少输入", "请先添加 PNG、DICOM 或 DCOM 文件。")
            return
        self.save_model_settings()
        self.progress.start(12)
        self.summary_var.set("正在本地读取文件并运行边缘计算...")
        worker = threading.Thread(target=self._analysis_worker, daemon=True)
        worker.start()

    def _analysis_worker(self) -> None:
        try:
            loaded = load_files(self.file_paths)
            study = analyze_loaded_images(loaded)
            report, model_status = run_diagnosis(study, self.config_model)
            self.after(0, lambda: self._show_result(loaded, study, report, model_status))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._show_error(str(exc)))

    def _show_result(self, loaded: list[LoadedImage], study: StudyAnalysis, report: str, model_status: str) -> None:
        self.progress.stop()
        self.loaded_images = loaded
        self.study = study
        self.last_report = report
        self._refresh_table()
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, report)
        cine_sources = sorted({frame.loaded.source_type for frame in study.frames})
        self.summary_var.set(f"{study.feature_summary}\n媒体类型：{', '.join(cine_sources)}；模型状态：{model_status}")
        guidance = build_primary_care_guidance(study, self._diagnosis_label_from_report(report))
        self.guidance_var.set(guidance.compact_text)
        self.update_preview()

    @staticmethod
    def _diagnosis_label_from_report(report: str) -> str:
        marker = "教学参考病症判断："
        if marker not in report:
            return ""
        tail = report.split(marker, 1)[1]
        return tail.split("。", 1)[0].strip()

    def _show_error(self, message: str) -> None:
        self.progress.stop()
        self.summary_var.set("分析失败。")
        messagebox.showerror("分析失败", message)

    def _refresh_table(self) -> None:
        self.table.delete(*self.table.get_children())
        if not self.study:
            return
        for frame in self.study.frames:
            self.table.insert(
                "",
                tk.END,
                values=(
                    frame.loaded.display_name,
                    frame.view,
                    frame.phase,
                    f"{frame.chamber_area_proxy:.3f}",
                    "yes" if frame.has_color_doppler else "low",
                ),
            )

    def update_preview(self) -> None:
        if not self.loaded_images:
            return
        index = self.file_list.curselection()[0] if self.file_list.curselection() else 0
        index = max(0, min(index, len(self.loaded_images) - 1))
        arr = self.loaded_images[index].image
        image = Image.fromarray(arr).resize((360, 260), Image.Resampling.BILINEAR)
        self.preview_image = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_image, text="")

    def save_report(self) -> None:
        if not self.last_report:
            messagebox.showwarning("没有报告", "请先完成一次分析。")
            return
        default = Path("D:/cardioconsult_PC_math_improved_runbook/exports/cardio_consult_pc_math_improved_report.txt")
        default.parent.mkdir(parents=True, exist_ok=True)
        selected = filedialog.asksaveasfilename(
            title="保存疑似诊断文本",
            defaultextension=".txt",
            initialfile=default.name,
            initialdir=str(default.parent),
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
        if selected:
            Path(selected).write_text(self.last_report, encoding="utf-8")
            messagebox.showinfo("已保存", selected)
