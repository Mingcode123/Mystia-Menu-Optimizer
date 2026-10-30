<a id="chinese"></a>

# Mystia Menu Optimizer

**面向顾客偏好、食材供给与厨具约束的料理规划工具**

**中文** | [English](#english)

本项目以《东方夜雀食堂》的备菜决策为应用场景，将料理选择与追加食材配置表述为组合优化问题。系统以 Excel 工作簿为输入，提供浏览器候选查询、Python 逐客规划，以及独立的得分与价格分析工具。设计重点包括规则形式化、优化目标的逐步明确、CPU 搜索方法，以及方案在资源条件下的比较。

项目包含多个开发阶段的实现。下文以 `singlePLAN_cover3_mixIng_nCookware.py`（简称 `nCookware`）说明覆盖封顶与厨具配置模型，并分别界定浏览器查询和其他脚本的用途。

[问题定义](#zh-problem) · [设计演进](#zh-evolution) · [数学模型](#zh-model) · [系统与算法](#zh-methods) · [运行方法](#zh-running) · [验证结果](#zh-verification) · [局限](#zh-limits) · [贡献与文档](#zh-sources)

<a id="zh-problem"></a>

## 1. 问题定义与功能范围

备菜决策需要同时确定基础料理、追加食材和厨具，并评估方案是否满足顾客偏好。最终标签由料理、厨具、售价、追加食材、标签覆盖关系和流行条件共同决定。基础配方消耗食材与格数，但其食材标签不再次计入；重复加料重复占格，同名标签只计一次。

本项目将该过程划分为候选生成与方案评价：前者依据配方规则和五格限制构造料理组合，后者依据具体入口的得分或优化目标比较候选。

| 入口 | 主要用途 | 输出 |
| --- | --- | --- |
| 浏览器查询 | 枚举单个稀客的料理与加料组合，支持标签、得分与替代策略筛选 | 候选表、CSV、单表 XLSX |
| Python PLAN 系列 | 按标签或按顾客生成方案，比较食材件数、供给余量与厨具配置 | 规划 XLSX |
| 得分与利润脚本 | 分析基础料理得分、价格及利润梯度 | 独立分析工作簿 |

浏览器采用“喜好命中数减厌恶命中数”的净分。`nCookware` 排除最终标签命中厌恶的候选，并使用分层优化目标。两类入口的候选范围和评价规则分别定义。

<a id="zh-evolution"></a>

## 2. 需求与设计演进

开发目标始于求解实际备菜问题，而“最优方案”的定义随决策单位和资源条件逐步调整。早期需求包含达标枚举与收益比较；PLAN 系列随后聚焦于喜好覆盖、食材件数和最低供给余量。

| 阶段与实现 | 设计变化 | 决策依据 |
| --- | --- | --- |
| `detailedPLAN.py` | 每个可覆盖喜好标签配置一套方案；先最少预期食材件数，再最大最低供给余量 | 为不同标签要求分配备菜方案 |
| `singlePLAN.py` | 每位顾客配置一套方案；先最大喜好覆盖，再比较件数与余量 | 将决策单位统一为顾客 |
| `singlePLAN_cover3.py` | 喜好覆盖收益封顶为 3 | 达到目标覆盖后优先减少食材消耗 |
| `singlePLAN_cover3_mixedingredients.py` | 基础食材与加料混排为五个输出格 | 使结果与实际配方用量对应；评价目标延续上一阶段 |
| `singlePLAN_cover3_mixIng_limitedCookware.py` | 通过源码配置排除指定厨具 | 约束可采用的制作方式 |
| `singlePLAN_cover3_mixIng_nCookware.py` | 交互指定厨具数量，比较共同厨具集合 | 在同一设备配置下安排各客方案 |

覆盖封顶体现了明确的边际收益选择：若两个候选分别命中 3、4 项喜好，食材件数分别为 2、3，封顶后两者的覆盖收益相同，前者因用料较少而优先。厨具约束则将独立的顾客方案置于共同设备条件下评价。

设计演进涉及优化问题本身的调整；计算加速则以既定规则与评价目标为前提。需求依据、角色案例和 CPU 提速讨论见[需求与设计决策演进](docs/prompt-journey.md)。

<a id="zh-model"></a>

## 3. 数学模型

### 3.1 历史多方案模型

设某顾客的日订单量为 $`K`$，订单在 $`m>0`$ 个具有可行候选的标签方案之间均分。令 $`u_i`$ 表示这些方案对食材 $`i`$ 的累计用量，$`q_i`$ 表示日供给估计，则预期食材件数与最低供给余量分别为：

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

优化顺序为先最小化 $`E_{\mathrm{old}}`$，再在并列组合中最大化 $`R_{\mathrm{old}}`$。订单均分属于模型假设，缺少对应的实测概率估计；没有可行标签时不生成方案。

### 3.2 单客覆盖封顶模型

对顾客 $`g`$ 和方案 $`p`$，令 $`c_i(p)`$ 表示包含基础配方与加料的食材用量，$`h_g(p)`$ 表示喜好命中数。每客采用同一方案承担其假设订单，定义：

```math
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

其中，$`L(p)`$ 为食材件数，$`R(p)`$ 为最低供给余量。$`q_i`$ 对应工作簿中的日供给估计（Total Daily Quantity，TDQ）。对于实现生成并保留的候选集 $`\mathcal C_g`$，比较目标为：

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
```

该词典序目标依次最大化覆盖收益、最小化食材件数、最大化最低供给余量。后续指标仅在前序指标相同时参与比较；三项均相同时，以售价、料理名和加料字符串处理平局。默认最低分为 `3`、每客日订单量为 `5`。最低分控制候选准入，覆盖上限控制评价收益。

### 3.3 共同厨具配置

`nCookware` 先计算每客每厨具的最佳保留候选，再枚举恰好 $`n`$ 种厨具的集合。集合评价依次使用覆盖收益总和、食材件数总和、逐客最低供给余量之和，并对无解顾客设置惩罚。在默认三分门槛下，第一项等价于优先增加有解顾客数。食材用量仍按顾客独立核算。

标签等价代表选择与中性补位截断会限制 $`\mathcal C_g`$。因此，候选集内的目标比较尚不构成全部合法食材组合上的全局最优性证明。约束、集合目标、平局规则及反例见[优化模型与算法边界](docs/design.md)。

<a id="zh-methods"></a>

## 4. 系统结构与 CPU 求解方法

浏览器和 Python 脚本是两个独立执行入口，共享 Excel 数据文件。浏览器的 HTTP 服务仅提供静态文件；候选计算由浏览器 CPU 完成。Python 脚本直接读写工作簿。系统的数据流与文件职责见[架构说明](docs/architecture.md)。

| 计算环节 | 实现方法 | 适用范围 |
| --- | --- | --- |
| 网页加料枚举 | 按料理静态分块，使用最多 8 个 Web Worker，结合重复组合枚举和候选过滤 | 浏览器查询 |
| Python 候选生成 | 标签等价分组、相关加料筛选、深度优先搜索（DFS）及得分上界 | PLAN 分支；代表选择与中性补位最多三项影响候选范围 |
| 多标签方案组合 | 将最低余量转为 $`\lambda`$ 可行性判定，使用二分、DFS、容量剪枝和状态缓存 | 历史多方案分支 |
| 厨具集合比较 | 预计算并复用每客每厨具结果，再枚举设备集合 | `nCookware` 分支 |

在历史多方案模型中，较高余量门槛可行意味着较低门槛可行，因此可对门槛进行二分搜索；每次判定仍包含组合搜索成本。各分支采用的筛选、剪枝和并行方法有所不同。现有实现均在 CPU 上运行，尚无可复核的跨设备性能基准或加速倍数。

<a id="zh-running"></a>

## 5. 环境、输入与运行方法

### 5.1 环境与数据

以下命令均从仓库根目录执行。完整 Python 依赖要求 Python 3.11 或更新版本：

```sh
python -m pip install -r requirements.txt
```

根目录的 [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) 为完整原始工作簿，共 13 张表，包含程序使用的 7 张输入表、5 张图像映射表及 `Sheet1`。程序读取已保存的单元格结果。修改公式或其输入后，需在支持相应公式的电子表格软件中重算并保存，再运行程序。

### 5.2 浏览器查询

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8000>。页面自动加载同目录工作簿，也支持通过文件选择器导入 XLSX。选择稀客、得分阈值与筛选条件后，执行“开始计算”。`index.html` 内含样式与计算脚本，运行时需要相邻 `HTML/` 目录中的 SheetJS、名称映射和图片资源。

导出文件为 `结果_<时间戳>.csv` 或 `.xlsx`；XLSX 包含一个 `结果` 工作表、8 列数据。筛选结果为空时，导出逻辑会回退至全部计算结果。操作步骤与各选项行为见[网页使用说明](docs/web-guide.md)。

### 5.3 Python 厨具规划

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

程序依次询问流行喜爱标签、流行厌恶标签和厨具数量。流行输入留空表示无对应流行条件；厨具数量留空表示使用全部可用厨具。默认输入为根目录工作簿。

结果写入 `稀客料理表/single_mixIng_nCookware/`，文件名以 `single_cover3_mixIng_ncw` 开头并包含流行与厨具条件。`Plans` 工作表共 14 列，包含顾客信息、料理、厨具、售价、五个食材格与最终标签；两列图标字段为空占位。

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

显式相对输入、输出路径以脚本目录 `Python/` 为基准解析。各脚本参数、完整字段、自动命名和输出位置见[输入输出规范](docs/input-output.md)。

<a id="zh-verification"></a>

## 6. 验证方法与结果

验证分别覆盖文件一致性、同条件输出对照和实际网页运行。主要结果如下：

| 验证对象 | 条件与方法 | 结果 |
| --- | --- | --- |
| 程序、资源与输入 | 对照作者提供的基准文件，比较 SHA-256 | 235 个源码及资源文件、完整原工作簿逐字节一致 |
| Python 输出 | 12 种食材、8 道料理、3 位顾客、5 种厨具；无流行，选择 3 种厨具；显式输出与自动命名各做原件／副本对照 | 4 次运行完成；输出 XLSX 除创建／修改时间外，各 ZIP 成员一致 |
| 完整工作簿网页运行 | 博丽灵梦、阈值 3，启用加料子集过滤与等价去重 | 生成 4,372 条候选；搜索“饭团”后保留 59 行 |
| 网页导出 | 对上述筛选结果执行 XLSX 导出并读取文件 | `结果` 单表、8 列、59 条数据，与该案例的既有对照记录一致 |

验证范围和实验条件详见[验证记录](docs/verification.md)。58 位顾客的 Python 全量输出对照尚未完成；现有结果主要支持文件一致性及指定案例的行为一致性。

<a id="zh-limits"></a>

## 7. 适用范围与局限

- **资源模型**：最低供给余量允许为负，且逐客独立核算；共同厨具配置未扩展为多顾客共享库存优化。
- **评价范围**：PLAN 系列未联合建模酒水搭配、完整满意度或现金利润；顾客预算为展示字段。独立利润脚本用于历史价格分析。
- **搜索范围**：Python 的等价食材代表偏好原始 TDQ，未完整求解计入基础耗用后的组内分配；中性补位存在前三项截断。
- **数据质量**：采样日期与次数未完整留存；历史采购价公式存在按行关联错位的风险。经验供给和价格估计具有相应不确定性。
- **网页行为**：已识别标签型禁忌、TDQ 替换、零阈值、停止响应、空筛选导出和重复等价组合权重等边界，具体触发条件见[网页使用说明](docs/web-guide.md)。

<a id="zh-sources"></a>

## 8. 作者贡献、来源与文档

| 工作 | 贡献与归属 |
| --- | --- |
| 需求与模型 | 作者提出游玩问题，定义规则语义、评价顺序、筛选与厨具条件，并以角色案例核对结果 |
| 经验数据 | 作者手工记录价格、日供给与委托相关数据，整理经验期望 |
| 实现与迭代 | 大量代码、算法推导和部分调试使用 AI 辅助；作者负责需求澄清、取舍与结果验收 |
| 标签与图像 | 标签资料来源于 [AnYiEE 的项目](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)；图像归属及依赖许可见[第三方说明](THIRD_PARTY_NOTICES.md) |

本项目为非官方个人工具。数据记录口径、来源与文件一致性见[数据来源说明](docs/data-provenance.md)。补充文档按以下主题组织：

| 文档 | 内容 |
| --- | --- |
| [系统架构](docs/architecture.md) | 执行边界、数据流与文件职责 |
| [优化模型与算法边界](docs/design.md) | 变量、约束、目标函数与候选范围 |
| [输入输出规范](docs/input-output.md) | 工作簿结构、参数、路径与输出格式 |
| [需求与设计决策演进](docs/prompt-journey.md) | 历史 prompt 中的需求、目标变化与取舍依据 |
| [数据来源说明](docs/data-provenance.md) | 手工记录、上游资料与估计口径 |
| [验证记录](docs/verification.md) | 实验条件、观测结果与未覆盖范围 |
| [网页使用说明](docs/web-guide.md) | 操作步骤、筛选含义与边界行为 |

---

<a id="english"></a>

# Mystia Menu Optimizer

**Recipe planning under guest preferences, ingredient supply, and cookware constraints**

[中文](#chinese) | **English**

This project formulates meal preparation in *Touhou Mystia's Izakaya* as a combinatorial optimization problem over dishes and additional ingredients. It uses an Excel workbook as input and provides browser-based candidate queries, Python planning for individual guests, and separate score and price analysis tools. The design focuses on rule formalization, evolving optimization objectives, CPU search methods, and comparison of plans under resource conditions.

The repository contains implementations from several development stages. The coverage-capped and cookware-selection models below use `singlePLAN_cover3_mixIng_nCookware.py` (`nCookware` for short); the browser query and other scripts are described according to their respective purposes.

[Problem](#en-problem) · [Design evolution](#en-evolution) · [Mathematical model](#en-model) · [System and algorithms](#en-methods) · [Usage](#en-running) · [Verification](#en-verification) · [Limitations](#en-limits) · [Contributions and documentation](#en-sources)

<a id="en-problem"></a>

## 1. Problem definition and functional scope

Meal preparation requires selecting a base dish, additional ingredients, and cookware, then evaluating whether the resulting plan meets guest preferences. Final tags depend on the dish, cookware, selling price, additions, tag overrides, and trend conditions. Base ingredients consume quantities and slots without contributing their tags again. Repeated additions occupy repeated slots, while each distinct tag is counted once.

The project separates candidate generation from plan evaluation. Generation constructs combinations under recipe rules and the five-ingredient limit; evaluation compares candidates using the score or objective defined by each entry point.

| Entry point | Main purpose | Output |
| --- | --- | --- |
| Browser query | Enumerate dishes and additions for one rare guest, with tag, score, and substitution filters | Candidate table, CSV, single-sheet XLSX |
| Python PLAN scripts | Produce tag-specific or guest-specific plans and compare ingredient units, supply slack, and cookware configurations | Planning XLSX |
| Score and profit scripts | Analyze base-dish scores, prices, and profit tiers | Separate analysis workbooks |

The browser uses a net score: liked tags matched minus disliked tags matched. `nCookware` excludes candidates whose final tags match dislikes and applies a hierarchical objective. The two entry points define their candidate spaces and evaluation rules separately.

<a id="en-evolution"></a>

## 2. Requirements and design evolution

Development began with the aim of solving a practical meal-preparation problem. The definition of an optimal plan changed as the decision unit and resource conditions became more explicit. Early requirements included qualifying-dish enumeration and economic comparisons; the PLAN series subsequently focused on preference coverage, ingredient units, and minimum supply slack.

| Stage and implementation | Design change | Rationale |
| --- | --- | --- |
| `detailedPLAN.py` | One plan per coverable liked tag; minimize expected ingredient units, then maximize minimum supply slack | Allocate preparation plans to different tag requirements |
| `singlePLAN.py` | One plan per guest; maximize preference coverage, then compare units and slack | Make the guest the decision unit |
| `singlePLAN_cover3.py` | Cap coverage benefit at 3 | Prioritize lower ingredient use after reaching the target coverage |
| `singlePLAN_cover3_mixedingredients.py` | Combine base ingredients and additions into five output slots | Align the output with recipe quantities while retaining the preceding objective |
| `singlePLAN_cover3_mixIng_limitedCookware.py` | Exclude selected cookware through source configuration | Restrict the available preparation methods |
| `singlePLAN_cover3_mixIng_nCookware.py` | Request a cookware count interactively and compare shared cookware sets | Plan for guests under a common equipment configuration |

The coverage cap defines a marginal-benefit choice. If two candidates match 3 and 4 preferences using 2 and 3 ingredient units respectively, their capped coverage benefits are equal, so the former takes priority through lower ingredient use. Cookware constraints then evaluate guest-specific plans under a common equipment set.

Design evolution changes the optimization problem itself; computational acceleration assumes fixed rules and objectives. Requirement evidence, character cases, and CPU optimization discussions are documented in the [requirements and design retrospective (Chinese)](docs/prompt-journey.md).

<a id="en-model"></a>

## 3. Mathematical model

### 3.1 Historical multiple-plan model

Let a guest place $`K`$ daily orders, distributed equally among $`m>0`$ tag-specific plans with feasible candidates. Let $`u_i`$ denote total use of ingredient $`i`$ across those plans, and $`q_i`$ its estimated daily supply. Expected ingredient units and minimum supply slack are:

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

The objective first minimizes $`E_{\mathrm{old}}`$, then maximizes $`R_{\mathrm{old}}`$ among ties. Equal order allocation is a modeling assumption without a corresponding measured probability estimate. No plan is produced when no tag has a feasible candidate.

### 3.2 Capped single-guest model

For guest $`g`$ and plan $`p`$, let $`c_i(p)`$ denote ingredient use including the base recipe and additions, and $`h_g(p)`$ the number of liked tags matched. One plan serves all assumed orders for that guest. Define:

```math
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

Here, $`L(p)`$ is the ingredient-unit count and $`R(p)`$ is minimum supply slack. $`q_i`$ corresponds to the workbook's estimated Total Daily Quantity (TDQ). For the candidate set $`\mathcal C_g`$ generated and retained by the implementation, the comparison objective is:

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
```

This lexicographic objective maximizes coverage benefit, minimizes ingredient units, and maximizes minimum supply slack, in that order. A later criterion is considered only when earlier criteria tie. Selling price, dish name, and the additions string resolve remaining ties. The default minimum score is `3`, with `5` daily orders per guest. The score threshold controls candidate eligibility; the coverage cap controls evaluation benefit.

### 3.3 Shared cookware configuration

`nCookware` first computes the best retained candidate for each guest and cookware type, then enumerates sets of exactly $`n`$ types. It compares total coverage benefit, total ingredient units, and the sum of per-guest minimum slack values, with penalties for guests lacking a feasible plan. At the default three-point threshold, the first criterion prioritizes the number of guests with a plan. Ingredient use remains independently accounted for per guest.

Equivalent-ingredient representative selection and the neutral-filler cutoff restrict $`\mathcal C_g`$. Objective comparison within this set therefore does not establish global optimality over all legal ingredient combinations. Constraints, the set-level objective, tie-breaking rules, and a counterexample appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

<a id="en-methods"></a>

## 4. System structure and CPU solution methods

The browser and Python scripts are independent execution entry points that share the Excel data file. The browser's HTTP service only serves static files; candidate computation runs on the browser CPU. Python scripts read and write workbooks directly. Data flows and file responsibilities are described in the [architecture documentation (Chinese)](docs/architecture.md).

| Computation | Method | Scope |
| --- | --- | --- |
| Browser additions | Static partitioning by dish across up to 8 Web Workers, with repeated-combination enumeration and candidate filters | Browser query |
| Python candidate generation | Equivalent-tag grouping, relevant-addition filtering, depth-first search (DFS), and score upper bounds | PLAN branches; representative selection and a three-candidate neutral-filler cutoff restrict the search space |
| Multiple-tag plan selection | Minimum-slack feasibility at threshold $`\lambda`$, with binary search, DFS, capacity pruning, and state caching | Historical multiple-plan branch |
| Cookware set comparison | Precompute and reuse per-guest, per-cookware results before enumerating equipment sets | `nCookware` branch |

In the historical multiple-plan model, feasibility at a higher slack threshold implies feasibility at a lower one, enabling binary search over the threshold. Each feasibility check still involves combinatorial search. Filtering, pruning, and parallelization differ across branches. All current implementations run on CPUs; no reproducible cross-device performance benchmark or speedup factor is available.

<a id="en-running"></a>

## 5. Environment, inputs, and usage

### 5.1 Environment and data

Run the following commands from the repository root. The complete Python dependencies require Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
```

The root [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) is the complete original workbook. Its 13 sheets comprise 7 program-input sheets, 5 image-mapping sheets, and `Sheet1`. The programs read saved cell results. After changing formulas or their inputs, recalculate and save the workbook in spreadsheet software that supports those formulas before running the programs.

### 5.2 Browser query

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Visit <http://127.0.0.1:8000>. The page automatically loads the workbook from the same directory and also accepts XLSX through its file selector. Select a guest, score threshold, and filters, then choose `开始计算`. `index.html` contains the styles and computation scripts; it requires the SheetJS library, name mapping, and images in the adjacent `HTML/` directory.

Exports use `结果_<时间戳>.csv` or `.xlsx`. XLSX contains one `结果` sheet with 8 columns. When filtering yields no rows, export falls back to the full computed result set. Operation and option behavior are documented in the [web guide (Chinese)](docs/web-guide.md).

### 5.3 Python cookware planning

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

The program requests liked-trend tags, disliked-trend tags, and a cookware count in sequence. An empty trend response specifies no corresponding trend condition; an empty cookware response selects all available types. The default input is the root workbook.

Results are written to `稀客料理表/single_mixIng_nCookware/`. Filenames begin with `single_cover3_mixIng_ncw` and include trend and cookware conditions. The `Plans` sheet has 14 columns covering guest information, dish, cookware, selling price, five ingredient slots, and final tags. Its two icon fields are empty placeholders.

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py --help
```

Explicit relative input and output paths are resolved from the script directory, `Python/`. Script options, complete fields, automatic naming, and output locations are specified in the [input/output reference (Chinese)](docs/input-output.md).

<a id="en-verification"></a>

## 6. Verification methods and results

Verification covers file identity, output comparisons under matching conditions, and an actual browser run. The principal observations are:

| Subject | Conditions and method | Result |
| --- | --- | --- |
| Programs, resources, and input | SHA-256 comparison against the author's supplied reference files | 235 source and resource files, plus the complete original workbook, are byte-identical |
| Python output | 12 ingredients, 8 dishes, 3 guests, and 5 cookware types; no trends, 3 selected types; original/copy comparisons for explicit and automatic output naming | 4 runs completed; XLSX ZIP members match except for creation/modification timestamps |
| Browser with the complete workbook | 博丽灵梦, threshold 3, subset filtering and equivalent-ingredient deduplication enabled | 4,372 candidates; 59 rows after searching for `饭团` |
| Browser export | XLSX export and file inspection for that filtered result | One `结果` sheet, 8 columns, and 59 data rows, consistent with the existing comparison record for this case |

Conditions and coverage are detailed in the [verification record (Chinese)](docs/verification.md). A full Python output comparison across all 58 guests remains incomplete. The available results primarily establish file identity and behavioral agreement for the specified cases.

<a id="en-limits"></a>

## 7. Scope and limitations

- **Resource model:** minimum supply slack may be negative and is evaluated independently per guest. Shared cookware selection does not jointly optimize inventory across guests.
- **Evaluation scope:** PLAN scripts do not jointly model drinks, full satisfaction, or cash profit. Guest budget is a display field; separate profit scripts analyze historical prices.
- **Search space:** Python favors equivalent representatives with higher raw TDQ without fully optimizing allocation after base-recipe consumption. Neutral filler selection has a three-candidate cutoff.
- **Data quality:** sampling dates and counts are incomplete. Historical purchase-price formulas carry a risk of row-based association errors, limiting the interpretation of empirical supply and price estimates.
- **Browser behavior:** identified boundaries concern tag-based restrictions, TDQ substitution, a zero threshold, stop responsiveness, empty-filter export, and weights for repeated equivalent combinations. Trigger conditions appear in the [web guide (Chinese)](docs/web-guide.md).

<a id="en-sources"></a>

## 8. Contributions, sources, and documentation

| Work | Contribution and attribution |
| --- | --- |
| Requirements and models | The author defined gameplay problems, rule semantics, objective order, filters, and cookware conditions, and evaluated results through character cases |
| Empirical data | The author manually recorded prices, daily supply, and commission-related data and compiled empirical expectations |
| Implementation and iteration | Much of the code, algorithm derivation, and some debugging were AI-assisted; the author clarified requirements, made design tradeoffs, and evaluated results |
| Tags and images | Tag data came from [AnYiEE's project](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant); image attribution and dependency licenses are documented in the [third-party notices (Chinese)](THIRD_PARTY_NOTICES.md) |

This is an unofficial personal tool. Data collection, sources, and file identity are described in the [data provenance notes (Chinese)](docs/data-provenance.md). Supplementary documentation is organized as follows:

| Document | Content |
| --- | --- |
| [System architecture (Chinese)](docs/architecture.md) | Execution boundaries, data flows, and file responsibilities |
| [Optimization model and algorithm boundaries (Chinese)](docs/design.md) | Variables, constraints, objectives, and candidate scope |
| [Input/output reference (Chinese)](docs/input-output.md) | Workbook structure, options, paths, and output formats |
| [Requirements and design retrospective (Chinese)](docs/prompt-journey.md) | Requirements, changing objectives, and tradeoffs from historical prompts |
| [Data provenance (Chinese)](docs/data-provenance.md) | Manual observations, upstream data, and estimation assumptions |
| [Verification record (Chinese)](docs/verification.md) | Experimental conditions, observations, and untested scope |
| [Web guide (Chinese)](docs/web-guide.md) | Operation, filter semantics, and boundary behavior |
