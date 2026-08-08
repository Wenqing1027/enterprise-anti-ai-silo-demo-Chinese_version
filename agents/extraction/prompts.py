"""Extraction System Prompt 底座与拼接。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.extraction.skill_schema import (
    EXTRACTION_PROMPT_SECTION_ORDER,
    ExtractionSkillConfig,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "docs" / "extraction" / "schemas"
TAG_VOCAB_PATH = ROOT / "data" / "vocab" / "tag_vocabulary.json"

BASE_SYSTEM = """你是虚构企业「青枢出行（Qingshu Mobility）」内部的 Extraction Agent（结构化抽取）。
架构原则：多部门共用同一套数据字段与标签字典；你当前只执行本 Skill 的抽取任务，不要扮演客服安抚、续费触达或万能企业大脑。

硬规则：
1. 你的唯一任务是：阅读输入文本，按给定 JSON Schema 抽出结构化字段。
2. 只输出一个 JSON 对象；不要输出 Markdown、解释、前言、代码篱笆。
3. 禁止臆造主数据：文本未出现的 customer_id / vin 必须输出 null，并设 needs_human_review=true。
4. 合成 VIN 必须以 QS0 开头；无法确认时输出 null，禁止编造 VIN。
5. 枚举字段必须落在 Schema 允许值内；不确定时：
   - ticket_type → other
   - fault_category → other
   - sentiment → neu（但若出现投诉/曝光/安全隐患等强负面，必须 neg）
6. tag_id 必须来自本轮提供的标签字典；禁止自造 TAG。
7. 阻断类标签（TAG-投诉未结、TAG-舆情风险、TAG-安全隐患）只要原文有证据，主标签或 secondary_tag_ids 必须命中其一，漏标不可接受。
8. 跨部门协作靠结构化产出写入共享层（AIOutput）；你不负责多步查库对话（那是 ReAct）。
9. 使用简体中文填写文本类字段（desc_text / sample_voice / problem_theme 等）。
10. 安全边界以代码闸门为准；不得尝试绕过校验。
"""

DEFAULT_TAG_DICTIONARY = """【标签字典 · 允许 tag_id】
产品：TAG-续航短, TAG-动力弱, TAG-异响, TAG-刹车, TAG-充电慢, TAG-控制器, TAG-电池鼓包, TAG-仪表黑屏
服务：TAG-三包争议, TAG-上门慢, TAG-态度差, TAG-配件缺货
App：TAG-绑车失败, TAG-定位飘, TAG-续费入口, TAG-推送骚扰
渠道：TAG-非专卖, TAG-VI违规, TAG-压货
风险/阻断：TAG-投诉未结, TAG-舆情风险, TAG-安全隐患

【其他枚举】
ticket_type: fault | consult | complaint | other
fault_category: battery | motor | brake | controller | charging | dashboard | frame | lighting | tire | other
ticket_channel: 400 | App | 电商 | 门店 | community
ticket_status: 草案默认 open
sentiment: pos | neu | neg
tag_domain: product | service | app | channel | risk
severity_risk_level: P0 | P1 | P2 | null
clue_confidence: weak | medium
"""

TICKET_EXTRACT_RULES = """【抽取细则】
1. desc_text：保留用户问题摘要，≤1000 字；脱敏手机号。
2. 若输入或已知键含 CUS-数字 / QS0…VIN，写入对应字段；否则 null。
3. 同时含故障与投诉意图时，ticket_type 优先 complaint，is_complaint=true。
4. fault 类工单应填 fault_category；consult 可填 consult_category 短标签。
5. tag_id 选最能概括主诉的一个；阻断证据存在时不得漏阻断标签（主标或可配合 secondary）。
6. confidence：把握高 ≥0.8；一般 0.5–0.7；缺 ID 或多义句 ≤0.5 且 needs_human_review=true。
7. ticket_channel：优先用已知 channel；否则从文本推断，默认 400。
"""

VOC_EXTRACT_RULES = """【抽取细则】
1. sample_voice：脱敏后的代表性原声，≤500 字；尽量保留用户原词。
2. problem_theme：短主题名，与主标签语义一致。
3. sentiment_score：pos≈0.3–1.0，neu≈-0.2–0.2，neg≈-1.0–-0.3。
4. 出现曝光/媒体/12315/报警 → 考虑 TAG-舆情风险 与 severity_risk_level=P0|P1。
5. 起火/冒烟/自燃/漏电 → TAG-安全隐患，severity_risk_level 至少 P1。
6. 多次投诉/一直没处理/超过7天未结 → TAG-投诉未结（阻断）。
7. clue_confidence：证据充分 medium；隐喻/单句含糊 weak，且 needs_human_review=true。
8. secondary_tag_ids 最多 3 个，且均须在字典内；不要重复主 tag_id。
9. tag_domain 必须与所选 tag_id 在字典中的域一致。
"""

OUTPUT_DISCIPLINE = """【输出纪律】
- 只输出一个 JSON 对象，键集合必须符合本轮 Schema。
- 不要包裹 ```json 代码块。
- 不要追加第二段说明文字。
"""


def load_schema_text(schema_id: str) -> str:
    path = SCHEMA_DIR / f"{schema_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"schema file missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def load_leaf_tag_ids() -> list[str]:
    if not TAG_VOCAB_PATH.is_file():
        return []
    raw = json.loads(TAG_VOCAB_PATH.read_text(encoding="utf-8"))
    tags = raw.get("tags") if isinstance(raw, dict) else raw
    out: list[str] = []
    for row in tags or []:
        tid = str(row.get("tag_id") or "")
        if not tid or tid.startswith("TAG-ROOT-"):
            continue
        out.append(tid)
    return out


def build_system_prompt(skill: ExtractionSkillConfig) -> str:
    schema_json = load_schema_text(skill.payload_schema)
    dictionary = DEFAULT_TAG_DICTIONARY.strip()
    if skill.dictionary_extra.strip():
        dictionary = dictionary + "\n" + skill.dictionary_extra.strip()
    leaf = load_leaf_tag_ids()
    if leaf:
        dictionary += "\n【字典叶标签完整列表】\n" + ", ".join(leaf)

    if skill.extract_rules.strip():
        extract_rules = "【抽取细则】\n" + skill.extract_rules.strip()
    elif skill.payload_schema == "voc_entities_v1":
        extract_rules = VOC_EXTRACT_RULES.strip()
    else:
        extract_rules = TICKET_EXTRACT_RULES.strip()

    security = (
        "【安全边界】\n"
        "- 禁止真实客户 PII、真实品牌名、API Key。\n"
        "- 禁止承诺赔付/必修好（本 Agent 不输出安抚话术）。\n"
        "- VIN 非法则 null；不得「补全」编造。"
    )
    if skill.security.prompt_forbid_extra.strip():
        security += "\n- " + skill.security.prompt_forbid_extra.strip()

    sections: dict[str, str] = {
        "A_base": BASE_SYSTEM.strip(),
        "B_schema": "【目标 Schema · " + skill.payload_schema + "】\n" + schema_json,
        "C_goal": (
            "【任务目标】\n"
            f"- 目标：{skill.goal}\n"
            f"- 成功标准：{skill.success_hint or '通过 Schema 校验'}\n"
            f"- 部门语气：{skill.tone.label}；{skill.tone.style}\n"
            f"- 禁用：{skill.tone.forbid or '无'}"
        ),
        "D_dictionary": dictionary,
        "E_extract_rules": extract_rules,
        "F_output": OUTPUT_DISCIPLINE.strip(),
        "G_security": security,
    }
    parts: list[str] = []
    for key in EXTRACTION_PROMPT_SECTION_ORDER:
        text = sections.get(key, "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def build_user_message(
    skill_id: str,
    schema_id: str,
    text: str,
    *,
    known: dict[str, Any] | None = None,
) -> str:
    known = known or {}
    kv_parts = []
    for k in ("customer_id", "vin", "channel"):
        v = known.get(k)
        if v not in (None, ""):
            kv_parts.append(f"{k}={v}")
    known_line = "; ".join(kv_parts) if kv_parts else "none"
    return "\n".join(
        [
            f"【Skill】{skill_id}",
            f"【SchemaID】{schema_id}",
            "【输入文本】",
            text,
            f"【已知键】{known_line}",
            "请只输出一个符合 Schema 的 JSON 对象。",
        ]
    )


def build_retry_message(error: str, previous_raw: str) -> str:
    return "\n".join(
        [
            "【校验失败 · 请修正后只输出 JSON】",
            error.strip(),
            "上一轮输出（供对照，勿原样重复错误）：",
            previous_raw[:2000],
        ]
    )
