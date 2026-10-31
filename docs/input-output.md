# 输入、输出与文件角色

本文列出各执行入口的数据依赖、参数、路径解析方式与输出格式。模型定义见[模型与算法](design.md)，网页操作见[网页指南](web-guide.md)。

## 1. 运行数据与目录

运行数据位于仓库根目录的 [东方夜雀食堂.xlsx](../东方夜雀食堂.xlsx)。该文件与作者提供的完整工作簿逐字节一致，共 13 张表：七张业务数据表 `稀客`、`普客`、`料理`、`食材`、`酒水`、`食材merchant_data`、`酒水merchant_data`，五张图像映射表，以及 `Sheet1`。公式、缓存值、格式、图片和 Icon 字段均包含在文件中。字段来源与文件哈希见[数据来源](data-provenance.md)及[工作簿审计](../data/workbook-provenance.json)。

网页依赖 `index.html`、`HTML/xlsx.full.min.js`、`HTML/icon_map.js` 和 `HTML/izakaya_icons_pack/` 的相对目录关系。样式与计算脚本内嵌于 HTML；角色和料理图像由独立资源目录提供。

| 入口 | 输入 | 输出 |
| --- | --- | --- |
| 根目录 `index.html` | 自动请求同目录 `东方夜雀食堂.xlsx`；文件选择器接受 XLSX | 候选 CSV，或含 `结果` 表的 XLSX |
| `Python/*PLAN*.py` | 读取 XLSX；主规划分支支持 `--input` | 按分支自动命名的规划 XLSX |
| `Python/base_score.py` | 根工作簿的稀客与料理表 | 根目录 `料理原始得分表.xlsx` |
| `Python/Export_Profit.py` | 根工作簿的价格与经营数据 | 根目录 `ALL利润.xlsx` |
| `Python/Classes/夜雀食堂料理推荐.py` | 根工作簿的普客、稀客、料理、酒水、食材表 | 交互菜单中的查询与分析显示 |

候选表、`Plans`、利润表和得分表属于分析输出，其结构与源工作簿不同。运行流程直接使用 XLSX 输入，不包含 JSON 数据导入或中间转换步骤。

## 2. 网页输入与导出

可直接打开 [GitHub Pages 在线页面](https://mingcode123.github.io/Mystia-Menu-Optimizer/)，或从仓库根目录启动本地静态服务：

```sh
python -m http.server 8000 --bind 127.0.0.1
```

本地服务启动后访问 <http://127.0.0.1:8000>。两种入口均自动请求 `./东方夜雀食堂.xlsx`；文件选择器支持手动指定 XLSX。HTTP 服务仅传输静态文件，计算在浏览器 CPU 中执行；手动选择的工作簿由浏览器读取，不上传至计算服务。

网页主要读取以下四张表：

| 表 | 字段示例 |
| --- | --- |
| `食材` | `Name`、`Tags` |
| `料理` | `Name`、`Tags`、`Cookware`、`Sell Price`、`Required Ingredients`、`Forbidden Ingredients` |
| `稀客` | `Name`、`Type`、`Preferred Tags`、`Disliked Tags` |
| `食材merchant_data` | `Name`、`Total Daily Quantity` |

稀客筛选要求 `Type` 为 `rare` 或 `稀客`。解析函数支持字段别名与列表分隔符，并排除食材“黑暗物质”“铃仙”及料理“黑暗物质”。网页不依据 Python 分支的 `Owned` 持有状态筛选料理。

导出文件名为 `结果_<时间戳>.csv` 或 `结果_<时间戳>.xlsx`。XLSX 仅含 `结果` 工作表，两种格式的列顺序一致：

```text
售价,得分,料理,cookware,总食材数,基础食材,加料,最终tag
```

每行对应当前稀客的一套料理与加料。导出的候选表不包含图像、完整输入数据、顾客参数或 Python 规划使用的最低供给余量指标；网页结果区另显示料理图标。

导出集合按以下顺序确定：筛选结果非空时选取筛选集合；筛选结果为空时选取全部计算结果；最后应用导出行数限制。因此，零行筛选仍可能生成包含全部候选的文件。其他已识别行为见[网页指南](web-guide.md)。

## 3. Python 主规划入口

安装完整依赖需要 Python 3.11 或更新版本。在仓库根目录执行：

```sh
python -m pip install -r requirements.txt
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

程序启动后将工作目录切换至 `Python/`，默认读取其上一级的 `东方夜雀食堂.xlsx`。显式传入的相对 `--input`、`--output` 路径也以 `Python/` 为基准，而非终端的启动目录。

| 参数 | 行为 |
| --- | --- |
| `--input` | 可选 XLSX 路径；省略时读取父目录工作簿 |
| `--output` | 可选 XLSX 路径，其父目录须已存在；省略时依据流行与厨具条件自动建目录并命名 |
| `--min-score` | 整数，默认 `3` |
| `--orders-per-day` | 整数，默认 `5` |
| `--trend-like`、`--trend-hate` | 非空参数代替对应流行提示；未提供或为空时进入交互输入 |

流行输入支持空格、逗号、顿号、分号等分隔符；直接回车表示该方向无流行标签。程序随后列出可用厨具并询问数量 `n`：空输入或无法转换为整数的回答采用全部可用厨具，越界值限制在有效范围内。该入口的参数列表不包含 `--cookware-count`、`--guest` 或 `--exclude-cookware`。

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

帮助文字显示的固定默认输出名与主流程存在差异；未指定 `--output` 时，实际采用以下自动命名规则。

### 自动输出位置

```text
稀客料理表/single_mixIng_nCookware/
  single_cover3_mixIng_ncw_<流行条件>_<n与厨具名称>.xlsx
```

文件名只包含非空的流行条件，厨具名称以 `&` 连接，并过滤文件名非法字符。相同条件可能生成相同路径并覆盖已有结果；保留多次实验结果时，可通过 `--output` 指定不同文件名。

### Plans 工作表

| 列 | 表头 | 内容 |
| --- | --- | --- |
| A | `Name` | 稀客名称 |
| B | `Name Icon` | 空字符串占位 |
| C | `Budget` | 展示预算 |
| D | `Preferred Tags` | 命中与未命中部分以 `\|` 分隔，各部分沿用喜好次序 |
| E | `Dish` | 料理名称 |
| F | `Dish Icon` | 空字符串占位 |
| G | `Cookware` | 厨具 |
| H | `Sell Price` | 售价 |
| I–M | `Ingredient1` 至 `Ingredient5` | 基础食材与追加食材混排，按 TDQ 降序、名称次序排列 |
| N | `Tags` | 最终标签 |

无解顾客仍占一行并显示姓名、预算和喜好，方案相关列为空。输出采用粗体表头、冻结 `A2`、顾客与料理区块合并及自动列宽；`Name Icon` 列宽为 `10.64`，数据行高为 `59.7`。两列 Icon 不嵌入图像。

## 4. 其他脚本

| 文件 | 用途 |
| --- | --- |
| [detailedPLAN.py](../Python/detailedPLAN.py) | 每标签多方案，自动写入 `稀客料理表/detailed/` |
| [singlePLAN.py](../Python/singlePLAN.py) | 每客单方案，喜好覆盖不封顶，输出至对应 `single` 分支目录 |
| [singlePLAN_cover3.py](../Python/singlePLAN_cover3.py) | 单客覆盖封顶，分别显示基础食材与加料 |
| [singlePLAN_cover3_mixedingredients.py](../Python/singlePLAN_cover3_mixedingredients.py) | 覆盖封顶，五格食材混排 |
| [singlePLAN_cover3_mixIng_limitedCookware.py](../Python/singlePLAN_cover3_mixIng_limitedCookware.py) | 通过源码中的 `EXCLUDE_COOKWARE` 配置排除厨具；默认值为烧烤架、蒸锅 |
| [base_score.py](../Python/base_score.py) | 生成基础料理标签得分表 `Scores` |
| [Export_Profit.py](../Python/Export_Profit.py) | 生成 `全料理价目`、`全酒水价目`、`全料理梯度`、`全酒水梯度` 四表 |
| [Classes/夜雀食堂料理推荐.py](../Python/Classes/夜雀食堂料理推荐.py) | 地点、料理、酒水和利润相关的交互查询菜单 |

各 PLAN 分支的目标、厨具处理与表格布局分别定义。`ALL利润.xlsx`、`料理原始得分表.xlsx`、网页候选表及历史带图规划表具有不同分析用途，文件之间不存在通用的输入替代关系。

## 5. 公式、图像与运行条件

程序读取已保存的单元格结果，不重算 Excel 公式。修改公式或其输入后，需要先在支持相关公式的电子表格软件中重算并保存，使程序读取到更新后的结果。工作簿本身保留全部公式及相关工作表。

网页通过 [HTML/icon_map.js](../HTML/icon_map.js) 从 [HTML/izakaya_icons_pack/](../HTML/izakaya_icons_pack/) 加载 58 张稀客头像和 163 张料理图片。工作簿中的 Icon 字段、映射表和内嵌图片属于原数据文件内容，网页显示使用上述独立资源。Python 规划输出的 Icon 列为空；历史带图版式由独立后处理生成。

[workbook-provenance.json](../data/workbook-provenance.json) 记录工作簿来源及原件与发布文件的哈希一致性，不参与运行计算。
