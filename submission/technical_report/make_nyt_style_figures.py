from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


REPORT_DIR = Path(__file__).resolve().parent
ROOT = REPORT_DIR.parents[1]
OUT_DIR = REPORT_DIR / "figures_nyt"

INK = "#1f2937"
MUTED = "#6b7280"
GRID = "#d1d5db"
BLUE = "#1f77b4"
GOLD = "#f28e2b"
RED = "#c43c39"
GREEN = "#3b8f5a"
TEAL = "#6fa4ad"
NAVY = "#24477f"
SOFT_BLUE = "#e8f1f8"
SOFT_GOLD = "#fff2df"
SOFT_GREEN = "#edf7ef"
SOFT_RED = "#fbecec"
PAPER = "#ffffff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT_TITLE = font(44, bold=True)
FONT_SUBTITLE = font(24)
FONT_BODY = font(23)
FONT_BODY_BOLD = font(23, bold=True)
FONT_SMALL = font(19)
FONT_TINY = font(16)


def draw_section_strip(draw: ImageDraw.ImageDraw, y: int = 1068) -> None:
    segments = [
        ("#3f3f46", 170),
        (NAVY, 230),
        ("#6b6f93", 210),
        (TEAL, 235),
        ("#b7cfd3", 220),
        ("#d9d9d9", 220),
        (GOLD, 230),
        ("#e86f2a", 215),
        (RED, 220),
    ]
    x = 0
    for color, width in segments:
        draw.rectangle((x, y, x + width, y + 18), fill=color)
        x += width
        draw.line((x, y, x, y + 18), fill=PAPER, width=2)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def row_by_label(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    for row in rows:
        if row.get("label") == label:
            return row
    raise KeyError(label)


def num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str = INK, font_obj=None, anchor: str | None = None) -> None:
    draw.text(xy, value, fill=fill, font=font_obj or FONT_BODY, anchor=anchor)


def wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, width: int, fill: str = MUTED, font_obj=None, line_gap: int = 7) -> int:
    font_obj = font_obj or FONT_BODY
    lines: list[str] = []
    for raw_line in value.splitlines() or [""]:
        current = ""
        for char in raw_line:
            candidate = current + char
            if draw.textlength(candidate, font=font_obj) <= width or not current:
                current = candidate
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    x, y = xy
    bbox = draw.textbbox((0, 0), "测", font=font_obj)
    line_height = bbox[3] - bbox[1] + line_gap
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font_obj)
        y += line_height
    return y


def add_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> int:
    text(draw, (90, 58), title, fill=NAVY, font_obj=FONT_TITLE)
    return wrapped(draw, (92, 128), subtitle, width=1320, fill=MUTED, font_obj=FONT_SUBTITLE, line_gap=9) + 18


def draw_source(draw: ImageDraw.ImageDraw, source: str, y: int = 1028) -> None:
    text(draw, (90, y), source, fill=MUTED, font_obj=FONT_TINY)
    draw_section_strip(draw)


def map_x(value: float, left: int, right: int, vmin: float = 0.0, vmax: float = 1.0) -> int:
    return int(left + (right - left) * (value - vmin) / (vmax - vmin))


def metric_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    full = read_csv(ROOT / "validation_speedopt" / "full_evidence" / "newtraining_metrics.csv")
    rep = read_csv(
        ROOT
        / "validation_speedopt"
        / "freeze_runs"
        / "echobench_20260604_175653"
        / "validation"
        / "newtraining_metrics.csv"
    )
    return full, rep


def figure_f1_story() -> Path:
    full, rep = metric_rows()
    labels = [
        ("mr", "二尖瓣反流 MR"),
        ("tr", "三尖瓣反流 TR"),
        ("ar", "主动脉瓣反流 AR"),
        ("low_ef", "低 EF / 收缩功能减低"),
        ("rwma", "节段性室壁运动异常"),
        ("la_enlargement", "左房扩大"),
    ]
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "12 帧输入最稳定的是 MR/TR，最敏感的是 AR",
        "完整证据与 12 帧代表输入对比。横线越短，说明该标签在现场输入上越稳；AR 与左房扩大更依赖补齐切面。",
    )

    left, right = 430, 1350
    top = y + 30
    row_gap = 105
    for tick in [0.0, 0.25, 0.50, 0.75, 1.0]:
        x = map_x(tick, left, right)
        draw.line((x, top - 20, x, top + row_gap * len(labels) - 34), fill="#eef2f7", width=2)
        text(draw, (x, top + row_gap * len(labels) - 24), f"{tick:.2f}", fill=MUTED, font_obj=FONT_TINY, anchor="mt")
    text(draw, (right, top + row_gap * len(labels) + 15), "F1 score", fill=MUTED, font_obj=FONT_TINY, anchor="ra")

    for idx, (label, zh) in enumerate(labels):
        y0 = top + idx * row_gap
        full_f1 = num(row_by_label(full, label).get("f1"))
        rep_f1 = num(row_by_label(rep, label).get("f1"))
        x_full = map_x(full_f1, left, right)
        x_rep = map_x(rep_f1, left, right)
        color = RED if label in {"ar", "la_enlargement"} else BLUE
        text(draw, (90, y0 - 9), zh, font_obj=FONT_BODY_BOLD)
        text(draw, (90, y0 + 24), f"完整 {full_f1:.2f}  ·  12 帧 {rep_f1:.2f}", fill=MUTED, font_obj=FONT_SMALL)
        draw.line((x_full, y0 + 14, x_rep, y0 + 14), fill="#9ca3af", width=5)
        draw.ellipse((x_full - 12, y0 + 2, x_full + 12, y0 + 26), fill=BLUE, outline=BLUE)
        draw.ellipse((x_rep - 13, y0 + 1, x_rep + 13, y0 + 27), fill=color, outline=color)
        text(draw, (x_full, y0 - 28), f"{full_f1:.2f}", fill=BLUE, font_obj=FONT_TINY, anchor="mm")
        text(draw, (x_rep, y0 + 53), f"{rep_f1:.2f}", fill=color, font_obj=FONT_TINY, anchor="mm")

    draw.rounded_rectangle((900, 820, 1490, 955), radius=18, outline="#e5e7eb", width=2, fill="#fafafa")
    wrapped(
        draw,
        (930, 846),
        "解读：当前工程强项不是所有病症都满分，而是把“稳定项”和“切面敏感项”明确分开，报告会提示补扫和复核。",
        width=520,
        fill=INK,
        font_obj=FONT_SMALL,
    )
    draw_source(draw, "数据：validation_speedopt/full_evidence 与 freeze 12-frame EchoBench v1。图表为 NYT-inspired 注释式设计。")
    path = OUT_DIR / "nyt_fig1_f1_story.png"
    image.save(path)
    return path


def figure_latency_story() -> Path:
    old_summary = read_json(ROOT / "validation_speedopt" / "old_baseline" / "newtraining_summary.json")
    cold_summary = read_json(ROOT / "validation_speedopt" / "speedopt_cold" / "newtraining_summary.json")
    rep_latency = read_json(
        ROOT / "validation_speedopt" / "freeze_runs" / "echobench_20260604_175653" / "latency_summary.json"
    )
    full_latency = read_json(ROOT / "validation_speedopt" / "full_evidence" / "latency_summary.json")
    server_case = read_json(ROOT / "validation_speedopt" / "server_pipeline_case1_current_20260604.json")
    rows = [
        ("旧 12 帧基线", num(old_summary.get("mean_case_runtime_seconds")), "#9ca3af"),
        ("SpeedOpt 冷缓存", num(cold_summary.get("mean_case_runtime_seconds")), GOLD),
        ("12 帧 warm-cache", num(rep_latency["runtime_seconds"].get("mean")), GREEN),
        ("完整证据 warm-cache", num(full_latency["runtime_seconds"].get("mean")), BLUE),
    ]
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "规则链路的现场延迟已经降到 1 秒级",
        "常驻 Gemma4 服务适合展示模型能力；规则与特征链路适合现场快速复现和输入输出合同验证。",
    )
    left, right = 430, 1360
    top = y + 65
    max_value = 3.2
    for tick in [0, 0.75, 1.5, 2.25, 3.0]:
        x = map_x(tick, left, right, 0, max_value)
        draw.line((x, top - 40, x, top + 470), fill="#eef2f7", width=2)
        text(draw, (x, top + 505), f"{tick:.2f}s", fill=MUTED, font_obj=FONT_TINY, anchor="mt")
    for idx, (name, value, color) in enumerate(rows):
        y0 = top + idx * 115
        x = map_x(min(value, max_value), left, right, 0, max_value)
        text(draw, (90, y0 - 16), name, font_obj=FONT_BODY_BOLD)
        draw.line((left, y0, x, y0), fill=color, width=14)
        draw.ellipse((x - 15, y0 - 15, x + 15, y0 + 15), fill=color)
        text(draw, (x + 22, y0 - 16), f"{value:.3f}s/例", fill=color, font_obj=FONT_BODY_BOLD)

    old = rows[0][1]
    warm = rows[2][1]
    drop = (old - warm) / old if old else 0
    server = num(server_case.get("diagnosis_seconds"))
    draw.rounded_rectangle((90, 810, 1490, 940), radius=18, outline="#e5e7eb", width=2, fill="#fbfbfb")
    wrapped(
        draw,
        (125, 838),
        f"从旧 12 帧基线到 12 帧 warm-cache，平均耗时下降约 {drop:.0%}；Gemma4 服务链路第 1 例服务诊断约 {server:.1f} 秒。建议演示时先用规则链验证合同，再展示常驻模型服务的结构化输出和审计 JSON。",
        width=1310,
        fill=INK,
        font_obj=FONT_BODY,
    )
    draw_source(draw, "数据：validation_speedopt latency summaries 与 server_pipeline_case1_current_20260604.json。")
    path = OUT_DIR / "nyt_fig2_latency_story.png"
    image.save(path)
    return path


def figure_submission_readiness() -> Path:
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "提交材料的强项已经集中到 PC 仓库",
        "最容易被评委复现的路径是：在线规则 demo → PC 本地 UI → 规则自检 → 技术报告与审计证据。",
    )
    cards = [
        ("代码仓库", "已集中", "PC V5 为唯一积极维护入口", GREEN),
        ("在线 demo", "已上线", "规则匹配页展示输入输出合同", GREEN),
        ("技术报告", "已生成", "Markdown / DOCX / PDF / 图表", GREEN),
        ("数据披露", "已整理", "公开数据与授权本地数据分层说明", GREEN),
        ("Gemma4 离线", "可复现", "GGUF 不入库，按 models/ 放置", BLUE),
        ("演示视频", "待上传", "这是最后一个人工提交动作", GOLD),
    ]
    start_x, start_y = 90, y + 30
    card_w, card_h = 450, 190
    gap_x, gap_y = 55, 45
    for idx, (title, status, note, color) in enumerate(cards):
        col = idx % 3
        row = idx // 3
        x = start_x + col * (card_w + gap_x)
        cy = start_y + row * (card_h + gap_y)
        draw.rounded_rectangle((x, cy, x + card_w, cy + card_h), radius=20, outline="#e5e7eb", width=2, fill="#fbfbfb")
        draw.rectangle((x, cy, x + 10, cy + card_h), fill=color)
        text(draw, (x + 32, cy + 28), title, font_obj=FONT_BODY_BOLD)
        text(draw, (x + 32, cy + 73), status, fill=color, font_obj=font(34, bold=True))
        wrapped(draw, (x + 32, cy + 122), note, width=card_w - 64, fill=MUTED, font_obj=FONT_SMALL)

    draw.rounded_rectangle((90, 790, 1490, 930), radius=18, outline="#e5e7eb", width=2, fill="#fafafa")
    wrapped(
        draw,
        (125, 820),
        "程序层面下一步最有价值的是保持提交前预检、结构化模型输出、报告守卫和审计 JSON，而不是临时加入难以验证的新模型。",
        width=1320,
        fill=INK,
        font_obj=FONT_BODY,
    )
    draw_source(draw, "来源：仓库提交清单、README、技术报告包和本地预检脚本。")
    path = OUT_DIR / "nyt_fig3_submission_readiness.png"
    image.save(path)
    return path


def figure_system_flow() -> Path:
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "离线读片链路被压成 6 个可审计节点",
        "参考视觉分析白皮书的做法：先回答评委最关心的问题，再把每个处理节点画成可检查的证据单元。",
    )
    nodes = [
        ("输入", "PNG / DICOM / DCOM\ncine / video", BLUE, SOFT_BLUE),
        ("安全解码", "元数据先读\n超时跳过大文件", TEAL, "#edf6f7"),
        ("B-mode", "SRAD/CLAHE\n纹理与相位代理", NAVY, "#eef2ff"),
        ("Color Doppler", "HSV 向量化\n喷流与涡量代理", GOLD, SOFT_GOLD),
        ("标签规则", "最小病症\n层级诊断", GREEN, SOFT_GREEN),
        ("Gemma4/审计", "JSON 合同\n报告守卫", RED, SOFT_RED),
    ]
    start_x, start_y = 95, y + 60
    card_w, card_h, gap = 220, 185, 25
    centers = []
    for idx, (title, body, color, fill) in enumerate(nodes):
        x = start_x + idx * (card_w + gap)
        centers.append((x + card_w // 2, start_y + card_h // 2))
        draw.rounded_rectangle((x, start_y, x + card_w, start_y + card_h), radius=24, fill=fill, outline="#d9e2ec", width=2)
        draw.rectangle((x, start_y, x + 9, start_y + card_h), fill=color)
        text(draw, (x + 28, start_y + 30), title, fill=color, font_obj=FONT_BODY_BOLD)
        wrapped(draw, (x + 28, start_y + 78), body, width=card_w - 48, fill=INK, font_obj=FONT_SMALL, line_gap=8)
    for (x1, y1), (x2, y2) in zip(centers, centers[1:]):
        draw.line((x1 + 92, y1, x2 - 92, y2), fill="#a7b4c2", width=4)
        draw.polygon([(x2 - 92, y2), (x2 - 108, y2 - 9), (x2 - 108, y2 + 9)], fill="#a7b4c2")

    y2 = start_y + card_h + 120
    draw.rounded_rectangle((110, y2, 1490, y2 + 250), radius=22, fill="#fbfbfb", outline="#e5e7eb", width=2)
    text(draw, (145, y2 + 36), "报告输出合同", fill=NAVY, font_obj=font(32, bold=True))
    bullets = [
        "必须包含：教学参考病症判断 / 最小病症 / 逻辑链 / 安全边界 / 多智能体审计。",
        "默认规则极速模式不等待 GGUF；Gemma4 4B 是离线增强路径，受硬超时保护。",
        "任何 DICOM、视频或模型阶段失败时，输出可解释的规则后备报告，而不是空白或卡死。",
    ]
    yy = y2 + 88
    for item in bullets:
        draw.ellipse((148, yy + 5, 160, yy + 17), fill=GREEN)
        yy = wrapped(draw, (178, yy), item, width=1230, fill=INK, font_obj=FONT_SMALL, line_gap=8) + 5
    draw_source(draw, "来源：cardio_pc 规则链、anti-hang smoke、submission preflight 与本地报告守卫。")
    path = OUT_DIR / "nyt_fig4_system_flow.png"
    image.save(path)
    return path


def figure_evidence_ladder() -> Path:
    rows = [
        ("规则自检", "已完成", 1.0, GREEN, "app.py --self-test-rule-only 通过"),
        ("授权 EchoBench 完整证据", "已完成", 1.0, GREEN, "60/60 成功；平均 1.418 秒/例"),
        ("EchoBench 12 帧输入", "已完成", 1.0, GREEN, "60/60 成功；MR F1 0.936"),
        ("Gemma4 本地服务链路", "可演示", 0.78, BLUE, "常驻 server 可复用；报告守卫启用"),
        ("CAMUS / EchoNet 公开基准", "阶段性", 0.55, GOLD, "用于校准和验证，不包装成完整临床验证"),
        ("多专家盲评一致性", "待补充", 0.25, RED, "需要 2-3 位专家评分后计算 Kappa/ICC"),
    ]
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "证据覆盖要让强项和边界同时可见",
        "白皮书强调可视化必须有目的。本页目的只有一个：告诉评委哪些证据已经完成，哪些不能过度宣称。",
    )
    left, right = 530, 1350
    top = y + 45
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = map_x(tick, left, right)
        draw.line((x, top - 20, x, top + 640), fill="#eef2f7", width=2)
        text(draw, (x, top + 668), f"{tick:.2f}", fill=MUTED, font_obj=FONT_TINY, anchor="mt")
    for idx, (name, status, score, color, note) in enumerate(rows):
        y0 = top + idx * 106
        text(draw, (95, y0 - 14), name, font_obj=FONT_BODY_BOLD)
        text(draw, (95, y0 + 22), status, fill=color, font_obj=FONT_SMALL)
        x = map_x(score, left, right)
        draw.line((left, y0, x, y0), fill=color, width=18)
        draw.ellipse((x - 16, y0 - 16, x + 16, y0 + 16), fill=color)
        if score >= 0.86:
            text(draw, (right - 500, y0 + 24), note, fill=MUTED, font_obj=FONT_SMALL)
        else:
            text(draw, (x + 26, y0 - 18), note, fill=MUTED, font_obj=FONT_SMALL)
    draw.rounded_rectangle((1030, 830, 1490, 940), radius=18, fill="#fafafa", outline="#e5e7eb", width=2)
    wrapped(draw, (1060, 858), "答辩口径：可以强调可运行、可审计和低成本；不能把授权 60 例说成多中心临床验证。", width=390, fill=INK, font_obj=FONT_SMALL)
    draw_source(draw, "来源：integrated_test_results、FREEZE_REVIEW_AUDIT、EchoBench v1 本地授权验证。")
    path = OUT_DIR / "nyt_fig5_evidence_ladder.png"
    image.save(path)
    return path


def figure_cost_boundary() -> Path:
    old_summary = read_json(ROOT / "validation_speedopt" / "old_baseline" / "newtraining_summary.json")
    rep_latency = read_json(
        ROOT / "validation_speedopt" / "freeze_runs" / "echobench_20260604_175653" / "latency_summary.json"
    )
    full_latency = read_json(ROOT / "validation_speedopt" / "full_evidence" / "latency_summary.json")
    warm = num(rep_latency["runtime_seconds"].get("mean"))
    full = num(full_latency["runtime_seconds"].get("mean"))
    old = num(old_summary.get("mean_case_runtime_seconds"))
    rows = [
        ("12 帧规则链路", warm, GREEN, f"约 {3600 / warm:.0f} 例/小时"),
        ("完整证据规则链路", full, BLUE, f"约 {3600 / full:.0f} 例/小时"),
        ("旧 12 帧基线", old, "#9ca3af", "优化前参照"),
    ]
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "成本优势来自本地推理，而不是牺牲审计边界",
        "规则链路按病例不产生云 API 成本；Gemma4 4B GGUF 用于离线增强，默认不阻塞快速报告。",
    )
    left, right = 420, 1320
    top = y + 70
    max_value = 3.0
    for tick in [0, 0.75, 1.5, 2.25, 3.0]:
        x = map_x(tick, left, right, 0, max_value)
        draw.line((x, top - 32, x, top + 270), fill="#edf2f7", width=2)
        text(draw, (x, top + 304), f"{tick:.2f}s", fill=MUTED, font_obj=FONT_TINY, anchor="mt")
    for idx, (name, seconds, color, note) in enumerate(rows):
        y0 = top + idx * 95
        x = map_x(min(seconds, max_value), left, right, 0, max_value)
        text(draw, (95, y0 - 14), name, font_obj=FONT_BODY_BOLD)
        draw.line((left, y0, x, y0), fill=color, width=16)
        draw.ellipse((x - 16, y0 - 16, x + 16, y0 + 16), fill=color)
        text(draw, (x + 25, y0 - 16), f"{seconds:.3f}s/例 · {note}", fill=color, font_obj=FONT_SMALL)

    card_y = 610
    cards = [
        ("低边际成本", "不按病例调用云 API；适合教学演示和基层离线场景。", GREEN, SOFT_GREEN),
        ("隐私边界", "脱敏图像可留在超声设备旁 PC；GGUF 权重不入库。", BLUE, SOFT_BLUE),
        ("准确性代价", "缺切面时 AR、RWMA、左房扩大下降，必须输出补扫建议。", GOLD, SOFT_GOLD),
    ]
    for i, (title, body, color, fill) in enumerate(cards):
        x = 95 + i * 500
        draw.rounded_rectangle((x, card_y, x + 430, card_y + 210), radius=22, fill=fill, outline="#e5e7eb", width=2)
        text(draw, (x + 30, card_y + 32), title, fill=color, font_obj=font(31, bold=True))
        wrapped(draw, (x + 30, card_y + 88), body, width=360, fill=INK, font_obj=FONT_SMALL, line_gap=8)
    draw_source(draw, "来源：latency_summary、old_baseline、新版 anti-hang 默认规则路径与本地 GGUF 策略。")
    path = OUT_DIR / "nyt_fig6_cost_boundary.png"
    image.save(path)
    return path


def figure_safety_contract() -> Path:
    image = Image.new("RGB", (1600, 1100), PAPER)
    draw = ImageDraw.Draw(image)
    y = add_header(
        draw,
        "最终输出不是一句诊断，而是一份受保护的教学合同",
        "评审时最应展示的是：系统会给出明确最小病症，同时保留证据充分度、补扫建议和安全边界。",
    )
    rows = [
        ("必须输出", "教学参考病症判断、最小病症、逻辑链", GREEN),
        ("必须解释", "B-mode / Color Doppler / 相位识别 / 切面覆盖", BLUE),
        ("必须审计", "多智能体审计 JSON、规则 fallback、prompt leakage 检查", NAVY),
        ("必须降级", "大文件、模型、DICOM 解码超时时返回规则报告", GOLD),
        ("必须声明", "不作为临床最终诊断、治疗建议或医嘱", RED),
    ]
    left, top = 125, y + 55
    for idx, (title, body, color) in enumerate(rows):
        yy = top + idx * 120
        draw.rounded_rectangle((left, yy, 1475, yy + 86), radius=18, fill="#fbfbfb", outline="#e5e7eb", width=2)
        draw.rectangle((left, yy, left + 12, yy + 86), fill=color)
        text(draw, (left + 38, yy + 24), title, fill=color, font_obj=FONT_BODY_BOLD)
        wrapped(draw, (left + 220, yy + 22), body, width=1040, fill=INK, font_obj=FONT_BODY, line_gap=7)
    draw.rounded_rectangle((125, 850, 1475, 945), radius=18, fill="#fafafa", outline="#e5e7eb", width=2)
    wrapped(draw, (155, 878), "答辩建议：先展示最小病症和逻辑链，再强调“可疑教学判断 + 安全分层 + 建议复核”。这样既满足明确输出，又不越过医疗边界。", width=1250, fill=INK, font_obj=FONT_SMALL)
    draw_source(draw, "来源：诊断输出合同、报告保护层、多智能体审计和 anti-hang smoke。")
    path = OUT_DIR / "nyt_fig7_safety_contract.png"
    image.save(path)
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        figure_f1_story(),
        figure_latency_story(),
        figure_submission_readiness(),
        figure_system_flow(),
        figure_evidence_ladder(),
        figure_cost_boundary(),
        figure_safety_contract(),
    ]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
