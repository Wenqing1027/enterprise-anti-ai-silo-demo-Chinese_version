"""青枢出行 · 统一数据模型（shared/models）。

字段口径来自 docs/标准字段定义表.csv，全量实体，不按优先级裁剪。
"""

from __future__ import annotations

from shared.models.base import QingshuModel
from shared.models.activation import (
    Activation,
    O2O,
)
from shared.models.ai_assets import (
    AIOutput,
    TagVocabulary,
    CapabilityCatalog,
    RunLog,
)
from shared.models.alert import (
    Alert,
    Collab,
)
from shared.models.channel import (
    Dealer,
    Store,
    Guide,
)
from shared.models.commerce import (
    Order,
    Inventory,
    Policy,
    ColorPlan,
)
from shared.models.customer import (
    Customer,
    UserBehavior,
    Renewal,
)
from shared.models.finance import (
    Finance,
)
from shared.models.inspection import (
    Inspection,
    Brand,
)
from shared.models.iot import (
    Telemetry,
)
from shared.models.meta import (
    ReportMeta,
)
from shared.models.org import (
    Org,
    Region,
)
from shared.models.product import (
    SKU,
    Competitor,
)
from shared.models.quality import (
    Quality,
)
from shared.models.retail import (
    Retail,
    Campaign,
    Content,
    Outreach,
)
from shared.models.sales import (
    SalesMetric,
    Health,
)
from shared.models.service import (
    Ticket,
    VoC,
)
from shared.models.store_dev import (
    StoreDev,
    Risk,
)
from shared.models.support import (
    Process,
    HR,
    Legal,
    Knowledge,
)
from shared.models.vehicle import (
    Vehicle,
)
from shared.models import enums as enums

__all__ = [
    "QingshuModel",
    "enums",
    "AIOutput",
    "Activation",
    "Alert",
    "Brand",
    "Campaign",
    "CapabilityCatalog",
    "Collab",
    "ColorPlan",
    "Competitor",
    "Content",
    "Customer",
    "Dealer",
    "Finance",
    "Guide",
    "HR",
    "Health",
    "Inspection",
    "Inventory",
    "Knowledge",
    "Legal",
    "O2O",
    "Order",
    "Org",
    "Outreach",
    "Policy",
    "Process",
    "Quality",
    "Region",
    "Renewal",
    "ReportMeta",
    "Retail",
    "Risk",
    "RunLog",
    "SKU",
    "SalesMetric",
    "Store",
    "StoreDev",
    "TagVocabulary",
    "Telemetry",
    "Ticket",
    "UserBehavior",
    "Vehicle",
    "VoC",
]
