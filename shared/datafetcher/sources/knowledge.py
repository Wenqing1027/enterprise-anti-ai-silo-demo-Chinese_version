"""来源 B：非结构化知识库 Markdown + 切块 TF-IDF 索引。只读。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shared.rag.tfidf_index import TfidfIndex


@dataclass(frozen=True)
class _Doc:
    kb_domain: str
    kb_doc_id: str
    title: str
    path: str
    content: str


@dataclass(frozen=True)
class _ChunkHit:
    kb_domain: str
    kb_doc_id: str
    kb_chunk_id: str
    title: str
    section_path: str
    content: str
    score: float
    source_path: str


class KnowledgeSource:
    """从 data/knowledge/** 加载长文本；优先用 tfidf_index.json 做块级检索。"""

    def __init__(self, knowledge_dir: Path) -> None:
        self._dir = knowledge_dir
        self._docs: list[_Doc] | None = None
        self._index: TfidfIndex | None | bool = None  # False = missing

    def reload(self) -> None:
        self._docs = None
        self._index = None

    def _ensure(self) -> list[_Doc]:
        if self._docs is not None:
            return self._docs
        docs: list[_Doc] = []
        index_path = self._dir / "index.json"
        if index_path.exists():
            meta = json.loads(index_path.read_text(encoding="utf-8"))
            for item in meta.get("documents", []):
                rel = item.get("path", "")
                # path like knowledge/repair/xxx.md → relative to data/
                file_path = self._dir.parent / rel if rel.startswith("knowledge/") else self._dir / Path(rel).name
                if not file_path.exists():
                    # fallback: domain/title
                    domain = item.get("kb_domain", "")
                    title = item.get("title", "")
                    file_path = self._dir / domain / f"{title}.md"
                if not file_path.exists():
                    continue
                content = file_path.read_text(encoding="utf-8")
                docs.append(
                    _Doc(
                        kb_domain=item.get("kb_domain") or file_path.parent.name,
                        kb_doc_id=item.get("kb_doc_id") or file_path.stem,
                        title=item.get("title") or file_path.stem,
                        path=str(file_path.relative_to(self._dir.parent)),
                        content=content,
                    )
                )
        else:
            for md in sorted(self._dir.rglob("*.md")):
                docs.append(
                    _Doc(
                        kb_domain=md.parent.name,
                        kb_doc_id=f"{md.parent.name}__{md.stem}",
                        title=md.stem,
                        path=str(md.relative_to(self._dir.parent)),
                        content=md.read_text(encoding="utf-8"),
                    )
                )
        self._docs = docs
        return docs

    def _ensure_index(self) -> TfidfIndex | None:
        if self._index is False:
            return None
        if isinstance(self._index, TfidfIndex):
            return self._index
        path = self._dir / "tfidf_index.json"
        if not path.exists():
            self._index = False
            return None
        self._index = TfidfIndex.load(path)
        return self._index

    def list_docs(self, domain: str | None = None) -> list[_Doc]:
        docs = self._ensure()
        if domain:
            return [d for d in docs if d.kb_domain == domain]
        return list(docs)

    def get_doc(self, kb_doc_id: str) -> _Doc | None:
        for d in self._ensure():
            if d.kb_doc_id == kb_doc_id:
                return d
        return None

    def list_domains(self) -> list[str]:
        idx = self._ensure_index()
        if idx is not None:
            return idx.list_domains()
        return sorted({d.kb_domain for d in self._ensure()})

    def get_chunk(self, kb_chunk_id: str) -> _ChunkHit | None:
        idx = self._ensure_index()
        if idx is None:
            return None
        ch = idx.get_chunk(kb_chunk_id)
        if ch is None:
            return None
        return _ChunkHit(
            kb_domain=ch.kb_domain,
            kb_doc_id=ch.kb_doc_id,
            kb_chunk_id=ch.kb_chunk_id,
            title=ch.title,
            section_path=ch.section_path,
            content=ch.content,
            score=1.0,
            source_path=ch.source_path,
        )

    def search(
        self,
        query: str,
        *,
        domain: str | None = None,
        top_k: int = 5,
    ) -> list[tuple[_Doc, float, str]]:
        """兼容旧接口：返回 (doc, score, snippet)。优先 TF-IDF 块检索再映射到文档。"""
        chunk_hits = self.search_chunks(query, domain=domain, top_k=top_k)
        if chunk_hits:
            out: list[tuple[_Doc, float, str]] = []
            seen_docs: set[str] = set()
            for hit in chunk_hits:
                if hit.kb_doc_id in seen_docs:
                    continue
                doc = self.get_doc(hit.kb_doc_id)
                if doc is None:
                    # synthesize lightweight doc from chunk
                    doc = _Doc(
                        kb_domain=hit.kb_domain,
                        kb_doc_id=hit.kb_doc_id,
                        title=hit.title,
                        path=hit.source_path,
                        content=hit.content,
                    )
                seen_docs.add(hit.kb_doc_id)
                out.append((doc, hit.score, hit.content[:240]))
            return out[:top_k]
        return self._keyword_search_docs(query, domain=domain, top_k=top_k)

    def search_chunks(
        self,
        query: str,
        *,
        domain: str | None = None,
        top_k: int = 5,
    ) -> list[_ChunkHit]:
        """块级检索（RAG 主路径）。有索引用 TF-IDF，否则回退关键词扫 chunks.json。"""
        idx = self._ensure_index()
        if idx is not None:
            hits = idx.search(query, domain=domain, top_k=top_k)
            return [
                _ChunkHit(
                    kb_domain=h.chunk.kb_domain,
                    kb_doc_id=h.chunk.kb_doc_id,
                    kb_chunk_id=h.chunk.kb_chunk_id,
                    title=h.chunk.title,
                    section_path=h.chunk.section_path,
                    content=h.chunk.content,
                    score=h.score,
                    source_path=h.chunk.source_path,
                )
                for h in hits
            ]
        return self._keyword_search_chunks(query, domain=domain, top_k=top_k)

    def _load_chunks_json(self) -> list[dict]:
        path = self._dir / "chunks.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("chunks") or [])

    def _keyword_search_chunks(
        self,
        query: str,
        *,
        domain: str | None,
        top_k: int,
    ) -> list[_ChunkHit]:
        q = (query or "").strip().lower()
        if not q:
            return []
        tokens = self._tokenize(q)
        hits: list[_ChunkHit] = []
        for ch in self._load_chunks_json():
            if domain and ch.get("kb_domain") != domain:
                continue
            text = (ch.get("content") or "")
            low = text.lower()
            title_l = (ch.get("title") or "").lower()
            score = 0.0
            if q in low:
                score += 0.45
            if q in title_l:
                score += 0.35
            for tok in tokens:
                if len(tok) < 2:
                    continue
                score += 0.08 * min(3, low.count(tok))
                if tok in title_l:
                    score += 0.12
            if score <= 0:
                continue
            score = min(1.0, score / (1.0 + 0.03 * max(0, len(tokens) - 1)))
            hits.append(
                _ChunkHit(
                    kb_domain=ch.get("kb_domain") or "",
                    kb_doc_id=ch.get("kb_doc_id") or "",
                    kb_chunk_id=ch.get("kb_chunk_id") or "",
                    title=ch.get("title") or "",
                    section_path=ch.get("section_path") or "",
                    content=text,
                    score=round(score, 4),
                    source_path=ch.get("source_path") or "",
                )
            )
        hits.sort(key=lambda x: x.score, reverse=True)
        return hits[:top_k]

    def _keyword_search_docs(
        self,
        query: str,
        *,
        domain: str | None,
        top_k: int,
    ) -> list[tuple[_Doc, float, str]]:
        """简易关键词检索，返回 (doc, score, snippet)。索引缺失时的最终回退。"""
        q = (query or "").strip().lower()
        if not q:
            return []
        tokens = self._tokenize(q)
        hits: list[tuple[_Doc, float, str]] = []
        for doc in self.list_docs(domain):
            text = doc.content
            low = text.lower()
            title_l = doc.title.lower()
            score = 0.0
            if q in low:
                score += 0.45
            if q in title_l:
                score += 0.35
            for tok in tokens:
                if len(tok) < 2:
                    continue
                score += 0.08 * min(3, low.count(tok))
                if tok in title_l:
                    score += 0.12
            if score <= 0:
                continue
            score = min(1.0, score / (1.0 + 0.03 * max(0, len(tokens) - 1)))
            snippet = self._snippet(text, tokens or [q])
            hits.append((doc, round(score, 4), snippet))
        hits.sort(key=lambda x: x[1], reverse=True)
        return hits[:top_k]

    @staticmethod
    def _tokenize(q: str) -> list[str]:
        """中英混合简易分词：空白切分 + 中文二字/三字滑动窗。"""
        from shared.rag.tokenize import tokenize

        return tokenize(q)

    @staticmethod
    def _snippet(text: str, tokens: list[str], width: int = 160) -> str:
        low = text.lower()
        pos = -1
        for tok in tokens:
            pos = low.find(tok.lower())
            if pos >= 0:
                break
        if pos < 0:
            pos = 0
        start = max(0, pos - width // 3)
        end = min(len(text), start + width)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet = snippet + "…"
        return snippet
