# CHTNE 化学试剂信息管理系统

AstrBot 插件 — 面向化学社团/实验室的试剂库存管理。支持试剂的增删改查、领用归还、跨分社调拨，数据持久化存储。

## 功能

- 试剂全生命周期管理（添加、删除、修改基础信息）
- 领用/消耗与归还/补充，自动单位换算（g/kg/ml/l）
- 跨分社调拨，目的分社自动创建试剂条目
- 分社管理与用户绑定（绑定后命令可省略分社参数）
- 按试剂名/分社名搜索盘点，显示规格、单价、库存、总价
- 重复试剂冲突提示，通过唯一 ID 精确操作
- 子命令模糊匹配（基于 Levenshtein 编辑距离纠错）
- 所有数据 JSON 持久化，重启不丢失
- 🆕 修改记录追踪：所有更改自动记录修改人、时间戳和改动内容
- 🆕 修改日志查询：`/ram log` 查看试剂历史改动，支持筛选和简洁模式
- 🆕 批量操作：add/del/take/ret/mv/mod 支持多行批量输入

## 指令

### 核心试剂操作

| 指令 | 说明 |
|------|------|
| `/ram add [-n/-c] <试剂名> <分社> [规格] [单价]` | 添加试剂（支持批量多行输入） |
| `/ram del <试剂名/ID> <分社>` | 删除试剂（支持批量多行输入） |
| `/ram take [-all] <试剂名/ID> <分社> <数量>` | 领用/消耗试剂（支持批量多行输入） |
| `/ram ret <试剂名/ID> <分社> <数量>` | 归还/补充试剂（支持批量多行输入） |
| `/ram mv <试剂名/ID> <源分社> <目的分社> [数量]` | 跨分社调拨（支持批量多行输入） |
| `/ram sh <关键词/分社>` | 查询/盘点试剂 |
| `/ram mod <试剂名/ID> <分社> <修改项>=<新值>` | 修改基础信息（支持批量多行输入） |

### 日志与历史

| 指令 | 说明 |
|------|------|
| `/ram log <试剂名/ID> <分社> [参数]` | 查看修改记录 |

### 分社与绑定

| 指令 | 说明 |
|------|------|
| `/ram addfs <分社名>` | 新建分社 |
| `/ram listfs` | 列出所有分社 |
| `/ram bind <分社名>` | 绑定个人与分社（省略分社参数时自动使用） |
| `/ram unbind <分社名>` | 解绑个人与分社 |

### 帮助

| 指令 | 说明 |
|------|------|
| `/ram help` | 查看所有可用指令 |
| `/ram help <指令名>` | 查看某个指令的详细帮助（如 `/ram help add`） |

## 示例

```bash
# 添加试剂：硝酸银，市中分社，规格 100g，单价 4.5元/克
/ram add 硝酸银 市中分社 100g 4.5

# 批量添加试剂
/ram add
硝酸银 市中分社 100g 4.5
硝酸铵 市中分社 500g
硫酸铜 新城分社 500g 3.0

# 有重名试剂时强制新建
/ram add -n 硝酸银 市中分社 100g 4.5

# 领用 20g
/ram take 硝酸银 市中分社 20g

# 一次性耗尽
/ram take -all 硝酸银 市中分社

# 归还 10g
/ram ret 硝酸银 市中分社 10g

# 跨分社调拨 50g
/ram mv 硝酸银 市中分社 新城分社 50g

# 搜索试剂
/ram sh 硝酸银

# 盘点某个分社
/ram sh 市中分社

# 修改规格
/ram mod 硝酸银 市中分社 规格=200g

# 查看修改记录
/ram log 硝酸银 市中分社

# 查看最近 5 次修改记录（简洁模式）
/ram log 硝酸银 市中分社 --oneline -5

# 筛选特定更改者的记录
/ram log 硝酸银 市中分社 --cmtr=user123

# 筛选涉及规格变动的记录
/ram log 硝酸银 市中分社 --grep=规格

# 绑定分社后，后续命令可省略分社
/ram bind 市中分社
/ram sh           # 自动显示市中分社库存
```

## 文件结构

```
astrbot_plugin_CHTNEReagentManager/
├── main.py              # 插件入口，命令路由与参数解析
├── models.py            # 数据模型（Reagent/ChangeRecord/ReagentLog dataclass、规格解析、单位转换）
├── reagent_manager.py   # 核心业务逻辑与 JSON 持久化（含修改日志）
├── utils.py             # 工具函数（Levenshtein 编辑距离、模糊匹配）
├── help_text.py         # 各子命令帮助文本
├── metadata.yaml        # 插件元信息
└── _conf_schema.json    # 配置 schema
```

## 数据存储

数据存储于 AstrBot 的 `plugin_data/astrbot_plugin_CHTNEReagentManager/` 目录下：

- `reagents.json` — 所有试剂数据
- `branches.json` — 分社列表
- `bindings.json` — 用户与分社的绑定关系
- `logs.json` — 所有修改记录（兼容旧数据，旧版本无此文件时自动创建）

## 设计细节

- **唯一 ID**：每个试剂创建时自动生成 8 位十六进制 ID，可通过 ID 精确操作
- **规格单位约束**：仅支持 `g/kg/ml/l`，质量与体积单位不可互转，同类别自动换算
- **重复处理**：同名同分社试剂添加时，未指定 `-n`/`-c` 参数会中断并列出冲突项
- **命令纠错**：输入 `/ram ad` 会提示「您是否想输入 `/ram add`？」（基于编辑距离 ≤3 的模糊匹配）
- **用户绑定**：`/ram bind <分社名>` 后，该用户的所有命令可省略分社参数

## 依赖

无需额外依赖（仅依赖 AstrBot 框架内置库）。

---

# Supports

- [AstrBot Repo](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot Plugin Development Docs (Chinese)](https://docs.astrbot.app/dev/star/plugin-new.html)

