"""LLM 客户端（DeepSeek / OpenAI 兼容）。"""

from shared.llm.client import DeepSeekClient, LLMConfig, get_llm_client

__all__ = ["DeepSeekClient", "LLMConfig", "get_llm_client"]
