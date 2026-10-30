<a id="chinese"></a>

# Mystia Menu Optimizer

**夜雀食堂料理规划器：从顾客偏好到食材与厨具选择**

**中文** | [English](#english)

本项目源于《东方夜雀食堂》的实际备菜需求：在配方、五格食材限制和顾客偏好下寻找料理，再比较重复制作时的用量、供给压力与厨具条件。项目保留原网页查询程序和不同阶段的 Python 脚本，以 Excel 为输入，提供交互查询、逐客规划及历史价格分析。

网页使用原版布局、按钮、文字和计算逻辑，默认读取根目录的 [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx)。[Python/](Python/) 保留原始脚本与各自的目标和输出格式；其中 `singlePLAN_cover3_mixIng_nCookware.py` 实现覆盖封顶、每客单方案与厨具数量选择。公开工作簿直接复制作者原文件，完整保留公式、已保存的计算结果和原有内容；来源与文件一致性见[数据说明](docs/data-provenance.md)。

[问题](#zh-problem) · [目标演进](#zh-evolution) · [数学模型](#zh-model) · [CPU 实现](#zh-methods) · [运行与输出](#zh-running) · [已知限制](#zh-limits) · [验证](#zh-verification) · [贡献与来源](#zh-sources)

<a id="zh-problem"></a>

## 1. 问题定义

料理规划包含两个问题：哪些方案达到顾客要求，以及如何比较多个达标方案。稀客具有喜好与厌恶标签；一份料理的最终标签由料理、厨具、售价、追加食材、覆盖关系和流行状态共同决定。基础配方消耗食材与格数，但不再次贡献食材标签；重复加料占重复格，标签只计一次。

| 入口 | 决策用途 | 输出 |
| --- | --- | --- |
| 网页查询 | 枚举单个稀客的料理与加料，按条件筛选 | 候选表、CSV 或单表 XLSX |
| Python PLAN 系列 | 按脚本对应目标比较标签方案或逐客方案 | 自动命名的规划 XLSX |
| 评分与利润脚本 | 分析基础料理标签得分、价格及利润梯度 | 独立分析工作簿 |

网页按喜好命中减厌恶命中的净分筛选。本文的单客数学目标以 `nCookware` 分支为例，该分支排除最终命中厌恶的候选。两者具有不同用途和实现细节，结果不要求逐条相同。

<a id="zh-evolution"></a>

## 2. 目标演进

最初的查询需求包括达标枚举和收益比较。随后，备菜问题逐步聚焦于喜好覆盖、食材件数与最低供给余量，并形成多个保留至今的脚本分支。

| 分支 | 目标或变化 |
| --- | --- |
| `detailedPLAN.py` | 每个可覆盖喜好标签分别选方案；先最少预期食材，再最大最低余量 |
| `singlePLAN.py` | 改为每客一套方案；先最大喜好覆盖，再比较件数与余量 |
| `singlePLAN_cover3.py` | 将喜好覆盖收益封顶为 3，达标后优先节省食材 |
| `singlePLAN_cover3_mixedingredients.py` | 延续封顶目标，将基础食材和加料混排为五个输出格 |
| `singlePLAN_cover3_mixIng_limitedCookware.py` | 按脚本内的排除列表限制厨具 |
| `singlePLAN_cover3_mixIng_nCookware.py` | 交互指定厨具数量，比较共同厨具集合 |

每客单方案使输出可以按顾客组织；覆盖封顶明确了达标后的取舍。例如，A 命中三个喜好、用两份食材，B 命中四个喜好、用三份食材，封顶后 A 在件数上优先。厨具约束进一步要求各客方案能够使用同一组设备。输出排版变化与目标变化分别保留在对应脚本中。需求背景见[设计复盘](docs/prompt-journey.md)。

<a id="zh-model"></a>

## 3. 数学模型与实现范围

### 历史多方案模型

假设一位顾客每日有 $`K`$ 单，均分给 $`m>0`$ 个有可行候选的标签方案。令 $`u_i`$ 为这些方案中食材 $`i`$ 的累计用量，$`q_i`$ 为其日供给估计：

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

先最小化预期件数，再在并列方案中最大化最低余量。均分是模型假设，不是实测订单概率；无可行标签时没有方案。

### 单客覆盖封顶模型

对顾客 $`g`$，方案 $`p`$ 的食材 $`i`$ 用量为 $`c_i(p)`$，包括基础配方和追加食材；$`h_g(p)`$ 为喜好命中数。定义：

```math
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

原程序对其生成并保留的候选集 $`\mathcal C_g`$ 按以下顺序比较：

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
```

词典序表示前项相同才比较后项：覆盖收益相同后，多用一份食材不能由更高余量抵消；再以售价、料理名和加料字符串处理平局。默认最低分为 `3`、每客日订单量为 `5`。最低分决定准入，覆盖上限决定比较收益，两者不同。

`nCookware` 先保存每客每厨具的最佳候选，再枚举恰好 $`n`$ 种厨具的集合，依次比较覆盖总和、件数总和与逐客最低余量总和。无解顾客计零覆盖，并加入 $`10^9`$ 件数惩罚及 $`10^{18}`$ 余量扣减。默认门槛下，覆盖总和首先推动更多顾客有方案。食材仍逐客核算，没有共同扣减库存。

这些公式说明比较目标。原实现包含等价食材代表选择和中性补位截断，$`\mathcal C_g`$ 不应直接等同于全部合法具体食材组合，不能据此宣称全局最优。详细约束、反例和版本区别见[数学与实现说明](docs/design.md)。

<a id="zh-methods"></a>

## 4. CPU 求解方法

| 计算位置 | 原实现的方法 | 适用范围 |
| --- | --- | --- |
| 网页加料枚举 | 按料理静态分块，最多 8 个 Web Worker；重复组合枚举、标签集合与候选过滤 | 浏览器 CPU 计算，不使用 GPU |
| Python 候选生成 | 标签等价分组、相关加料筛选、DFS 与得分上界 | 保留原代表选择和中性补位最多前三项的处理 |
| 历史多方案组合 | 将最低余量目标转为 $`\lambda`$ 可行性判定，结合二分、DFS、容量剪枝和状态缓存 | 多标签方案分支，不代表 `nCookware` 主流程使用同一求解器 |
| 厨具组合 | 预计算每客每厨具结果，再枚举厨具集合 | 复用子问题，逐客余量仍独立 |

较高余量门槛可行时，较低门槛也可行，因此历史模型可对门槛二分；内部组合判定仍有计算成本。等价标签并不意味着供给效果相同，原程序按原始 TDQ 偏好代表的方式也不是完整的组内资源分配。本文不报告未经留存基准支持的加速倍数。模块和执行路径见[架构说明](docs/architecture.md)。

<a id="zh-running"></a>

## 5. 输入、运行与输出

### 准备环境

在仓库根目录运行。完整 Python 依赖需要 Python 3.11 或更新版本：

```sh
python -m pip install -r requirements.txt
```

根目录工作簿为作者完整原文件，共 13 张表，其中 `稀客`、`普客`、`料理`、`食材`、`酒水`、`食材merchant_data`、`酒水merchant_data` 是程序使用的七张输入表；另有五张图像映射表和 `Sheet1`。原公式、缓存值、格式、图片和 Icon 字段均保留，采购价与 `Owned` 未改写。程序读取已保存的单元格结果，不负责重算 Excel 公式；修改公式或其输入后，应先在支持这些公式的表格软件中重算并保存。详情及原件哈希见[工作簿说明](docs/data-provenance.md)和[文件一致性审计](data/workbook-provenance.json)。

### 网页

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8000>。页面会请求同目录的 `东方夜雀食堂.xlsx`；也可通过原文件选择器导入 XLSX。`index.html` 是原 `INDEX.html` 的完整副本，样式和计算脚本仍在文件内；请同时保留 `HTML/` 下的 SheetJS、名称映射和图片资源。网页不接受 JSON 数据。头像和料理图像只负责显示，Excel 不需要内嵌这些图片。

网页输出 `结果_<时间戳>.csv` 或 `.xlsx`，XLSX 只有 `结果` 工作表。操作和保留的边界行为见[网页指南](docs/web-guide.md)。

### Python 厨具规划

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

依次输入流行喜爱标签、流行厌恶标签和允许的厨具数量。两次流行输入回车表示没有；厨具数量回车表示使用全部可用厨具。程序直接读取根工作簿，显示读取、扫描和写表进度。

结果自动写入 `稀客料理表/single_mixIng_nCookware/`，文件名以 `single_cover3_mixIng_ncw` 开头并附流行与厨具条件。工作表 `Plans` 保留 14 列，包括预算、喜好命中分隔、五个混排食材格和两列空图标占位；Python 不自动嵌入头像。查看原参数：

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

显式相对输入、输出路径按脚本目录 `Python/` 解释。完整列名、其他脚本用途和自动命名规则见[输入输出说明](docs/input-output.md)。候选表和规划工作簿是结果，不能代替源工作簿。

<a id="zh-limits"></a>

## 6. 已知行为与限制

本版保留原程序行为，包括以下已识别的边界：

- 网页的配方禁忌只按食材名称匹配；标签型禁忌可能未生效，TDQ 等价替换也可能重新带入禁用成员。
- 网页输入阈值 `0` 会回退为 `3`；零售价会派生“实惠”。“停止”发送消息，忙碌的同步 Worker 不保证立即响应。
- 网页筛选为空时，导出会回退到全部结果；重复等价加料的 Top-N 权重仍按原组大小连乘方式处理。
- Python 等价代表偏好原始日供给较高的食材，未完整优化结合基础耗用后的组内分配；中性补位候选存在前三项截断。
- 历史采购价公式含按行关联的错位风险。原工作簿保留这些公式及缓存值，利润分析结果需要结合数据来源理解。

模型中的供给余量可以为负，不保证整晚可供给。PLAN 系列没有联合优化共享库存、酒水搭配、完整满意度或现金利润；预算用于展示。独立利润脚本提供历史价格分析，不能替代完整经营模型。

<a id="zh-verification"></a>

## 7. 验证与复现范围

原版一致性需要分别核对源代码、输入和输出：Python 文件与基准脚本比较；发布 `index.html` 与原 `INDEX.html` 完整文件比较；发布工作簿与原 XLSX 比较整个文件的 SHA-256；同条件运行比较交互、候选及 Excel 单元格和版式。

具体完成项与尚未覆盖项统一记录在[验证记录](docs/verification.md)。完整游戏条件、所有浏览器、任意数据规模和全局最优性均不由一次成功运行推出。不同 PLAN 脚本的目标不同，跨分支结果变化应结合对应模型解释。

<a id="zh-sources"></a>

## 8. 作者贡献与来源

| 工作 | 贡献与归属 |
| --- | --- |
| 需求与模型 | 作者定义游玩问题、规则语义、目标顺序、筛选与厨具条件，并以角色案例检查结果 |
| 经验数据 | 作者手工记录价格、日供给和委托相关数据，整理经验期望 |
| 求解实现 | 大量代码、算法推导和部分调试使用 AI 辅助；作者提出效率与一致性要求并核验方案 |
| 发布整理 | 选取原程序、直接复制完整原工作簿、保留原资源目录、补充来源及输入输出说明 |
| 标签与图标 | 标签和图标整理来源为 [AnYiEE 的项目](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)，游戏美术归原权利人 |

公开包附完整原工作簿、58 张稀客头像和 163 张料理图片；完整游戏资料、备份和原始聊天不随包分发。原始采样次数与日期未完整留存，不把经验值视为确定游戏常数。SheetJS 与上游许可分别随附；本项目代码尚未单独选定开源许可证，见[第三方与许可说明](THIRD_PARTY_NOTICES.md)。这是非官方个人工具。

---

<a id="english"></a>

# Mystia Menu Optimizer

**From guest preferences to ingredient and cookware choices**

[中文](#chinese) | **English**

This project grew out of meal preparation in *Touhou Mystia's Izakaya*: finding dishes under recipe rules, a five-ingredient limit, and guest preferences, then comparing ingredient use, supply pressure, and cookware requirements for repeated preparation. It retains the original browser query program and Python scripts from different development stages, using Excel for interactive queries, per-guest planning, and historical price analysis.

The browser retains the original layout, controls, wording, and computation, and loads [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) from the repository root. [Python/](Python/) preserves the original scripts with their respective objectives and output formats. `singlePLAN_cover3_mixIng_nCookware.py` combines capped coverage, one plan per guest, and cookware-count selection. The public workbook is a direct copy of the author's original file, preserving its formulas, saved calculation results, and existing contents. Sources and file identity are described in the [data notes (Chinese)](docs/data-provenance.md).

[Problem](#en-problem) · [Objective evolution](#en-evolution) · [Mathematical model](#en-model) · [CPU implementation](#en-methods) · [Running and outputs](#en-running) · [Known limitations](#en-limits) · [Verification](#en-verification) · [Contributions and sources](#en-sources)

<a id="en-problem"></a>

## 1. Problem definition

Meal planning asks which plans meet a guest's requirements and how qualifying plans should be compared. Rare guests have liked and disliked tags. A dish's final tags depend on the dish, cookware, selling price, additions, overrides, and trends. Base ingredients consume quantities and slots without contributing their tags again; repeated additions occupy repeated slots, while tags count once.

| Entry point | Purpose | Output |
| --- | --- | --- |
| Browser query | Enumerate and filter dishes and additions for one rare guest | Candidate table, CSV, or a single-sheet XLSX |
| Python PLAN scripts | Compare tag-specific or per-guest plans under the selected script's objective | Automatically named planning XLSX |
| Score and profit scripts | Analyze base-dish tag scores, prices, and profit tiers | Separate analysis workbooks |

The browser filters by liked tags minus disliked tags. The single-guest model below uses the `nCookware` branch, which excludes candidates whose final tags match dislikes. These tools serve different purposes and have different implementation details; their results need not match candidate for candidate.

<a id="en-evolution"></a>

## 2. Objective evolution

The initial query requirements included qualifying-dish enumeration and economic comparisons. Subsequent planning focused on preference coverage, ingredient units, and minimum supply slack, producing several retained script branches.

| Branch | Objective or change |
| --- | --- |
| `detailedPLAN.py` | One plan per coverable liked tag; first minimize expected ingredient units, then maximize minimum slack |
| `singlePLAN.py` | One plan per guest; maximize preference coverage, then compare units and slack |
| `singlePLAN_cover3.py` | Cap coverage benefit at 3 and prioritize fewer ingredients after qualification |
| `singlePLAN_cover3_mixedingredients.py` | Retain the capped objective and mix base ingredients and additions into five output slots |
| `singlePLAN_cover3_mixIng_limitedCookware.py` | Restrict cookware through an exclusion list in the script |
| `singlePLAN_cover3_mixIng_nCookware.py` | Request a cookware count interactively and compare shared cookware sets |

One plan per guest organizes the output around preparation for individual guests. Capping coverage defines the tradeoff after qualification: if A matches three preferences using two ingredient units and B matches four using three, A takes priority on ingredient count once coverage is capped. Cookware constraints then require guest plans to use a common equipment set. Output-layout changes and objective changes remain in their respective scripts. See the [design retrospective (Chinese)](docs/prompt-journey.md).

<a id="en-model"></a>

## 3. Mathematical model and implementation scope

### Historical multiple-plan model

Assume a guest places $`K`$ daily orders, split equally among $`m>0`$ tag-specific plans with feasible candidates. Let $`u_i`$ be total use of ingredient $`i`$ across those plans and $`q_i`$ its estimated daily supply:

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

Expected units are minimized first; minimum slack is then maximized among ties. Equal order allocation is a modeling assumption, not a measured order probability. No feasible tag means no plan.

### Capped single-guest model

For guest $`g`$, plan $`p`$ uses ingredient $`i`$ in quantity $`c_i(p)`$, including the base recipe and additions. Let $`h_g(p)`$ be the number of liked tags matched. Define:

```math
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

The original program compares its generated and retained candidate set $`\mathcal C_g`$ in this order:

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
```

Lexicographic order considers a later criterion only when earlier criteria tie. At equal coverage benefit, greater slack cannot compensate for an extra ingredient unit. Selling price, dish name, and the additions string break remaining ties. Defaults are a minimum score of `3` and `5` daily orders per guest. The score threshold controls eligibility; the coverage cap controls ranking benefit.

`nCookware` first stores the best retained candidate for each guest and cookware type, then enumerates sets of exactly $`n`$ types. It compares total coverage, total ingredient units, and the sum of per-guest minimum slack values, in that order. Each unserved guest contributes zero coverage, a $`10^9`$ ingredient-count penalty, and a $`10^{18}`$ slack deduction. At the default threshold, total coverage first favors serving more guests. Ingredients are still accounted for separately per guest, without shared inventory deductions.

These formulas describe the comparison objectives. The original implementation includes equivalent-ingredient representative selection and a neutral-filler cutoff. Its $`\mathcal C_g`$ must not be equated with every legal combination of specific ingredients, so these objectives do not establish global optimality. See the [model and implementation notes (Chinese)](docs/design.md) for constraints, a counterexample, and branch differences.

<a id="en-methods"></a>

## 4. CPU solution methods

| Computation | Original method | Scope |
| --- | --- | --- |
| Browser additions | Static partitioning by dish across up to eight Web Workers; repeated combinations, tag sets, and candidate filters | Browser CPU computation, without a GPU |
| Python candidate generation | Equivalent-tag grouping, relevant-ingredient filtering, DFS, and score upper bounds | Retains original representative selection and the top-three neutral-filler cutoff |
| Historical multiple-plan selection | Reformulate minimum slack as $`\lambda`$ feasibility, with binary search, DFS, capacity pruning, and state caching | The multiple-tag branch; this is not the same solver as the `nCookware` main workflow |
| Cookware sets | Precompute per-guest, per-cookware results, then enumerate cookware sets | Reuses subproblems while keeping each guest's slack independent |

A feasible higher slack threshold implies that a lower threshold is feasible, allowing binary search in the historical model. The internal combination check still has a computational cost. Identical tags do not imply identical supply effects; the original preference for representatives with higher raw TDQ is not a complete allocation of resources within each group. No speedup factor is reported without a retained benchmark. See the [architecture notes (Chinese)](docs/architecture.md) for components and execution paths.

<a id="en-running"></a>

## 5. Inputs, running, and outputs

### Environment

Run commands from the repository root. Installing the complete Python dependencies requires Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
```

The root workbook is the author's complete original file with 13 sheets. The programs use seven input sheets: `稀客`, `普客`, `料理`, `食材`, `酒水`, `食材merchant_data`, and `酒水merchant_data`; the file also retains five image-mapping sheets and `Sheet1`. Original formulas, cached values, formatting, images, and Icon fields are preserved. Purchase prices and `Owned` are unchanged. The programs read saved cell results and do not recalculate Excel formulas. After changing formulas or their inputs, recalculate and save in spreadsheet software that supports those formulas. See the [workbook notes (Chinese)](docs/data-provenance.md) and [file-identity audit](data/workbook-provenance.json) for details and original-file hashes.

### Browser

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Visit <http://127.0.0.1:8000>. The page requests `东方夜雀食堂.xlsx` from the same directory; the original file selector also accepts XLSX. `index.html` is a complete copy of the original `INDEX.html`, with its styles and computation scripts still embedded. Keep the SheetJS library, name mapping, and image resources under `HTML/` alongside it. The browser does not accept JSON data. Portraits and dish images are display resources and need not be embedded in Excel.

The browser exports `结果_<时间戳>.csv` or `.xlsx`; XLSX contains only the `结果` sheet. See the [web guide (Chinese)](docs/web-guide.md) for operation and retained edge cases.

### Python cookware planning

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

Enter the liked-trend tags, disliked-trend tags, and permitted cookware count in sequence. Press Enter for either trend prompt to specify none; press Enter for the cookware count to use all available types. The program reads the root workbook directly and reports loading, scanning, and workbook-writing progress.

Results are written automatically to `稀客料理表/single_mixIng_nCookware/`. Filenames begin with `single_cover3_mixIng_ncw` and include trend and cookware conditions. The `Plans` sheet retains 14 columns, including budget, matched/unmatched preferences, five mixed ingredient slots, and two empty icon placeholders. Python does not automatically embed portraits. View the original options with:

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

Explicit relative input and output paths are resolved from the script directory, `Python/`. See the [input/output guide (Chinese)](docs/input-output.md) for full columns, other scripts, and naming rules. Candidate tables and planning workbooks are results, not replacements for the source workbook.

<a id="en-limits"></a>

## 6. Known behavior and limitations

This version retains the original behavior, including these identified boundaries:

- Browser recipe restrictions match ingredient names only. Tag-based restrictions may not apply, and TDQ-based equivalent substitution may reintroduce forbidden members.
- A browser threshold of `0` falls back to `3`; a zero selling price receives `实惠`. Stop sends a message that a busy synchronous Worker may not process immediately.
- Export with an empty browser filter falls back to all results. Top-N weighting for repeated equivalent additions retains the original product-of-group-sizes calculation.
- Python favors equivalent representatives with higher raw daily supply without fully optimizing allocation after base-recipe consumption. Neutral filler candidates are limited to the top three.
- Historical purchase-price formulas carry a risk of row-based association errors. The original workbook preserves those formulas and cached values, so profit analysis must be interpreted with its data provenance.

Supply slack may be negative and does not guarantee sufficient stock for an evening. The PLAN scripts do not jointly optimize shared inventory, drink pairing, full satisfaction, or cash profit; budget is displayed only. Separate profit scripts provide historical price analysis rather than a complete operating model.

<a id="en-verification"></a>

## 7. Verification and reproduction scope

Original-version fidelity requires separate checks of source, inputs, and outputs: compare Python files against the reference scripts; compare the complete published `index.html` with the original `INDEX.html`; compare the published workbook's whole-file SHA-256 with the original XLSX; and run matching conditions to compare interaction, candidates, Excel cells, and formatting.

Completed and outstanding checks are recorded in the [verification notes (Chinese)](docs/verification.md). One successful run does not establish correctness across all game conditions, browsers, data sizes, or global optima. PLAN branches have different objectives, so differences between their outputs must be interpreted against their respective models.

<a id="en-sources"></a>

## 8. Author contributions and sources

| Work | Contribution and attribution |
| --- | --- |
| Requirements and models | The author defined gameplay problems, rule semantics, objective order, filters, and cookware conditions, and checked results through character cases |
| Empirical data | The author manually recorded prices, daily supply, and commission-related data and compiled empirical expectations |
| Solver implementation | Much of the code, algorithm derivation, and some debugging were AI-assisted; the author set efficiency and consistency requirements and checked solutions |
| Publication preparation | Selection of original programs, a direct copy of the complete original workbook, preservation of the original resource directories, and source and input/output documentation |
| Tags and icons | Tag and icon collections come from [AnYiEE's project](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant); game artwork belongs to its original rights holders |

The package includes the complete original workbook, 58 rare-guest portraits, and 163 dish images. It does not distribute complete game materials, backups, or original chats. Original sampling counts and dates are incomplete, so empirical values are not treated as fixed game constants. SheetJS and upstream licenses are included separately. No separate open-source license has been selected for this project's own code; see the [third-party and licensing notes (Chinese)](THIRD_PARTY_NOTICES.md). This is an unofficial personal tool.
