"""按数据来源划分的只读适配器（上层 DataFetcher 不暴露这些类型）。"""

from shared.datafetcher.sources.entities import EntitySource
from shared.datafetcher.sources.knowledge import KnowledgeSource
from shared.datafetcher.sources.vocab import VocabSource

__all__ = ["EntitySource", "KnowledgeSource", "VocabSource"]
