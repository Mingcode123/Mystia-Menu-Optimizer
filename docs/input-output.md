# 输入、输出与文件角色

## 默认数据与运行方式

网页打开后自动载入 [`data/game.json`](../data/game.json) 对应的游戏数据快照：62 条食材记录、164 条料理记录、58 位稀客。网页排除食材表中的非食材记录“铃仙”，使用 61 种食材；一条无具体配方的特殊料理在 Python 中禁用，163 条料理可参与规划。数据来自作者历史工作簿，不代表游戏最新版本或完整覆盖率。

合成数据 [`data/demo.json`](../data/demo.json) 保留用于规则演示、回归测试和参数对照案例。`tools/reproduce_examples.py` 使用它重建四组合成案例，并使用 `data/game.json` 重建游戏数据规划结果。

发布包包含标准数据 JSON、对应的 `web/game-data.js` 与 `web/demo-data.js` 浏览器载入文件，以及显示用的 `web/icon-map.js` 和 `web/icons/` 图片；原始 Excel 不随包发布。修改 JSON 后运行 `python tools/sync_demo.py` 同步两个浏览器数据文件。数据来源与归一化说明见[数据来源文档](data-provenance.md)。

运行网页时应保留整个仓库目录结构，不要只复制 `index.html`。入口依赖 `web/` 下的脚本、样式、SheetJS、数据载入文件、图标映射和图片，图片路径也相对这套目录解析。

稀客头像和料理图标按名称查询 `web/icon-map.js`，再读取 `web/icons/` 中的图片，不是由导入的 Excel 生成。当前映射包含 58 位稀客与 163 道料理的 221 张 PNG；稀客无匹配头像或图片加载失败时，以名字首字占位。图像只用于显示，不参与标签计算、供给比较或方案选择。素材说明见[第三方来源与许可](../THIRD_PARTY_NOTICES.md)。

Python 没有隐含的默认输入或输出路径。使用游戏快照时，从仓库根目录运行：

```sh
python tools/run_planner.py --input data/game.json --cookware-count 3 --output outputs/game-plan.json --csv outputs/game-plan.csv
```

这里的 `game-plan.json` 和 `game-plan.csv` 是命令指定的名称，不是程序自动生成的固定名称。合成数据规划可将 `--input` 改为 `data/demo.json`。

## 三个入口的输入与输出

| 入口 | 接受的输入 | 输出 |
| --- | --- | --- |
| 网页 `index.html` | 内置游戏/合成数据，或导入 XLSX、标准数据 JSON | 当前候选表的 CSV 或 XLSX |
| Python `tools/run_planner.py` | `--input` 指定的标准数据 JSON | `--output` 指定的规划 JSON；`--csv 路径` 可另存 CSV |
| 导入器 `tools/prepare_data.py` | 位置参数指定的 XLSX 工作簿 | 标准数据 JSON，以及独立的导入审计 JSON |

网页直接读取 XLSX；Python 规划入口不直接读取 XLSX，应先转换：

```sh
python -m pip install -r requirements.txt
python tools/prepare_data.py my-workbook.xlsx --output local-data/game-data.json --report local-data/import-report.json
python tools/run_planner.py --input local-data/game-data.json --output outputs/my-plan.json
```

导入器省略 `--output` 和 `--report` 时，分别写入 `local-data/game-data.json` 与 `local-data/import-report.json`。命令行相对路径均以当前工作目录为基准，输出父目录自动创建；同名输出会被覆盖。输入、数据输出和报告输出必须使用不同路径。

## 四表数据结构

工作簿只含以下四张表即可，不需要原工作簿中的普客、酒水、图像映射或其他说明表。第一行使用英文表头，各表内 `Name` 唯一，跨表名称和配方引用保持一致。

| 表名 | 主要字段 | 用途 |
| --- | --- | --- |
| `食材` | `Name`、`Tags` | 食材名称及加料标签；可附带 `Buy Price`、`Level` |
| `料理` | `Name`、`Cookware`、`Sell Price`、`Required Ingredients`、`Tags`、`Forbidden Ingredients`、`Owned` | 基础配方、售价、厨具与加料限制 |
| `稀客` | `Name`、`Type`、`Preferred Tags`、`Disliked Tags`、`Budget` | 顾客偏好；网页要求 `Type` 为 `rare` 或 `稀客` |
| `食材merchant_data` | `Name`、`Total Daily Quantity`、`Average Buy Price` | 日供给估计及导入时使用的采购均价 |

标准数据 JSON 不要求 `Icon` 字段，也不包含历史工作簿或原型结果中的 `Name Icon`、`Dish Icon` 等展示列。网页图片映射与四表输入独立维护；原工作簿的图标列、图片公式和图像映射 sheet 均不是导入要求。

标签可空；无喜好的顾客在 Python 中没有可行方案。每种食材必须有同名供给记录，`Total Daily Quantity` 为有限非负数；未知 `Average Buy Price` 可留空。有效的已拥有料理需有厨具和 1–5 件可识别的基础食材，`Owned` 建议显式填写 0 或 1。

标签和食材清单支持顿号、中英文逗号或分号、斜线、竖线、换行、制表符分隔，普通空格不作为分隔符。两份相同基础食材写为 `豆腐、豆腐`，重复项计入用量；不要将其写成 `豆腐×2`。

标准数据 JSON 采用以下外层结构，四个数组中存放以表头为键的记录对象：

```json
{
  "format": "mystia-planner-data/v1",
  "metadata": {},
  "sheets": {
    "食材": [],
    "料理": [],
    "稀客": [],
    "食材merchant_data": []
  }
}
```

此处空数组仅展示结构，实际输入须含有效记录。完整实例见 [`game.json`](../data/game.json) 和 [`demo.json`](../data/demo.json)。网页与 Python 支持部分字段别名，导入器只保留白名单中的英文表头，因此跨入口使用时应采用上述名称。

导入器只读取 Excel 已保存的缓存值，不计算公式。若精简工作簿涉及跨表公式，应先在电子表格软件中重算并保存所需值；缺失供给缓存会阻止转换。导入器按 `Name` 对应商贩均价，修正输出 JSON 中的食材采购价，未知价格保留 `null`，原 XLSX 不被改写。

两个计算入口的校验和规则并非完全相同：Python严格校验供给、重复名称和已拥有配方，并按料理 `Owned` 筛选；网页当前不以 `Owned` 排除料理，按净标签得分筛选候选。Python不要求稀客 `Type`，并支持将无名续行并入上一名稀客；网页和导入器不会保留这种续行。为兼容三个入口，宜将一名稀客的信息整理在同一条具名记录中。

## 网页候选表

| 属性 | CSV | XLSX |
| --- | --- | --- |
| 文件名 | `结果_<毫秒时间戳>.csv` | `结果_<毫秒时间戳>.xlsx` |
| 格式 | UTF-8 BOM，逗号分隔 | 新工作簿，仅含 `结果` sheet |
| 列顺序 | `售价`、`得分`、`料理`、`cookware`、`总食材数`、`基础食材`、`加料`、`最终tag` | 同左 |

每行是一套当前所选稀客的候选方案。`售价` 为基础料理售价，`得分` 为喜好命中数减厌恶命中数，`总食材数` 为基础与追加食材总件数。基础食材保留重复名称，加料中的重复项显示为 `名称×数量`，最终标签以顿号连接。

导出保留当前的料理、厨具、得分、总食材数筛选及文本搜索，并沿用当前排序。“导出限制”为 0 时导出全部筛选结果，大于 0 时只取前 N 行。页面最多显示前 5,000 行，该显示上限不限制导出；筛选后无结果时不能导出隐藏候选。

候选表不包含完整源数据、稀客名称或计算参数，也不包含 Python 的供给余量指标。网页显示的图片不会添加到上述 CSV/XLSX 导出列中。导出的 XLSX 只有结果表，不是四表数据模板，不能再次作为规划数据导入。

## Python 规划报告

`--input` 和 `--output` 均为必填参数；`--csv` 可省略，省略时不生成 CSV。CSV 路径必须显式提供，不会由 JSON 文件名自动派生。默认计算参数为最低分 3、每客日订单量 5、全部稀客、全部未排除的可用厨具、无流行附着；用 `--help` 查看选择稀客和厨具等选项。

### JSON：完整规划结果

JSON 的 `format` 为 `mystia-planner-result/v1`。顶层包括：

| 字段 | 内容 |
| --- | --- |
| `source_metadata` | 输入数据的来源元数据 |
| `settings` | 最低分、订单量、覆盖上限、流行、厨具数量及排除项 |
| `selected_cookware` | 选中的共同厨具集合 |
| `summary` | 顾客/有解/无解数量，覆盖、食材件数、余量汇总，以及带无解惩罚的比较值 |
| `model_scope` | 预算、供给、共享库存和目标单位的模型边界 |
| `guests` | 每位所选稀客的状态、偏好、展示预算及方案 |

`guests` 每条记录含 `guest`、`budget_display_only`、`preferred_tags`、`disliked_tags`、`status`、`plan`。状态为 `planned` 或 `no_feasible_plan`；无可行方案时 `plan` 为 `null`。

非空 `plan` 含 `dish`、`cookware`、`sell_price`、`base_ingredients`、`added_ingredients`、`final_tags`、`covered_tags`、`score`、`coverage_capped`、`total_ingredients`、`supply_margin`、`ingredient_counts`、`remaining_supply`。

数组字段保留具体标签和重复食材；`ingredient_counts` 记录每种食材的件数。`remaining_supply` 为该客假设订单量下的逐食材余量，`supply_margin` 取其中最小值，允许为负。它们没有跨顾客共同扣减库存；汇总食材件数按每客一份代表料理计算，不乘以每日订单量。

### CSV：逐客摘要

CSV 使用 UTF-8 BOM，每位所选稀客一行，列顺序为：

```text
guest,status,dish,cookware,sell_price,base_ingredients,added_ingredients,final_tags,covered_tags,score,coverage_capped,total_ingredients,supply_margin
```

列表以顿号连接；无方案稀客保留 `guest`、`status`，其余列为空。CSV不包含完整参数、总体厨具集合、汇总或逐食材剩余供给。以公式触发字符开头的字符串会添加单引号，以便按文本打开。

## 导入审计与回读限制

导入器的标准数据 JSON 可供网页或 Python 继续使用。审计 JSON 则记录 `price_corrections`、`unknown_prices`、`disabled_recipes`、`warnings`、`row_counts` 和源文件 `source_sha256`，用于检查价格关联、未知值及禁用料理原因，不参与规划。

| 文件类别 | 能否作为规划数据输入 | 原因 |
| --- | --- | --- |
| 四表 XLSX 源数据 | 网页可直接读；Python需先转换 | 提供食材、料理、稀客与供给 |
| `mystia-planner-data/v1` JSON | 可以 | 标准输入格式，含四表记录 |
| 网页 CSV / 单表 XLSX | 不可以 | 仅含计算后的候选行 |
| `mystia-planner-result/v1` JSON / Python CSV | 不可以 | 结果格式，缺少四表源数据 |
| 导入审计 JSON | 不可以 | 仅含修正、校验与来源记录 |

## 原始文件与历史分析的角色

下表说明项目历史材料的用途。这些原始工作簿和整理版报告不随发布包提供；当前运行可直接使用已发布的纯数据快照，无须收集这些文件。

| 原始文件 | 实际角色 | 与当前运行的关系 |
| --- | --- | --- |
| `东方夜雀食堂.xlsx` | 网页和 Python 原型使用的游戏源工作簿，包含四个必需 sheet | 可作为本地 XLSX 输入；发布版由其必要字段形成 `data/game.json` |
| `ALL利润.xlsx` | 历史 `Export_Profit.py` 根据源数据生成的料理/酒水利润及价格梯度报表 | 历史输出，不是规划输入；现存利润数值不代表本版已重新计算或验证 |
| `料理原始得分表.xlsx` | 历史 `base_score.py` 按原料理标签与稀客喜好/厌恶生成的基础得分明细 | 历史输出，不包含完整加料和动态标签规划 |
| `izakaya自用推荐菜单.xlsx` | 独立 Excel 参考与推荐分析工具，含料理、酒水、顾客、厨具及公式推荐矩阵 | 未发现网页或 Python 原型读取或生成它；结构不符合四表输入要求 |
| `稀客料理表/` 下整理后的 `single_cover3_mixIng_ncw_*.xlsx` | 历史逐客方案，经过补图或版式整理 | 可作历史展示参考；不能声称当前发布版会逐字再生成该工作簿 |
| `map.xlsx` 与原工作簿图像映射表 | 本地图片关联及结果展示辅助材料 | 不是当前规划输入；发布网页使用独立的 `web/icon-map.js` 与 `web/icons/` |

当前发布版 Python 输出 JSON/CSV，网页输出候选 CSV/XLSX，导入器输出数据 JSON 与审计 JSON。它们与历史利润表、基础得分表、带图方案工作簿是不同产物。
