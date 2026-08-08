"""共享枚举：来自《标准字段定义表》中的有限取值。"""

from __future__ import annotations

from enum import StrEnum


class PeriodType(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    CUSTOM = "custom"


class TrafficLight(StrEnum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class OrgLevel(StrEnum):
    NATION = "nation"
    WARZONE = "warzone"
    SUBZONE = "subzone"
    BLOCK = "block"
    DEALER = "dealer"
    OUTLET = "outlet"
    STORE = "store"


class StoreType(StrEnum):
    EXCLUSIVE = "exclusive"
    MIXED = "mixed"
    NON_EXCLUSIVE = "non_exclusive"


class StoreGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class IdentityType(StrEnum):
    END_USER = "end_user"
    DEALER = "dealer"
    PROSPECT = "prospect"
    EMPLOYEE = "employee"


class OneIdMatchMethod(StrEnum):
    PHONE = "phone"
    DEVICE = "device"
    VIN = "vin"
    PROBABILISTIC = "probabilistic"


class RfmSegment(StrEnum):
    HIGH_VALUE = "high_value"
    POTENTIAL = "potential"
    SILENT = "silent"
    CHURN_RISK = "churn_risk"


class PaidType(StrEnum):
    NEW_PURCHASE = "new_purchase"
    RENEW = "renew"
    UNKNOWN = "unknown"


class RenewPoolLayer(StrEnum):
    T_30 = "T-30"
    T_7 = "T-7"
    SLEEP = "sleep"
    NON_SMART = "non_smart"


class OutreachChannel(StrEnum):
    PUSH = "push"
    SMS = "sms"
    AI_CALL = "ai_call"
    HUMAN = "human"
    WECOM = "wecom"


class IntentLevel(StrEnum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class BatteryType(StrEnum):
    LEAD_ACID = "lead_acid"
    LITHIUM = "lithium"
    GRAPHENE = "graphene"


class HotSlowFlag(StrEnum):
    HOT = "hot"
    NORMAL = "normal"
    SLOW = "slow"


class SelfCoverageFlag(StrEnum):
    YES = "yes"
    WEAK = "weak"
    BLANK = "blank"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdmissionSuggest(StrEnum):
    PASS = "pass"
    SUPPLEMENT = "supplement"
    REJECT = "reject"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING_AUDIT = "pending_audit"
    APPROVED = "approved"
    REJECTED = "rejected"
    SHIPPED = "shipped"
    COMPLETED = "completed"


class AuditResult(StrEnum):
    PASS = "pass"
    REJECT_SHORTAGE = "reject_shortage"
    SUGGEST_SUBSTITUTE = "suggest_substitute"


class ShortageRootCause(StrEnum):
    PRODUCTION = "production"
    LOGISTICS = "logistics"
    COLOR_PLAN = "color_plan"
    SUPPLY = "supply"


class PayStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    EXCEPTION = "exception"


class TicketType(StrEnum):
    FAULT = "fault"
    CONSULT = "consult"
    COMPLAINT = "complaint"
    OTHER = "other"


class FaultCategory(StrEnum):
    BATTERY = "battery"
    MOTOR = "motor"
    BRAKE = "brake"
    CONTROLLER = "controller"
    CHARGING = "charging"
    DASHBOARD = "dashboard"
    FRAME = "frame"
    LIGHTING = "lighting"
    TIRE = "tire"
    OTHER = "other"


class TicketStatus(StrEnum):
    OPEN = "open"
    PROCESSING = "processing"
    CLOSED = "closed"


class SopPassFail(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class Sentiment(StrEnum):
    POS = "pos"
    NEU = "neu"
    NEG = "neg"


class ClueConfidence(StrEnum):
    WEAK = "weak"
    MEDIUM = "medium"


class PrRiskLevel(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class CoverDim(StrEnum):
    VEHICLE = "vehicle"
    NON_VEHICLE = "non_vehicle"
    ALL = "all"


class ModuleName(StrEnum):
    APP = "app"
    MINIAPP = "miniapp"
    WEBSITE = "website"
    HOTLINE = "hotline"
    AFTERSALES = "aftersales"


class TagDomain(StrEnum):
    PRODUCT = "product"
    SERVICE = "service"
    APP = "app"
    CHANNEL = "channel"
    RISK = "risk"


class QcResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class RecallLevel(StrEnum):
    WATCH = "watch"
    TARGETED = "targeted"
    RECALL_EVAL = "recall_eval"


class PassFail(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class MatchStatus(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"


class AlertType(StrEnum):
    SALES_DROP = "sales_drop"
    COMPLIANCE = "compliance"
    SHORTAGE = "shortage"
    COMPLAINT = "complaint"
    COMPETITOR = "competitor"


class Severity(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class StepStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class ProposalLevel(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ClauseRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class KbDomain(StrEnum):
    REPAIR = "repair"
    POLICY = "policy"
    HR = "hr"
    PRODUCT = "product"
    CHANNEL = "channel"
