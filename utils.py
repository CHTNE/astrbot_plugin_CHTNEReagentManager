"""工具函数 - 字符串匹配、编辑距离等"""


def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串之间的 Levenshtein 编辑距离。"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        cur_row = [i + 1]
        for j, c2 in enumerate(s2):
            # 插入、删除、替换的代价
            insert = prev_row[j + 1] + 1
            delete = cur_row[j] + 1
            substitute = prev_row[j] + (0 if c1 == c2 else 1)
            cur_row.append(min(insert, delete, substitute))
        prev_row = cur_row

    return prev_row[-1]


def find_closest_command(user_input: str, known_commands: list[str], max_distance: int = 3) -> str | None:
    """在已知命令列表中查找与用户输入最接近的命令。
    返回 None 表示没有在编辑距离阈值内的匹配。"""
    best_match = None
    best_distance = max_distance + 1

    for cmd in known_commands:
        dist = levenshtein_distance(user_input, cmd)
        if dist < best_distance:
            best_distance = dist
            best_match = cmd

    if best_distance <= max_distance:
        return best_match
    return None


def find_by_id_or_name(user_input: str, reagents: list) -> tuple[list, bool]:
    """根据用户输入（名称或 ID）查找试剂。
    返回 (匹配列表, 是否为精确ID匹配)。
    - 如果 user_input 能精确匹配某个 ID，返回单个元素的列表和 True
    - 否则按名称模糊匹配，返回匹配列表和 False
    """
    from models import Reagent

    user_input = user_input.strip()

    # 先尝试精确 ID 匹配
    for r in reagents:
        if r.id == user_input:
            return ([r], True)

    # 按名称匹配（不区分大小写）
    matches = [r for r in reagents if r.name.lower() == user_input.lower()]
    return (matches, False)