"""Unified DataFetcher：唯一数据访问入口。

原则：
1. 按数据来源组织内部适配器（entities / knowledge / vocab）
2. 只读不写
3. 返回 shared.models 统一模型（及 KbChunk）
4. 数据来源对上层透明（方法签名与返回值不含 source/path）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.datafetcher.coerce import to_model
from shared.datafetcher.sources.entities import EntitySource
from shared.datafetcher.sources.knowledge import KnowledgeSource
from shared.datafetcher.sources.vocab import VocabSource
from shared.datafetcher.types import KbChunk
from shared.models.ai_assets import CapabilityCatalog, TagVocabulary
from shared.models.alert import Alert
from shared.models.channel import Dealer, Guide, Store
from shared.models.commerce import ColorPlan, Inventory, Order, Policy
from shared.models.customer import Customer, Renewal, UserBehavior
from shared.models.finance import Finance
from shared.models.inspection import Inspection
from shared.models.iot import Telemetry
from shared.models.org import Org, Region
from shared.models.product import Competitor, SKU
from shared.models.quality import Quality
from shared.models.retail import Campaign, Content, Outreach, Retail
from shared.models.sales import Health, SalesMetric
from shared.models.service import Ticket, VoC
from shared.models.store_dev import Risk, StoreDev
from shared.models.vehicle import Vehicle
from shared.store.paths import DATA_DIR


class DataFetcher:
    """全 Demo 唯一 DataFetcher。禁止在 agents/* 内复制同类实现。"""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or DATA_DIR
        self._entities = EntitySource(self._data_dir / "entities")
        self._knowledge = KnowledgeSource(self._data_dir / "knowledge")
        self._vocab = VocabSource(self._data_dir / "vocab")

    def reload(self) -> None:
        """测试/重生成数据后刷新缓存。"""
        self._entities.reload()
        self._knowledge.reload()
        self._vocab.reload()

    # ------------------------------------------------------------------
    # 主数据：客户 / 车辆 / 渠道
    # ------------------------------------------------------------------

    def get_customer(self, customer_id: str) -> Customer | None:
        row = self._entities.by_key("customers", "customer_id", customer_id)
        return to_model(Customer, row) if row else None

    def list_customers(self, *, limit: int | None = None) -> list[Customer]:
        return [to_model(Customer, r) for r in self._entities.find_many("customers", limit=limit)]

    def get_vehicle(self, vin: str) -> Vehicle | None:
        row = self._entities.by_key("vehicles", "vin", vin)
        return to_model(Vehicle, row) if row else None

    def list_vehicles(
        self,
        *,
        customer_id: str | None = None,
        model: str | None = None,
        limit: int | None = None,
    ) -> list[Vehicle]:
        def pred(r: dict[str, Any]) -> bool:
            if customer_id is not None and r.get("customer_id") != customer_id:
                return False
            if model is not None and r.get("vehicle_model") != model:
                return False
            return True

        return [to_model(Vehicle, r) for r in self._entities.find_many("vehicles", pred, limit=limit)]

    def get_dealer(self, dealer_id: str) -> Dealer | None:
        row = self._entities.by_key("dealers", "dealer_id", dealer_id)
        return to_model(Dealer, row) if row else None

    def get_store(self, store_id: str) -> Store | None:
        row = self._entities.by_key("stores", "store_id", store_id)
        return to_model(Store, row) if row else None

    def list_stores(self, *, dealer_id: str | None = None) -> list[Store]:
        pred = (lambda r: r.get("dealer_id") == dealer_id) if dealer_id else None
        return [to_model(Store, r) for r in self._entities.find_many("stores", pred)]

    def get_guide(self, guide_id: str) -> Guide | None:
        row = self._entities.by_key("guides", "guide_id", guide_id)
        return to_model(Guide, row) if row else None

    def get_sku(self, sku_id: str) -> SKU | None:
        row = self._entities.by_key("skus", "sku_id", sku_id)
        return to_model(SKU, row) if row else None

    def list_skus(self, *, model: str | None = None) -> list[SKU]:
        # sku_id like SKU-E60-BK — filter by model substring if provided
        rows = self._entities.all("skus")
        if model:
            rows = [r for r in rows if model in str(r.get("sku_id", "")) or model in str(r.get("sku_name", ""))]
        return [to_model(SKU, r) for r in rows]

    def get_org(self, org_id: str) -> Org | None:
        row = self._entities.by_key("orgs", "org_id", org_id)
        return to_model(Org, row) if row else None

    def list_regions(self) -> list[Region]:
        return [to_model(Region, r) for r in self._entities.all("regions")]

    def list_competitors(self) -> list[Competitor]:
        return [to_model(Competitor, r) for r in self._entities.all("competitors")]

    # ------------------------------------------------------------------
    # 交易：订单 / 库存 / 政策
    # ------------------------------------------------------------------

    def get_order(self, order_id: str) -> Order | None:
        row = self._entities.by_key("orders", "order_id", order_id)
        return to_model(Order, row) if row else None

    def list_orders(
        self,
        *,
        dealer_id: str | None = None,
        store_id: str | None = None,
        sku_id: str | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        def pred(r: dict[str, Any]) -> bool:
            if dealer_id is not None and r.get("dealer_id") != dealer_id:
                return False
            if store_id is not None and r.get("store_id") != store_id:
                return False
            if sku_id is not None and r.get("sku_id") != sku_id:
                return False
            return True

        return [to_model(Order, r) for r in self._entities.find_many("orders", pred, limit=limit)]

    def list_inventory(
        self,
        *,
        sku_id: str | None = None,
        store_id: str | None = None,
        dealer_id: str | None = None,
    ) -> list[Inventory]:
        def pred(r: dict[str, Any]) -> bool:
            if sku_id is not None and r.get("sku_id") != sku_id:
                return False
            if store_id is not None and r.get("store_id") != store_id:
                return False
            if dealer_id is not None and r.get("dealer_id") != dealer_id:
                return False
            return True

        return [to_model(Inventory, r) for r in self._entities.find_many("inventory", pred)]

    def get_policy(self, dealer_id: str) -> Policy | None:
        row = self._entities.by_key("policies", "dealer_id", dealer_id)
        return to_model(Policy, row) if row else None

    def list_color_plans(self, *, week: str | None = None) -> list[ColorPlan]:
        pred = (lambda r: r.get("color_plan_week") == week) if week else None
        return [to_model(ColorPlan, r) for r in self._entities.find_many("color_plans", pred)]

    # ------------------------------------------------------------------
    # 服务 / VoC / 续费 / IoT
    # ------------------------------------------------------------------

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        row = self._entities.by_key("tickets", "ticket_id", ticket_id)
        return to_model(Ticket, row) if row else None

    def list_tickets(
        self,
        *,
        customer_id: str | None = None,
        vin: str | None = None,
        ticket_status: str | None = None,
        tag_id: str | None = None,
        limit: int | None = None,
    ) -> list[Ticket]:
        def pred(r: dict[str, Any]) -> bool:
            if customer_id is not None and r.get("customer_id") != customer_id:
                return False
            if vin is not None and r.get("vin") != vin:
                return False
            if ticket_status is not None and r.get("ticket_status") != ticket_status:
                return False
            if tag_id is not None and r.get("tag_id") != tag_id:
                return False
            return True

        return [to_model(Ticket, r) for r in self._entities.find_many("tickets", pred, limit=limit)]

    def list_voc(
        self,
        *,
        customer_id: str | None = None,
        tag_id: str | None = None,
        limit: int | None = None,
    ) -> list[VoC]:
        def pred(r: dict[str, Any]) -> bool:
            if customer_id is not None and r.get("customer_id") != customer_id:
                return False
            if tag_id is not None and r.get("tag_id") != tag_id:
                return False
            return True

        return [to_model(VoC, r) for r in self._entities.find_many("voc_feedback", pred, limit=limit)]

    def get_renewal(self, customer_id: str, vin: str | None = None) -> Renewal | None:
        if vin:
            row = self._entities.by_keys("renewals", customer_id=customer_id, vin=vin)
        else:
            row = self._entities.find_one("renewals", lambda r: r.get("customer_id") == customer_id)
        return to_model(Renewal, row) if row else None

    def list_renewals(
        self,
        *,
        pool_layer: str | None = None,
        due_only: bool = False,
        limit: int | None = None,
    ) -> list[Renewal]:
        def pred(r: dict[str, Any]) -> bool:
            if pool_layer is not None and r.get("renew_pool_layer") != pool_layer:
                return False
            if due_only and not r.get("due_renew_flag"):
                return False
            return True

        return [to_model(Renewal, r) for r in self._entities.find_many("renewals", pred, limit=limit)]

    def get_user_behavior(self, customer_id: str, vin: str | None = None) -> UserBehavior | None:
        if vin:
            row = self._entities.by_keys("user_behaviors", customer_id=customer_id, vin=vin)
        else:
            row = self._entities.find_one(
                "user_behaviors", lambda r: r.get("customer_id") == customer_id
            )
        return to_model(UserBehavior, row) if row else None

    def get_telemetry(self, vin: str) -> Telemetry | None:
        row = self._entities.by_key("telemetry", "vin", vin)
        return to_model(Telemetry, row) if row else None

    # ------------------------------------------------------------------
    # 经营切片 / 质检 / 其他实体
    # ------------------------------------------------------------------

    def list_sales_metrics(self, *, org_id: str | None = None) -> list[SalesMetric]:
        pred = (lambda r: r.get("org_id") == org_id) if org_id else None
        return [to_model(SalesMetric, r) for r in self._entities.find_many("sales_metrics", pred)]

    def get_dealer_health(self, dealer_id: str) -> Health | None:
        row = self._entities.by_key("dealer_health", "dealer_id", dealer_id)
        return to_model(Health, row) if row else None

    def list_retail_daily(self, *, store_id: str | None = None) -> list[Retail]:
        pred = (lambda r: r.get("store_id") == store_id) if store_id else None
        return [to_model(Retail, r) for r in self._entities.find_many("retail_daily", pred)]

    def list_campaigns(self) -> list[Campaign]:
        return [to_model(Campaign, r) for r in self._entities.all("campaigns")]

    def list_contents(self) -> list[Content]:
        return [to_model(Content, r) for r in self._entities.all("contents")]

    def list_outreach(self) -> list[Outreach]:
        return [to_model(Outreach, r) for r in self._entities.all("outreach")]

    def list_quality_checks(self, *, vin: str | None = None) -> list[Quality]:
        pred = (lambda r: r.get("vin") == vin) if vin else None
        return [to_model(Quality, r) for r in self._entities.find_many("quality_checks", pred)]

    def list_inspections(self, *, store_id: str | None = None) -> list[Inspection]:
        pred = (lambda r: r.get("store_id") == store_id) if store_id else None
        return [to_model(Inspection, r) for r in self._entities.find_many("inspections", pred)]

    def list_finance_expenses(self) -> list[Finance]:
        return [to_model(Finance, r) for r in self._entities.all("finance_expense")]

    def list_alerts(self, *, dealer_id: str | None = None) -> list[Alert]:
        pred = (lambda r: r.get("dealer_id") == dealer_id) if dealer_id else None
        return [to_model(Alert, r) for r in self._entities.find_many("alerts", pred)]

    def list_store_dev(self) -> list[StoreDev]:
        return [to_model(StoreDev, r) for r in self._entities.all("store_dev")]

    def get_risk(self, dealer_id: str) -> Risk | None:
        row = self._entities.by_key("risks", "dealer_id", dealer_id)
        return to_model(Risk, row) if row else None

    # ------------------------------------------------------------------
    # 知识库（RAG）
    # ------------------------------------------------------------------

    def search_kb(
        self,
        query: str,
        *,
        domain: str | None = None,
        top_k: int = 5,
    ) -> list[KbChunk]:
        """按域检索知识库（块级 TF-IDF）；domain 例：repair / policy / hr / product / channel。"""
        hits = self._knowledge.search_chunks(query, domain=domain, top_k=top_k)
        out: list[KbChunk] = []
        for hit in hits:
            out.append(
                KbChunk(
                    kb_domain=hit.kb_domain,
                    kb_doc_id=hit.kb_doc_id,
                    kb_chunk_id=hit.kb_chunk_id,
                    title=hit.title or hit.section_path,
                    content=hit.content,
                    kb_score=hit.score,
                )
            )
        return out

    def get_kb_document(self, kb_doc_id: str) -> KbChunk | None:
        doc = self._knowledge.get_doc(kb_doc_id)
        if not doc:
            return None
        return KbChunk(
            kb_domain=doc.kb_domain,
            kb_doc_id=doc.kb_doc_id,
            kb_chunk_id=f"{doc.kb_doc_id}#full",
            title=doc.title,
            content=doc.content,
            kb_score=1.0,
        )

    def get_kb_chunk(self, kb_chunk_id: str) -> KbChunk | None:
        """按稳定 chunk id 取片段（供 RAG 引用回读）。"""
        hit = self._knowledge.get_chunk(kb_chunk_id)
        if not hit:
            return None
        return KbChunk(
            kb_domain=hit.kb_domain,
            kb_doc_id=hit.kb_doc_id,
            kb_chunk_id=hit.kb_chunk_id,
            title=hit.title or hit.section_path,
            content=hit.content,
            kb_score=hit.score,
        )

    def list_kb_domains(self) -> list[str]:
        return self._knowledge.list_domains()

    # ------------------------------------------------------------------
    # 共享语义 / 能力目录
    # ------------------------------------------------------------------

    def get_tag(self, tag_id: str) -> TagVocabulary | None:
        row = self._vocab.tag_by_id(tag_id)
        return to_model(TagVocabulary, row) if row else None

    def list_tags(self, *, domain: str | None = None) -> list[TagVocabulary]:
        rows = self._vocab.tags()
        if domain:
            rows = [r for r in rows if r.get("tag_domain") == domain]
        return [to_model(TagVocabulary, r) for r in rows]

    def list_capabilities(self) -> list[CapabilityCatalog]:
        return [
            to_model(CapabilityCatalog, r)
            for r in self._entities.all("capability_catalog")
        ]

    def get_capability(self, skill_id: str) -> CapabilityCatalog | None:
        row = self._entities.by_key("capability_catalog", "skill_id", skill_id)
        return to_model(CapabilityCatalog, row) if row else None

    # ------------------------------------------------------------------
    # 诊断（不上抛给 Agent 业务逻辑；仅运维/测试）
    # ------------------------------------------------------------------

    def describe_sources(self) -> dict[str, str]:
        """可选调试信息：说明内部来源划分。Agent/Tool 层不应依赖此方法。"""
        return {
            "entities": str(self._data_dir / "entities"),
            "knowledge": str(self._data_dir / "knowledge"),
            "vocab": str(self._data_dir / "vocab"),
            "contract": "read_only; returns unified shared.models; source opaque to callers",
        }


# 进程内默认单例
default_fetcher = DataFetcher()
