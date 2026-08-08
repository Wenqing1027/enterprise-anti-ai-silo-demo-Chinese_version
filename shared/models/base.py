"""Pydantic 基类配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class QingshuModel(BaseModel):
    """青枢出行统一数据模型基类。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False,
    )
