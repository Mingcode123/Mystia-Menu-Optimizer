# 输入、输出与文件角色

## 1. 运行数据与目录

网页与原 Python 程序使用根目录的 [东方夜雀食堂.xlsx](../东方夜雀食堂.xlsx)。发布文件直接复制完整原件，含 13 张表；其中 `稀客`、`普客`、`料理`、`食材`、`酒水`、`食材merchant_data`、`酒水merchant_data` 是程序使用的七张输入表，五张图像映射表和 `Sheet1` 也完整保留。原公式、缓存值、格式、图片和 Icon 字段均未清洗。各脚本按自己的原规则选择和解释数据。来源与文件一致性见[数据来源](data-provenance.md)及[原件审计](../data/workbook-provenance.json)。

保留整个仓库目录：`index.html` 内嵌原样式和脚本，并读取 `HTML/xlsx.full.min.js`、`HTML/icon_map.js` 和 `HTML/izakaya_icons_pack/` 下的图片。图像按名称映射到原相对路径资源，不来自运行工作簿的内嵌图片。

| 入口 | 输入 | 输出 |
| --- | --- | --- |
| 根目录 `index.html` | 自动请求同目录 `东方夜雀食堂.xlsx`；文件选择器接受 XLSX | 候选 CSV 或只有 `结果` 表的 XLSX |
| `Python/*PLAN*.py` | 直接读取 XLSX；主规划分支支持原有 `--input` | 按分支自动命名的规划 XLSX |
| `Python/base_score.py` | 根工作簿的稀客与料理表 | 根目录 `料理原始得分表.xlsx` |
| `Python/Export_Profit.py` | 根工作簿的价格与经营数据 | 根目录 `ALL利润.xlsx` |
| `Python/Classes/夜雀食堂料理推荐.py` | 根工作簿的普客、稀客、料理、酒水、食材表 | 原交互菜单的查询与分析显示 |

候选表、`Plans` 和利润／得分表都是分析结果，不包含完整源表结构，不能用它们替换根工作簿。当前原程序没有 JSON 数据导入、JSON 规划报告或独立的 XLSX→JSON 转换步骤。

## 2. 网页输入与导出

从仓库根目录启动本地静态服务：

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8000>。页面自动请求 `./东方夜雀食堂.xlsx`；默认读取失败时，可用原文件选择器选取 XLSX。HTTP 服务只提供静态文件，计算在浏览器 CPU 中执行。

网页主要读取四表：

| 表 | 原字段示例 |
| --- | --- |
| `食材` | `Name`、`Tags` |
| `料理` | `Name`、`Tags`、`Cookware`、`Sell Price`、`Required Ingredients`、`Forbidden Ingredients` |
| `稀客` | `Name`、`Type`、`Preferred Tags`、`Disliked Tags` |
| `食材merchant_data` | `Name`、`Total Daily Quantity` |

网页稀客筛选要求 `Type` 为 `rare` 或 `稀客`；保留原有字段别名与列表解析。食材中的“黑暗物质”“铃仙”和料理中的“黑暗物质”按原规则排除。网页不按 Python 的 `Owned` 规则筛料理。自有文件应以原工作簿和所选脚本为结构参考。

导出文件名为 `结果_<时间戳>.csv` 或 `结果_<时间戳>.xlsx`。XLSX 只有 `结果` 工作表，两种输出的列顺序相同：

```text
售价,得分,料理,cookware,总食材数,基础食材,加料,最终tag
```

每行对应当前稀客的一套料理与加料。头像和料理图片不写入这八列。候选表也不保存完整输入、顾客参数或 Python 的供给余量指标。

原导出逻辑在筛选结果非空时采用筛选集合，筛选为空时回退到全部计算结果，再应用导出行数限制。因此空筛选不代表导出空文件。更多边界见[网页指南](web-guide.md)。

## 3. Python 主规划入口

完整依赖需要 Python 3.11 或更新版本：

```sh
python -m pip install -r requirements.txt
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

程序切换到脚本所在目录 `Python/`，默认读取其上一级的 `东方夜雀食堂.xlsx`。命令的启动目录不改变该默认输入；显式传入的相对 `--input`、`--output` 同样按脚本目录解释。

| 原参数 | 行为 |
| --- | --- |
| `--input` | 可选 XLSX 路径；省略时使用父目录工作簿 |
| `--output` | 可选 XLSX 路径；省略时按实际流行和厨具条件自动命名 |
| `--min-score` | 整数，默认 3；保留原入口的取值处理 |
| `--orders-per-day` | 整数，默认 5 |
| `--trend-like`、`--trend-hate` | 非空参数代替对应流行提示；未提供或为空时交互询问 |

流行提示支持空格及原有分隔符，回车表示没有该方向的流行。程序随后列出可用厨具并询问数量 `n`；回车或无法转换的回答使用全部可用厨具，越界值夹到有效范围。原入口没有 `--cookware-count`、`--guest` 或 `--exclude-cookware` 参数。

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

帮助文字中的固定默认输出名是遗留说明；实际未指定 `--output` 时执行以下自动命名规则。

### 自动输出位置

```text
稀客料理表/single_mixIng_nCookware/
  single_cover3_mixIng_ncw_<流行条件>_<n与厨具名称>.xlsx
```

没有某方向流行时不加入该段；选中厨具名称以 `&` 连接，并按原规则处理文件名非法字符。相同条件可能生成相同文件名，运行前应保存需要保留的旧结果。

### Plans 工作表

| 列 | 原表头 | 内容 |
| --- | --- | --- |
| A | `Name` | 稀客名称 |
| B | `Name Icon` | 空字符串占位，不嵌入头像 |
| C | `Budget` | 展示预算 |
| D | `Preferred Tags` | 命中部分与未命中部分以 `|` 分隔，保持原喜好次序 |
| E | `Dish` | 料理名称 |
| F | `Dish Icon` | 空字符串占位，不嵌入料理图片 |
| G | `Cookware` | 厨具 |
| H | `Sell Price` | 售价 |
| I–M | `Ingredient1` 至 `Ingredient5` | 基础食材与追加食材混排，按 TDQ 降序和名称稳定排序 |
| N | `Tags` | 最终标签 |

无解顾客仍保留姓名、预算和喜好，其余方案列为空。原表还保留粗体表头、冻结 `A2`、顾客与料理区块合并、自动列宽、`Name Icon` 宽度 `10.64` 及数据行高 `59.7`。两列 Icon 只是原输出格式的一部分，不能理解为 Python 自动插图功能。

## 4. 其他原始脚本

| 文件 | 用途 |
| --- | --- |
| [detailedPLAN.py](../Python/detailedPLAN.py) | 每标签多方案，自动写入 `稀客料理表/detailed/` |
| [singlePLAN.py](../Python/singlePLAN.py) | 每客单方案，覆盖不封顶，输出到对应 `single` 分支目录 |
| [singlePLAN_cover3.py](../Python/singlePLAN_cover3.py) | 单客覆盖封顶，保留该版本的基础／加料列布局 |
| [singlePLAN_cover3_mixedingredients.py](../Python/singlePLAN_cover3_mixedingredients.py) | 覆盖封顶，五格食材混排 |
| [singlePLAN_cover3_mixIng_limitedCookware.py](../Python/singlePLAN_cover3_mixIng_limitedCookware.py) | 在源码 `EXCLUDE_COOKWARE` 中配置厨具排除；原值为烧烤架、蒸锅 |
| [base_score.py](../Python/base_score.py) | 生成基础料理标签得分表 `Scores` |
| [Export_Profit.py](../Python/Export_Profit.py) | 生成 `全料理价目`、`全酒水价目`、`全料理梯度`、`全酒水梯度` 四表 |
| [Classes/夜雀食堂料理推荐.py](../Python/Classes/夜雀食堂料理推荐.py) | 保留地点、料理、酒水和利润相关的原交互菜单 |

各 PLAN 分支的目标、厨具处理与表格布局不同。不能把某一分支输出当作其余脚本的等价替代。`ALL利润.xlsx`、`料理原始得分表.xlsx` 和历史带图规划表也不等同于网页导出或当前一次 PLAN 结果。

## 5. 工作簿与图片的关系

网页使用 58 张稀客头像和 163 张料理图片，按 [HTML/icon_map.js](../HTML/icon_map.js) 映射到 [HTML/izakaya_icons_pack/](../HTML/izakaya_icons_pack/)；缺图行为沿用原程序。原工作簿中的 Icon 字段、图像映射表和图片也完整保留，但网页显示仍使用独立资源目录。原 Python 输出仍保留空 Icon 列；如需历史带图版式，它属于独立的后处理，不是该规划入口自动输出的内容。

公开审计 [workbook-provenance.json](../data/workbook-provenance.json) 记录原文件来源及原件与发布副本的哈希一致性，它不是规划输入。程序读取已保存的单元格结果，不重算 Excel 公式。修改公式或其输入后，应先在支持这些公式的电子表格软件中重算并保存。去除公式后，原先依赖这些公式的计算不会再随输入更新，因此发布版直接保留完整原文件。
