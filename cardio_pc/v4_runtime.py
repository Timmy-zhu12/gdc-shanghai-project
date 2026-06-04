from __future__ import annotations

import re


def llama3_style_token_estimate(text: str) -> int:
    """Small offline estimator used only for prompt budgeting, not model tokenization."""
    if not text:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_chunks = len(re.findall(r"[A-Za-z0-9_./:%+-]+", text))
    punctuation = len(re.findall(r"[^\w\s\u4e00-\u9fff]", text))
    return int(cjk * 1.15 + latin_chunks * 1.35 + punctuation * 0.35)


def compact_prompt_for_llama3_budget(prompt: str, max_estimated_tokens: int = 1800) -> str:
    """Keep required output fields and compact long repeated evidence blocks."""
    if llama3_style_token_estimate(prompt) <= max_estimated_tokens:
        return prompt

    blocks = split_markdown_blocks(prompt)
    kept: list[str] = []
    for header, body in blocks:
        if header == "### System":
            kept.append(header + "\n" + compact_system_block(body))
        elif header == "### User task":
            kept.append(header + "\n" + compact_user_task_block(body))
        else:
            kept.append((header + "\n" + body).strip())

    candidate = "\n\n".join(kept)
    if llama3_style_token_estimate(candidate) > max_estimated_tokens:
        candidate = "\n\n".join(
            block for block in kept if not block.startswith("### System")
        )
        candidate = (
            "### System\n"
            "你是离线 Gemma4 4B 医学教学辅助系统。必须逐字使用 Required first/minimum/logic chain 三句；"
            "仅作教学参考，不是临床最终诊断、治疗建议或医嘱。\n\n"
            + candidate
        )
    return candidate


def split_markdown_blocks(prompt: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_header = "preamble"
    current_lines: list[str] = []
    for line in prompt.splitlines():
        if line.startswith("### "):
            blocks.append((current_header, "\n".join(current_lines)))
            current_header = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    blocks.append((current_header, "\n".join(current_lines)))
    return [(header, body) for header, body in blocks if header != "preamble" or body.strip()]


def first_lines(text: str, limit: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return text
    return "\n".join(lines[:limit] + ["..."])


def compact_system_block(text: str) -> str:
    required_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if (
            "第一句话必须" in stripped
            or "第二句话必须" in stripped
            or "第三句话必须" in stripped
            or "禁止把" in stripped
            or "医学边界" in stripped
            or "不是医疗器械" in stripped
            or "正式判断必须" in stripped
        ):
            required_lines.append(stripped)
    return "\n".join(required_lines[:12])


def compact_user_task_block(text: str) -> str:
    intro = "\n".join(first_lines(text, 5).splitlines()[:5])
    sections = [
        extract_named_section(text, "层级候选：", ["候选规则依据："]),
        extract_named_section(text, "候选规则依据：", ["数据库/标签体系来源摘要：", "基层辅助提示："]),
        extract_named_section(text, "特征摘要：", ["紧凑数值特征："]),
        extract_named_section(text, "紧凑数值特征：", []),
    ]
    return "\n\n".join([intro] + [section for section in sections if section.strip()])


def extract_named_section(text: str, title: str, next_titles: list[str]) -> str:
    start = text.find(title)
    if start < 0:
        return ""
    end = len(text)
    for next_title in next_titles:
        index = text.find(next_title, start + len(title))
        if index >= 0:
            end = min(end, index)
    section = text[start:end].strip()
    if title == "候选规则依据：":
        return first_lines(section, 8)
    if title == "特征摘要：":
        return first_lines(section, 6)
    if title == "紧凑数值特征：":
        return first_lines(section, 5)
    return section


def scheduler_audit_note(prompt_before: str, prompt_after: str) -> str:
    before = llama3_style_token_estimate(prompt_before)
    after = llama3_style_token_estimate(prompt_after)
    return f"V4调度器: Llama-3风格离线token估计 {before}->{after}; 已保留三句强制输出和关键证据。"
