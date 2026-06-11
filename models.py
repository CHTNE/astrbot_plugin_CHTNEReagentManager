"""数据模型定义 - 化学试剂信息管理系统"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import uuid


# 合法的规格单位
VALID_UNITS = {"g", "kg", "ml", "l"}

# 质量单位转换系数（以 g 为基准）
MASS_CONVERSION = {
    "g": 1.0,
    "kg": 1000.0,
}

# 体积单位转换系数（以 ml 为基准）
VOLUME_CONVERSION = {
    "ml": 1.0,
    "l": 1000.0,
}

# 单位类别
MASS_UNITS = {"g", "kg"}
VOLUME_UNITS = {"ml", "l"}


def generate_id() -> str:
    """生成短唯一 ID（8 位十六进制）。"""
    return uuid.uuid4().hex[:8]


def parse_spec(spec_str: str) -> tuple[float, str] | None:
    """解析规格字符串，如 '100g' -> (100.0, 'g')。
    返回 None 表示解析失败或单位不合法。"""
    spec_str = spec_str.strip().lower()
    if not spec_str:
        return None

    # 尝试匹配数字+单位
    for i, ch in enumerate(spec_str):
        if ch.isalpha():
            value_str = spec_str[:i]
            unit = spec_str[i:]
            if unit not in VALID_UNITS:
                return None
            try:
                value = float(value_str)
                if value <= 0:
                    return None
                return (value, unit)
            except ValueError:
                return None
    return None


def normalize_to_base_unit(value: float, unit: str) -> float:
    """将带单位的数值转换为基准单位（g 或 ml）。"""
    if unit in MASS_CONVERSION:
        return value * MASS_CONVERSION[unit]
    elif unit in VOLUME_CONVERSION:
        return value * VOLUME_CONVERSION[unit]
    raise ValueError(f"未知单位: {unit}")


def convert_unit(value: float, from_unit: str, to_unit: str) -> float | None:
    """在同类别（质量/体积）之间转换单位。不同类别返回 None。"""
    if from_unit == to_unit:
        return value

    # 判断类别
    from_is_mass = from_unit in MASS_UNITS
    to_is_mass = to_unit in MASS_UNITS
    from_is_vol = from_unit in VOLUME_UNITS
    to_is_vol = to_unit in VOLUME_UNITS

    if from_is_mass and to_is_mass:
        base = value * MASS_CONVERSION[from_unit]
        return base / MASS_CONVERSION[to_unit]
    elif from_is_vol and to_is_vol:
        base = value * VOLUME_CONVERSION[from_unit]
        return base / VOLUME_CONVERSION[to_unit]
    else:
        return None  # 不同类别无法转换


def format_quantity(value: float, unit: str) -> str:
    """格式化数量字符串，如 (100.0, 'g') -> '100.0g'。"""
    # 去掉多余的 .0
    if value == int(value):
        return f"{int(value)}{unit}"
    return f"{value}{unit}"


@dataclass
class Reagent:
    """试剂数据模型。"""
    id: str = field(default_factory=generate_id)
    name: str = ""
    branch: str = ""
    spec_value: float = 0.0       # 规格数值（以 spec_unit 为单位）
    spec_unit: str = "g"           # 规格单位
    unit_price: float = 0.0        # 单价（元/规格单位）
    stock: float = 0.0             # 库存（以 spec_unit 为单位）

    @property
    def specification(self) -> str:
        """返回规格字符串，如 '100g'。"""
        return format_quantity(self.spec_value, self.spec_unit)

    @property
    def total_price(self) -> float:
        """总价 = 库存 × 单价。"""
        return round(self.stock * self.unit_price, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "branch": self.branch,
            "spec_value": self.spec_value,
            "spec_unit": self.spec_unit,
            "unit_price": self.unit_price,
            "stock": self.stock,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Reagent":
        return cls(
            id=d.get("id", generate_id()),
            name=d.get("name", ""),
            branch=d.get("branch", ""),
            spec_value=d.get("spec_value", 0.0),
            spec_unit=d.get("spec_unit", "g"),
            unit_price=d.get("unit_price", 0.0),
            stock=d.get("stock", 0.0),
        )

    def display_name(self) -> str:
        """返回用于展示的名称，如 '硝酸银(100g) [市中分社]'。"""
        return f"{self.name}({self.specification}) [{self.branch}]"


@dataclass
class ChangeRecord:
    """单次修改记录。"""
    timestamp: str = ""              # 修改时间（YYYY-MM-DD HH:MM）
    user_nickname: str = ""          # 修改人昵称
    user_id: str = ""                # 修改人 ID
    changes: list[str] = field(default_factory=list)  # 每一项是 "属性: 旧值 → 新值" 或描述

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "user_nickname": self.user_nickname,
            "user_id": self.user_id,
            "changes": self.changes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeRecord":
        return cls(
            timestamp=d.get("timestamp", ""),
            user_nickname=d.get("user_nickname", ""),
            user_id=d.get("user_id", ""),
            changes=d.get("changes", []),
        )

    def oneline(self) -> str:
        """单行摘要。"""
        return f"[{self.timestamp}] {', '.join(self.changes)}"

    def detail(self) -> str:
        """详细描述，含改动人信息。"""
        return (f"[{self.timestamp}] {self.user_nickname}({self.user_id}) "
                f"{', '.join(self.changes)}")


@dataclass
class ReagentLog:
    """某个试剂的所有修改记录。"""
    reagent_id: str = ""             # 试剂 ID（也可能是已删除试剂的历史记录）
    reagent_name: str = ""           # 试剂名称快照
    reagent_branch: str = ""         # 试剂分社快照
    records: list[ChangeRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reagent_id": self.reagent_id,
            "reagent_name": self.reagent_name,
            "reagent_branch": self.reagent_branch,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReagentLog":
        return cls(
            reagent_id=d.get("reagent_id", ""),
            reagent_name=d.get("reagent_name", ""),
            reagent_branch=d.get("reagent_branch", ""),
            records=[ChangeRecord.from_dict(r) for r in d.get("records", [])],
        )
