"""DataFetcher 对外返回的补充类型（仍属统一模型层，不含数据源信息）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import KbDomain


class KbChunk(QingshuModel):
    """知识库检索命中块（对上层只暴露内容与分域，不暴露文件 IO 细节）。"""

    kb_domain: KbDomain | str | None = Field(default=None, description="知识库域")
    kb_doc_id: str | None = Field(default=None, description="文档ID")
    kb_chunk_id: str | None = Field(default=None, description="片段ID")
    title: str | None = Field(default=None, description="文档标题")
    content: str | None = Field(default=None, description="文本内容或片段")
    kb_score: float | None = Field(default=None, description="检索相关分 0-1")
