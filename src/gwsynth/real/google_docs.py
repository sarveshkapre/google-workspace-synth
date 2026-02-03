from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DocSection:
    heading: str
    paragraphs: tuple[str, ...]
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class DocContent:
    title: str
    summary: str
    sections: tuple[DocSection, ...]
    metadata: tuple[str, ...]


def apply_doc_content(
    docs_service: Any,
    *,
    document_id: str,
    content: DocContent,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    requests = build_doc_requests(content)
    docs_service.documents().batchUpdate(
        documentId=document_id, body={"requests": requests}
    ).execute()


def build_doc_requests(content: DocContent) -> list[dict[str, Any]]:
    lines: list[_Line] = []
    lines.append(_Line(text=content.title, style="TITLE"))
    lines.append(_Line(text=content.summary, style=None))
    lines.append(_Line(text="", style=None))
    for section in content.sections:
        lines.append(_Line(text=section.heading, style="HEADING_2"))
        for paragraph in section.paragraphs:
            lines.append(_Line(text=paragraph, style=None))
        if section.bullets:
            for bullet in section.bullets:
                lines.append(_Line(text=bullet, style=None, bullet=True))
        lines.append(_Line(text="", style=None))
    for meta in content.metadata:
        lines.append(_Line(text=meta, style=None))

    text, line_ranges, bullet_ranges = _render_lines(lines)
    requests: list[dict[str, Any]] = [
        {"insertText": {"location": {"index": 1}, "text": text}},
    ]
    for line in line_ranges:
        if not line.style:
            continue
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": line.start, "endIndex": line.end},
                    "paragraphStyle": {"namedStyleType": line.style},
                    "fields": "namedStyleType",
                }
            }
        )
    for bullet_range in bullet_ranges:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": bullet_range.start,
                        "endIndex": bullet_range.end,
                    },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )
    return requests


@dataclass(frozen=True)
class _Line:
    text: str
    style: str | None
    bullet: bool = False


@dataclass(frozen=True)
class _Range:
    start: int
    end: int
    style: str | None = None


def _render_lines(lines: Iterable[_Line]) -> tuple[str, list[_Range], list[_Range]]:
    cursor = 1
    text_parts: list[str] = []
    line_ranges: list[_Range] = []
    bullet_ranges: list[_Range] = []
    current_bullet_start: int | None = None
    current_bullet_end: int | None = None
    for line in lines:
        line_start = cursor
        text_parts.append(line.text + "\n")
        cursor += len(line.text) + 1
        line_end = cursor - 1
        line_ranges.append(_Range(start=line_start, end=line_end, style=line.style))
        if line.bullet:
            if current_bullet_start is None:
                current_bullet_start = line_start
            current_bullet_end = line_end
        else:
            if current_bullet_start is not None and current_bullet_end is not None:
                bullet_ranges.append(_Range(start=current_bullet_start, end=current_bullet_end))
            current_bullet_start = None
            current_bullet_end = None
    if current_bullet_start is not None and current_bullet_end is not None:
        bullet_ranges.append(_Range(start=current_bullet_start, end=current_bullet_end))
    return "".join(text_parts), line_ranges, bullet_ranges
