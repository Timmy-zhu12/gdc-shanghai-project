from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import make_nyt_style_figures


REPORT_DIR = Path(__file__).resolve().parent
ROOT = REPORT_DIR.parents[1]
TEX_OUT = REPORT_DIR / "CardioConsult_Chinese_LaTeX_Report.tex"
PDF_OUT = REPORT_DIR / "CardioConsult_Chinese_LaTeX_Report.pdf"
BUILD_NOTE = REPORT_DIR / "CardioConsult_Chinese_LaTeX_Build.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def row(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    for item in rows:
        if item.get("label") == label:
            return item
    raise KeyError(label)


def f(value: object, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def pct(value: object) -> str:
    try:
        return f"{float(value) * 100:.1f}\\%"
    except Exception:
        return str(value)


def tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def gather() -> dict[str, object]:
    full = read_csv(ROOT / "validation_speedopt" / "full_evidence" / "newtraining_metrics.csv")
    rep = read_csv(
        ROOT
        / "validation_speedopt"
        / "freeze_runs"
        / "echobench_20260604_175653"
        / "validation"
        / "newtraining_metrics.csv"
    )
    full_latency = read_json(ROOT / "validation_speedopt" / "full_evidence" / "latency_summary.json")
    rep_latency = read_json(
        ROOT / "validation_speedopt" / "freeze_runs" / "echobench_20260604_175653" / "latency_summary.json"
    )
    old_summary = read_json(ROOT / "validation_speedopt" / "old_baseline" / "newtraining_summary.json")
    server_case = read_json(ROOT / "validation_speedopt" / "server_pipeline_case1_current_20260604.json")
    return {
        "full": full,
        "rep": rep,
        "full_latency": full_latency,
        "rep_latency": rep_latency,
        "old_summary": old_summary,
        "server_case": server_case,
    }


def metric_table(rows: list[dict[str, str]]) -> str:
    labels = [
        ("mr", "二尖瓣反流 MR"),
        ("tr", "三尖瓣反流 TR"),
        ("ar", "主动脉瓣反流 AR"),
        ("low_ef", "低 EF / 收缩功能减低"),
        ("rwma", "节段性室壁运动异常"),
        ("la_enlargement", "左房扩大"),
    ]
    body = []
    for label, name in labels:
        item = row(rows, label)
        body.append(
            " & ".join(
                [
                    name,
                    item["n"],
                    item["positive_gold"],
                    f(item["accuracy"]),
                    f(item["sensitivity"]),
                    f(item["specificity"]),
                    f(item["f1"]),
                ]
            )
            + r" \\"
        )
    return "\n".join(body)


def render_tex(data: dict[str, object]) -> str:
    full = data["full"]  # type: ignore[assignment]
    rep = data["rep"]  # type: ignore[assignment]
    full_latency = data["full_latency"]  # type: ignore[assignment]
    rep_latency = data["rep_latency"]  # type: ignore[assignment]
    old_summary = data["old_summary"]  # type: ignore[assignment]
    server_case = data["server_case"]  # type: ignore[assignment]

    full_mr = row(full, "mr")
    full_tr = row(full, "tr")
    full_ar = row(full, "ar")
    full_low = row(full, "low_ef")
    rep_mr = row(rep, "mr")
    rep_ar = row(rep, "ar")
    rep_low = row(rep, "low_ef")
    old_mean = float(old_summary["mean_case_runtime_seconds"])
    warm_mean = float(rep_latency["runtime_seconds"]["mean"])
    speedup = (old_mean - warm_mean) / old_mean
    server_seconds = float(server_case["diagnosis_seconds"])

    return rf"""\documentclass[UTF8,fontset=windows,zihao=-4]{{ctexart}}
\usepackage[a4paper,margin=2.35cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{hyperref}}
\usepackage{{xcolor}}
\usepackage{{caption}}
\usepackage{{enumitem}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue}}
\definecolor{{cardioBlue}}{{HTML}}{{2563EB}}
\definecolor{{cardioGold}}{{HTML}}{{D97706}}
\definecolor{{cardioInk}}{{HTML}}{{111827}}
\setlist{{nosep,leftmargin=2em}}
\captionsetup{{font=small,labelfont=bf}}
\title{{CardioConsult PC V5 中文技术报告：离线心脏超声教学参考系统}}
\author{{CardioConsult 项目组}}
\date{{{date.today().isoformat()}}}

\begin{{document}}
\maketitle

\begin{{abstract}}
CardioConsult PC V5 被设计为可接入超声机器或超声工作站导出目录的离线分析终端。系统读取 PNG、DICOM/DCOM、cine 和常见视频输入，在本机完成 B-mode 预处理、Color Doppler 血流代理、动图代表帧、层级病症标签、轻量多智能体审计和 Gemma4 4B GGUF 报告生成。当前版本新增结构化 JSON 输出合同和报告守卫：Gemma4 默认输出 JSON object，再由本地代码重渲染为固定中文诊断字段，以降低最小病症漂移风险。本报告仅面向医学教学和算法演示，不构成医疗器械输出、正式临床诊断、治疗建议或医嘱。
\end{{abstract}}

\section{{问题陈述}}
基层医疗点和超声初学者常见的问题不是完全没有图像，而是有导出图像却缺少稳定的心脏超声专科解释。传统多人会诊依赖专家时间，云端多模态模型又会带来隐私、网络和持续调用成本。CardioConsult 的目标是在离线 PC 上提供一层可审计的教学参考：输出疑似病症判断、证据链、补扫建议和安全边界，而不替代正式超声报告。

\section{{系统方案}}
系统由五个本地层组成：
\begin{{enumerate}}
  \item 输入层：读取 PNG/JPG、DICOM/DCOM、多帧 TIFF、GIF、MP4/MOV/AVI 等文件。
  \item B-mode 分支：执行 SRAD/CLAHE 风格预处理、边缘密度、纹理熵、散斑残差、腔室面积代理和收缩舒张差。
  \item Color Doppler 分支：将 HSV 血流颜色转为活跃区、连通域、喷流宽度、方向一致性、湍流、涡量代理，并在体位证据不足时输出 MR/TR/AR/PR 瓣膜定位评分。
  \item 校准与标签层：结合 V4 shared-EK/coupled-EK、V5 EchoNet-Dynamic 校准和层级病症规则。
  \item 报告层：Gemma4 4B GGUF 默认输出结构化 JSON，本地报告守卫重渲染为包含“教学参考病症判断 / 最小病症 / 逻辑链”的中文报告。
\end{{enumerate}}

\section{{Benchmark 结果}}
完整证据场景 60/60 例运行成功。MR F1={f(full_mr["f1"])}，TR F1={f(full_tr["f1"])}，AR F1={f(full_ar["f1"])}，低 EF F1={f(full_low["f1"])}。12 帧代表输入场景同样 60/60 例运行成功，MR F1={f(rep_mr["f1"])}，AR F1={f(rep_ar["f1"])}，低 EF F1={f(rep_low["f1"])}。这说明 MR/TR 在当前本地数据上较稳定，而 AR、左房扩大和 RWMA 对切面覆盖更敏感。

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{figures_nyt/nyt_fig1_f1_story.png}}
  \caption{{完整证据与 12 帧输入的 F1 对比。图表采用注释式新闻图表风格，强调稳定项和切面敏感项。}}
\end{{figure}}

\begin{{longtable}}{{p{{4.2cm}}rrrrrr}}
\toprule
标签 & n & 阳性 & 准确率 & 敏感性 & 特异性 & F1\\
\midrule
\endfirsthead
\toprule
标签 & n & 阳性 & 准确率 & 敏感性 & 特异性 & F1\\
\midrule
\endhead
{metric_table(full)}
\bottomrule
\caption{{完整证据场景主要标签指标。}}
\end{{longtable}}

\section{{性能与成本}}
旧 12 帧基线平均耗时 {old_mean:.3f} 秒/例，当前 12 帧 warm-cache 平均耗时 {warm_mean:.3f} 秒/例，下降约 {pct(speedup)}。完整证据 warm-cache 平均 {float(full_latency["runtime_seconds"]["mean"]):.3f} 秒/例。本地 Gemma4 服务链路第 1 例诊断耗时约 {server_seconds:.1f} 秒，适合在演示中展示模型能力和结构化报告；规则链路适合快速证明输入输出合同和边缘特征链路。

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{figures_nyt/nyt_fig2_latency_story.png}}
  \caption{{规则链路、缓存和 Gemma4 服务链路的延迟对比。}}
\end{{figure}}

\section{{提交完整性}}
当前提交材料集中在 PC 仓库，包括可运行代码、README、在线规则 demo、技术报告、数据来源说明、Apache-2.0 许可证、规则自检和多智能体审计。最后仍需人工完成的是 5 分钟内演示视频上传，并在提交表单中填写公开视频链接。

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{figures_nyt/nyt_fig3_submission_readiness.png}}
  \caption{{提交材料状态总览。}}
\end{{figure}}

\section{{取舍}}
\begin{{itemize}}
  \item 为了离线和低成本，系统牺牲了云端大模型的算力弹性。
  \item 为了安全和可审计，最小病症由本地规则和校准层锁定，LLM 主要负责表达和解释。
  \item 为了兼容 DICOM/DCOM 和动图，代码保留了较复杂的输入解析、代表帧采样和相位推断。
  \item 为了现场复现稳定性，在线 demo 只做规则匹配；完整图像特征和 GGUF 推理以 PC V5 应用为准。
\end{{itemize}}

\section{{局限与下一步}}
当前 60 例为授权本地教学数据和报告链接标签，不是多中心外部临床验证，也不是多专家盲评共识。TR 在本批数据中几乎全阳性，特异性解释有限；AR、PR、严重反流、HCM、RWMA 等标签需要更多均衡样本。下一步应建立 2--3 位心超医生盲评表，计算 Cohen's Kappa、加权 Kappa 或 ICC，并补充外部数据验证。

\section{{可复现命令}}
\begin{{verbatim}}
python app.py --self-test-rule-only
python tools/submission_preflight.py
python submission/technical_report/make_nyt_style_figures.py
python submission/technical_report/build_latex_report.py --compile
\end{{verbatim}}

\begin{{thebibliography}}{{9}}
\bibitem{{Leclerc2019}} Leclerc, S., Smistad, E., Pedrosa, J., et al. (2019). Deep learning for segmentation using an open large-scale dataset in 2D echocardiography. \textit{{IEEE Transactions on Medical Imaging}}, 38(9), 2198--2210.
\bibitem{{Ouyang2020}} Ouyang, D., He, B., Ghorbani, A., et al. (2020). Video-based AI for beat-to-beat assessment of cardiac function. \textit{{Nature}}, 580(7802), 252--256.
\bibitem{{Lang2015}} Lang, R. M., Badano, L. P., Mor-Avi, V., et al. (2015). Recommendations for cardiac chamber quantification by echocardiography in adults. \textit{{Journal of the American Society of Echocardiography}}, 28(1), 1--39.e14.
\bibitem{{Zoghbi2017}} Zoghbi, W. A., Adams, D., Bonow, R. O., et al. (2017). Recommendations for noninvasive evaluation of native valvular regurgitation. \textit{{Journal of the American Society of Echocardiography}}, 30(4), 303--371.
\bibitem{{Yu2002}} Yu, Y., \& Acton, S. T. (2002). Speckle reducing anisotropic diffusion. \textit{{IEEE Transactions on Image Processing}}, 11(11), 1260--1270.
\end{{thebibliography}}

\end{{document}}
"""


def compile_pdf() -> tuple[bool, str]:
    engine = shutil.which("xelatex")
    if not engine:
        return False, "未找到 xelatex；已生成 .tex，安装 TeX Live 或 MiKTeX 后可编译。"
    for _ in range(2):
        proc = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", TEX_OUT.name],
            cwd=REPORT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if proc.returncode != 0:
            return False, proc.stdout[-3000:] + "\n" + proc.stderr[-1000:]
    return PDF_OUT.exists(), "xelatex 编译完成。" if PDF_OUT.exists() else "xelatex 返回成功但 PDF 未生成。"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate the Chinese LaTeX technical report.")
    parser.add_argument("--compile", action="store_true", help="Compile with xelatex if available.")
    args = parser.parse_args()

    make_nyt_style_figures.main()
    data = gather()
    TEX_OUT.write_text(render_tex(data), encoding="utf-8")

    compiled = False
    compile_note = "未请求编译；已生成 .tex。"
    if args.compile:
        compiled, compile_note = compile_pdf()

    BUILD_NOTE.write_text(
        "\n".join(
            [
                "# 中文 LaTeX 报告构建说明",
                "",
                f"生成日期：{date.today().isoformat()}",
                "",
                f"- TeX 源文件：`{TEX_OUT.name}`",
                f"- PDF 状态：{'已生成' if compiled else '未生成'}",
                f"- 编译说明：{compile_note}",
                "",
                "本脚本不会训练模型；只读取已有验证 CSV/JSON，生成中文 LaTeX 技术文章和三张注释式 PNG 图表。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(TEX_OUT)
    print(BUILD_NOTE)
    if compiled:
        print(PDF_OUT)
    else:
        print(compile_note)
    if args.compile and not compiled and "未找到 xelatex" not in compile_note:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
