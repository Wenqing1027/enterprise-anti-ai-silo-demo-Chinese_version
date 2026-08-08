"""纯 Python TF-IDF 索引：基于 chunks.json，无 numpy/sklearn 依赖。"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.rag.tokenize import tokenize

INDEX_ID = "tfidf_charngram_v1"
INDEX_VERSION = "v1"


@dataclass(frozen=True)
class IndexParams:
    ngram_ns: tuple[int, ...] = (2, 3)
    title_boost: float = 1.35  # title/section_path 中出现的词加权


@dataclass
class IndexedChunk:
    kb_chunk_id: str
    kb_doc_id: str
    kb_domain: str
    title: str
    section_path: str
    content: str
    source_path: str
    norm: float
    tfidf: dict[int, float]  # term_id -> weight


@dataclass
class SearchHit:
    chunk: IndexedChunk
    score: float


class TfidfIndex:
    """内存中的 TF-IDF 索引；可序列化到 JSON。"""

    def __init__(
        self,
        *,
        vocab: dict[str, int],
        idf: list[float],
        docs: list[IndexedChunk],
        params: IndexParams | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.vocab = vocab
        self.idf = idf
        self.docs = docs
        self.params = params or IndexParams()
        self.meta = meta or {}
        self._term_by_id = {i: t for t, i in vocab.items()}

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    @classmethod
    def build_from_chunks(
        cls,
        chunks: list[dict[str, Any]],
        *,
        params: IndexParams | None = None,
        source_chunks: str = "knowledge/chunks.json",
    ) -> TfidfIndex:
        params = params or IndexParams()
        if not chunks:
            raise ValueError("chunks 为空，无法建索引")

        # 1) DF
        df: dict[str, int] = {}
        tokenized: list[tuple[dict[str, Any], list[str], list[str]]] = []
        for ch in chunks:
            body_tokens = tokenize(ch.get("content") or "", ngram_ns=params.ngram_ns)
            title_text = " ".join(
                [
                    ch.get("title") or "",
                    ch.get("section_path") or "",
                    ch.get("section_heading") or "",
                ]
            )
            title_tokens = tokenize(title_text, ngram_ns=params.ngram_ns)
            # DF 用 body ∪ title 的去重词
            uniq = set(body_tokens) | set(title_tokens)
            for t in uniq:
                df[t] = df.get(t, 0) + 1
            tokenized.append((ch, body_tokens, title_tokens))

        vocab = {t: i for i, t in enumerate(sorted(df.keys()))}
        n_docs = len(chunks)
        idf = [0.0] * len(vocab)
        for t, i in vocab.items():
            # smooth IDF
            idf[i] = math.log((1.0 + n_docs) / (1.0 + df[t])) + 1.0

        docs: list[IndexedChunk] = []
        for ch, body_tokens, title_tokens in tokenized:
            weights: dict[int, float] = {}
            # body TF
            tf_body: dict[str, int] = {}
            for t in body_tokens:
                tf_body[t] = tf_body.get(t, 0) + 1
            for t, c in tf_body.items():
                tid = vocab[t]
                weights[tid] = (1.0 + math.log(c)) * idf[tid]
            # title boost (add, not replace)
            tf_title: dict[str, int] = {}
            for t in title_tokens:
                tf_title[t] = tf_title.get(t, 0) + 1
            for t, c in tf_title.items():
                tid = vocab[t]
                boost = (1.0 + math.log(c)) * idf[tid] * (params.title_boost - 1.0)
                weights[tid] = weights.get(tid, (1.0 + math.log(c)) * idf[tid]) + boost

            norm = math.sqrt(sum(v * v for v in weights.values())) or 1.0
            docs.append(
                IndexedChunk(
                    kb_chunk_id=ch["kb_chunk_id"],
                    kb_doc_id=ch["kb_doc_id"],
                    kb_domain=ch["kb_domain"],
                    title=ch.get("title") or "",
                    section_path=ch.get("section_path") or "",
                    content=ch.get("content") or "",
                    source_path=ch.get("source_path") or "",
                    norm=norm,
                    tfidf=weights,
                )
            )

        by_domain: dict[str, int] = {}
        for d in docs:
            by_domain[d.kb_domain] = by_domain.get(d.kb_domain, 0) + 1

        meta = {
            "version": INDEX_VERSION,
            "index_id": INDEX_ID,
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_chunks": source_chunks,
            "params": {
                "ngram_ns": list(params.ngram_ns),
                "title_boost": params.title_boost,
            },
            "stats": {
                "chunks": len(docs),
                "vocab_size": len(vocab),
                "by_domain": dict(sorted(by_domain.items())),
            },
        }
        return cls(vocab=vocab, idf=idf, docs=docs, params=params, meta=meta)

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        domain: str | None = None,
        top_k: int = 5,
    ) -> list[SearchHit]:
        q_tokens = tokenize(query, ngram_ns=self.params.ngram_ns)
        if not q_tokens:
            return []

        tf: dict[str, int] = {}
        for t in q_tokens:
            tf[t] = tf.get(t, 0) + 1

        q_vec: dict[int, float] = {}
        for t, c in tf.items():
            tid = self.vocab.get(t)
            if tid is None:
                continue
            q_vec[tid] = (1.0 + math.log(c)) * self.idf[tid]
        if not q_vec:
            return []
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        hits: list[SearchHit] = []
        q_lower = (query or "").strip().lower()
        for doc in self.docs:
            if domain and doc.kb_domain != domain:
                continue
            dot = 0.0
            for tid, qw in q_vec.items():
                dw = doc.tfidf.get(tid)
                if dw:
                    dot += qw * dw
            if dot <= 0:
                # 仍允许「整句/标题命中」的短语回退（Demo 友好）
                blob = f"{doc.title}\n{doc.section_path}\n{doc.content}".lower()
                if q_lower and q_lower in blob:
                    hits.append(SearchHit(chunk=doc, score=0.55))
                continue
            score = dot / (q_norm * doc.norm)
            # 短语/标题加权：不改索引，只抬升可演示命中的可读分
            blob = f"{doc.title}\n{doc.section_path}\n{doc.content}".lower()
            if q_lower and q_lower in blob:
                score += 0.28
            elif any(t in doc.title.lower() for t in q_tokens if len(t) >= 2):
                score += 0.12
            hits.append(SearchHit(chunk=doc, score=round(min(1.0, score), 6)))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: max(1, top_k)]

    def get_chunk(self, kb_chunk_id: str) -> IndexedChunk | None:
        for d in self.docs:
            if d.kb_chunk_id == kb_chunk_id:
                return d
        return None

    def list_domains(self) -> list[str]:
        return sorted({d.kb_domain for d in self.docs})

    # ------------------------------------------------------------------
    # serialize
    # ------------------------------------------------------------------

    def to_payload(self) -> dict[str, Any]:
        # sparse tfidf with string keys for JSON stability
        docs_out = []
        for d in self.docs:
            docs_out.append(
                {
                    "kb_chunk_id": d.kb_chunk_id,
                    "kb_doc_id": d.kb_doc_id,
                    "kb_domain": d.kb_domain,
                    "title": d.title,
                    "section_path": d.section_path,
                    "content": d.content,
                    "source_path": d.source_path,
                    "norm": round(d.norm, 6),
                    "tfidf": {str(k): round(v, 6) for k, v in sorted(d.tfidf.items())},
                }
            )
        # vocab as list for compactness: index == position
        vocab_list = [""] * len(self.vocab)
        for t, i in self.vocab.items():
            vocab_list[i] = t
        payload = dict(self.meta)
        payload["vocab"] = vocab_list
        payload["idf"] = [round(x, 6) for x in self.idf]
        payload["docs"] = docs_out
        return payload

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_payload(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> TfidfIndex:
        raw = json.loads(path.read_text(encoding="utf-8"))
        vocab_list: list[str] = raw["vocab"]
        vocab = {t: i for i, t in enumerate(vocab_list)}
        idf = list(raw["idf"])
        params_raw = raw.get("params") or {}
        ngram = tuple(params_raw.get("ngram_ns") or (2, 3))
        params = IndexParams(
            ngram_ns=ngram,  # type: ignore[arg-type]
            title_boost=float(params_raw.get("title_boost") or 1.35),
        )
        docs: list[IndexedChunk] = []
        for d in raw.get("docs") or []:
            tfidf = {int(k): float(v) for k, v in (d.get("tfidf") or {}).items()}
            docs.append(
                IndexedChunk(
                    kb_chunk_id=d["kb_chunk_id"],
                    kb_doc_id=d["kb_doc_id"],
                    kb_domain=d["kb_domain"],
                    title=d.get("title") or "",
                    section_path=d.get("section_path") or "",
                    content=d.get("content") or "",
                    source_path=d.get("source_path") or "",
                    norm=float(d.get("norm") or 1.0),
                    tfidf=tfidf,
                )
            )
        meta = {
            k: raw[k]
            for k in ("version", "index_id", "built_at", "source_chunks", "params", "stats")
            if k in raw
        }
        return cls(vocab=vocab, idf=idf, docs=docs, params=params, meta=meta)


def load_chunks_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"无效 chunks 文件: {path}")
    return chunks


def build_and_save_index(
    chunks_path: Path,
    index_path: Path,
    *,
    params: IndexParams | None = None,
) -> TfidfIndex:
    chunks = load_chunks_file(chunks_path)
    idx = TfidfIndex.build_from_chunks(
        chunks,
        params=params,
        source_chunks="knowledge/chunks.json",
    )
    idx.save(index_path)
    return idx
