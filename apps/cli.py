"""统一入口：control_loop / agent_type + skill + input。

规范名：retrieve | act | extract | plan
历史别名仍可用：rag | react | extraction | planning
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.loops import (  # noqa: E402
    AGENT_TYPE_ALIASES,
    PLATFORM_LOOPS,
    canonicalize,
    to_legacy,
)

# CLI choices：规范名 + 历史名（扩展类型仅占位提示）
AGENT_TYPE_CHOICES = (
    *PLATFORM_LOOPS,
    "rag",
    "react",
    "extraction",
    "planning",
    "rule_llm",
    "vision",
)


def _load_input(raw: str) -> str | dict:
    if not raw:
        return ""
    path = Path(raw)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text)
        return text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Qingshu Mobility · Anti-AI-Silo Demo CLI"
    )
    parser.add_argument(
        "--agent-type",
        choices=AGENT_TYPE_CHOICES,
        required=True,
        help="平台控制环：retrieve|act|extract|plan（别名 rag|react|extraction|planning）",
    )
    parser.add_argument("--skill", required=True, help="skill_id")
    parser.add_argument(
        "--input",
        default="",
        help="输入文本、JSON 字符串，或种子文件路径",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="可选 run_id（默认自动生成）",
    )
    parser.add_argument(
        "--json-out",
        action="store_true",
        help="打印完整 JSON 结果",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Extraction：校验通过后不写 AIOutput（调试用）",
    )
    args = parser.parse_args()

    loop = canonicalize(args.agent_type)
    user_input = _load_input(args.input)

    if loop == "act":
        from agents.react.agent import run_react

        result = run_react(args.skill, user_input, run_id=args.run_id)
        ok = result.ok
        if args.json_out:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        else:
            print(f"run_id={result.run_id}")
            print(f"control_loop=act legacy={to_legacy('act')}")
            print(f"skill={result.skill_id}")
            print(f"stop_reason={result.stop_reason} ok={result.ok}")
            print(f"steps={len(result.steps)} flags={result.success_flags}")
            for s in result.steps:
                mark = "OK" if s.get("ok") else "ERR"
                print(
                    f"  [{mark}] step={s.get('step')} tool={s.get('tool')} "
                    f"{s.get('error_code') or ''}"
                )
            print("--- final_answer ---")
            print(result.final_answer)
        sys.exit(0 if ok else 1)

    if loop == "extract":
        from agents.extraction.agent import run_extraction

        result = run_extraction(
            args.skill,
            user_input,
            run_id=args.run_id,
            write_output=False if args.no_write else None,
        )
        ok = result.ok
        if args.json_out:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        else:
            print(f"run_id={result.run_id}")
            print(f"control_loop=extract legacy={to_legacy('extract')}")
            print(f"skill={result.skill_id}")
            print(f"schema={result.payload_schema}")
            print(f"stop_reason={result.stop_reason} ok={result.ok}")
            print(f"attempts={result.attempts} ai_output_id={result.ai_output_id}")
            if result.warnings:
                print(f"warnings={result.warnings}")
            for s in result.steps:
                mark = "OK" if s.get("ok") else "ERR"
                print(
                    f"  [{mark}] step={s.get('step')} phase={s.get('phase')} "
                    f"{s.get('error') or ''}"
                )
            print("--- payload ---")
            print(json.dumps(result.payload, ensure_ascii=False, indent=2, default=str))
            print("--- final_answer ---")
            print(result.final_answer)
        sys.exit(0 if ok else 1)

    if loop == "retrieve":
        from agents.rag.agent import run_rag

        result = run_rag(args.skill, user_input, run_id=args.run_id)
        ok = result.ok
        if args.json_out:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        else:
            print(f"run_id={result.run_id}")
            print(f"control_loop=retrieve legacy={to_legacy('retrieve')}")
            print(f"skill={result.skill_id}")
            print(f"domains={result.domains}")
            print(f"stop_reason={result.stop_reason} ok={result.ok}")
            print(f"citations={len(result.citations)} contexts={len(result.contexts)}")
            for s in result.steps:
                mark = "OK" if s.get("ok") else "ERR"
                print(
                    f"  [{mark}] step={s.get('step')} phase={s.get('phase')} "
                    f"hits={s.get('hit_count', '')} {s.get('error') or ''}"
                )
            if result.citations:
                print("--- citations ---")
                for c in result.citations:
                    print(f"  - {c.get('kb_chunk_id')} ({c.get('kb_score')})")
            print("--- final_answer ---")
            print(result.final_answer)
        sys.exit(0 if ok else 1)

    if loop == "plan":
        from agents.planning.agent import run_planning

        result = run_planning(args.skill, user_input, run_id=args.run_id)
        ok = result.ok
        if args.json_out:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        else:
            print(f"run_id={result.run_id}")
            print(f"control_loop=plan legacy={to_legacy('plan')}")
            print(f"skill={result.skill_id}")
            print(f"stop_reason={result.stop_reason} ok={result.ok}")
            print(f"gate={result.gate}")
            if result.plan:
                print(f"plan={json.dumps(result.plan, ensure_ascii=False)}")
            for s in result.steps:
                mark = "OK" if s.get("ok") else "ERR"
                print(
                    f"  [{mark}] step={s.get('step')} phase={s.get('phase')} "
                    f"{s.get('name') or ''} {s.get('error') or ''}"
                )
            print("--- final_answer ---")
            print(result.final_answer)
        sys.exit(0 if ok else 1)

    print(
        f"[scaffold] agent_type={args.agent_type} → loop={loop} skill={args.skill} "
        "尚未实现控制环；当前可用：retrieve|act|extract|plan。"
        f" aliases={ {k: v for k, v in AGENT_TYPE_ALIASES.items() if k != v} }"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
