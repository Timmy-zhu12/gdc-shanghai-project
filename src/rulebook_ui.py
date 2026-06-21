from __future__ import annotations

from dataclasses import replace
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cardio_pc.diagnosis import (
    ModelConfig,
    load_config as load_model_config,
    request_stop_active_llm,
    run_llama_cli,
    run_llama_server,
    save_config as save_model_config,
)
from clinical_rule_engine import DEFAULT_RULEBOOK, evaluate_patient, load_json
from image_case_adapter import DEFAULT_PROJECT_ROOT, collect_media_paths, patient_from_media, supported_media_extensions


ROOT = Path(__file__).resolve().parents[1]

INFERENCE_MODE_LABELS = {
    "规则极速模式": "rule_only",
    "Gemma4 server 增强": "gemma4_server",
    "Gemma4 CLI 增强": "gemma4_cli",
}
INFERENCE_MODE_NAMES = {value: key for key, value in INFERENCE_MODE_LABELS.items()}

MEASUREMENT_FIELDS = [
    ("EF (%)", "ef_percent"),
    ("MR VC (cm)", "mr_vena_contracta_cm"),
    ("MR EROA (cm2)", "mr_eroa_cm2"),
    ("TR VC (cm)", "tr_vena_contracta_cm"),
    ("TRV (m/s)", "tr_peak_velocity_m_s"),
    ("AS Vmax (m/s)", "aortic_vmax_m_s"),
    ("AS mean gradient (mmHg)", "aortic_mean_gradient_mmhg"),
    ("AVA (cm2)", "aortic_valve_area_cm2"),
    ("AR VC (cm)", "ar_vena_contracta_cm"),
    ("PHT (ms)", "ar_pressure_half_time_ms"),
    ("心包积液 (mm)", "pericardial_effusion_mm"),
    ("E/e'", "average_e_over_e_prime"),
    ("LAVI (mL/m2)", "la_volume_index_ml_m2"),
    ("LA diameter (mm)", "la_diameter_mm"),
    ("IVS 厚度 (mm)", "ivs_diastolic_thickness_mm"),
    ("LVPW 厚度 (mm)", "lvpw_diastolic_thickness_mm"),
]


class ClinicalRulebookApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CardioConsult 临床规则引擎 + Gemma4 离线增强")
        self.geometry("1320x860")
        self.minsize(1080, 700)

        self.file_paths: list[Path] = []
        self.rulebook = load_json(DEFAULT_RULEBOOK)
        self.model_config: ModelConfig = load_model_config()
        self.cancel_event: threading.Event | None = None
        self.worker_running = False
        self.analysis_token = 0
        self.emergency_rule_requested = False
        self.current_rule_payload: dict | None = None
        self.current_rule_text = ""
        self.last_payload: dict | None = None
        self.final_text = ""

        self.project_root_var = tk.StringVar(value=str(DEFAULT_PROJECT_ROOT))
        self.max_frames_var = tk.StringVar(value="48")
        self.decode_timeout_var = tk.StringVar(value="6")
        self.max_input_files_var = tk.StringVar(value="12")
        self.decode_workers_var = tk.StringVar(value="4")
        self.case_id_var = tk.StringVar(value="")
        self.patient_id_var = tk.StringVar(value="")

        self.mode_var = tk.StringVar(
            value=INFERENCE_MODE_NAMES.get(self.model_config.normalized_inference_mode, "规则极速模式")
        )
        self.model_path_var = tk.StringVar(value=self.model_config.model_path)
        self.llama_exe_var = tk.StringVar(value=self.model_config.llama_exe)
        self.server_url_var = tk.StringVar(value=self.model_config.server_url)
        self.llm_timeout_var = tk.StringVar(value=str(self.model_config.llm_timeout_seconds or 60))
        self.max_tokens_var = tk.StringVar(value=str(self.model_config.max_tokens or 320))
        self.temperature_var = tk.StringVar(value=str(self.model_config.temperature))

        self.status_var = tk.StringVar(value="请选择同一患者一次检查的一组 DICOM/DCOM/PNG/动图/视频。默认先跑规则，不等待 Gemma4。")
        self.measurement_vars: dict[str, tk.StringVar] = {}
        self.measurement_source_vars: dict[str, tk.StringVar] = {}
        self.autofill_enabled_var = tk.BooleanVar(value=True)
        self._programmatic_measurement_update = False

        self._build_ui()
        self._refresh_model_status()

    def _build_ui(self) -> None:
        root = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(root, padding=8)
        right = ttk.Frame(root, padding=8)
        root.add(left, weight=1)
        root.add(right, weight=2)

        ttk.Label(left, text="患者级输入", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W)
        file_row = ttk.Frame(left)
        file_row.pack(fill=tk.X, pady=(8, 6))
        ttk.Button(file_row, text="添加文件", command=self.add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(file_row, text="添加文件夹", command=self.add_folder).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(file_row, text="清空", command=self.clear_files).pack(side=tk.LEFT)

        self.file_list = tk.Listbox(left, height=9)
        self.file_list.pack(fill=tk.BOTH, expand=False)

        id_box = ttk.LabelFrame(left, text="样本信息", padding=8)
        id_box.pack(fill=tk.X, pady=(10, 0))
        self._entry(id_box, "case_id", self.case_id_var)
        self._entry(id_box, "patient_id", self.patient_id_var)

        config_box = ttk.LabelFrame(left, text="读取与防卡设置", padding=8)
        config_box.pack(fill=tk.X, pady=(10, 0))
        self._entry(config_box, "图像处理根目录", self.project_root_var)

        speed1 = ttk.Frame(config_box)
        speed1.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(speed1, text="最大代表帧").pack(side=tk.LEFT)
        ttk.Entry(speed1, textvariable=self.max_frames_var, width=8).pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(speed1, text="单文件超时秒").pack(side=tk.LEFT)
        ttk.Entry(speed1, textvariable=self.decode_timeout_var, width=8).pack(side=tk.LEFT, padx=(6, 0))

        speed2 = ttk.Frame(config_box)
        speed2.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(speed2, text="代表文件数").pack(side=tk.LEFT)
        ttk.Entry(speed2, textvariable=self.max_input_files_var, width=8).pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(speed2, text="并行解码数").pack(side=tk.LEFT)
        ttk.Entry(speed2, textvariable=self.decode_workers_var, width=8).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(
            config_box,
            text="提示：代表文件数设为 0 才会全量解码；默认极速模式会对多文件 DCOM 均匀采样。",
            wraplength=440,
        ).pack(anchor=tk.W, pady=(6, 0))

        gemma_box = ttk.LabelFrame(left, text="Gemma4 离线增强", padding=8)
        gemma_box.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(gemma_box, text="推理模式").pack(anchor=tk.W)
        self.mode_combo = ttk.Combobox(
            gemma_box,
            textvariable=self.mode_var,
            values=list(INFERENCE_MODE_LABELS),
            state="readonly",
        )
        self.mode_combo.pack(fill=tk.X, pady=(2, 6))
        self._entry(gemma_box, "server URL", self.server_url_var)
        self._entry(gemma_box, "GGUF 模型", self.model_path_var)
        self._entry(gemma_box, "llama-cli.exe", self.llama_exe_var)

        gemma_row = ttk.Frame(gemma_box)
        gemma_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(gemma_row, text="LLM超时").pack(side=tk.LEFT)
        ttk.Entry(gemma_row, textvariable=self.llm_timeout_var, width=8).pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(gemma_row, text="max tokens").pack(side=tk.LEFT)
        ttk.Entry(gemma_row, textvariable=self.max_tokens_var, width=8).pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(gemma_row, text="temperature").pack(side=tk.LEFT)
        ttk.Entry(gemma_row, textvariable=self.temperature_var, width=8).pack(side=tk.LEFT, padx=(6, 0))

        gemma_buttons = ttk.Frame(gemma_box)
        gemma_buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(gemma_buttons, text="选择模型", command=self.choose_model).pack(side=tk.LEFT)
        ttk.Button(gemma_buttons, text="选择CLI", command=self.choose_llama).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(gemma_buttons, text="保存设置", command=self.save_model_settings).pack(side=tk.RIGHT)
        self.model_status_var = tk.StringVar(value="")
        ttk.Label(gemma_box, textvariable=self.model_status_var, wraplength=440).pack(anchor=tk.W, pady=(6, 0))

        measure_box = ttk.LabelFrame(left, text="可选临床测量值（医生可填写；诊断后可自动填空白项）", padding=8)
        measure_box.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        for label, key in MEASUREMENT_FIELDS:
            var = tk.StringVar(value="")
            self.measurement_vars[key] = var
            source_var = tk.StringVar(value="")
            self.measurement_source_vars[key] = source_var
            var.trace_add("write", lambda *_args, k=key: self._on_measurement_edited(k))
            line = ttk.Frame(measure_box)
            line.pack(fill=tk.X, pady=1)
            ttk.Label(line, text=label, width=24).pack(side=tk.LEFT)
            ttk.Entry(line, textvariable=var, width=10).pack(side=tk.LEFT)
            ttk.Label(line, textvariable=source_var, width=12).pack(side=tk.LEFT, padx=(6, 0))

        auto_row = ttk.Frame(measure_box)
        auto_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Checkbutton(auto_row, text="诊断后自动填充空白项", variable=self.autofill_enabled_var).pack(side=tk.LEFT)
        ttk.Button(auto_row, text="手动自动填充", command=self.autofill_measurements_from_last_result).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(auto_row, text="清空自动值", command=self.clear_autofilled_measurements).pack(side=tk.LEFT, padx=(8, 0))

        run_row = ttk.Frame(right)
        run_row.pack(fill=tk.X)
        self.run_button = ttk.Button(run_row, text="开始分析", command=self.start_analysis)
        self.run_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(run_row, text="取消分析", command=self.cancel_analysis, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_gemma_button = ttk.Button(run_row, text="急停 Gemma", command=self.stop_gemma_now, state=tk.DISABLED)
        self.stop_gemma_button.pack(side=tk.LEFT, padx=(8, 0))
        self.emergency_rule_button = ttk.Button(run_row, text="紧急规则模式", command=self.emergency_rule_only)
        self.emergency_rule_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(run_row, text="保存结果 JSON", command=self.save_result).pack(side=tk.LEFT, padx=(8, 0))
        self.progress = ttk.Progressbar(run_row, mode="indeterminate")
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(16, 0))

        ttk.Label(right, textvariable=self.status_var, wraplength=820).pack(anchor=tk.W, pady=(10, 8))

        ttk.Label(right, text="规则命中证据", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        columns = ("label", "severity", "score", "evidence", "proxy", "refs")
        self.table = ttk.Treeview(right, columns=columns, show="headings", height=8)
        headings = {
            "label": "病症",
            "severity": "程度",
            "score": "分数",
            "evidence": "证据等级",
            "proxy": "仅代理",
            "refs": "引用",
        }
        widths = {"label": 220, "severity": 90, "score": 80, "evidence": 80, "proxy": 80, "refs": 280}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor=tk.W)
        self.table.pack(fill=tk.X, pady=(4, 10))

        ttk.Label(right, text="诊断输出", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W)
        self.output = tk.Text(right, wrap=tk.WORD, height=26, font=("Microsoft YaHei UI", 11))
        self.output.pack(fill=tk.BOTH, expand=True)

    def _entry(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> None:
        line = ttk.Frame(parent)
        line.pack(fill=tk.X, pady=2)
        ttk.Label(line, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(line, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _on_measurement_edited(self, key: str) -> None:
        if self._programmatic_measurement_update:
            return
        value = self.measurement_vars[key].get().strip()
        self.measurement_source_vars[key].set("医生填写" if value else "")

    def choose_model(self) -> None:
        selected = filedialog.askopenfilename(title="选择 Gemma4 4B GGUF", filetypes=[("GGUF", "*.gguf"), ("All files", "*.*")])
        if selected:
            self.model_path_var.set(selected)
            self.save_model_settings()

    def choose_llama(self) -> None:
        selected = filedialog.askopenfilename(title="选择 llama-cli.exe", filetypes=[("llama-cli", "*.exe"), ("All files", "*.*")])
        if selected:
            self.llama_exe_var.set(selected)
            self.save_model_settings()

    def save_model_settings(self) -> None:
        self.model_config.model_path = self.model_path_var.get().strip()
        self.model_config.llama_exe = self.llama_exe_var.get().strip()
        self.model_config.server_url = self.server_url_var.get().strip() or "http://127.0.0.1:8088"
        self.model_config.inference_mode = INFERENCE_MODE_LABELS.get(self.mode_var.get(), "rule_only")
        self.model_config.use_server = self.model_config.normalized_inference_mode == "gemma4_server"
        self.model_config.llm_timeout_seconds = max(1, int(float(self.llm_timeout_var.get().strip() or "60")))
        self.model_config.max_tokens = max(32, int(float(self.max_tokens_var.get().strip() or "320")))
        self.model_config.temperature = float(self.temperature_var.get().strip() or "0.1")
        save_model_config(self.model_config)
        self._refresh_model_status()

    def _refresh_model_status(self) -> None:
        self.model_status_var.set(self.model_config.status)

    def add_files(self) -> None:
        try:
            exts = sorted(supported_media_extensions(self.project_root_var.get()))
        except Exception:
            exts = [".png", ".jpg", ".jpeg", ".dcm", ".dicom", ".dcom", ".gif", ".tif", ".tiff", ".mp4", ".mov", ".avi"]
        pattern = " ".join(f"*{ext}" for ext in exts)
        selected = filedialog.askopenfilenames(
            title="选择心超 DICOM/DCOM/PNG/动图/视频",
            filetypes=[("Supported ultrasound media", pattern), ("All files", "*.*")],
        )
        self._add_paths([Path(item) for item in selected])

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择一个患者一次检查的文件夹")
        if not folder:
            return
        try:
            paths = collect_media_paths([folder], self.project_root_var.get())
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            return
        self._add_paths(paths)

    def _add_paths(self, paths: list[Path]) -> None:
        for path in paths:
            resolved = path.resolve()
            if resolved not in self.file_paths:
                self.file_paths.append(resolved)
                self.file_list.insert(tk.END, str(resolved))
        self.status_var.set(f"已选择 {len(self.file_paths)} 个文件。默认极速模式会均匀采样代表文件。")

    def clear_files(self) -> None:
        self.file_paths.clear()
        self.file_list.delete(0, tk.END)
        self.table.delete(*self.table.get_children())
        self.output.delete("1.0", tk.END)
        self.last_payload = None
        self.current_rule_payload = None
        self.current_rule_text = ""
        self.final_text = ""
        self.status_var.set("已清空。")

    def measurements(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for key, var in self.measurement_vars.items():
            text = var.get().strip()
            if not text:
                continue
            try:
                out[key] = float(text)
            except ValueError as exc:
                raise ValueError(f"测量值 {key} 不是数字：{text}") from exc
        return out

    def start_analysis(self) -> None:
        if self.worker_running:
            return
        if not self.file_paths:
            messagebox.showwarning("缺少输入", "请先添加一组 DICOM/DCOM/PNG/动图/视频文件。")
            return
        try:
            self.save_model_settings()
            measurements = self.measurements()
            max_frames = int(self.max_frames_var.get().strip() or "48")
            decode_timeout = float(self.decode_timeout_var.get().strip() or "6")
            max_input_files = int(self.max_input_files_var.get().strip() or "12")
            decode_workers = int(self.decode_workers_var.get().strip() or "4")
        except Exception as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.worker_running = True
        self.emergency_rule_requested = False
        self.current_rule_payload = None
        self.current_rule_text = ""
        self.analysis_token += 1
        token = self.analysis_token
        self.cancel_event = threading.Event()
        self.run_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.stop_gemma_button.configure(state=tk.DISABLED)
        self.progress.start(12)
        self.status_var.set(
            f"阶段 1/4：并行读取文件。输入 {len(self.file_paths)} 个，代表文件数 {max_input_files or '全量'}，"
            f"并行 {decode_workers}，单文件超时 {decode_timeout}s。"
        )
        thread = threading.Thread(
            target=self._worker,
            args=(token, measurements, max_frames, decode_timeout, max_input_files, decode_workers),
            daemon=True,
        )
        thread.start()

    def cancel_analysis(self) -> None:
        if self.cancel_event:
            self.cancel_event.set()
        request_stop_active_llm(self.model_config.server_url, kill_local_server=True)
        self.analysis_token += 1
        self.worker_running = False
        self.emergency_rule_requested = False
        self.progress.stop()
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        self.stop_gemma_button.configure(state=tk.DISABLED)
        self.status_var.set("已取消本次分析；正在返回的后台结果会被忽略。")

    def stop_gemma_now(self) -> None:
        if self.cancel_event:
            self.cancel_event.set()
        detail = request_stop_active_llm(self.model_config.server_url, kill_local_server=True)
        self.stop_gemma_button.configure(state=tk.DISABLED)
        self.status_var.set(f"已急停 Gemma4。{detail}。需要立即出报告时点击“紧急规则模式”。")

    def emergency_rule_only(self) -> None:
        self.emergency_rule_requested = True
        if self.cancel_event:
            self.cancel_event.set()
        detail = request_stop_active_llm(self.model_config.server_url, kill_local_server=True)
        self.mode_var.set(INFERENCE_MODE_NAMES["rule_only"])
        self.model_config.inference_mode = "rule_only"
        self.model_config.use_server = False
        save_model_config(self.model_config)
        self._refresh_model_status()

        if self.current_rule_payload and self.current_rule_text:
            self.analysis_token += 1
            text = (
                f"{self.current_rule_text.rstrip()}\n\n"
                f"[紧急规则模式：用户已中断 Gemma4 CLI/server，本报告由已提取的边缘特征和临床规则直接生成。急停记录：{detail}]"
            )
            payload = self.current_rule_payload
            payload.setdefault("gemma", {})["emergency_rule_only"] = True
            payload["gemma"]["stop_detail"] = detail
            self._show_result(self.analysis_token, payload, text, "紧急规则模式：Gemma4 已跳过")
            return

        self.status_var.set(f"已切换为纯规则模式。当前还没有完成特征提取，待安全解码返回后将直接生成规则报告。急停记录：{detail}")

    def _worker(
        self,
        token: int,
        measurements: dict[str, float],
        max_frames: int,
        decode_timeout: float,
        max_input_files: int,
        decode_workers: int,
    ) -> None:
        try:
            patient = patient_from_media(
                self.file_paths,
                project_root=self.project_root_var.get(),
                measurements=measurements,
                case_id=self.case_id_var.get().strip(),
                patient_id=self.patient_id_var.get().strip(),
                max_loaded_frames=max_frames,
                decode_timeout=decode_timeout,
                max_input_files=max_input_files,
                decode_workers=decode_workers,
            )
            self._post_status(token, "阶段 2/4：规则引擎正在计算临床阈值、代理特征和证据等级。")
            result = evaluate_patient(patient, self.rulebook)
            payload = {"patient": patient, "result": result, "gemma": {"mode": self.model_config.normalized_inference_mode}}
            rule_text = format_result_text(payload)
            self.current_rule_payload = payload
            self.current_rule_text = rule_text

            if self.cancel_event and self.cancel_event.is_set() and not self.emergency_rule_requested:
                self.after(0, lambda: self._show_cancelled(token))
                return

            runtime_config = replace(self.model_config)
            if self.emergency_rule_requested or runtime_config.normalized_inference_mode == "rule_only":
                status = "规则极速模式；Gemma4 已跳过"
                self.after(0, lambda: self._show_result(token, payload, rule_text, status))
                return

            self._post_status(token, f"阶段 3/4：正在运行 {INFERENCE_MODE_NAMES[runtime_config.normalized_inference_mode]}。可随时急停。")
            self.after(0, lambda: self.stop_gemma_button.configure(state=tk.NORMAL))
            enhanced_text, status = run_gemma4_enhancement(payload, rule_text, runtime_config, self.cancel_event)

            if self.cancel_event and self.cancel_event.is_set() and self.emergency_rule_requested:
                payload.setdefault("gemma", {})["emergency_rule_only"] = True
                text = f"{rule_text.rstrip()}\n\n[紧急规则模式：Gemma4 已被中断，系统保留规则引擎报告。]"
                self.after(0, lambda: self._show_result(token, payload, text, "紧急规则模式：Gemma4 已跳过"))
                return
            if self.cancel_event and self.cancel_event.is_set():
                self.after(0, lambda: self._show_cancelled(token))
                return

            self._post_status(token, "阶段 4/4：正在生成 UI 报告。")
            self.after(0, lambda: self._show_result(token, payload, enhanced_text, status))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda exc=exc: self._show_error(token, exc))

    def _post_status(self, token: int, message: str) -> None:
        self.after(0, lambda: self._set_status_if_current(token, message))

    def _set_status_if_current(self, token: int, message: str) -> None:
        if token == self.analysis_token:
            self.status_var.set(message)

    def _show_cancelled(self, token: int) -> None:
        if token != self.analysis_token:
            return
        self.worker_running = False
        self.progress.stop()
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        self.stop_gemma_button.configure(state=tk.DISABLED)
        self.status_var.set("已取消本次分析。")

    def _show_error(self, token: int, exc: Exception) -> None:
        if token != self.analysis_token:
            return
        self.worker_running = False
        self.progress.stop()
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        self.stop_gemma_button.configure(state=tk.DISABLED)
        self.status_var.set("分析失败。")
        messagebox.showerror("分析失败", str(exc))

    def _show_result(self, token: int, payload: dict, final_text: str, model_status: str) -> None:
        if token != self.analysis_token:
            return
        self.last_payload = payload
        self.final_text = final_text
        suggestions = suggest_measurements_from_payload(payload)
        payload["ui_measurement_suggestions"] = {
            key: {"value": value, "source": source}
            for key, (value, source) in suggestions.items()
        }

        if self.autofill_enabled_var.get():
            filled = self.apply_measurement_suggestions(suggestions)
            if filled:
                payload["patient"].setdefault("ui_autofill", {})["filled_count"] = filled

        self.worker_running = False
        self.progress.stop()
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        self.stop_gemma_button.configure(state=tk.DISABLED)

        patient = payload["patient"]
        mode = patient.get("decode_mode", {})
        self.status_var.set(
            f"完成：输入 {mode.get('input_file_count', len(self.file_paths))} 个文件，"
            f"采样 {mode.get('selected_file_count', 'NA')} 个，成功解码 {mode.get('decoded_file_count', 'NA')} 个，"
            f"代表帧 {patient.get('loaded_frame_count', 0)}，特征耗时 {patient.get('elapsed_seconds_feature_extraction', 'NA')} 秒；"
            f"推理状态：{model_status}"
        )
        self.table.delete(*self.table.get_children())
        for item in payload["result"].get("top_results", []):
            self.table.insert(
                "",
                tk.END,
                values=(
                    item.get("zh", ""),
                    item.get("severity", ""),
                    item.get("score", ""),
                    item.get("evidence_level", ""),
                    "是" if item.get("proxy_only") else "否",
                    ", ".join(item.get("references", [])),
                ),
            )
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, final_text)

    def autofill_measurements_from_last_result(self) -> None:
        if not self.last_payload:
            messagebox.showinfo("没有结果", "请先完成一次诊断，再自动填充。")
            return
        suggestions = suggest_measurements_from_payload(self.last_payload)
        if not suggestions:
            messagebox.showinfo("没有可填充项", "当前规则结果没有可自动填充的测量建议。")
            return
        filled = self.apply_measurement_suggestions(suggestions)
        self.status_var.set(f"已根据诊断结果自动填充 {filled} 个空白测量项；医生手填项未覆盖。")

    def apply_measurement_suggestions(self, suggestions: dict[str, tuple[float, str]]) -> int:
        filled = 0
        self._programmatic_measurement_update = True
        try:
            for key, (value, source) in suggestions.items():
                if key not in self.measurement_vars:
                    continue
                if self.measurement_vars[key].get().strip():
                    continue
                self.measurement_vars[key].set(format_suggested_number(value))
                self.measurement_source_vars[key].set(source)
                filled += 1
        finally:
            self._programmatic_measurement_update = False
        return filled

    def clear_autofilled_measurements(self) -> None:
        cleared = 0
        self._programmatic_measurement_update = True
        try:
            for key, source_var in self.measurement_source_vars.items():
                if source_var.get().startswith("自动"):
                    self.measurement_vars[key].set("")
                    source_var.set("")
                    cleared += 1
        finally:
            self._programmatic_measurement_update = False
        self.status_var.set(f"已清空 {cleared} 个自动填充值，医生手填项保留。")

    def save_result(self) -> None:
        if not self.last_payload:
            messagebox.showinfo("没有结果", "请先完成一次分析。")
            return
        default = ROOT / "outputs" / f"ui_rule_gemma_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        selected = filedialog.asksaveasfilename(
            title="保存规则/Gemma4诊断结果",
            defaultextension=".json",
            initialfile=default.name,
            initialdir=str(default.parent),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not selected:
            return
        payload = {**self.last_payload, "final_text": self.final_text}
        Path(selected).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.status_var.set(f"已保存：{selected}")


def run_gemma4_enhancement(
    payload: dict,
    rule_text: str,
    config: ModelConfig,
    cancel_event: threading.Event | None,
) -> tuple[str, str]:
    prompt = build_gemma4_rulebook_prompt(payload, rule_text)
    mode = config.normalized_inference_mode
    if mode == "gemma4_server":
        text, error = run_llama_server(prompt, config, cancel_event=cancel_event)
        status = f"Gemma4 server 增强：{config.server_url}"
    elif mode == "gemma4_cli":
        if not config.model_ready:
            error = "Gemma4 CLI 模式缺少 llama-cli.exe 或 GGUF 模型。"
            text = ""
        else:
            text, error = run_llama_cli(prompt, config, cancel_event=cancel_event)
        status = f"Gemma4 CLI 增强：{Path(config.model_path).name}"
    else:
        return rule_text, "规则极速模式；Gemma4 已跳过"

    payload.setdefault("gemma", {})["mode"] = mode
    payload["gemma"]["status"] = status
    payload["gemma"]["error"] = error
    payload["gemma"]["raw_text"] = text

    if text.strip():
        clean = sanitize_gemma_text(text)
        payload["gemma"]["rendered_text"] = clean
        final_text = (
            f"{rule_text.rstrip()}\n\n"
            "Gemma4 教学解释增强（不改变上方规则诊断）：\n"
            f"{clean}\n\n"
            "Gemma4安全约束：以上增强解释只能围绕规则引擎已给出的诊断、证据和缺失项展开，不能替代正式超声报告。"
        )
        return final_text, status

    final_text = (
        f"{rule_text.rstrip()}\n\n"
        f"[Gemma4降级：{status} 未返回可用文本，已保留本地规则引擎报告。原因：{error}]"
    )
    return final_text, status + "；已降级为规则报告"


def build_gemma4_rulebook_prompt(payload: dict, rule_text: str) -> str:
    result = payload.get("result", {})
    patient = payload.get("patient", {})
    compact_payload = {
        "case_id": patient.get("case_id", ""),
        "core_fields": {
            "教学参考病症判断": result.get("教学参考病症判断", ""),
            "最小病症": result.get("最小病症", ""),
            "逻辑链": result.get("逻辑链", ""),
        },
        "top_results": result.get("top_results", [])[:5],
        "measurements": patient.get("measurements", {}),
        "proxies": patient.get("proxies", {}),
        "views": patient.get("views", []),
        "decode_mode": patient.get("decode_mode", {}),
        "loaded_frame_count": patient.get("loaded_frame_count", 0),
        "decode_warnings": patient.get("decode_warnings", [])[:6],
        "safety_boundary": result.get("safety_boundary", ""),
    }
    compact_json = json.dumps(compact_payload, ensure_ascii=False, indent=2)
    if len(compact_json) > 9000:
        compact_json = compact_json[:9000] + "\n...TRUNCATED..."
    return f"""
你是 CardioConsult 的 Gemma4 4B 离线教学解释模块。你只能解释本地临床规则引擎已经给出的结论，不能新增病症、不能改变分级、不能把代理证据包装成临床金标准。

必须遵守：
1. 不改写“教学参考病症判断 / 最小病症 / 逻辑链”。
2. 如果证据等级低或 proxy_only 为 true，要明确说明这是代理证据，需要复核。
3. 输出中文，面向基层医生和超声初学者，控制在 350 到 600 字。
4. 输出结构为：教学解释、复核重点、补扫/测量建议、安全边界。
5. 不要输出 JSON，不要输出 Markdown 表格，不要声称这是最终临床诊断。

本地规则报告：
{rule_text}

结构化证据：
{compact_json}
""".strip()


def sanitize_gemma_text(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.replace("```json", "").replace("```", "").strip()
    banned = ["最终诊断：", "治疗方案：", "医嘱："]
    for token in banned:
        clean = clean.replace(token, token.replace("：", "参考说明："))
    return clean[:1800].strip()


def format_result_text(payload: dict) -> str:
    patient = payload["patient"]
    result = payload["result"]
    mode = patient.get("decode_mode", {})
    skipped = patient.get("skipped_files_by_sampling", [])
    lines = [
        f"教学参考病症判断：{result['教学参考病症判断']}",
        f"最小病症：{result['最小病症']}",
        f"逻辑链：{result['逻辑链']}",
        "",
        "输入与速度摘要：",
        f"- case_id：{patient.get('case_id', '')}",
        f"- 输入文件数：{mode.get('input_file_count', len(patient.get('source_files', [])))}",
        f"- 代表文件数：{mode.get('selected_file_count', 'NA')}",
        f"- 成功解码文件数：{mode.get('decoded_file_count', 'NA')}",
        f"- 代表帧：{patient.get('loaded_frame_count', 0)}",
        f"- 并行解码数：{mode.get('workers', 'NA')}",
        f"- 单文件超时：{mode.get('file_decode_timeout_seconds', 'NA')} 秒",
        f"- 特征耗时：{patient.get('elapsed_seconds_feature_extraction', 'NA')} 秒",
        f"- 识别体位：{', '.join(patient.get('views', [])) or '未能可靠定位'}",
        f"- 质量分：{patient.get('proxies', {}).get('quality_score', 'NA')}",
        "",
        "命中规则：",
    ]
    for item in result.get("top_results", []):
        lines.append(f"- {item.get('zh')} / {item.get('severity')} / 证据等级 {item.get('evidence_level')} / score={item.get('score')}")
        if item.get("clinical_hits"):
            lines.append("  临床量化：" + "; ".join(f"{hit['measurement']}={hit['value']}{hit.get('unit','')}" for hit in item["clinical_hits"]))
        if item.get("proxy_hits"):
            lines.append("  代理特征：" + "; ".join(f"{hit['feature']}={hit['value']:.3f}" for hit in item["proxy_hits"]))
        if item.get("missing_or_blocking"):
            lines.append("  缺失/限制：" + "; ".join(item["missing_or_blocking"]))
        if item.get("warnings"):
            lines.append("  提醒：" + "; ".join(item["warnings"]))
    if not result.get("top_results"):
        lines.append("- 未达到当前规则库的可量化异常阈值。")
    warnings = patient.get("decode_warnings", [])
    if warnings:
        lines.extend(["", "文件读取与采样提醒：", *[f"- {warning}" for warning in warnings]])
    if skipped:
        lines.append("")
        lines.append(f"极速模式跳过 {len(skipped)} 个未采样文件。如需全量分析，把“代表文件数”设为 0。")
    lines.extend(["", "安全边界：", result.get("safety_boundary", "")])
    return "\n".join(lines)


def suggest_measurements_from_payload(payload: dict) -> dict[str, tuple[float, str]]:
    result = payload.get("result", {})
    patient = payload.get("patient", {})
    suggestions: dict[str, tuple[float, str]] = {}
    for item in result.get("top_results", []):
        label = item.get("label", "")
        severity = item.get("severity", "unknown")
        proxy_only = bool(item.get("proxy_only"))
        source = "自动估算-代理" if proxy_only else "自动估算-规则"

        for hit in item.get("clinical_hits", []):
            measurement = hit.get("measurement")
            value = hit.get("value")
            if measurement and value is not None:
                suggestions[measurement] = (float(value), "自动读取-临床")

        if label == "reduced_lv_systolic_function":
            suggestions.setdefault("ef_percent", (estimate_ef(patient, severity), source))
        elif label == "mitral_regurgitation":
            suggestions.update(regurgitation_suggestions("mr", severity, source))
        elif label == "tricuspid_regurgitation":
            suggestions.update(regurgitation_suggestions("tr", severity, source))
            if severity in {"mild", "moderate", "severe"}:
                suggestions.setdefault("tr_peak_velocity_m_s", ({"mild": 2.6, "moderate": 3.0, "severe": 3.5}[severity], source))
        elif label == "combined_mitral_tricuspid_regurgitation":
            suggestions.update(regurgitation_suggestions("mr", severity, source))
            suggestions.update(regurgitation_suggestions("tr", severity, source))
            suggestions.setdefault("tr_peak_velocity_m_s", ({"mild": 2.6, "moderate": 3.0, "severe": 3.5}.get(severity, 2.6), source))
        elif label == "aortic_regurgitation":
            suggestions.update(regurgitation_suggestions("ar", severity, source))
            suggestions.setdefault("ar_pressure_half_time_ms", ({"mild": 520, "moderate": 350, "severe": 180}.get(severity, 350), source))
        elif label == "pulmonary_regurgitation":
            pass
        elif label == "aortic_stenosis":
            suggestions.update(aortic_stenosis_suggestions(severity, source))
        elif label == "pericardial_effusion":
            suggestions.setdefault("pericardial_effusion_mm", ({"mild": 6, "moderate": 15, "severe": 25}.get(severity, 10), source))
        elif label == "right_heart_load_or_pulmonary_hypertension":
            suggestions.setdefault("tr_peak_velocity_m_s", (3.5 if severity in {"severe", "high_probability_component"} else 2.9, source))
        elif label == "diastolic_dysfunction_or_elevated_lv_filling_pressure":
            suggestions.setdefault("average_e_over_e_prime", (15, source))
            suggestions.setdefault("la_volume_index_ml_m2", (35, source))
        elif label == "left_ventricular_hypertrophy":
            suggestions.setdefault("ivs_diastolic_thickness_mm", ({"mild": 11.5, "moderate": 13.5, "severe": 15.5}.get(severity, 11.5), source))
            suggestions.setdefault("lvpw_diastolic_thickness_mm", ({"mild": 11.5, "moderate": 13.5, "severe": 15.5}.get(severity, 11.5), source))
        elif label == "left_atrial_enlargement":
            suggestions.setdefault("la_volume_index_ml_m2", ({"mild": 36, "moderate": 44, "severe": 50}.get(severity, 36), source))
            suggestions.setdefault("la_diameter_mm", ({"mild": 42, "moderate": 47, "severe": 52}.get(severity, 42), source))
    return suggestions


def estimate_ef(patient: dict, severity: str) -> float:
    clinical = patient.get("measurements", {}).get("ef_percent")
    if clinical not in (None, ""):
        try:
            return float(clinical)
        except Exception:
            pass
    proxy = patient.get("proxies", {}).get("contractility_fraction_proxy")
    if proxy is not None:
        try:
            value = 25.0 + max(0.0, min(1.0, float(proxy))) * 35.0
            return max(20.0, min(60.0, value))
        except Exception:
            pass
    return {"mild": 45.0, "moderate": 35.0, "severe": 25.0}.get(severity, 45.0)


def regurgitation_suggestions(prefix: str, severity: str, source: str) -> dict[str, tuple[float, str]]:
    if prefix == "mr":
        return {
            "mr_vena_contracta_cm": ({"mild": 0.25, "moderate": 0.50, "severe": 0.75}.get(severity, 0.35), source),
            "mr_eroa_cm2": ({"mild": 0.15, "moderate": 0.30, "severe": 0.45}.get(severity, 0.20), source),
        }
    if prefix == "tr":
        return {"tr_vena_contracta_cm": ({"mild": 0.35, "moderate": 0.55, "severe": 0.75}.get(severity, 0.45), source)}
    if prefix == "ar":
        return {"ar_vena_contracta_cm": ({"mild": 0.25, "moderate": 0.45, "severe": 0.65}.get(severity, 0.35), source)}
    return {}


def aortic_stenosis_suggestions(severity: str, source: str) -> dict[str, tuple[float, str]]:
    return {
        "aortic_vmax_m_s": ({"mild": 2.5, "moderate": 3.5, "severe": 4.2}.get(severity, 3.0), source),
        "aortic_mean_gradient_mmhg": ({"mild": 15, "moderate": 30, "severe": 45}.get(severity, 25), source),
        "aortic_valve_area_cm2": ({"mild": 1.7, "moderate": 1.2, "severe": 0.8}.get(severity, 1.4), source),
    }


def format_suggested_number(value: float) -> str:
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def main() -> None:
    ClinicalRulebookApp().mainloop()


if __name__ == "__main__":
    main()
