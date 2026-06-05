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

INK = "#111827"
MUTED = "#6b7280"
GRID = "#d1d5db"
BLUE = "#2563eb"
GOLD = "#d97706"
RED = "#b91c1c"
GREEN = "#0f766e"
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
    words = list(value)
    lines: list[str] = []
    current = ""
    for char in words:
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
    text(draw, (90, 60), title, font_obj=FONT_TITLE)
    return wrapped(draw, (92, 126), subtitle, width=1320, fill=MUTED, font_obj=FONT_SUBTITLE, line_gap=9) + 18


def draw_source(draw: ImageDraw.ImageDraw, source: str, y: int = 1028) -> None:
    text(draw, (90, y), source, fill=MUTED, font_obj=FONT_TINY)


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
    draw.rounded_rectangle((930, 245, 1485, 410), radius=18, outline="#e5e7eb", width=2, fill="#fafafa")
    wrapped(draw, (960, 272), f"从旧基线到 12 帧 warm-cache，平均耗时下降约 {drop:.0%}。这部分提升不依赖重新训练。", width=470, fill=INK, font_obj=FONT_BODY)

    server = num(server_case.get("diagnosis_seconds"))
    draw.rounded_rectangle((90, 810, 1490, 940), radius=18, outline="#e5e7eb", width=2, fill="#fbfbfb")
    wrapped(
        draw,
        (125, 838),
        f"Gemma4 服务链路：EchoBench 第 1 例服务诊断约 {server:.1f} 秒。建议演示时先用规则链验证合同，再展示常驻模型服务的结构化输出和审计 JSON。",
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [figure_f1_story(), figure_latency_story(), figure_submission_readiness()]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
