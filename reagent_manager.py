"""核心业务逻辑 - 试剂管理"""

import json
import os
from pathlib import Path
from typing import Optional

from models import (
    Reagent, generate_id, parse_spec, format_quantity,
    VALID_UNITS, convert_unit,
)
from utils import find_by_id_or_name


class ReagentManager:
    """试剂信息管理核心类。"""

    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = str(self._data_dir / "reagents.json")
        self._branches_file = str(self._data_dir / "branches.json")
        self._bindings_file = str(self._data_dir / "bindings.json")

        self._reagents: list[Reagent] = []
        self._branches: list[str] = []
        self._bindings: dict[str, str] = {}  # sender_id -> branch_name

        self._load()

    # ---------- 持久化 ----------

    def _load(self):
        """从文件加载所有数据。"""
        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._reagents = [Reagent.from_dict(d) for d in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self._reagents = []

        try:
            with open(self._branches_file, "r", encoding="utf-8") as f:
                self._branches = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._branches = []

        try:
            with open(self._bindings_file, "r", encoding="utf-8") as f:
                self._bindings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._bindings = {}

    def _save(self):
        """保存所有数据到文件。"""
        with open(self._data_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._reagents], f, ensure_ascii=False, indent=2)
        with open(self._branches_file, "w", encoding="utf-8") as f:
            json.dump(self._branches, f, ensure_ascii=False, indent=2)
        with open(self._bindings_file, "w", encoding="utf-8") as f:
            json.dump(self._bindings, f, ensure_ascii=False, indent=2)

    # ---------- 分社管理 ----------

    def add_branch(self, name: str) -> str:
        """新建分社。返回操作结果消息。"""
        name = name.strip()
        if not name:
            return "❌ 分社名不能为空。"
        if name in self._branches:
            return f"⚠️ 分社「{name}」已存在。"
        self._branches.append(name)
        self._save()
        return f"✅ 已新建分社「{name}」。"

    def list_branches(self) -> str:
        """列出所有分社。"""
        if not self._branches:
            return "📋 当前没有任何分社。"
        lines = ["📋 当前分社列表："]
        for i, b in enumerate(self._branches, 1):
            lines.append(f"  {i}. {b}")
        return "\n".join(lines)

    def branch_exists(self, name: str) -> bool:
        return name.strip() in self._branches

    # ---------- 绑定管理 ----------

    def bind_user(self, sender_id: str, branch: str) -> str:
        """绑定用户与分社。"""
        branch = branch.strip()
        if not self.branch_exists(branch):
            return f"❌ 分社「{branch}」不存在，请先使用 /ram addfs 创建。"
        self._bindings[sender_id] = branch
        self._save()
        return f"✅ 已将您绑定到分社「{branch}」。此后您的命令默认使用该分社。"

    def unbind_user(self, sender_id: str, branch: str) -> str:
        """解绑用户与分社。"""
        branch = branch.strip()
        if sender_id not in self._bindings:
            return "⚠️ 您当前没有绑定任何分社。"
        if self._bindings.get(sender_id) != branch:
            return f"⚠️ 您当前绑定的分社是「{self._bindings[sender_id]}」，而非「{branch}」。"
        del self._bindings[sender_id]
        self._save()
        return f"✅ 已解除与分社「{branch}」的绑定。"

    def get_user_branch(self, sender_id: str) -> str | None:
        """获取用户绑定的分社。"""
        return self._bindings.get(sender_id)

    # ---------- 试剂查询辅助 ----------

    def _find_reagents(self, name_or_id: str, branch: str | None = None) -> tuple[list[Reagent], bool]:
        """查找试剂。branch 为 None 时不限制分社。
        返回 (匹配列表, 是否精确ID匹配)。"""
        if branch:
            candidates = [r for r in self._reagents if r.branch == branch]
        else:
            candidates = list(self._reagents)
        return find_by_id_or_name(name_or_id, candidates)

    def _check_duplicates(self, matches: list[Reagent], is_id_match: bool) -> str | None:
        """检查是否有重复匹配。如果有，返回提示消息；否则返回 None。"""
        if is_id_match:
            return None  # ID 精确匹配，不重复
        if len(matches) == 0:
            return None
        if len(matches) > 1:
            lines = ["⚠️ 找到多个匹配的试剂，请使用 ID 精确指定："]
            for r in matches:
                lines.append(f"  - ID: {r.id} | {r.display_name()} | 库存: {format_quantity(r.stock, r.spec_unit)}")
            return "\n".join(lines)
        return None

    # ---------- 添加试剂 ----------

    def add_reagent(self, name: str, branch: str, spec_str: str,
                    unit_price: float, force_new: bool = False,
                    force_cover: bool = False) -> str:
        """添加试剂。"""
        name = name.strip()
        branch = branch.strip()

        if not self.branch_exists(branch):
            return f"❌ 分社「{branch}」不存在，请先使用 /ram addfs 创建。"

        # 解析规格
        parsed = parse_spec(spec_str)
        if parsed is None:
            return f"❌ 规格「{spec_str}」格式错误。规格单位只能是 g/kg/ml/l 之一，如 100g、500ml。"

        spec_value, spec_unit = parsed

        # 检查同名同分社试剂
        existing = [r for r in self._reagents
                    if r.name.lower() == name.lower() and r.branch == branch]

        if existing and not force_new and not force_cover:
            lines = [f"⚠️ 分社「{branch}」下已存在试剂「{name}」："]
            for r in existing:
                lines.append(f"  - ID: {r.id} | {r.specification} | 单价: {r.unit_price}元/{r.spec_unit} | 库存: {format_quantity(r.stock, r.spec_unit)}")
            lines.append("\n请选择操作：")
            lines.append("  /ram add -n ...   → 新建一个（自动追加区分符）")
            lines.append("  /ram add -c ...   → 覆盖原有试剂信息")
            return "\n".join(lines)

        if force_cover and existing:
            # 覆盖第一个匹配的
            target = existing[0]
            target.spec_value = spec_value
            target.spec_unit = spec_unit
            target.unit_price = unit_price
            target.stock = 0.0
            self._save()
            return f"✅ 已覆盖试剂「{target.display_name()}」，规格={spec_str}，单价={unit_price}元/{spec_unit}。"

        if force_new and existing:
            # 自动追加区分符
            existing_names = {r.name.lower() for r in existing}
            suffix = 1
            while f"{name.lower()}-{suffix}" in existing_names:
                suffix += 1
            name = f"{name}-{suffix}"

        reagent = Reagent(
            name=name,
            branch=branch,
            spec_value=spec_value,
            spec_unit=spec_unit,
            unit_price=unit_price,
            stock=0.0,
        )
        self._reagents.append(reagent)
        self._save()
        return f"✅ 已添加试剂「{reagent.display_name()}」，规格={spec_str}，单价={unit_price}元/{spec_unit}，ID: {reagent.id}。"

    # ---------- 删除试剂 ----------

    def delete_reagent(self, name_or_id: str, branch: str) -> str:
        """删除试剂。"""
        branch = branch.strip()
        matches, is_id = self._find_reagents(name_or_id, branch)

        if not matches:
            return f"❌ 在分社「{branch}」下未找到试剂「{name_or_id}」。"

        dup_msg = self._check_duplicates(matches, is_id)
        if dup_msg:
            return dup_msg

        target = matches[0]
        display = target.display_name()
        self._reagents.remove(target)
        self._save()
        return f"✅ 已删除试剂「{display}」。"

    # ---------- 领用/消耗 ----------

    def take_reagent(self, name_or_id: str, branch: str, quantity_str: str,
                     use_all: bool = False) -> str:
        """领用/消耗试剂。"""
        branch = branch.strip()
        matches, is_id = self._find_reagents(name_or_id, branch)

        if not matches:
            return f"❌ 在分社「{branch}」下未找到试剂「{name_or_id}」。"

        dup_msg = self._check_duplicates(matches, is_id)
        if dup_msg:
            return dup_msg

        target = matches[0]

        if use_all:
            if target.stock <= 0:
                return f"❌ 试剂「{target.display_name()}」当前库存为 0，无法消耗。"
            taken = target.stock
            target.stock = 0.0
            self._save()
            return f"✅ 已耗尽试剂「{target.display_name()}」，消耗 {format_quantity(taken, target.spec_unit)}，当前库存: 0{target.spec_unit}。"

        # 解析数量
        parsed = parse_spec(quantity_str)
        if parsed is None:
            return f"❌ 数量「{quantity_str}」格式错误。请使用如 20g、500ml 的格式。"

        qty_value, qty_unit = parsed

        # 单位转换
        if qty_unit != target.spec_unit:
            converted = convert_unit(qty_value, qty_unit, target.spec_unit)
            if converted is None:
                return f"❌ 数量单位「{qty_unit}」与试剂规格单位「{target.spec_unit}」不兼容（质量与体积不可互转）。"
            qty_value = converted

        if target.stock <= 0:
            return f"❌ 试剂「{target.display_name()}」当前库存为 0，无法消耗。"

        if qty_value > target.stock:
            return f"❌ 试剂「{target.display_name()}」库存不足。当前库存: {format_quantity(target.stock, target.spec_unit)}，需要: {format_quantity(qty_value, target.spec_unit)}。"

        target.stock -= qty_value
        self._save()
        return f"✅ 已消耗试剂「{target.display_name()}」{format_quantity(qty_value, target.spec_unit)}，剩余库存: {format_quantity(target.stock, target.spec_unit)}。"

    # ---------- 归还/补充 ----------

    def return_reagent(self, name_or_id: str, branch: str, quantity_str: str) -> str:
        """归还/补充试剂。"""
        branch = branch.strip()
        matches, is_id = self._find_reagents(name_or_id, branch)

        if not matches:
            return f"❌ 在分社「{branch}」下未找到试剂「{name_or_id}」。如需新购试剂请使用 /ram add。"

        dup_msg = self._check_duplicates(matches, is_id)
        if dup_msg:
            return dup_msg

        target = matches[0]

        parsed = parse_spec(quantity_str)
        if parsed is None:
            return f"❌ 数量「{quantity_str}」格式错误。请使用如 20g、500ml 的格式。"

        qty_value, qty_unit = parsed

        if qty_unit != target.spec_unit:
            converted = convert_unit(qty_value, qty_unit, target.spec_unit)
            if converted is None:
                return f"❌ 数量单位「{qty_unit}」与试剂规格单位「{target.spec_unit}」不兼容（质量与体积不可互转）。"
            qty_value = converted

        target.stock += qty_value
        self._save()
        return f"✅ 已补充试剂「{target.display_name()}」{format_quantity(qty_value, target.spec_unit)}，当前库存: {format_quantity(target.stock, target.spec_unit)}。"

    # ---------- 跨分社调拨 ----------

    def move_reagent(self, name_or_id: str, src_branch: str, dst_branch: str,
                     quantity_str: str | None = None) -> str:
        """跨分社调拨试剂。"""
        src_branch = src_branch.strip()
        dst_branch = dst_branch.strip()

        if not self.branch_exists(dst_branch):
            return f"❌ 目的分社「{dst_branch}」不存在，请先使用 /ram addfs 创建。"

        src_matches, is_id = self._find_reagents(name_or_id, src_branch)

        if not src_matches:
            return f"❌ 在源分社「{src_branch}」下未找到试剂「{name_or_id}」。"

        dup_msg = self._check_duplicates(src_matches, is_id)
        if dup_msg:
            return dup_msg

        src_reagent = src_matches[0]

        if quantity_str is None:
            # 默认全部调拨
            qty_value = src_reagent.stock
        else:
            parsed = parse_spec(quantity_str)
            if parsed is None:
                return f"❌ 数量「{quantity_str}」格式错误。请使用如 20g、500ml 的格式。"
            qty_value, qty_unit = parsed
            if qty_unit != src_reagent.spec_unit:
                converted = convert_unit(qty_value, qty_unit, src_reagent.spec_unit)
                if converted is None:
                    return f"❌ 数量单位「{qty_unit}」与试剂规格单位「{src_reagent.spec_unit}」不兼容。"
                qty_value = converted

        if qty_value <= 0:
            return "❌ 调拨数量必须大于 0。"

        if qty_value > src_reagent.stock:
            return f"❌ 源分社库存不足。当前库存: {format_quantity(src_reagent.stock, src_reagent.spec_unit)}，需要: {format_quantity(qty_value, src_reagent.spec_unit)}。"

        # 扣减源分社
        src_reagent.stock -= qty_value

        # 查找目的分社是否存在同名同规格试剂
        dst_reagent = None
        for r in self._reagents:
            if (r.name.lower() == src_reagent.name.lower()
                    and r.branch == dst_branch
                    and r.spec_value == src_reagent.spec_value
                    and r.spec_unit == src_reagent.spec_unit):
                dst_reagent = r
                break

        if dst_reagent:
            dst_reagent.stock += qty_value
        else:
            # 自动在目的分社创建
            dst_reagent = Reagent(
                name=src_reagent.name,
                branch=dst_branch,
                spec_value=src_reagent.spec_value,
                spec_unit=src_reagent.spec_unit,
                unit_price=src_reagent.unit_price,
                stock=qty_value,
            )
            self._reagents.append(dst_reagent)

        self._save()
        return (f"✅ 已从「{src_branch}」调拨 {format_quantity(qty_value, src_reagent.spec_unit)} "
                f"「{src_reagent.name}」到「{dst_branch}」。")

    # ---------- 查询/盘点 ----------

    def show_reagents(self, keyword: str) -> str:
        """查询/盘点试剂。"""
        keyword = keyword.strip()

        # 先检查是否为分社名
        if keyword in self._branches:
            return self._show_branch_inventory(keyword)

        # 全局搜索试剂名
        matches = [r for r in self._reagents if keyword.lower() in r.name.lower()]
        if not matches:
            return f"❌ 未找到与「{keyword}」相关的试剂。"

        # 按分社和名称分组
        lines = [f"🔍 搜索「{keyword}」的结果："]
        for r in matches:
            lines.append(
                f"  - ID: {r.id} | {r.name}({r.specification}) [{r.branch}] | "
                f"单价: {r.unit_price}元/{r.spec_unit} | "
                f"库存: {format_quantity(r.stock, r.spec_unit)} | "
                f"总价: {r.total_price}元"
            )
        return "\n".join(lines)

    def _show_branch_inventory(self, branch: str) -> str:
        """列出某分社的所有试剂。"""
        items = [r for r in self._reagents if r.branch == branch]
        if not items:
            return f"📋 分社「{branch}」下暂无试剂。"
        lines = [f"📋 分社「{branch}」试剂清单："]
        total_value = 0.0
        for r in items:
            lines.append(
                f"  - ID: {r.id} | {r.name}({r.specification}) | "
                f"单价: {r.unit_price}元/{r.spec_unit} | "
                f"库存: {format_quantity(r.stock, r.spec_unit)} | "
                f"总价: {r.total_price}元"
            )
            total_value += r.total_price
        lines.append(f"  ──────────────")
        lines.append(f"  试剂总价值: {round(total_value, 2)}元")
        return "\n".join(lines)

    # ---------- 修改基础信息 ----------

    def modify_reagent(self, name_or_id: str, branch: str, mod_key: str,
                       mod_value: str) -> str:
        """修改试剂基础信息。"""
        branch = branch.strip()
        matches, is_id = self._find_reagents(name_or_id, branch)

        if not matches:
            return f"❌ 在分社「{branch}」下未找到试剂「{name_or_id}」。"

        dup_msg = self._check_duplicates(matches, is_id)
        if dup_msg:
            return dup_msg

        target = matches[0]
        mod_key = mod_key.strip().lower()
        mod_value = mod_value.strip()

        if mod_key in ("规格", "spec", "规格="):
            parsed = parse_spec(mod_value)
            if parsed is None:
                return f"❌ 规格「{mod_value}」格式错误。规格单位只能是 g/kg/ml/l 之一。"
            target.spec_value, target.spec_unit = parsed
            self._save()
            return f"✅ 已将「{target.name}」的规格修改为 {mod_value}。"

        elif mod_key in ("单价", "价格", "price", "单价=", "价格="):
            try:
                price = float(mod_value)
                if price < 0:
                    return "❌ 单价不能为负数。"
                target.unit_price = price
                self._save()
                return f"✅ 已将「{target.name}」的单价修改为 {price}元/{target.spec_unit}。"
            except ValueError:
                return f"❌ 单价「{mod_value}」不是有效的数字。"

        elif mod_key in ("名称", "name", "名称="):
            target.name = mod_value
            self._save()
            return f"✅ 已将试剂名称修改为「{mod_value}」。"

        elif mod_key in ("库存", "stock", "库存="):
            try:
                stock = float(mod_value)
                if stock < 0:
                    return "❌ 库存不能为负数。"
                target.stock = stock
                self._save()
                return f"✅ 已将「{target.name}」的库存修改为 {format_quantity(stock, target.spec_unit)}。"
            except ValueError:
                return f"❌ 库存「{mod_value}」不是有效的数字。"

        else:
            return f"❌ 未知的修改项「{mod_key}」。支持修改：规格、单价、名称、库存。"
