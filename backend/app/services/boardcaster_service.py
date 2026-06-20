from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.models import Document
from app.tools.document_processing import chunk_text, extract_keywords


CS_KEYWORDS = (
    "计算机",
    "软件",
    "人工智能",
    "智能",
    "信息科学",
    "交叉信息",
    "电子信息",
    "网络",
    "网络空间",
    "网络安全",
    "数据",
    "数据科学",
    "大数据",
    "电子",
    "自动化",
    "机器人",
    "网安",
    "算法",
    "computer",
    "software",
    "artificial intelligence",
    "machine learning",
    "data",
    "network",
    "cyber",
    "ai",
    "systems",
    "retrieval",
)


@dataclass(frozen=True)
class BoardCasterImportResult:
    imported: list[Document]
    skipped_duplicates: int


def load_boardcaster_documents(
    years: list[str] | None = None,
    max_items: int = 160,
    only_cs_related: bool = True,
) -> list[Document]:
    data = _load_boardcaster_data()
    sections = years or ["camp2026", "camp2025", "yutuimian2024"]
    seen: set[tuple[str, str, str]] = set()
    documents: list[Document] = []

    for section in sections:
        for entry in data.get(section, []):
            if only_cs_related and not _is_cs_related(entry):
                continue
            key = (
                str(entry.get("name", "")).strip(),
                str(entry.get("institute", "")).strip(),
                str(entry.get("website", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            documents.append(_entry_to_document(section, entry))
            if len(documents) >= max_items:
                return documents
    return documents


def import_boardcaster_documents(
    existing_documents: list[Document],
    years: list[str] | None = None,
    max_items: int = 160,
    only_cs_related: bool = True,
) -> BoardCasterImportResult:
    existing_keys = {
        (
            document.title.strip().lower(),
            document.source.strip().lower(),
        )
        for document in existing_documents
    }
    imported: list[Document] = []
    skipped_duplicates = 0

    for document in load_boardcaster_documents(years=years, max_items=max_items, only_cs_related=only_cs_related):
        key = (document.title.strip().lower(), document.source.strip().lower())
        if key in existing_keys:
            skipped_duplicates += 1
            continue
        existing_keys.add(key)
        imported.append(document)

    return BoardCasterImportResult(imported=imported, skipped_duplicates=skipped_duplicates)


def _load_boardcaster_data() -> dict[str, list[dict[str, object]]]:
    path = _resolve_boardcaster_path()
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_boardcaster_path() -> Path:
    settings = get_settings()
    configured = settings.boardcaster_data_path.strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return path

    project_root = Path(__file__).resolve().parents[3]
    candidates = (
        project_root / ".tmp" / "BoardCaster" / "data.json",
        project_root.parent / "BoardCaster" / "data.json",
    )
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("BoardCaster data.json not found. Clone CS-BAOYAN/BoardCaster first.")


def _is_cs_related(entry: dict[str, object]) -> bool:
    haystack = " ".join(
        str(entry.get(field, "")).lower()
        for field in ("name", "institute", "description", "website")
    )
    tags = " ".join(str(item).lower() for item in entry.get("tags", []) if item)
    combined = f"{haystack} {tags}"
    return any(keyword in combined for keyword in CS_KEYWORDS)


def _entry_to_document(section: str, entry: dict[str, object]) -> Document:
    school = str(entry.get("name", "")).strip()
    institute = str(entry.get("institute", "")).strip()
    description = str(entry.get("description", "")).strip()
    deadline = str(entry.get("deadline", "")).strip()
    website = str(entry.get("website", "")).strip()
    province = str(entry.get("province", "")).strip()
    tags = [str(item).strip() for item in entry.get("tags", []) if str(item).strip()]
    title = " / ".join(part for part in (school, institute, section) if part)
    content = "\n".join(
        part
        for part in (
            f"学校：{school}" if school else "",
            f"院系/项目：{institute}" if institute else "",
            f"类型：{section}",
            f"描述：{description}" if description and description != "_No response_" else "",
            f"截止时间：{deadline}" if deadline else "",
            f"地区：{province}" if province else "",
            f"标签：{', '.join(tags)}" if tags else "",
            f"来源链接：{website}" if website else "",
            "说明：本条记录来自 BoardCaster 结构化汇总，适合作为选校线索，正式报名要求仍需回到原通知核对。",
        )
        if part
    )
    extracted = {
        "school_or_unit": school,
        "project_name": institute or title,
        "deadline": deadline,
        "materials": [],
        "exam_format": [],
        "important_dates": [deadline] if deadline and deadline != "暂无" else [],
        "institute": institute,
        "website": website,
        "tags": tags,
        "province": province,
        "source_dataset": "BoardCaster",
        "source_section": section,
    }
    document = Document(
        title=title,
        doc_type="notice",
        content=content,
        source=website or "boardcaster",
        source_type="text",
        extracted=extracted,
        analysis={
            "status": "completed",
            "mode": "boardcaster_import",
            "summary": description if description and description != "_No response_" else "BoardCaster 收录了该项目的结构化招募信息。",
            "source_dataset": "BoardCaster",
            "source_section": section,
            "original_website": website,
            "tags": tags,
            "note": "该条目是聚合索引，不等于原始通知全文。",
        },
    )
    document.keywords = extract_keywords(f"{title} {content}")
    document.chunks = chunk_text(document.id, document.content)
    return document
