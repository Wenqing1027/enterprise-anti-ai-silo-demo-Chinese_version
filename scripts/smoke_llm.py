"""DeepSeek 连通性冒烟：确认 .env + base_url 可正常返回。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from shared.llm.client import DEFAULT_BASE_URL, load_llm_config, get_llm_client


def main() -> None:
    cfg = load_llm_config()
    print("env_file", ROOT / ".env", "exists=", (ROOT / ".env").is_file())
    print("model", cfg.model)
    print("base_url", cfg.base_url)
    print("default_base_url", DEFAULT_BASE_URL)
    print("api_key_prefix", cfg.api_key[:7] + "…" if cfg.api_key else "(empty)")
    assert cfg.base_url.rstrip("/").endswith("/v1"), f"base_url 应含 /v1，当前={cfg.base_url}"
    assert cfg.api_key, "DEEPSEEK_API_KEY 为空"

    client = get_llm_client()
    resp = client.chat(
        messages=[
            {"role": "system", "content": "只回复两个字：正常"},
            {"role": "user", "content": "ping"},
        ],
        temperature=0,
    )
    text = (resp.choices[0].message.content or "").strip()
    print("response", text)
    print("OK llm smoke")


if __name__ == "__main__":
    main()
