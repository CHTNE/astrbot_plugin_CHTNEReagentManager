"""化学试剂信息管理系统 - AstrBot 插件入口"""

import os
import sys
from pathlib import Path

# 确保插件自身目录在 sys.path 中，以便导入本地模块
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from reagent_manager import ReagentManager
from help_text import GENERAL_HELP, HELP_MAP, KNOWN_COMMANDS
from utils import find_closest_command
from models import VALID_UNITS


@register("astrbot_plugin_CHTNEReagentManager", "CHTNE Chem Club",
          "CHTNE化学试剂信息管理系统", "1.0.0")
class ReagentPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        plugin_data_dir = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self._manager = ReagentManager(str(plugin_data_dir))

    # ==================== 主命令路由 ====================

    @filter.command("ram")
    async def ram(self, event: AstrMessageEvent):
        """/ram 主命令入口。解析子命令并分发。"""
        message = event.message_str.strip()
        # 去掉 /ram 前缀
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(GENERAL_HELP)
            return

        args_str = parts[1].strip()
        if not args_str:
            yield event.plain_result(GENERAL_HELP)
            return

        # 分割参数（处理引号等情况）
        tokens = self._tokenize(args_str)
        if not tokens:
            yield event.plain_result(GENERAL_HELP)
            return

        action = tokens[0].lower()
        rest = tokens[1:]

        # 特殊处理 help
        if action == "help":
            result = self._handle_help(rest)
            yield event.plain_result(result)
            return

        # 特殊处理 bind/unbind/addfs/listfs（不需要试剂操作的命令）
        if action == "bind":
            result = self._handle_bind(event, rest)
            yield event.plain_result(result)
            return
        if action == "unbind":
            result = self._handle_unbind(event, rest)
            yield event.plain_result(result)
            return
        if action == "addfs":
            result = self._handle_addfs(rest)
            yield event.plain_result(result)
            return
        if action == "listfs":
            yield event.plain_result(self._manager.list_branches())
            return

        # 检查 action 是否合法
        known_actions = {"add", "del", "take", "ret", "mv", "sh", "mod"}
        if action not in known_actions:
            closest = find_closest_command(list(known_actions), action)
            if closest:
                yield event.plain_result(
                    f'❌ 未知指令 "{action}"。您是否想输入 "/ram {closest}"？\n'
                    f'输入 /ram help 查看所有可用指令。'
                )
            else:
                yield event.plain_result(
                    f'❌ 未知指令 "{action}"。\n输入 /ram help 查看所有可用指令。'
                )
            return

        # 解析子命令（先处理可能的 -all 参数和 -n/-c 参数，再获取其余位置参数）
        result = self._dispatch(event, action, rest)
        yield event.plain_result(result)

    # ==================== 参数解析 ====================

    def _tokenize(self, s: str) -> list[str]:
        """简单的参数分割，处理带空格但不用引号的场景。
        保留原始含义，按空格分割。"""
        return s.split()

    def _resolve_branch(self, event: AstrMessageEvent, tokens: list[str],
                         branch_index: int) -> tuple[str | None, list[str], bool]:
        """尝试从 tokens[branch_index] 获取分社名。
        如果该位置不存在或看起来不像分社名，尝试使用用户绑定的分社。
        返回 (branch_name, remaining_tokens, branch_was_explicit)
        
        remaining_tokens 是去掉了显式分社名后的参数列表（如果分社来自绑定则不删除）。
        branch_was_explicit 表示分社是否来自 tokens 中的显式指定。
        """
        sender_id = event.get_sender_id()
        bound_branch = self._manager.get_user_branch(sender_id)

        if branch_index >= len(tokens):
            if bound_branch:
                return (bound_branch, tokens, False)
            return (None, tokens, False)

        candidate = tokens[branch_index]

        # 如果候选看起来像参数而非分社名（规格、key=value 等），则可能是省略了分社
        if self._looks_like_param(candidate):
            if bound_branch:
                return (bound_branch, tokens, False)
            return (None, tokens, False)

        # 检查候选是否是合法分社
        if self._manager.branch_exists(candidate):
            # 从 tokens 中移除该分社名，返回剩余参数
            remaining = tokens[:branch_index] + tokens[branch_index + 1:]
            return (candidate, remaining, True)

        # 候选不是已知分社，尝试使用绑定分社
        if bound_branch:
            return (bound_branch, tokens, False)

        return (candidate, tokens, False)

    def _looks_like_spec(self, s: str) -> bool:
        """检查字符串是否看起来像规格（如 100g、500ml）。"""
        s = s.strip().lower()
        if not s:
            return False
        for i, ch in enumerate(s):
            if ch.isalpha():
                unit = s[i:]
                if unit in VALID_UNITS:
                    try:
                        float(s[:i])
                        return True
                    except ValueError:
                        pass
                return False
        return False

    def _looks_like_param(self, s: str) -> bool:
        """检查字符串是否看起来像命令参数而非分社名。
        包括：规格（100g）、key=value（规格=100g）、纯数字（4.5）等。"""
        if self._looks_like_spec(s):
            return True
        # key=value 模式（如 规格=100g、单价=5.0）
        if "=" in s:
            return True
        # 纯数字（如价格 4.5）
        try:
            float(s)
            return True
        except ValueError:
            pass
        return False

    def _parse_action_params(self, tokens: list[str], known_flags: set[str]) -> tuple[set[str], list[str]]:
        """从 tokens 中提取以 - 开头的标志参数和剩余的位置参数。
        返回 (flags_set, positional_tokens)"""
        flags = set()
        positional = []
        for t in tokens:
            if t.startswith("-") and t in known_flags:
                flags.add(t)
            else:
                positional.append(t)
        return (flags, positional)

    # ==================== 命令分发 ====================

    def _dispatch(self, event: AstrMessageEvent, action: str,
                  rest: list[str]) -> str:
        """根据 action 分发到具体处理函数。"""
        if action == "add":
            return self._cmd_add(event, rest)
        elif action == "del":
            return self._cmd_del(event, rest)
        elif action == "take":
            return self._cmd_take(event, rest)
        elif action == "ret":
            return self._cmd_ret(event, rest)
        elif action == "mv":
            return self._cmd_mv(event, rest)
        elif action == "sh":
            return self._cmd_sh(rest)
        elif action == "mod":
            return self._cmd_mod(event, rest)
        else:
            return f'❌ 未知指令 "{action}"。输入 /ram help 查看帮助。'

    # ==================== add ====================

    def _cmd_add(self, event: AstrMessageEvent, rest: list[str]) -> str:
        flags, pos = self._parse_action_params(rest, {"-n", "-c"})
        if len(pos) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["add"]

        name = pos[0]

        # 使用 _resolve_branch 智能解析分社（支持用户绑定分社时省略分社名）
        branch, pos, _ = self._resolve_branch(event, pos, 1)
        if branch is None:
            return "❌ 请指定分社名，或使用 /ram bind <分社名> 绑定默认分社。\n" + HELP_MAP["add"]

        # 检查分社是否存在
        if not self._manager.branch_exists(branch):
            return f"❌ 分社「{branch}」不存在，请先使用 /ram addfs 创建。\n" + HELP_MAP["add"]

        # pos 中已去掉显式指定的分社名，剩余参数从索引1开始（索引0是name）
        remaining = pos[1:]

        if len(remaining) < 1:
            return "❌ 缺少规格参数。\n" + HELP_MAP["add"]

        spec_str = remaining[0]
        unit_price = 0.0
        if len(remaining) >= 2:
            try:
                unit_price = float(remaining[1])
            except ValueError:
                return f"❌ 单价「{remaining[1]}」不是有效的数字。\n" + HELP_MAP["add"]

        return self._manager.add_reagent(
            name=name,
            branch=branch,
            spec_str=spec_str,
            unit_price=unit_price,
            force_new="-n" in flags,
            force_cover="-c" in flags,
        )

    # ==================== del ====================

    def _cmd_del(self, event: AstrMessageEvent, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["del"]
        name_or_id = rest[0]
        branch, _, _ = self._resolve_branch(event, rest, 1)
        if branch is None:
            return "❌ 请指定分社名，或使用 /ram bind <分社名> 绑定默认分社。\n" + HELP_MAP["del"]
        return self._manager.delete_reagent(name_or_id, branch)

    # ==================== take ====================

    def _cmd_take(self, event: AstrMessageEvent, rest: list[str]) -> str:
        flags, pos = self._parse_action_params(rest, {"-all"})
        if len(pos) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["take"]

        name_or_id = pos[0]
        branch, pos, _ = self._resolve_branch(event, pos, 1)
        if branch is None:
            return "❌ 请指定分社名，或使用 /ram bind <分社名> 绑定默认分社。\n" + HELP_MAP["take"]

        if "-all" in flags:
            return self._manager.take_reagent(name_or_id, branch, "", use_all=True)
        else:
            remaining = pos[1:]  # pos 已去掉显式分社名
            if len(remaining) < 1:
                return "❌ 缺少数量参数。\n" + HELP_MAP["take"]
            return self._manager.take_reagent(name_or_id, branch, remaining[0])

    # ==================== ret ====================

    def _cmd_ret(self, event: AstrMessageEvent, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["ret"]
        name_or_id = rest[0]
        branch, pos, _ = self._resolve_branch(event, rest, 1)
        if branch is None:
            return "❌ 请指定分社名，或使用 /ram bind <分社名> 绑定默认分社。\n" + HELP_MAP["ret"]
        remaining = pos[1:]  # pos 已去掉显式分社名
        if len(remaining) < 1:
            return "❌ 缺少数量参数。\n" + HELP_MAP["ret"]
        return self._manager.return_reagent(name_or_id, branch, remaining[0])

    # ==================== mv ====================

    def _cmd_mv(self, event: AstrMessageEvent, rest: list[str]) -> str:
        """跨分社调拨。支持省略源分社（使用绑定分社作为源）。"""
        if len(rest) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["mv"]
        name_or_id = rest[0]

        sender_id = event.get_sender_id()
        bound_branch = self._manager.get_user_branch(sender_id)
        remaining = rest[1:]

        if len(remaining) < 1:
            return "❌ 参数不足（至少需要目的分社）。\n" + HELP_MAP["mv"]

        # 判断是否有显式源分社
        # 情况1: 只有一个或两个参数 + 有绑定 → 参数是 目的分社 [数量]
        # 情况2: 没有绑定 + 至少2个参数 → 第一个是源分社，第二个是目的分社
        # 情况3: 有绑定 + 第一个参数是已知分社且看起来有足够参数 → 显式指定源分社

        has_explicit_src = False
        if len(remaining) >= 2:
            # 有至少两个参数，可能第一个是源分社
            first = remaining[0]
            if self._manager.branch_exists(first):
                has_explicit_src = True

        if has_explicit_src:
            src_branch = remaining[0]
            dst_branch = remaining[1]
            quantity = remaining[2] if len(remaining) >= 3 else None
        elif bound_branch:
            src_branch = bound_branch
            dst_branch = remaining[0]
            quantity = remaining[1] if len(remaining) >= 2 else None
        else:
            return "❌ 请指定源分社和目的分社，或使用 /ram bind <分社名> 绑定默认分社作为源分社。\n" + HELP_MAP["mv"]

        return self._manager.move_reagent(name_or_id, src_branch, dst_branch, quantity)

    # ==================== sh ====================

    def _cmd_sh(self, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 请输入搜索关键词或分社名。\n" + HELP_MAP["sh"]
        return self._manager.show_reagents(rest[0])

    # ==================== mod ====================

    def _cmd_mod(self, event: AstrMessageEvent, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 参数不足。\n" + HELP_MAP["mod"]
        name_or_id = rest[0]
        branch, pos, _ = self._resolve_branch(event, rest, 1)
        if branch is None:
            return "❌ 请指定分社名，或使用 /ram bind <分社名> 绑定默认分社。\n" + HELP_MAP["mod"]

        # 修改项格式：key=value 或 key = value
        remaining = pos[1:]  # pos 已去掉显式分社名
        if len(remaining) < 1:
            return "❌ 缺少修改项。\n" + HELP_MAP["mod"]
        mod_str = " ".join(remaining)
        if "=" in mod_str:
            parts = mod_str.split("=", 1)
            mod_key = parts[0].strip()
            mod_value = parts[1].strip()
        else:
            return "❌ 修改项格式错误，应为 <修改项>=<新值>。\n" + HELP_MAP["mod"]

        return self._manager.modify_reagent(name_or_id, branch, mod_key, mod_value)

    # ==================== help ====================

    def _handle_help(self, rest: list[str]) -> str:
        if not rest:
            return GENERAL_HELP
        cmd_name = rest[0].lower()
        if cmd_name in HELP_MAP:
            return HELP_MAP[cmd_name]

        # 模糊匹配
        closest = find_closest_command(KNOWN_COMMANDS, cmd_name)
        if closest:
            return (f'⚠️ 未找到指令 "{cmd_name}" 的帮助。您是否想查看 "/ram help {closest}"？\n\n'
                    + HELP_MAP[closest])
        return f'❌ 未找到指令 "{cmd_name}" 的帮助。输入 /ram help 查看所有可用指令。'

    # ==================== bind / unbind / addfs ====================

    def _handle_bind(self, event: AstrMessageEvent, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 请指定要绑定的分社名。\n" + HELP_MAP["bind"]
        sender_id = event.get_sender_id()
        return self._manager.bind_user(sender_id, rest[0])

    def _handle_unbind(self, event: AstrMessageEvent, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 请指定要解绑的分社名。\n" + HELP_MAP["unbind"]
        sender_id = event.get_sender_id()
        return self._manager.unbind_user(sender_id, rest[0])

    def _handle_addfs(self, rest: list[str]) -> str:
        if len(rest) < 1:
            return "❌ 请指定分社名。\n" + HELP_MAP["addfs"]
        return self._manager.add_branch(rest[0])

