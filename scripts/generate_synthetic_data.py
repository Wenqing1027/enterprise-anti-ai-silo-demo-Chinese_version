#!/usr/bin/env python3
"""生成青枢出行 Demo 全合成数据（entities / vocab / knowledge / seeds）。

合规约束：
- 禁止写入任何真实客户、真实 VIN、真实手机号、真实车企内部数据
- VIN 统一以 QS0 前缀标识合成车架号
- 手机号仅存脱敏形态，底层用确定性伪随机生成，非真实号段业务数据
- 可用 `python scripts/generate_synthetic_data.py` 全量重生成
"""

from __future__ import annotations

import hashlib
import json
import random
import string
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 20260801  # 可复现；改种子即换一批假数据

rng = random.Random(SEED)

MODELS = [
    "E40", "E60", "E80", "S7", "S9", "C3", "M1 Pro", "CityGo", "TrailX", "LiteAir",
]
COLORS = ["哑光黑", "星空灰", "极光白", "烈焰红", "薄荷绿", "午夜蓝", "沙丘金"]
CONFIGS = ["铅酸标准", "锂电舒适", "锂电旗舰", "石墨烯续航版"]
BATTERY = [
    ("lithium", "48V24Ah", 80),
    ("lithium", "48V32Ah", 100),
    ("lead_acid", "48V20Ah", 55),
    ("graphene", "48V24Ah", 90),
]
CITIES = [
    ("江苏", "南京", "320115", "江宁区"),
    ("江苏", "苏州", "320505", "虎丘区"),
    ("浙江", "杭州", "330106", "西湖区"),
    ("浙江", "宁波", "330212", "鄞州区"),
    ("安徽", "合肥", "340104", "蜀山区"),
    ("山东", "济南", "370102", "历下区"),
    ("四川", "成都", "510107", "武侯区"),
    ("广东", "广州", "440106", "天河区"),
]
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN = [
    "子轩", "一诺", "思远", "雨桐", "浩然", "欣怡", "嘉怡", "明轩", "诗涵", "俊杰",
    "佳宁", "志强", "婉清", "承泽", "若曦", "天佑", "语嫣", "博文", "清扬", "景行",
]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def fake_name() -> str:
    return rng.choice(SURNAMES) + rng.choice(GIVEN)


def fake_phone_masked() -> str:
    """仅输出脱敏手机号；中间四位恒为 ****，前后为伪随机。"""
    prefix = "1" + rng.choice(list("35789")) + str(rng.randint(0, 9))
    suffix = f"{rng.randint(0, 9999):04d}"
    return f"{prefix}****{suffix}"


def fake_vin(seq: int) -> str:
    """合成 VIN：QS0 + 伪随机，长度 17，绝非真实车企号段。"""
    body = hashlib.sha256(f"qingshu-vin-{SEED}-{seq}".encode()).hexdigest()[:14].upper()
    body = body.replace("O", "A").replace("I", "B")
    vin = ("QS0" + body)[:17]
    assert len(vin) == 17
    return vin


def fake_openid(seq: int) -> str:
    return "qs_oid_" + hashlib.md5(f"openid-{SEED}-{seq}".encode()).hexdigest()[:16]


def fake_oneid(seq: int) -> str:
    return "OID-" + hashlib.md5(f"oneid-{SEED}-{seq}".encode()).hexdigest()[:8]


def daterange_back(days_max: int = 800) -> date:
    return date(2026, 8, 1) - timedelta(days=rng.randint(30, days_max))


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone(timedelta(hours=8))).isoformat()


# ---------------------------------------------------------------------------
# 1) 名词对象分类
# ---------------------------------------------------------------------------

def write_object_catalog() -> None:
    text = """# 名词对象分类（结构化）

> 青枢出行（Qingshu Mobility）· Demo 合成数据目录  
> 口径：按「名词对象 / 实体」分类，不按部门拆库；各部门消费同一套 ID。

## A. 主数据（Master）

| 对象 | 文件 | 说明 |
|------|------|------|
| Org / Region | `entities/orgs.json`, `entities/regions.json` | 组织树与行政区 |
| Dealer | `entities/dealers.json` | 一代经销商 |
| Store | `entities/stores.json` | 门店 |
| Guide | `entities/guides.json` | 导购 |
| Customer | `entities/customers.json` | C 端客户 / 身份 |
| Vehicle | `entities/vehicles.json` | 车辆（VIN 一律 `QS0…` 合成） |
| SKU | `entities/skus.json` | 车型颜色 SKU |
| Competitor | `entities/competitors.json` | 竞品快照（虚构品牌） |

## B. 交易与库存（Transactional）

| 对象 | 文件 | 说明 |
|------|------|------|
| Order | `entities/orders.json` | 提货/订单 |
| Inventory | `entities/inventory.json` | 仓/店库存 |
| Policy | `entities/policies.json` | 返利政策与结算摘要 |
| ColorPlan | `entities/color_plans.json` | 颜色排产计划 |
| SalesMetric | `entities/sales_metrics.json` | 销量/签约达成切片 |
| Health | `entities/dealer_health.json` | 一代经营健康指数 |

## C. 服务与声音（Service / VoC）

| 对象 | 文件 | 说明 |
|------|------|------|
| Ticket | `entities/tickets.json` | 工单 |
| VoC | `entities/voc_feedback.json` | 反馈/调研切片 |
| Telemetry | `entities/telemetry.json` | 车联告警与里程电量 |
| Renewal | `entities/renewals.json` | 车联续费池 |
| UserBehavior | `entities/user_behaviors.json` | App 行为 / RFM |

## D. 零售营销与触达

| 对象 | 文件 | 说明 |
|------|------|------|
| Retail | `entities/retail_daily.json` | 门店零售日报切片 |
| Campaign | `entities/campaigns.json` | 活动 |
| Content | `entities/contents.json` | 矩阵/内容账号表现 |
| Outreach | `entities/outreach.json` | 触达渠道能力 |

## E. 质量 / 巡检 / 财经（扩展主数据）

| 对象 | 文件 | 说明 |
|------|------|------|
| Quality | `entities/quality_checks.json` | OBD/质检记录 |
| Inspection | `entities/inspections.json` | 门店巡检 |
| Finance | `entities/finance_expense.json` | 三单匹配样例 |
| Alert | `entities/alerts.json` | 经营预警 |
| StoreDev / Risk | `entities/store_dev.json`, `entities/risks.json` | 开店与风控 |

## F. 共享语义与 AI 资产

| 对象 | 文件 | 说明 |
|------|------|------|
| TagVocabulary | `vocab/tag_vocabulary.json` | 统一标签字典 |
| FieldGlossary | `vocab/field_glossary.json` | 跨部门字段统一释义 |
| CapabilityCatalog | `entities/capability_catalog.json` | Skill 能力目录骨架 |
| DepartmentFlows | `entities/department_flows.json` | 部门内串并编排（**手工维护**；本脚本不写入/不覆盖） |
| Knowledge | `knowledge/**` | 非结构化长文本（维修/政策/制度） |
| KnowledgeChunks | `knowledge/chunks.json` | RAG 切块产物（**`scripts/build_kb_chunks.py` 维护**；本脚本不写入/不覆盖） |
| KnowledgeIndex | `knowledge/tfidf_index.json` | RAG TF-IDF 索引（**`scripts/build_kb_index.py` 维护**；本脚本不写入/不覆盖） |

## G. 演示种子

| 对象 | 文件 | 说明 |
|------|------|------|
| Story seeds | `seeds/story_1_fill_ticket.json`, `seeds/story_2_renewal_block.json` | Story1/2 输入 |

## 关联键（全库统一）

`customer_id` · `vin` · `dealer_id` · `store_id` · `sku_id` · `ticket_id` · `order_id` · `tag_id` · `campaign_id` · `oneid`
"""
    _write_text(DATA / "OBJECT_CATALOG.md", text)


# ---------------------------------------------------------------------------
# 2) 跨部门字段统一释义
# ---------------------------------------------------------------------------

def write_field_glossary() -> None:
    """从《标准字段定义表》全量生成跨部门统一释义（不管谁用，只管字段）。"""
    import csv

    csv_path = ROOT / "docs" / "标准字段定义表.csv"
    fields = []
    # 示例值中若出现真实车企名，统一替换为虚构品牌，避免合规风险
    brand_sanitize = {
        "雅迪": "北辰出行",
        "爱玛": "云梭动力",
        "台铃": "星轨两轮",
        "绿源": "青枢出行",
        "Luyuan": "Qingshu",
    }
    with csv_path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            example = row["example"] or ""
            meaning = row["description"] or ""
            related = row["related_reports"] or ""
            for bad, good in brand_sanitize.items():
                example = example.replace(bad, good)
                meaning = meaning.replace(bad, good)
                related = related.replace(bad, good)
            fields.append({
                "field_id": row["field_id"],
                "field": row["field_name"],
                "cn": row["cn_name"],
                "entity": row["entity"],
                "domain": row["domain"],
                "data_type": row["data_type"],
                "unit": row["unit"],
                "example": example,
                "meaning": meaning,
                "related_reports": related,
            })
    # 额外统一原则条目
    principles = [
        {"rule": "一义一名", "detail": "同一业务含义只保留一个 field_name，禁止部门私建同义字段"},
        {"rule": "脱敏优先", "detail": "手机号仅 phone_masked；VIN 仅 QS0 合成前缀"},
        {"rule": "关联键共用", "detail": "customer_id/vin/dealer_id/store_id/sku_id/tag_id 全库统一"},
        {"rule": "部门差异进 Skill", "detail": "话术/决策表不进字段分叉"},
    ]
    _write_json(DATA / "vocab" / "field_glossary.json", {
        "version": "v1.1",
        "brand": "Qingshu Mobility",
        "principle": "不管谁用，只管统一字段名与释义；部门差异进 Skill，不进字段分叉",
        "source": "docs/标准字段定义表.csv",
        "principles": principles,
        "fields": fields,
    })
    lines = [
        "# 跨部门标准字段释义（结构化统一）",
        "",
        "> 与 `field_glossary.json` 同步，字段全集来自 `docs/标准字段定义表.csv`。",
        "> 原则：不管哪个部门使用，字段名与释义必须一致。",
        "",
        "## 统一原则",
        "",
    ]
    for p in principles:
        lines.append(f"- **{p['rule']}**：{p['detail']}")
    lines += [
        "",
        f"## 字段明细（共 {len(fields)} 个）",
        "",
        "| 字段ID | 字段名 | 中文 | 实体 | 数据域 | 类型 | 释义 |",
        "|--------|--------|------|------|--------|------|------|",
    ]
    for g in fields:
        meaning = g["meaning"].replace("|", "\\|")
        lines.append(
            f"| {g['field_id']} | `{g['field']}` | {g['cn']} | {g['entity']} | {g['domain']} | {g['data_type']} | {meaning} |"
        )
    _write_text(DATA / "vocab" / "FIELD_GLOSSARY.md", "\n".join(lines))


# ---------------------------------------------------------------------------
# 3) Vocab tags
# ---------------------------------------------------------------------------

def build_vocab() -> list[dict]:
    version = "voc-tags-2026.08"
    tags = [
        ("TAG-ROOT-PRODUCT", "整车体验", "product", None),
        ("TAG-续航短", "续航短", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-动力弱", "动力弱", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-异响", "异响/减震", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-刹车", "刹车问题", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-充电慢", "充电慢", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-控制器", "控制器故障", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-电池鼓包", "电池鼓包/温升", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-仪表黑屏", "仪表黑屏", "product", "TAG-ROOT-PRODUCT"),
        ("TAG-ROOT-SERVICE", "服务体验", "service", None),
        ("TAG-三包争议", "三包争议", "service", "TAG-ROOT-SERVICE"),
        ("TAG-上门慢", "上门维修慢", "service", "TAG-ROOT-SERVICE"),
        ("TAG-态度差", "服务态度", "service", "TAG-ROOT-SERVICE"),
        ("TAG-配件缺货", "配件缺货", "service", "TAG-ROOT-SERVICE"),
        ("TAG-ROOT-APP", "App/车联", "app", None),
        ("TAG-绑车失败", "绑车失败", "app", "TAG-ROOT-APP"),
        ("TAG-定位飘", "定位不准", "app", "TAG-ROOT-APP"),
        ("TAG-续费入口", "续费入口难找", "app", "TAG-ROOT-APP"),
        ("TAG-推送骚扰", "推送过多", "app", "TAG-ROOT-APP"),
        ("TAG-ROOT-CHANNEL", "渠道终端", "channel", None),
        ("TAG-非专卖", "非专卖陈列", "channel", "TAG-ROOT-CHANNEL"),
        ("TAG-VI违规", "VI违规", "channel", "TAG-ROOT-CHANNEL"),
        ("TAG-压货", "压货未动销", "channel", "TAG-ROOT-CHANNEL"),
        ("TAG-ROOT-RISK", "风险舆情", "risk", None),
        ("TAG-投诉未结", "投诉未结", "risk", "TAG-ROOT-RISK"),
        ("TAG-舆情风险", "舆情风险", "risk", "TAG-ROOT-RISK"),
        ("TAG-安全隐患", "安全隐患", "risk", "TAG-ROOT-RISK"),
    ]
    return [
        {
            "tag_id": tid,
            "tag_name": name,
            "tag_domain": domain,
            "tag_parent_id": parent,
            "tag_vocab_version": version,
        }
        for tid, name, domain, parent in tags
    ]


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

def build_regions_orgs() -> tuple[list, list]:
    regions = []
    for i, (prov, city, code, county) in enumerate(CITIES):
        regions.append({
            "region_id": f"REG-{code}",
            "province": prov,
            "city": city,
            "county_code": code,
            "county_name": county,
        })
    orgs = [
        {"org_id": "NATION-CN", "org_name": "青枢出行-全国", "org_level": "nation", "parent_org_id": None, "org_path": "全国"},
        {"org_id": "WZ-EAST", "org_name": "东区战区", "org_level": "warzone", "parent_org_id": "NATION-CN", "org_path": "全国/东区"},
        {"org_id": "WZ-SOUTH", "org_name": "南区战区", "org_level": "warzone", "parent_org_id": "NATION-CN", "org_path": "全国/南区"},
        {"org_id": "WZ-WEST", "org_name": "西区战区", "org_level": "warzone", "parent_org_id": "NATION-CN", "org_path": "全国/西区"},
        {"org_id": "WZ-NORTH", "org_name": "北区战区", "org_level": "warzone", "parent_org_id": "NATION-CN", "org_path": "全国/北区"},
        {"org_id": "SZ-EAST-SN", "org_name": "东区-苏南小战区", "org_level": "subzone", "parent_org_id": "WZ-EAST", "org_path": "全国/东区/苏南"},
        {"org_id": "SZ-EAST-ZJ", "org_name": "东区-浙北小战区", "org_level": "subzone", "parent_org_id": "WZ-EAST", "org_path": "全国/东区/浙北"},
        {"org_id": "SZ-SOUTH-GD", "org_name": "南区-粤中小战区", "org_level": "subzone", "parent_org_id": "WZ-SOUTH", "org_path": "全国/南区/粤中"},
    ]
    return regions, orgs


def build_dealers_stores_guides(regions: list, n_dealers: int = 20) -> tuple[list, list, list]:
    dealers, stores, guides = [], [], []
    warzone_cycle = ["WZ-EAST", "WZ-EAST", "WZ-SOUTH", "WZ-WEST", "WZ-NORTH"]
    for i in range(1, n_dealers + 1):
        reg = regions[(i - 1) % len(regions)]
        did = f"DLR-{3000 + i}"
        dealers.append({
            "dealer_id": did,
            "dealer_name": f"青枢{reg['city']}第{(i % 3) + 1}一网",
            "legal_person": fake_name(),
            "open_account_date": str(daterange_back(1500)),
            "developer_name": fake_name(),
            "org_id": warzone_cycle[(i - 1) % len(warzone_cycle)],
            "province": reg["province"],
            "city": reg["city"],
            "county_code": reg["county_code"],
        })
        for j in range(1, 3):
            sid = f"ST-{did[-4:]}{j}"
            st_type = rng.choice(["exclusive", "exclusive", "mixed", "non_exclusive"])
            stores.append({
                "store_id": sid,
                "store_name": f"青枢{reg['city']}{reg['county_name']}{'专卖' if st_type == 'exclusive' else '体验'}店{j}",
                "store_address": f"{reg['province']}{reg['city']}{reg['county_name']}合成路{rng.randint(1, 200)}号",
                "store_type": st_type,
                "store_grade": rng.choice(["A", "B", "B", "C", "D"]),
                "store_area_sqm": float(rng.choice([80, 100, 120, 150, 200])),
                "biz_district": f"{reg['county_name']}商圈",
                "dealer_id": did,
                "province": reg["province"],
                "city": reg["city"],
            })
            guides.append({
                "guide_id": f"GD-{sid[-5:]}",
                "store_id": sid,
                "channel_account_id": f"DY-{rng.randint(10000, 99999)}",
                "guide_name": fake_name(),
            })
    return dealers, stores, guides


def build_skus() -> list:
    skus = []
    for model in MODELS:
        for color in COLORS[:5]:
            color_code = {"哑光黑": "BK", "星空灰": "GY", "极光白": "WH", "烈焰红": "RD", "薄荷绿": "GN"}[color]
            sid = f"SKU-{model.replace(' ', '')}-{color_code}"
            asp = rng.choice([2599, 2999, 3299, 3599, 3999, 4299])
            skus.append({
                "sku_id": sid,
                "sku_name": f"{model} {color}",
                "vehicle_model": model,
                "color": color,
                "asp_cny": float(asp),
                "hot_slow_flag": rng.choice(["hot", "normal", "normal", "slow"]),
                "substitute_sku_id": None,
            })
    # wire substitutes for some reds -> grey
    by_model = {}
    for s in skus:
        by_model.setdefault(s["vehicle_model"], []).append(s)
    for model, items in by_model.items():
        red = next((x for x in items if x["color"] == "烈焰红"), None)
        grey = next((x for x in items if x["color"] == "星空灰"), None)
        if red and grey:
            red["substitute_sku_id"] = grey["sku_id"]
    return skus


def build_competitors() -> list:
    brands = [
        ("北辰出行", "Pulse X1", 3499, 0.22),
        ("云梭动力", "Yuno S", 3199, 0.18),
        ("海川两轮", "HC-Max", 2899, 0.15),
        ("星轨出行", "Orbit 7", 3799, 0.12),
    ]
    out = []
    for i, (b, m, price, share) in enumerate(brands, 1):
        out.append({
            "competitor_id": f"CP-{i:02d}",
            "competitor_brand": b,
            "competitor_model": m,
            "competitor_price_cny": float(price),
            "competitor_share": share * 100,
            "competitor_share_pp_change": round(rng.uniform(-2.0, 1.5), 1),
            "promo_type": rng.choice(["以旧换新", "开学季立减", "赠头盔"]),
            "promo_region": rng.choice(["苏皖", "浙闽", "成渝", "粤港澳周边"]),
            "promo_window": "2026-07-01~2026-07-31",
            "price_cut_amt": float(rng.choice([0, 200, 300, 500])),
            "sentiment_score": round(rng.uniform(0.45, 0.75), 2),
            "launch_date": str(date(2026, rng.randint(3, 6), rng.randint(1, 28))),
            "battery_type": "lithium",
            "claimed_range_km": float(rng.choice([60, 70, 80, 90])),
        })
    return out


def build_customers_vehicles(
    n_customers: int, stores: list
) -> tuple[list, list, list, list]:
    customers, vehicles, behaviors, renewals = [], [], [], []
    for i in range(1, n_customers + 1):
        cid = f"CUS-{10000 + i}"
        customers.append({
            "customer_id": cid,
            "phone_masked": fake_phone_masked(),
            "openid": fake_openid(i),
            "unionid": "qs_uid_" + hashlib.md5(f"uid-{SEED}-{i}".encode()).hexdigest()[:12],
            "identity_type": rng.choices(
                ["end_user", "prospect", "dealer"], weights=[0.85, 0.1, 0.05]
            )[0],
            "oneid": fake_oneid(i),
            "oneid_match_method": "phone",
            "province": (loc := rng.choice(CITIES))[0],
            "city": loc[1],
        })
        # 1 vehicle each, some get second
        n_v = 1 if rng.random() > 0.15 else 2
        for k in range(n_v):
            seq = i * 10 + k
            vin = fake_vin(seq)
            model = rng.choice(MODELS)
            color = rng.choice(COLORS)
            btype, bspec, rng_km = rng.choice(BATTERY)
            smart = rng.random() > 0.18
            purchase = daterange_back(900)
            vehicles.append({
                "vin": vin,
                "frame_no": f"FR-{rng.randint(100000, 999999)}",
                "sn": f"SN-2026{rng.randint(100000, 999999)}",
                "vehicle_model": model,
                "vehicle_config": rng.choice(CONFIGS),
                "color": color,
                "battery_type": btype,
                "battery_spec": bspec,
                "claimed_range_km": float(rng_km),
                "purchase_date": str(purchase),
                "purchase_year": purchase.year,
                "is_smart_vehicle": smart,
                "plant": rng.choice(["华东一厂", "华南二厂", "西南三厂"]),
                "line_id": f"LINE-{rng.randint(1, 6):02d}",
                "batch_no": f"BATCH-2026W{rng.randint(10, 30):02d}-{model.replace(' ', '')}",
                "ota_version": rng.choice(["v2.1.0", "v2.2.3", "v2.3.1", "v2.4.0"]),
                "customer_id": cid,
                "store_id": rng.choice(stores)["store_id"],
            })
            behaviors.append({
                "customer_id": cid,
                "vin": vin,
                "app_register_flag": True if smart else rng.random() > 0.4,
                "bind_vehicle_flag": smart and rng.random() > 0.2,
                "last_active_at": iso(datetime(2026, 7, rng.randint(1, 28), rng.randint(8, 22), tzinfo=timezone.utc)),
                "active_days_30d": rng.randint(0, 25),
                "mau_flag": rng.random() > 0.35,
                "dau_flag": rng.random() > 0.7,
                "rfm_segment": rng.choice(["high_value", "potential", "silent", "churn_risk"]),
                "r_days": rng.randint(1, 120),
                "f_month": rng.randint(0, 20),
                "m_value": float(rng.randint(0, 2000)),
                "first_touch_channel": rng.choice(["400", "App", "门店", "电商"]),
                "last_touch_channel": rng.choice(["400", "App", "门店", "Push"]),
            })
            if smart:
                expire = date(2026, 8, 1) + timedelta(days=rng.randint(-20, 60))
                layer = "T-7" if (expire - date(2026, 8, 1)).days <= 7 else (
                    "T-30" if (expire - date(2026, 8, 1)).days <= 30 else "sleep"
                )
                if rng.random() < 0.15:
                    layer = "sleep"
                renewals.append({
                    "customer_id": cid,
                    "vin": vin,
                    "service_expire_date": str(expire),
                    "due_renew_flag": expire <= date(2026, 8, 31),
                    "paid_flag": rng.random() < 0.22,
                    "paid_type": rng.choice(["renew", "unknown", "new_purchase"]),
                    "active_t30_flag": layer in ("T-30", "T-7") and rng.random() > 0.3,
                    "active_t7_flag": layer == "T-7" and rng.random() > 0.4,
                    "sleep_90d_app_flag": layer == "sleep",
                    "active_90d_4g_flag": rng.random() > 0.25,
                    "renew_intent_score": round(rng.uniform(0.1, 0.95), 2),
                    "renew_pool_layer": layer,
                    "outreach_channel": rng.choice(["push", "sms", "ai_call", "human", "wecom"]),
                    "intent_level": rng.choice(["high", "mid", "low"]),
                })
            else:
                renewals.append({
                    "customer_id": cid,
                    "vin": vin,
                    "service_expire_date": None,
                    "due_renew_flag": False,
                    "paid_flag": False,
                    "paid_type": "unknown",
                    "active_t30_flag": False,
                    "active_t7_flag": False,
                    "sleep_90d_app_flag": True,
                    "active_90d_4g_flag": False,
                    "renew_intent_score": 0.05,
                    "renew_pool_layer": "non_smart",
                    "outreach_channel": "push",
                    "intent_level": "low",
                })
    return customers, vehicles, behaviors, renewals


def build_orders_inventory(dealers, stores, skus, n_orders: int = 80) -> tuple[list, list, list, list]:
    orders, inventory, policies, color_plans = [], [], [], []
    for i in range(1, n_orders + 1):
        d = rng.choice(dealers)
        st = rng.choice([s for s in stores if s["dealer_id"] == d["dealer_id"]] or stores)
        sku = rng.choice(skus)
        status = rng.choice(["pending_audit", "approved", "approved", "rejected", "shipped", "completed"])
        audit = None
        if status == "pending_audit":
            audit = rng.choice(["pass", "reject_shortage", "suggest_substitute"])
        elif status == "rejected":
            audit = "reject_shortage"
        elif status in ("approved", "shipped", "completed"):
            audit = "pass"
        orders.append({
            "order_id": f"SO-2026{i:04d}",
            "dealer_id": d["dealer_id"],
            "store_id": st["store_id"],
            "sku_id": sku["sku_id"],
            "customer_id": None,
            "order_qty": rng.randint(5, 60),
            "order_status": status,
            "audit_result": audit,
            "policy_version": "2026Q3-提货返利-V3",
        })
    for sku in skus:
        inventory.append({
            "sku_id": sku["sku_id"],
            "store_id": None,
            "dealer_id": None,
            "wms_stock_qty": rng.randint(0, 200),
            "wms_in_transit_qty": rng.randint(0, 80),
            "store_stock_qty": rng.randint(0, 20),
            "stock_days_cover": round(rng.uniform(0.5, 25), 1),
            "stock_age_days": rng.randint(0, 60),
            "inventory_turn_days": round(rng.uniform(10, 55), 1),
            "shortage_days": rng.choice([0, 0, 0, 3, 7, 11]),
            "demand_daily_est": round(rng.uniform(2, 25), 1),
            "lost_units_est": rng.randint(0, 200),
            "lost_gmv_est": float(rng.randint(0, 600000)),
            "lost_margin_est": float(rng.randint(0, 120000)),
            "shortage_root_cause": rng.choice(["production", "logistics", "color_plan", "supply", None]),
            "replenish_qty_suggest": rng.randint(0, 200),
            "eta_date": str(date(2026, 8, rng.randint(2, 20))),
        })
    for d in dealers:
        qty = rng.randint(400, 1200)
        policies.append({
            "dealer_id": d["dealer_id"],
            "settlement_id": f"STL-2026Q3-{d['dealer_id'][-4:]}",
            "policy_version": "2026Q3-提货返利-V3",
            "current_rebate_tier": "银牌档" if qty < 800 else "金牌档",
            "current_pickup_qty_mtd": qty,
            "qty_to_next_tier": max(0, 800 - qty) if qty < 800 else max(0, 1200 - qty),
            "next_tier_name": "金牌档" if qty < 800 else "钻石档",
            "next_tier_rebate_amt": float(28000 if qty < 800 else 45000),
            "rebate_rate": 3.5 if qty < 800 else 4.2,
            "color_bonus_amt": float(rng.choice([0, 1000, 2000])),
            "clawback_amt": float(rng.choice([0, 0, 500])),
            "payable_amt": float(rng.randint(8000, 50000)),
            "pay_status": rng.choice(["unpaid", "unpaid", "paid"]),
        })
    for week in ("2026-W30", "2026-W31", "2026-W32"):
        for model in MODELS[:5]:
            for color in COLORS[:4]:
                color_plans.append({
                    "color_plan_week": week,
                    "vehicle_model": model,
                    "color": color,
                    "color_plan_qty": rng.randint(0, 150),
                    "plant": rng.choice(["华东一厂", "华南二厂"]),
                })
    return orders, inventory, policies, color_plans


def build_tickets_voc(customers, vehicles, stores, tags, n_tickets: int = 100) -> tuple[list, list]:
    tickets, voc = [], []
    fault_tags = [t for t in tags if t["tag_domain"] == "product" and t["tag_parent_id"]]
    risk_tags = [t for t in tags if t["tag_domain"] == "risk" and t["tag_parent_id"]]
    descs = [
        "骑行续航明显低于说明书标称，充满电市区骑行不到一半里程。",
        "爬坡动力不足，双人骑行时电机有过热保护提示。",
        "前叉异响，减速带过后震动偏大，怀疑减震漏油。",
        "刹车手感变软，雨天制动距离变长，请求上门检测。",
        "充电器指示灯异常，充电超过8小时仍无法充满。",
        "App绑车一直提示设备离线，车辆重启后依旧失败。",
        "仪表偶发黑屏，需断电重启才能恢复。",
        "投诉门店未按三包政策处理电池更换，工单已超过7天未结。",
        "控制器报故障码后车辆限速，附近网点说配件缺货。",
        "定位漂移严重，寻车功能无法准确找到车辆。",
    ]
    for i in range(1, n_tickets + 1):
        cust = rng.choice(customers)
        vehs = [v for v in vehicles if v["customer_id"] == cust["customer_id"]] or vehicles
        veh = rng.choice(vehs)
        ttype = rng.choices(
            ["fault", "consult", "complaint", "other"], weights=[0.55, 0.25, 0.15, 0.05]
        )[0]
        tag = rng.choice(fault_tags if ttype != "complaint" else fault_tags + risk_tags)
        # Story 需要：至少若干「投诉未结」
        if i <= 6:
            tag = next(t for t in tags if t["tag_id"] == "TAG-投诉未结")
            ttype = "complaint"
        sent = "neg" if ttype in ("fault", "complaint") else rng.choice(["neu", "pos", "neg"])
        desc = rng.choice(descs)
        tid = f"TK-202607{i:04d}"
        tickets.append({
            "ticket_id": tid,
            "customer_id": cust["customer_id"],
            "vin": veh["vin"],
            "store_id": veh.get("store_id") or rng.choice(stores)["store_id"],
            "dealer_id": next(s["dealer_id"] for s in stores if s["store_id"] == (veh.get("store_id") or stores[0]["store_id"])),
            "tag_id": tag["tag_id"],
            "sentiment": sent,
            "ticket_type": ttype,
            "fault_category": rng.choice(
                ["battery", "motor", "brake", "controller", "charging", "dashboard", "other"]
            ) if ttype == "fault" else None,
            "consult_category": rng.choice(["整车信息", "配件", "系统事宜", "上牌"]) if ttype == "consult" else None,
            "ticket_channel": rng.choice(["400", "App", "电商", "门店"]),
            "ticket_status": "open" if tag["tag_id"] == "TAG-投诉未结" else rng.choice(["open", "processing", "closed"]),
            "ticket_created_at": iso(datetime(2026, 7, rng.randint(1, 28), rng.randint(9, 20), tzinfo=timezone.utc)),
            "handle_duration_min": float(rng.randint(5, 90)),
            "is_complaint": ttype == "complaint" or tag["tag_id"] == "TAG-投诉未结",
            "three_guarantees_reject_flag": rng.random() < 0.08,
            "desc_text": desc,
            "desc_chars": len(desc),
            "transcript_text": f"坐席：您好，青枢出行客服。用户：{desc}",
            "agent_id": f"AG-{rng.randint(2000, 2999)}",
            "sop_item": "是否确认VIN与车型",
            "sop_pass_fail": rng.choice(["pass", "pass", "fail"]),
            "risk_words": ["绝对没问题"] if rng.random() < 0.1 else [],
        })
        voc.append({
            "feedback_id": f"FB-{90000 + i}",
            "ticket_id": tid,
            "customer_id": cust["customer_id"],
            "vin": veh["vin"],
            "nps": rng.randint(-100, 100),
            "csat": round(rng.uniform(1.5, 5.0), 1),
            "nps_delta": rng.randint(-15, 10),
            "feedback_cnt": 1,
            "tag_id": tag["tag_id"],
            "tag_name": tag["tag_name"],
            "tag_domain": tag["tag_domain"],
            "sentiment": sent,
            "sentiment_score": round(rng.uniform(-0.95, 0.9), 2),
            "problem_theme": tag["tag_name"],
            "theme_cnt": rng.randint(10, 300),
            "neg_ratio": round(rng.uniform(20, 85), 1),
            "wow_change": round(rng.uniform(-10, 30), 1),
            "closed_loop_rate": round(rng.uniform(30, 90), 1),
            "recurrence_rate": round(rng.uniform(5, 25), 1),
            "cover_dim": "vehicle",
            "module_name": None,
            "sample_voice": desc,
            "clue_confidence": rng.choice(["weak", "medium"]),
            "pr_risk_level": "P1" if tag["tag_id"] == "TAG-投诉未结" else rng.choice(["P2", "P2", "P1"]),
            "consumer_sat_score": None,
            "channel_sat_score": None,
            "survey_recover_rate": None,
            "dissatisfaction_reason": tag["tag_name"] if sent == "neg" else None,
        })
    return tickets, voc


def build_telemetry(vehicles: list) -> list:
    out = []
    for v in rng.sample(vehicles, k=min(40, len(vehicles))):
        out.append({
            "vin": v["vin"],
            "fault_code": rng.choice([None, None, "BMS_OT_01", "MCU_OC_02", "GPS_DRIFT", "CHG_TIMEOUT"]),
            "iot_alert_cnt": rng.randint(0, 5),
            "mileage_km": float(rng.randint(200, 12000)),
            "soc_pct": float(rng.randint(15, 100)),
            "telemetry_coverage_rate": 81.0,
            "battery_health_pct": float(rng.randint(78, 99)),
            "ota_version": v["ota_version"],
        })
    return out


def build_misc(dealers, stores, skus, vehicles) -> dict:
    sales = []
    for d in dealers:
        target = rng.randint(800, 2000)
        qty = int(target * rng.uniform(0.7, 1.05))
        sales.append({
            "dealer_id": d["dealer_id"],
            "org_id": d["org_id"],
            "period": "2026-07",
            "sales_qty": qty,
            "sales_target_qty": target,
            "sales_achieve_rate": round(100 * qty / target, 1),
            "contract_qty": int(qty * 0.9),
            "contract_target_qty": int(target * 0.92),
            "contract_achieve_rate": round(100 * (qty * 0.9) / (target * 0.92), 1),
            "yoy_sales_qty": int(qty * rng.uniform(0.85, 1.1)),
            "yoy_rate": round(rng.uniform(-5, 20), 1),
            "mom_sales_qty": int(qty * rng.uniform(0.9, 1.1)),
            "mom_rate": round(rng.uniform(-12, 8), 1),
            "rank_dealer": rng.randint(1, 40),
            "full_achieve_outlet_cnt": rng.randint(2, 20),
            "full_achieve_outlet_ratio": round(rng.uniform(20, 60), 1),
            "abnormal_outlet_cnt": rng.randint(0, 8),
            "abnormal_outlet_ratio": round(rng.uniform(0, 20), 1),
            "abnormal_reason": rng.choice(["颜色缺货", "压货未动销", "竞品降价", None]),
            "abnormal_reason_cnt": rng.randint(0, 9),
            "core_market_gap_to_top3": rng.randint(100, 2000),
            "online_sales_qty": rng.randint(10, 120),
            "rank_warzone": None,
            "rank_subzone": None,
        })
    health = []
    for d in dealers:
        health.append({
            "dealer_id": d["dealer_id"],
            "period": "2026-07",
            "sales_score": float(rng.randint(50, 95)),
            "retail_score": float(rng.randint(45, 90)),
            "compliance_score": float(rng.randint(55, 100)),
            "complaint_score": float(rng.randint(40, 95)),
            "inventory_turn_score": float(rng.randint(40, 90)),
            "health_index": float(rng.randint(50, 92)),
        })
    retail = []
    for st in stores:
        retail.append({
            "store_id": st["store_id"],
            "report_date": "2026-07-28",
            "retail_qty": rng.randint(0, 20),
            "retail_qty_day": rng.randint(0, 6),
            "retail_qty_mtd": rng.randint(20, 180),
            "retail_yoy": round(rng.uniform(-10, 25), 1),
            "writeoff_qty": rng.randint(0, 30),
            "redeem_rate": round(rng.uniform(40, 90), 1),
            "gross_margin_amt": float(rng.randint(2000, 20000)),
            "gross_margin_rate": round(rng.uniform(12, 22), 1),
            "non_exclusive_rate": 0.0 if st["store_type"] == "exclusive" else round(rng.uniform(10, 40), 1),
            "non_exclusive_flag": st["store_type"] != "exclusive",
        })
    campaigns = [
        {
            "campaign_id": "CAMP-暑期换新",
            "campaign_name": "暑期以旧换新",
            "campaign_goal": "提升零售核销与智能车续费曝光",
            "campaign_budget": 50000.0,
            "participants": 3200,
            "campaign_roi": 2.4,
            "campaign_complaint_rate": 0.3,
        },
        {
            "campaign_id": "CAMP-开学季",
            "campaign_name": "开学季通勤礼包",
            "campaign_goal": "冲刺年轻用户绑车激活",
            "campaign_budget": 30000.0,
            "participants": 1800,
            "campaign_roi": 1.9,
            "campaign_complaint_rate": 0.2,
        },
    ]
    contents = []
    for g in rng.sample(
        [{"guide_id": f"GD-{s['store_id'][-5:]}", "store_id": s["store_id"], "channel_account_id": f"DY-{10000+i}"} for i, s in enumerate(stores)],
        k=min(16, len(stores)),
    ):
        contents.append({
            **g,
            "short_video_cnt": rng.randint(5, 40),
            "followers": rng.randint(800, 30000),
            "play_cnt": rng.randint(2000, 120000),
            "gmv_convert_rate": round(rng.uniform(0.3, 3.5), 2),
            "deals_cnt": rng.randint(0, 50),
            "gmv": float(rng.randint(0, 150000)),
            "aov": float(rng.choice([2599, 2999, 3299, 3599])),
            "valid_seller_flag": rng.random() > 0.4,
            "live_sessions": rng.randint(0, 8),
            "live_watch_uv": rng.randint(0, 8000),
            "influencer_cvr": round(rng.uniform(0.5, 2.5), 2),
            "refund_rate": round(rng.uniform(0.5, 3.0), 2),
            "content_script_id": f"SCRIPT-{rng.choice(['续航对比', '通勤场景', '雨天刹车'])}-01",
            "benchmark_case_id": "CASE-合成标杆店-01",
            "short_video_valid_participate_rate": round(rng.uniform(20, 60), 1),
        })
    outreach = [
        {"channel": ch, "channel_quota_daily": q, "delivery_rate": dr, "open_rate": op, "connect_rate": cr, "transfer_human_cnt": th, "template_approve_days": 2.0}
        for ch, q, dr, op, cr, th in [
            ("push", 20000, 96.2, 28.4, None, 0),
            ("sms", 8000, 94.0, 12.0, None, 0),
            ("ai_call", 3000, 99.0, None, 41.0, 86),
            ("human", 500, 99.0, None, 55.0, 0),
            ("wecom", 2000, 90.0, 35.0, None, 12),
        ]
    ]
    quality = []
    for v in rng.sample(vehicles, k=min(25, len(vehicles))):
        quality.append({
            "vin": v["vin"],
            "test_station": f"OBD-台架-{rng.randint(1, 4):02d}",
            "test_ts": iso(datetime(2026, 6, rng.randint(1, 28), 10, tzinfo=timezone.utc)),
            "obd_protocol": "ISO15765",
            "voltage_v": round(rng.uniform(48, 56), 1),
            "current_a": round(rng.uniform(5, 20), 1),
            "speed_rpm": float(rng.randint(200, 600)),
            "controller_temp_c": float(rng.randint(30, 70)),
            "qc_result": rng.choice(["pass", "pass", "pass", "fail"]),
            "operator_id": f"OP-{rng.randint(100, 399)}",
            "part_name": rng.choice(["控制器", "电池包", "仪表"]),
            "part_batch_no": f"PB-{rng.randint(1000, 9999)}",
            "supplier_id": f"SUP-{rng.randint(8000, 8999)}",
            "delta_e": round(rng.uniform(0.2, 1.5), 2),
            "gloss": float(rng.randint(70, 95)),
            "defect_type": rng.choice([None, None, "色差", "颗粒"]),
            "anomaly_score": round(rng.uniform(0.1, 0.9), 2),
            "predict_fail_days": rng.randint(7, 60),
            "release_ts": iso(datetime(2026, 6, rng.randint(1, 28), 16, tzinfo=timezone.utc)),
            "trace_package_url": f"synthetic://trace/{v['vin']}.zip",
            "recall_level": "watch",
        })
    inspections = []
    for st in rng.sample(stores, k=min(18, len(stores))):
        inspections.append({
            "inspect_id": f"INS-20260728-{st['store_id'][-4:]}",
            "store_id": st["store_id"],
            "inspect_time": iso(datetime(2026, 7, 28, 8, 30, tzinfo=timezone.utc)),
            "check_item": rng.choice(["门头VI完整性", "海报物料", "着装规范", "竞品堆货"]),
            "ai_confidence": round(rng.uniform(0.7, 0.98), 2),
            "pass_fail": "fail" if st["store_type"] == "non_exclusive" else rng.choice(["pass", "pass", "fail"]),
            "photo_url": f"synthetic://inspect/{st['store_id']}.jpg",
            "morning_photo_url": f"synthetic://inspect/{st['store_id']}-am.jpg",
            "evening_photo_url": f"synthetic://inspect/{st['store_id']}-pm.jpg",
            "competitor_logo_detected": ["北辰出行"] if st["store_type"] != "exclusive" and rng.random() > 0.5 else [],
            "suspect_type": "非专卖堆货" if st["store_type"] != "exclusive" else None,
            "vi_score": float(rng.randint(55, 98)),
            "rectify_ticket_id": f"RC-{st['store_id'][-4:]}" if st["store_type"] != "exclusive" else None,
            "due_date": "2026-08-05",
        })
    finance = []
    for i in range(1, 13):
        inv = round(rng.uniform(500, 3000), 2)
        po = inv + rng.choice([0, 0, 20, -15])
        finance.append({
            "expense_id": f"EXP-202607-{100 + i}",
            "employee_id": f"EMP-{rng.randint(1000, 1999)}",
            "invoice_no": f"INV-SYN-{rng.randint(100000, 999999)}",
            "po_no": f"PO-SYN-{rng.randint(10000, 99999)}",
            "receipt_amt": inv,
            "invoice_amt": inv,
            "po_amt": float(po),
            "match_status": "match" if abs(po - inv) < 0.01 else "mismatch",
            "diff_amt": round(abs(po - inv), 2),
            "diff_reason": None if abs(po - inv) < 0.01 else rng.choice(["税额不符", "SKU不符", "重复票"]),
            "revenue_forecast": None,
            "pickup_forecast_units": None,
            "rebate_cashout_forecast": None,
            "opex_forecast": None,
            "net_cash_forecast": None,
            "forecast_confidence_low": None,
            "forecast_confidence_high": None,
        })
    alerts = []
    for i, d in enumerate(dealers[:8], 1):
        alerts.append({
            "alert_id": f"ALERT-20260728-{i:03d}",
            "alert_type": rng.choice(["sales_drop", "compliance", "shortage", "complaint", "competitor"]),
            "dealer_id": d["dealer_id"],
            "store_id": None,
            "metric_name": "mom_rate",
            "metric_value": round(rng.uniform(-15, -8), 1),
            "threshold_value": -10.0,
            "severity": rng.choice(["P0", "P1", "P2"]),
            "required_action": rng.choice(["3日内补色", "整改VI", "暂停续费触达并回访投诉"]),
            "due_date": "2026-08-05",
            "verify_method": rng.choice(["二次巡检", "复检拍照", "工单闭环复核"]),
        })
    store_dev = []
    for reg in CITIES:
        store_dev.append({
            "county_code": reg[2],
            "county_name": reg[3],
            "blank_l1_plan_cnt": rng.randint(2, 10),
            "blank_l1_opened_cnt": rng.randint(0, 6),
            "blank_l1_achieve_rate": round(rng.uniform(30, 90), 1),
            "store_dev_plan_cnt": rng.randint(10, 40),
            "store_dev_done_cnt": rng.randint(5, 30),
            "store_dev_rate": round(rng.uniform(40, 85), 1),
            "market_capacity_annual": rng.randint(15000, 50000),
            "self_coverage_flag": rng.choice(["yes", "weak", "blank"]),
            "open_roi_months": float(rng.randint(10, 20)),
            "support_quota_total_wan": float(rng.randint(8, 20)),
            "support_quota_applied_wan": float(rng.randint(2, 10)),
            "support_quota_remain_wan": float(rng.randint(1, 10)),
            "first_order_qty": rng.randint(40, 120),
            "m1_m3_order_qty": rng.randint(100, 400),
            "gantt_owner": fake_name(),
            "gantt_start": "2026-07-01",
            "gantt_end": "2026-09-15",
            "fitout_suggest_grade": rng.choice(["A", "B", "C"]),
        })
    risks = []
    for d in dealers:
        risks.append({
            "dealer_id": d["dealer_id"],
            "company_name": d["dealer_name"],
            "credit_code": "91" + hashlib.md5(f"credit-{SEED}-{d['dealer_id']}".encode()).hexdigest()[:16].upper(),
            "reg_capital_wan": float(rng.choice([100, 200, 500, 1000])),
            "lawsuit_cnt_3y": rng.randint(0, 3),
            "dishonest_flag": False,
            "negative_news_cnt_90d": rng.randint(0, 2),
            "risk_level": rng.choice(["low", "low", "medium", "high"]),
            "risk_score": float(rng.randint(20, 85)),
            "admission_suggest": rng.choice(["pass", "pass", "supplement", "reject"]),
        })
    # Skill → 工具白名单（与 ToolRegistry / data/entities/capability_catalog.json 对齐）
    catalog = [
        {
            "skill_id": "fill_ticket",
            "skill_desc": "对话/文本生成工单草案并写入共享产出",
            "input_schema": {"text": "string", "customer_id": "string?", "vin": "string?"},
            "output_schema": {"ticket_draft": "object", "ai_output_id": "string"},
            "allowed_tools": [
                "get_customer", "get_vehicle", "get_ticket", "list_tickets",
                "extract_ticket_fields", "suggest_voc_tags", "get_tag",
                "write_ai_output", "log_step",
            ],
        },
        {
            "skill_id": "renewal_plan",
            "skill_desc": "续费触达计划；若存在未结投诉标签则阻断",
            "input_schema": {"customer_id": "string", "vin": "string?"},
            "output_schema": {"allow_outreach": "boolean", "reason": "string"},
            "allowed_tools": [
                "get_customer", "get_vehicle", "get_renewal", "get_user_behavior",
                "score_renewal", "route_renewal_pool", "read_ai_outputs",
                "read_shared_tags", "check_outreach_block", "log_step",
            ],
        },
        {
            "skill_id": "repair_kb",
            "skill_desc": "维修知识库 RAG 问答",
            "input_schema": {"query": "string", "vin": "string?"},
            "output_schema": {"answer": "string", "citations": "list"},
            "allowed_tools": [
                "search_kb", "get_kb_document", "list_kb_domains", "log_step",
            ],
        },
        {
            "skill_id": "policy_kb",
            "skill_desc": "销售/三包政策 RAG 问答",
            "input_schema": {"query": "string", "dealer_id": "string?"},
            "output_schema": {"answer": "string", "citations": "list"},
            "allowed_tools": [
                "search_kb", "get_kb_document", "list_kb_domains", "log_step",
            ],
        },
        {
            "skill_id": "hr_rules",
            "skill_desc": "人资制度 / 坐席 SOP RAG 问答",
            "input_schema": {"query": "string"},
            "output_schema": {"answer": "string", "citations": "list"},
            "allowed_tools": [
                "search_kb", "get_kb_document", "list_kb_domains", "log_step",
            ],
        },
        {
            "skill_id": "voc_tagging",
            "skill_desc": "VoC 打标与情感分析并资产化",
            "input_schema": {"text": "string", "customer_id": "string?"},
            "output_schema": {"tag_id": "string", "sentiment": "string"},
            "allowed_tools": [
                "suggest_voc_tags", "list_tags", "get_tag", "list_voc",
                "write_ai_output", "list_capabilities", "log_step",
            ],
        },
        {
            "skill_id": "shared_write",
            "skill_desc": "通用共享产出写入示例",
            "input_schema": {"payload": "object"},
            "output_schema": {"ai_output_id": "string"},
            "allowed_tools": [
                "write_ai_output", "read_ai_outputs", "get_ai_output", "log_step",
            ],
        },
        {
            "skill_id": "crm_lookup",
            "skill_desc": "主数据/订单/库存综合查询",
            "input_schema": {"customer_id": "string?", "vin": "string?", "order_id": "string?"},
            "output_schema": {"entities": "object"},
            "allowed_tools": [
                "get_customer", "get_vehicle", "list_vehicles", "get_order",
                "list_orders", "list_inventory", "get_dealer", "get_store",
                "get_sku", "log_step",
            ],
        },
        {
            "skill_id": "channel_ops",
            "skill_desc": "渠道经营健康/预警/巡检查询",
            "input_schema": {"dealer_id": "string?"},
            "output_schema": {"insights": "object"},
            "allowed_tools": [
                "get_dealer", "get_dealer_health", "list_alerts", "list_sales_metrics",
                "list_retail_daily", "list_inspections", "get_risk", "get_policy",
                "simulate_rebate_tier", "log_step",
            ],
        },
    ]
    return {
        "sales_metrics": sales,
        "dealer_health": health,
        "retail_daily": retail,
        "campaigns": campaigns,
        "contents": contents,
        "outreach": outreach,
        "quality_checks": quality,
        "inspections": inspections,
        "finance_expense": finance,
        "alerts": alerts,
        "store_dev": store_dev,
        "risks": risks,
        "capability_catalog": catalog,
    }


# ---------------------------------------------------------------------------
# Knowledge (unstructured)
# ---------------------------------------------------------------------------

def write_knowledge() -> None:
    """非结构化长文本入库：维修 / 政策 / 制度 / 产品 / 渠道。"""
    docs = {
        "repair/续航异常排查.md": """# 续航异常排查手册（青枢出行 · 合成知识）

适用车型：E40 / E60 / E80 / S7 / S9 锂电系列（合成文档，非真实售后手册）。

## 1. 现象确认
1. 向用户确认最近一次充满电的指示（App SOC=100% 或充电器绿灯）。
2. 确认骑行场景：纯市区、长坡、载重双人、低温（<5℃）。
3. 记录 VIN（Demo 中均为 QS0 开头合成号）、OTA 版本、电池规格、最近一次深度充放电时间。

## 2. 快速区分
| 现象 | 可能原因 | 一线动作 |
|------|----------|----------|
| 满电里程约为标称 50% 以下 | BMS 校准漂移 / 电芯衰减 | 远程拉取 SOH；指导深度充放电校准一次 |
| 爬坡后掉电快 | 电机过载保护、胎压不足 | 检查胎压 2.5–3.0 bar；查询 MCU 过流告警 |
| 充电到 80% 后极慢 | 充电器限流或充电口接触不良 | 更换同规格充电器试验；检查充电口烧蚀 |
| 低温续航腰斩 | 锂电低温内阻上升 | 说明物理特性；建议室内充电预热后再骑行 |

## 3. 标准话术（可引用）
- 「您反馈的续航低于标称，我们先做三步：确认充满电标准、核对 OTA、查看电池健康度。」
- 「若 SOH 低于 80% 且在三包期内，按《青枢三包政策·电池分册》进入检测工单。」
- 「低温场景下续航下降属于锂电池物理特性，不等同于故障，但我们会帮您核对 SOH。」

## 4. 升级条件
- 同 VIN 30 天内重复进线 ≥2 次；
- 伴随电池温升告警 `BMS_OT_01`；
- 用户明确表示媒体曝光意向 → 标记 `TAG-舆情风险` 并升级专席。

## 5. 与共享层协作
- 填单 Skill 产出 `AIOutput` 时必须写入 `tag_id`（如 `TAG-续航短`）与 `sentiment`；
- 若同时存在 `TAG-投诉未结`，续费 Planning Skill 读取后应阻断触达。
""",
        "repair/电机异响与限速.md": """# 电机异响与限速处理（合成）

## 症状
- 加速时轮毂电机有周期性异响；
- 仪表提示限速，最高车速被限制在 15km/h；
- 偶发仪表弹出「驱动系统保护」。

## 排查步骤
1. 读取故障码：优先关注 `MCU_OC_02`（过流）、`MCU_OT_01`（过温）。
2. 检查后轮是否缠绕异物，轴承间隙是否异常。
3. 确认最近是否发生泡水或涉水骑行。
4. 核对 OTA：部分旧版本在陡坡急加速误触发限速，可建议升级到 v2.3.1+。

## 处置
- 无故障码：紧固电机线束接地，路试 3km 复测。
- 有过流码：创建配件工单，配件仓优先调拨同批次控制器/电机。
- 涉及 `TAG-安全隐患` 时，禁止仅远程清码结案，必须预约线下检测。

## 坐席禁语
- 不得承诺「一定能当天修好」；
- 不得引导用户自行拆卸电机端盖。
""",
        "repair/App绑车失败.md": """# App 绑车失败排障（合成）

## 常见原因
1. 车辆未激活 4G 或车联服务已过期；
2. 手机蓝牙/定位权限未开；
3. 门店出厂绑定未解绑；
4. 非智能车被误导入智能车绑车流程。

## 处理流程
1. 查 VIN 是否 `is_smart_vehicle=true`；
2. 查续费池：若服务过期，引导续费后再绑；
3. 后台触发「强制解绑（需门店验证码）」；
4. 引导用户在 2 米内重试，保持 App 前台。

## 关联标签
- 失败原因偏软件/账号：`TAG-绑车失败`
- 用户情绪激动且重复进线：评估是否打 `TAG-投诉未结`

禁止承诺「一定是软件问题」——需先排除硬件天线与 IoT 覆盖。
""",
        "repair/刹车异响与刹车皮.md": """# 刹车异响与刹车皮更换指引（合成）

## 现象
- 轻刹金属摩擦音；重刹正常。
- 雨后首刹尖啸，之后消失。

## 判定
1. 询问使用里程与最近保养；
2. 目视刹车皮厚度（示意阈值：<2mm 建议更换）；
3. 排除石子嵌入与碟片轻微锈蚀（雨后常见，非故障）。

## 工单字段要求
- `fault_category=brake`
- `desc_text` 需包含：异响场景（轻刹/重刹/雨后）、里程、是否影响制动距离主观感受。
""",
        "repair/充电口与充电器兼容.md": """# 充电口与充电器兼容说明（合成）

## 原则
- 仅允许使用青枢认证充电器型号（示意：QS-CHG-48-xx）。
- 非原装快充可能导致充电慢、温升告警，甚至不在三包范围。

## 排障
1. 互换同规格充电器试验；
2. 检查充电口针脚是否烧蚀、松动；
3. 查看 telemetry：是否存在 `CHG_OT_01`。

## 话术
「为了电池安全，请使用车辆匹配的充电器。我们可帮您核验充电器型号是否在兼容列表。」
""",
        "policy/三包与电池政策.md": """# 青枢出行三包政策摘要（合成）

> 本文供 Demo RAG 使用，条款为虚构示意，不构成真实法律文本。

## 整车三包
- 三包期：开票之日起 12 个月或行驶 1 万公里（以先到为准）。
- 主要部件（电机、控制器、仪表）：三包期内免费维修，严重故障可申请更换。

## 电池
- 铅酸：6 个月容量质保；
- 锂电：12 个月或 SOH≥80% 质保策略（示意）；
- 人为进水、私拆 BMS、使用非原装充电器导致的损坏不在三包范围。

## 服务时限
- 市区预约上门：48 小时内响应；
- 配件缺货：需在工单注明预计到货日，并同步用户。

## 争议升级
- 用户主张「拒保不合理」时打标 `TAG-三包争议`；
- 若伴随公开传播意向，加打 `TAG-舆情风险`。
""",
        "policy/2026Q3提货返利.md": """# 2026Q3 提货返利政策（合成）

版本号：`2026Q3-提货返利-V3`

## 档位
| 档位 | 月累计提货 | 返利点位 | 备注 |
|------|------------|----------|------|
| 铜牌 | ≥300 台 | 2.0% | |
| 银牌 | ≥800 台 | 3.5% | 颜色齐全奖励最高 +0.5% |
| 金牌 | ≥1200 台 | 4.2% | |
| 钻石 | ≥1800 台 | 5.0% | 需合规巡检通过 |

## 审单规则（示意）
- 主推色（哑光黑/星空灰）缺货时，可建议同价带替代色；
- 烈焰红长期缺货，优先引导星空灰替代；
- 存在未闭环 P0 客诉的一代，暂停冲档激励提醒。

## 结算字段
结算单需包含：`settlement_id`、`dealer_id`、`policy_version`、`current_rebate_tier`、`payable_amt`、`clawback_amt`。
""",
        "policy/续费触达红线.md": """# 智能车车联续费触达红线（合成）

1. 存在标签 `TAG-投诉未结` 的用户，**禁止**自动外呼与优惠 Push。
2. 触达顺序：Push → 短信 → AI 外呼 → 人工；每日单用户渠道合计 ≤3 次。
3. 非智能车进入 `non_smart` 池，只允许产品升级引导，不算续费率分母。
4. 高意向（intent_level=high）才允许转人工。
5. 触达前必须 `read_ai_outputs` / 读取共享标签；不得只靠部门私有名单。

## 与 Story2 对齐
Planning Skill `renewal_plan` 若读到未结投诉标签，应返回 `allow_outreach=false` 并给出阻断原因。
""",
        "policy/门店VI与非专卖红线.md": """# 门店 VI 与非专卖红线（合成）

## 禁止事项
- 同一营业面积内混售未授权竞品整车（`TAG-非专卖`）；
- 擅自更改门头主色与标准字体（`TAG-VI违规`）；
- 使用过期海报或错误价签模板。

## 巡检处置
1. Vision/巡检产出疑点报告；
2. 生成整改工单，写入 `due_date` 与 `verify_method`；
3. 连续两次 P0 违规，可影响返利钻石档资格。
""",
        "hr/员工制度问答摘要.md": """# 员工制度问答摘要（合成）

## 请假
- 年假按司龄阶梯；事假需直属上级审批。
- 门店导购调班需在排班系统提交，禁止口口相传。

## 信息安全
- 禁止导出真实用户手机号与完整 VIN 到私人设备。
- Demo/培训仅允许使用 QS0 合成车架号与脱敏手机号。
- 禁止将客户原声截图发到外部社群。

## 培训陪练
- 新坐席需完成「续航异常」「三包争议」「续费红线」三个场景陪练才可独立接听。
""",
        "hr/坐席质检SOP要点.md": """# 坐席质检 SOP 要点（合成）

## 必检项
1. 是否核对 VIN 与车型；
2. 是否复述用户问题并确认；
3. 是否告知下一步与时限；
4. 是否避免绝对化承诺（「一定」「绝对没问题」）。

## 风险话术词（示例）
- 「绝对没问题」「保证三天修好」「官方肯定全额退」

命中风险词 → 质检失败，进入辅导清单。
""",
        "product/车型卖点与竞品口径.md": """# 车型卖点与竞品口径（合成）

## E60 锂电旗舰
- 卖点：通勤续航、App 车控、防盗提醒。
- 话术禁区：不得承诺「实测续航=标称续航」。

## S9 都市通勤
- 卖点：轻量化、转向灵活、基础车联。
- 适合：短途上班族；不主推长途拉货场景。

## 对虚构竞品
- 北辰出行 Pulse X1：偏重外观，售后网点密度低于青枢（示意）。
- 云梭动力 Yuno S：价格带接近，强调价格战需用政策模拟器测算返利后再跟进。
- 星轨两轮 Orbit 7：主打年轻配色，渠道下沉快，需关注县域空白一网。
""",
        "product/OTA版本说明-v2.md": """# OTA 版本说明（合成）

| 版本 | 主要内容 | 已知问题 |
|------|----------|----------|
| v2.1.0 | 基础车控 | 绑车偶发超时 |
| v2.2.3 | 续航估算优化 | 低温估算偏差大 |
| v2.3.1 | 陡坡限速策略修正 | — |
| v2.4.0 | 推送订阅分类 | 部分机型需二次确认蓝牙权限 |

VoC 分析时可按 `ota_version` 做粗关联，不得直接断言「版本导致故障」除非有共现证据。
""",
        "channel/一代提货与颜色缺货话术.md": """# 一代提货与颜色缺货话术（合成）

## 缺货场景
「当前烈焰红在途有限，建议同价带星空灰替代，不影响返利累计台数。」

## 冲档场景
「您本月再提 188 台可到金牌档，预计返利增量约 2.8 万元（示意）。是否需要我帮您锁配额？」

## 红线
- 不得向一代承诺未排产颜色的准确到货日；
- 若该一代存在 P0 客诉未闭环，不主动推送冲档激励。
""",
        "channel/开店推进检查清单.md": """# 开店推进检查清单（合成）

1. 县域容量与竞品份额是否齐全；
2. 装修等级建议是否与支持额度匹配；
3. 新商首批订单与 1–3 月提货是否跟踪；
4. 加盟风控等级是否为 pass/supplement；
5. 开店甘特负责人与起止日是否落地。
""",
    }
    for rel, body in docs.items():
        _write_text(DATA / "knowledge" / rel, body)

    index = []
    for rel in docs:
        index.append({
            "kb_domain": rel.split("/")[0],
            "kb_doc_id": rel.replace("/", "__").replace(".md", ""),
            "path": f"knowledge/{rel}",
            "title": Path(rel).stem,
            "chars": len(docs[rel]),
        })
    _write_json(DATA / "knowledge" / "index.json", {
        "brand": "Qingshu Mobility",
        "documents": index,
        "total_docs": len(index),
        "total_chars": sum(len(v) for v in docs.values()),
    })


def write_seeds(customers, vehicles, tickets, renewals) -> None:
    # pick a complaint-open ticket for story 1/2
    open_complaint = next(
        t for t in tickets
        if t.get("tag_id") == "TAG-投诉未结" and t.get("ticket_status") == "open"
    )
    cust = next(c for c in customers if c["customer_id"] == open_complaint["customer_id"])
    veh = next(v for v in vehicles if v["vin"] == open_complaint["vin"])
    renew = next(
        (r for r in renewals if r["customer_id"] == cust["customer_id"] and r["vin"] == veh["vin"]),
        renewals[0],
    )
    _write_json(DATA / "seeds" / "story_1_fill_ticket.json", {
        "story": "Story1-产出资产化",
        "agent_type": "react",
        "skill_id": "fill_ticket",
        "input": {
            "text": open_complaint["desc_text"],
            "customer_id": cust["customer_id"],
            "vin": veh["vin"],
            "channel": "400",
        },
        "expect_write_ai_output": {
            "producer_skill": "fill_ticket",
            "consumer_allow": ["renewal_plan", "voc_tagging"],
            "payload_keys": ["ticket_id", "tag_id", "sentiment", "customer_id", "vin"],
        },
        "fixture_ticket_id": open_complaint["ticket_id"],
    })
    _write_json(DATA / "seeds" / "story_2_renewal_block.json", {
        "story": "Story2-跨类型消费并阻断触达",
        "agent_type": "planning",
        "skill_id": "renewal_plan",
        "input": {
            "customer_id": cust["customer_id"],
            "vin": veh["vin"],
        },
        "renewal_snapshot": renew,
        "expect": {
            "allow_outreach": False,
            "block_reason_contains": "投诉未结",
            "read_from_shared": True,
        },
    })
    _write_json(DATA / "seeds" / "demo_query_pack.json", {
        "sample_vins": [v["vin"] for v in vehicles[:5]],
        "sample_customer_ids": [c["customer_id"] for c in customers[:5]],
        "sample_dealer_ids": sorted({t["dealer_id"] for t in tickets if t.get("dealer_id")})[:5],
        "kb_smoke_queries": [
            "锂电车续航只有标称一半怎么排查",
            "2026Q3 银牌档提货返利点位是多少",
            "有未结投诉的用户能否 AI 外呼续费",
        ],
    })


def write_manifest(stats: dict) -> None:
    _write_json(DATA / "MANIFEST.json", {
        "brand": "Qingshu Mobility / 青枢出行",
        "generated_at": iso(datetime.now(timezone.utc)),
        "seed": SEED,
        "compliance": {
            "real_customer_data": False,
            "real_vin": False,
            "real_phone": False,
            "vin_prefix": "QS0",
            "phone_storage": "masked_only",
            "source": "fully_synthetic",
            "note": "全量合成；禁止入库任何真实客户/真实车企经营数据与真实 VIN/手机号",
        },
        "stats": stats,
    })
    _write_text(
        DATA / "README.md",
        f"""# data/ 合成数据说明

品牌：**青枢出行（Qingshu Mobility）**  
生成种子：`{SEED}`  
重生成：`python scripts/generate_synthetic_data.py`

## 合规

- 全量合成，**无**真实客户 / 合同 / 工单录音
- VIN 一律 `QS0…` 前缀
- 手机号仅 `phone_masked`（中间四位 ****）
- 禁止拷贝任何真实客户或真实车企材料入库

## 目录

| 路径 | 内容 |
|------|------|
| `OBJECT_CATALOG.md` | 名词对象分类 |
| `vocab/field_glossary.json` | 跨部门字段统一释义 |
| `vocab/tag_vocabulary.json` | 标签字典 |
| `entities/*.json` | 结构化实体 |
| `knowledge/**` | 非结构化长文本 |
| `seeds/*.json` | Story1/2 演示种子 |
| `MANIFEST.json` | 生成统计与合规声明 |

## 规模（本次）

{json.dumps(stats, ensure_ascii=False, indent=2)}
""",
    )


def main() -> None:
    # clean generated json/md under data (keep dirs)
    for sub in ("entities", "vocab", "knowledge", "seeds"):
        p = DATA / sub
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    f.unlink()

    write_object_catalog()
    write_field_glossary()
    tags = build_vocab()
    _write_json(DATA / "vocab" / "tag_vocabulary.json", {
        "version": tags[0]["tag_vocab_version"],
        "tags": tags,
    })

    regions, orgs = build_regions_orgs()
    dealers, stores, guides = build_dealers_stores_guides(regions, n_dealers=20)
    skus = build_skus()
    competitors = build_competitors()
    customers, vehicles, behaviors, renewals = build_customers_vehicles(120, stores)
    orders, inventory, policies, color_plans = build_orders_inventory(dealers, stores, skus, n_orders=80)
    tickets, voc = build_tickets_voc(customers, vehicles, stores, tags, n_tickets=120)
    telemetry = build_telemetry(vehicles)
    misc = build_misc(dealers, stores, skus, vehicles)

    ent = DATA / "entities"
    mapping = {
        "regions.json": regions,
        "orgs.json": orgs,
        "dealers.json": dealers,
        "stores.json": stores,
        "guides.json": guides,
        "skus.json": skus,
        "competitors.json": competitors,
        "customers.json": customers,
        "vehicles.json": vehicles,
        "user_behaviors.json": behaviors,
        "renewals.json": renewals,
        "orders.json": orders,
        "inventory.json": inventory,
        "policies.json": policies,
        "color_plans.json": color_plans,
        "tickets.json": tickets,
        "voc_feedback.json": voc,
        "telemetry.json": telemetry,
        "sales_metrics.json": misc["sales_metrics"],
        "dealer_health.json": misc["dealer_health"],
        "retail_daily.json": misc["retail_daily"],
        "campaigns.json": misc["campaigns"],
        "contents.json": misc["contents"],
        "outreach.json": misc["outreach"],
        "quality_checks.json": misc["quality_checks"],
        "inspections.json": misc["inspections"],
        "finance_expense.json": misc["finance_expense"],
        "alerts.json": misc["alerts"],
        "store_dev.json": misc["store_dev"],
        "risks.json": misc["risks"],
        "capability_catalog.json": misc["capability_catalog"],
        # 注意：department_flows.json 为手工维护的 Planning 编排契约，切勿加入本 mapping，避免被清空覆盖。
    }
    for name, payload in mapping.items():
        _write_json(ent / name, payload)

    write_knowledge()
    write_seeds(customers, vehicles, tickets, renewals)

    stats = {name: len(payload) if isinstance(payload, list) else 1 for name, payload in mapping.items()}
    stats["tag_vocabulary"] = len(tags)
    stats["knowledge_docs"] = len(list((DATA / "knowledge").rglob("*.md")))
    stats["field_glossary"] = len(json.loads((DATA / "vocab" / "field_glossary.json").read_text(encoding="utf-8"))["fields"])
    write_manifest(stats)

    # 合规自检
    for v in vehicles:
        assert v["vin"].startswith("QS0") and len(v["vin"]) == 17, v["vin"]
    for c in customers:
        assert "****" in c["phone_masked"] and len(c["phone_masked"]) == 11, c["phone_masked"]
    assert any(t["tag_id"] == "TAG-投诉未结" and t["ticket_status"] == "open" for t in tickets)

    print("OK synthetic data written under", DATA)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
