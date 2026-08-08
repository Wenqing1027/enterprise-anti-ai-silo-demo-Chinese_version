"""RAG System Prompt 底座与拼接。"""

from __future__ import annotations

from agents.rag.skill_schema import RAG_PROMPT_SECTION_ORDER, RagSkillConfig

BASE_SYSTEM = """你是虚构企业「青枢出行（Qingshu Mobility）」内部的 RAG Agent（检索增强生成）。
架构原则：多部门共用同一套知识库检索手脚（DataFetcher / search_kb）；你当前只执行本 Skill 的知识问答，不要扮演万能企业大脑，也不要假装已查主数据（除非上下文明确给出）。

硬规则：
1. 只根据「检索片段」回答；片段未覆盖的内容必须明确说「知识库未覆盖 / 依据不足」。
2. 禁止编造零件号、返利点位、制度条款、VIN、手机号。
3. 终答必须列出引用的 kb_chunk_id（若有命中）；无命中时写「引用：无」。
4. 合成政策/手册仅供 Demo，可注明「青枢出行合成口径」。
5. 跨部门协作靠共享产出与统一标签；本环不做 Multi-Agent 互聊。
6. 使用简体中文。
"""

RETRIEVE_RULES = """【检索与引用纪律】
1. 下方「检索片段」已由系统按本 Skill 的 kb_domains_allow 检得；你不得声称检索了其他域。
2. 优先综合高分片段；冲突时指出冲突并建议人工复核。
3. 引用格式：在文末用列表写出 kb_chunk_id 与文档标题（至少命中条数或写「无」）。
4. 不要输出与问题无关的长篇复述；给可执行步骤或口径要点。
"""


def build_system_prompt(skill: RagSkillConfig) -> str:
    sections: dict[str, str] = {
        "A_base": BASE_SYSTEM.strip(),
        "B_tone": (
            f"【语气】{skill.tone.label}\n"
            f"风格：{skill.tone.style}\n"
            f"禁止：{skill.tone.forbid or '（无额外）'}"
        ),
        "C_goal": f"【本 Skill 目标】{skill.goal}\n成功提示：{skill.success_hint or '（见输出格式）'}",
        "C2_system_extra": (skill.system_extra or "").strip(),
        "D_retrieve_rules": (
            RETRIEVE_RULES
            + f"\n允许知识域：{', '.join(skill.kb_domains_allow)}"
            + f"\ntop_k={skill.top_k} · max_context_chars={skill.max_context_chars}"
            + f"\ncite_required={skill.cite_required} · allow_no_hit={skill.allow_no_hit_answer}"
        ),
        "E_output": (skill.output_format or "按默认：复述→建议→引用→下一步").strip(),
        "F_security": (
            "【安全】"
            + (skill.security.prompt_forbid_extra or "遵守企业 Demo 合规：无真实客户 PII。")
            + f"\n域闸：{', '.join(skill.security.kb_domains_allow or skill.kb_domains_allow)}"
        ),
    }
    parts: list[str] = []
    for key in RAG_PROMPT_SECTION_ORDER:
        text = (sections.get(key) or "").strip()
        if not text:
            continue
        parts.append(text)
    return "\n\n".join(parts)


def format_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return "【检索片段】\n（无命中）"
    lines = ["【检索片段】"]
    for i, ch in enumerate(chunks, start=1):
        lines.append(
            f"--- [{i}] kb_chunk_id={ch.get('kb_chunk_id')} "
            f"score={ch.get('kb_score')} title={ch.get('title')} ---\n"
            f"{ch.get('content') or ''}"
        )
    return "\n\n".join(lines)


def build_user_message(query: str, context_block: str) -> str:
    return (
        f"【用户问题】\n{query.strip()}\n\n"
        f"{context_block}\n\n"
        "请仅依据检索片段作答，并在文末给出引用列表。"
    )
