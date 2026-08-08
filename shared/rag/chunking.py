"""RAG 文档切块（纯函数）：Markdown 先按 ## 再窗切。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


STRATEGY_ID = "heading_then_window_v1"

DEFAULT_MAX_CHUNK_CHARS = 520
DEFAULT_MIN_CHUNK_CHARS = 48
DEFAULT_OVERLAP_CHARS = 64

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ChunkParams:
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS
    min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS
    overlap_chars: int = DEFAULT_OVERLAP_CHARS


@dataclass
class ChunkRecord:
    kb_chunk_id: str
    kb_doc_id: str
    kb_domain: str
    title: str
    section_heading: str
    section_path: str
    content: str
    char_count: int
    char_start: int
    char_end: int
    source_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_h1(text: str, fallback: str) -> str:
    m = _H1_RE.search(text)
    if not m:
        return fallback
    return m.group(1).strip()


def _strip_h1(text: str) -> str:
    return _H1_RE.sub("", text, count=1).lstrip("\n")


def _split_h2_sections(body: str) -> list[tuple[str, str, int]]:
    """返回 (section_heading, section_body, char_start_in_body)。"""
    matches = list(_H2_RE.finditer(body))
    if not matches:
        return [("", body.strip(), 0)] if body.strip() else []

    sections: list[tuple[str, str, int]] = []
    # preface before first ##
    preface = body[: matches[0].start()].strip()
    if preface:
        sections.append(("", preface, 0))

    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        # include heading line offset as start of section block
        sections.append((heading, content, m.start()))
    return sections


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def _window_split(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    overlap = max(0, min(overlap, max_chars // 2))
    step = max(1, max_chars - overlap)
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        piece = text[i : i + max_chars].strip()
        if piece:
            out.append(piece)
        if i + max_chars >= n:
            break
        i += step
    return out


def _chunk_section_body(
    body: str,
    *,
    params: ChunkParams,
) -> list[str]:
    body = body.strip()
    if not body:
        return []
    if len(body) <= params.max_chunk_chars:
        return [body]

    pieces: list[str] = []
    buf = ""
    for para in _split_paragraphs(body):
        if len(para) > params.max_chunk_chars:
            if buf:
                pieces.append(buf.strip())
                buf = ""
            pieces.extend(
                _window_split(para, params.max_chunk_chars, params.overlap_chars)
            )
            continue
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= params.max_chunk_chars:
            buf = candidate
        else:
            if buf:
                pieces.append(buf.strip())
            buf = para
    if buf:
        pieces.append(buf.strip())
    return pieces


def _merge_short(pieces: list[tuple[str, str]], min_chars: int, max_chars: int) -> list[tuple[str, str]]:
    """pieces: (section_heading, text). Merge consecutive short ones under same heading when possible."""
    if not pieces:
        return []
    out: list[tuple[str, str]] = []
    for heading, text in pieces:
        if (
            out
            and len(text) < min_chars
            and out[-1][0] == heading
            and len(out[-1][1]) + 2 + len(text) <= max_chars
        ):
            prev_h, prev_t = out[-1]
            out[-1] = (prev_h, f"{prev_t}\n\n{text}".strip())
        elif (
            out
            and len(out[-1][1]) < min_chars
            and len(out[-1][1]) + 2 + len(text) <= max_chars
        ):
            # merge short previous into current; keep current heading if richer
            prev_h, prev_t = out.pop()
            use_h = heading or prev_h
            out.append((use_h, f"{prev_t}\n\n{text}".strip()))
        else:
            out.append((heading, text))
    return out


def _format_content(doc_title: str, section_heading: str, body: str) -> str:
    path = f"{doc_title} › {section_heading}" if section_heading else doc_title
    return f"【{path}】\n{body.strip()}".strip()


def chunk_markdown_document(
    *,
    text: str,
    kb_doc_id: str,
    kb_domain: str,
    title: str,
    source_path: str,
    params: ChunkParams | None = None,
) -> list[ChunkRecord]:
    """将单篇 Markdown 切成 ChunkRecord 列表。"""
    params = params or ChunkParams()
    doc_title = _extract_h1(text, title)
    body = _strip_h1(text)
    # map body offsets → full text: h1 may shift; approximate via find
    body_offset = text.find(body) if body else 0
    if body_offset < 0:
        body_offset = 0

    raw_sections = _split_h2_sections(body)
    flat: list[tuple[str, str, int, int]] = []  # heading, piece, start, end in full text

    for section_heading, section_body, sec_start_in_body in raw_sections:
        abs_sec_start = body_offset + sec_start_in_body
        for piece in _chunk_section_body(section_body, params=params):
            # best-effort locate piece within section
            rel = section_body.find(piece[: min(40, len(piece))])
            start = abs_sec_start + (rel if rel >= 0 else 0)
            end = start + len(piece)
            flat.append((section_heading, piece, start, end))

    merged = _merge_short(
        [(h, t) for h, t, _, _ in flat],
        params.min_chunk_chars,
        params.max_chunk_chars,
    )
    # rebuild offsets loosely from merged order
    records: list[ChunkRecord] = []
    cursor = body_offset
    for i, (section_heading, piece) in enumerate(merged, start=1):
        content = _format_content(doc_title, section_heading, piece)
        # prefer original offset if same piece still in flat
        start = cursor
        end = start + len(piece)
        for h0, t0, s0, e0 in flat:
            if t0 == piece and h0 == section_heading:
                start, end = s0, e0
                break
        cursor = end
        records.append(
            ChunkRecord(
                kb_chunk_id=f"{kb_doc_id}#c{i:04d}",
                kb_doc_id=kb_doc_id,
                kb_domain=kb_domain,
                title=title,
                section_heading=section_heading,
                section_path=(
                    f"{doc_title} › {section_heading}" if section_heading else doc_title
                ),
                content=content,
                char_count=len(content),
                char_start=max(0, start),
                char_end=max(0, end),
                source_path=source_path,
            )
        )
    return records


def build_chunks_payload(
    *,
    documents: list[dict[str, Any]],
    params: ChunkParams | None = None,
    source_index: str = "knowledge/index.json",
) -> dict[str, Any]:
    """
    documents 项需含：kb_doc_id, kb_domain, title, path|source_path, content
    """
    params = params or ChunkParams()
    all_chunks: list[ChunkRecord] = []
    for doc in documents:
        source_path = doc.get("source_path") or doc.get("path") or ""
        all_chunks.extend(
            chunk_markdown_document(
                text=doc["content"],
                kb_doc_id=doc["kb_doc_id"],
                kb_domain=doc["kb_domain"],
                title=doc.get("title") or doc["kb_doc_id"],
                source_path=source_path,
                params=params,
            )
        )

    by_domain: dict[str, int] = {}
    for c in all_chunks:
        by_domain[c.kb_domain] = by_domain.get(c.kb_domain, 0) + 1

    return {
        "version": "v1",
        "strategy_id": STRATEGY_ID,
        "params": {
            "max_chunk_chars": params.max_chunk_chars,
            "min_chunk_chars": params.min_chunk_chars,
            "overlap_chars": params.overlap_chars,
        },
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_index": source_index,
        "stats": {
            "docs": len(documents),
            "chunks": len(all_chunks),
            "by_domain": dict(sorted(by_domain.items())),
        },
        "chunks": [c.to_dict() for c in all_chunks],
    }
