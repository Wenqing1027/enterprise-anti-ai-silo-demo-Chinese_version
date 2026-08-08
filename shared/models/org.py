"""数据模型 · org（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import OrgLevel

class Org(QingshuModel):
    """组织 · Org。字段来自《标准字段定义表》。"""

    org_id: str | None = Field(
        default=None,
        description="组织ID。组织节点唯一ID",
        json_schema_extra={"example": "WZ-EAST"},
    )
    org_name: str | None = Field(
        default=None,
        description="组织名称。组织显示名",
        json_schema_extra={"example": "东区战区"},
    )
    org_level: OrgLevel | None = Field(
        default=None,
        description="组织层级。nation|warzone|subzone|block|dealer|outlet|store",
        json_schema_extra={"example": "warzone"},
    )
    parent_org_id: str | None = Field(
        default=None,
        description="上级组织ID。组织树父节点",
        json_schema_extra={"example": "NATION-CN"},
    )
    org_path: str | None = Field(
        default=None,
        description="组织路径。完整层级路径",
        json_schema_extra={"example": "全国/东区/苏南/一代A"},
    )

class Region(QingshuModel):
    """组织 · Region。字段来自《标准字段定义表》。"""

    province: str | None = Field(
        default=None,
        description="省份。行政区-省",
        json_schema_extra={"example": "江苏"},
    )
    city: str | None = Field(
        default=None,
        description="城市。行政区-市",
        json_schema_extra={"example": "南京"},
    )
    county_code: str | None = Field(
        default=None,
        description="区县编码。国标区县码",
        json_schema_extra={"example": "320115"},
    )
    county_name: str | None = Field(
        default=None,
        description="区县名称。区县名",
        json_schema_extra={"example": "江宁区"},
    )
