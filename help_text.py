"""帮助文本 - 化学试剂信息管理系统"""

GENERAL_HELP = """🧪 CHTNE化学试剂信息管理系统(CHTNERAM) - 帮助

可用指令：

  /ram add [参数] <试剂名> <分社> [规格] [单价]
      添加试剂。可选参数：-n（新建）、-c（覆盖）
      支持批量：多行输入，每行格式同上

  /ram del <试剂名/ID> <分社>
      删除试剂。支持批量：多行输入

  /ram take [参数] <试剂名/ID> <分社> <数量>
      领用/消耗试剂。可选参数：-all（全部耗尽）
      支持批量：多行输入

  /ram ret <试剂名/ID> <分社> <数量>
      归还/补充试剂。支持批量：多行输入

  /ram mv <试剂名/ID> <源分社> <目的分社> [数量]
      跨分社调拨。不指定数量则全部调拨。支持批量：多行输入

  /ram sh [关键词/分社]
      查询/盘点试剂

  /ram mod <试剂名/ID> <分社> <修改项>=<新值>
      修改基础信息（规格、单价、名称、库存）。支持批量：多行输入

  /ram log <试剂名/ID> <分社> [参数]
      查看修改记录

  /ram addfs <分社名>
      新建分社

  /ram listfs
      列出所有分社

  /ram bind <分社名>
      绑定个人与分社

  /ram unbind <分社名>
      解绑个人与分社

  /ram help [指令名]
      查看帮助。如 /ram help add

输入 /ram help <指令名> 查看具体指令的详细帮助。"""


ADD_HELP = """📌 /ram add - 添加试剂

用法：/ram add [参数] <试剂名> <分社> [规格] [单价]

参数说明：
  （可选）-n   有重复试剂名时，新建一个（自动追加 -1 等区分符）
  （可选）-c   有重复试剂名时，直接覆盖原有试剂信息

示例：
  /ram add 硝酸银 市中分社 100g 4.5
  /ram add -n 硝酸银 市中分社 100g 4.5
  /ram add -c 硝酸银 市中分社 200g 5.0

批量添加（多行输入）：
  /ram add
  硝酸银 市中分社 100g 4.5
  硝酸铵 市中分社 500g
  硫酸铜 新城分社 500g 3.0

注意：
  - 规格单位只能是 g/kg/ml/l 之一
  - 单价为每单位规格的价格（如 100g 单价 4.5 表示 4.5元/克）
  - 存在同名同分社试剂且未指定 -n/-c 时，会提示选择操作"""


DEL_HELP = """📌 /ram del - 删除试剂

用法：/ram del <试剂名/ID> <分社>

示例：
  /ram del 硝酸银 市中分社
  /ram del abc12345 市中分社

批量删除（多行输入）：
  /ram del
  硝酸银 市中分社
  硝酸铵 市中分社

注意：
  - 可使用试剂名或唯一 ID 指定
  - 若匹配到多条同名不同规格的试剂，会列出带 ID 的列表，请使用 ID 精确删除"""


TAKE_HELP = """📌 /ram take - 领用/消耗试剂

用法：/ram take [参数] <试剂名/ID> <分社> <数量>

参数说明：
  （可选）-all   一次性耗尽该分社下的该种试剂（无需输数量）

示例：
  /ram take 硝酸银 市中分社 20g
  /ram take -all 硝酸银 市中分社

批量领用（多行输入）：
  /ram take
  硝酸银 市中分社 20g
  乙醇 市中分社 100ml

注意：
  - 数量单位与规格单位相同（g/kg/ml/l）
  - 不同质量/体积单位会自动换算（如试剂规格为 g，输入 kg 会自动转换）
  - 质量单位与体积单位不可互转
  - 库存不足时会提示"""


RET_HELP = """📌 /ram ret - 归还/补充试剂

用法：/ram ret <试剂名/ID> <分社> <数量>

示例：
  /ram ret 硝酸银 市中分社 10g

批量归还（多行输入）：
  /ram ret
  硝酸银 市中分社 10g
  乙醇 市中分社 50ml

注意：
  - 仅限已存在的试剂，新购试剂请使用 /ram add
  - 不同质量/体积单位会自动换算"""


MV_HELP = """📌 /ram mv - 跨分社调拨

用法：/ram mv <试剂名/ID> <源分社> <目的分社> [数量]

示例：
  /ram mv 硝酸银 市中分社 新城分社 50g
  /ram mv 硝酸银 市中分社 新城分社

批量调拨（多行输入）：
  /ram mv
  硝酸银 市中分社 新城分社 50g
  乙醇 市中分社 新城分社 100ml

注意：
  - 不指定数量则默认全部调拨
  - 若目的分社不存在该试剂，自动按原规格创建"""


SH_HELP = """📌 /ram sh - 查询/盘点试剂

用法：/ram sh [关键词/分社]

示例：
  /ram sh 硝酸银          （全局搜索试剂名）
  /ram sh 市中分社         （列出该分社所有试剂）

注意：
  - 当关键词匹配分社名时，列出该分社全部试剂及库存
  - 否则按试剂名全局搜索
  - 显示信息包含：ID、规格、单价、库存、总价"""


MOD_HELP = """📌 /ram mod - 修改基础信息

用法：/ram mod <试剂名/ID> <分社> <修改项>=<新值>

支持的修改项：
  规格    - 修改试剂规格（如 规格=200g）
  单价    - 修改单价（如 单价=5.0）
  名称    - 修改试剂名称（如 名称=硝酸银溶液）
  库存    - 修改库存数量（如 库存=500g）

示例：
  /ram mod 硝酸银 市中分社 规格=200g
  /ram mod 硝酸银 市中分社 单价=5.0
  /ram mod abc12345 市中分社 名称=硝酸钾

批量修改（多行输入）：
  /ram mod
  硝酸银 市中分社 规格=200g
  乙醇 市中分社 单价=3.0

注意：
  - 此操作用于修正非库存变动类的基础属性
  - 规格单位只能是 g/kg/ml/l 之一"""


LOG_HELP = """📌 /ram log - 查看修改记录

用法：/ram log <试剂名/ID> <分社> [参数]

参数说明（顺序不限）：
  -<数字>       只显示最近 N 次提交
  --oneline     简洁模式，只显示时间和改动内容
  --cmtr=<id>   只筛选某个更改者的更改
  --grep=<属性>  只筛选更改了某个属性的更改（如：规格、余量、单价等）

示例：
  /ram log 硝酸银 市中分社
  /ram log 硝酸银 市中分社 -5
  /ram log 硝酸银 市中分社 --oneline
  /ram log 硝酸银 市中分社 --cmtr=user123
  /ram log 硝酸银 市中分社 --grep=规格 -10
  /ram log abc12345 --oneline -3

注意：
  - 每条记录显示时间（YYYY-MM-DD HH:MM）、改动人昵称(ID)、改动内容
  - 所有更改操作（add/del/take/ret/mv/mod）均会自动记录"""


ADDFS_HELP = """📌 /ram addfs - 新建分社

用法：/ram addfs <分社名>

示例：
  /ram addfs 新城分社"""


LISTFS_HELP = """📌 /ram listfs - 列出所有分社

用法：/ram listfs"""


BIND_HELP = """📌 /ram bind - 绑定个人与分社

用法：/ram bind <分社名>

示例：
  /ram bind 市中分社

注意：
  - 绑定后，您的命令可省略分社参数，系统会自动使用绑定的分社"""


UNBIND_HELP = """📌 /ram unbind - 解绑个人与分社

用法：/ram unbind <分社名>

示例：
  /ram unbind 市中分社"""


HELP_MAP: dict[str, str] = {
    "add": ADD_HELP,
    "del": DEL_HELP,
    "take": TAKE_HELP,
    "ret": RET_HELP,
    "mv": MV_HELP,
    "sh": SH_HELP,
    "mod": MOD_HELP,
    "log": LOG_HELP,
    "addfs": ADDFS_HELP,
    "listfs": LISTFS_HELP,
    "bind": BIND_HELP,
    "unbind": UNBIND_HELP,
    "help": GENERAL_HELP,
}

KNOWN_COMMANDS = list(HELP_MAP.keys())

KNOWN_COMMANDS = list(HELP_MAP.keys())