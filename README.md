<a id="chinese"></a>

# Mystia Menu Optimizer · 夜雀食堂料理规划器

**中文** | [English](#english)

**把备菜需求转成优化问题，求解明确目标与约束下的料理方案。**

这是一个源于《东方夜雀食堂》游玩需求的个人项目。我的本意是做一个帮助自己求最优解的程序：把“什么料理最好”变成明确的目标函数和约束，再让程序搜索。随着需求澄清，最优的定义也经历了变化——从多套标签方案的预期食材与供给优化，到每客单方案的喜好覆盖，再到覆盖封顶与有限厨具下的整体选择。

项目包含 **浏览器单客查询工具** 和 **Python 批量规划器**。我的工作集中在需求定义、规则澄清、游戏内价格与供给记录、目标优先级设计和案例验收，代码实现与部分调试使用 AI 辅助。

[解决的问题](#解决的问题) · [设计过程](#设计过程) · [CPU 求解](#在-cpu-上缩短求解时间) · [当前目标](#当前规划目标) · [案例](#用参数变化检查设计) · [架构](#项目架构) · [运行](#运行与复现)

## 解决的问题

为顾客选择料理时，基础配方、追加食材、标签覆盖、流行状态和配方禁忌会共同影响结果。一份料理能达标之后，还要在多种可行组合之间选择：更多喜好是否值得多加食材，供应紧张的食材是否有替代，以及这些料理能否使用同一组厨具制作。

理解后文需要三个概念：

- **稀客**：当前规划对象是输入数据中“稀客”表里的顾客，普通顾客不参与本版规划。
- **标签分**：一种最终标签命中喜好加一分，命中厌恶减一分，重复标签只计一次。网页按净分筛选；Python 先排除任何厌恶命中，因此默认三分门槛对应至少三个喜好。
- **流行附着**：使用者指定哪些标签触发流行；料理最终命中这些标签时，追加“流行·喜爱”或“流行·厌恶”，再依据该顾客的偏好计分。

工具将这些选择分成三个层次：

| 决策层次 | 输入条件 | 输出 |
| --- | --- | --- |
| 判断可行性 | 顾客、标签门槛、流行状态、必含／排除标签 | 满足规则的基础料理与加料组合，以及最终标签 |
| 比较逐客方案 | 喜好覆盖、食材件数、日供给和假设订单量 | 按明确优先级选出的每客一套方案 |
| 选择厨具组合 | 可用厨具、排除项、允许的厨具数量 | 选中厨具、对应的逐客方案和无解顾客 |

网页负责探索第一层的多种候选，Python 负责逐客推荐与厨具组合比较。它们是两条独立使用路径。

## 设计过程

以下按问题演进整理历史 prompt 中的关键决策；各阶段存在分支与反复，不表示精确的开发时间线。持续不变的是求最优解的意图，发生变化的是搜索对象、评价标准和允许使用的资源。

| 阶段 | 此时“最优”指什么 | 改变了什么 |
| --- | --- | --- |
| 达标枚举与收益比较 | 列出合法、达标的料理与加料，早期还提出按实际利润排列 | 最初的查询与收益比较设想；当前主流程未采用利润目标 |
| 候选简化 | 定义哪些达标方案可以被子集或低级替代方案取代 | 候选保留策略与适用条件 |
| 按标签多方案 | 预期食材件数最少；在此基础上，最低供给余量最大 | 多套方案的组合与标签责任分配 |
| 每客单方案 | 一份方案覆盖喜好最多，再比较件数与余量 | 决策单位与目标优先级 |
| 覆盖封顶为 3 | 达到三个喜好后，优先少用食材，再比较余量 | 第四个及以后喜好的目标收益归零 |
| 限定厨具 | 在共同厨具集合下比较各客方案；默认三分时先让更多顾客有方案 | 从单客选择扩展到共享设备约束 |

同时存在另一条迭代线：**在模型不变时，提高求解速度并保持结果一致。** 历史上对等价改写、λ 判定与二分的讨论属于这条线；排版修改也被要求不改变算法结果。它与主动修改“最优”的定义需要分别说明。

### 1. 把“达标料理”拆成能检查的规则

最初的需求是给定稀客，枚举达到三分标签门槛的料理与加料。为让结果有明确含义，我逐项澄清：基础配方食材计算用量和格数，但不再次贡献标签；追加食材可以重复，重复份数占格，标签只计一次；总食材数最多五份；配方禁忌只限制追加食材。

最早的 prompt 还提出过“按照实际利润排列”。这是需求起点的一部分；后续主流程明确采用喜好覆盖、食材件数与供给余量，不能将早期意图或利润表写成当前已经实现的利润最优化。

标签处理也有顺序。先合并料理、厨具、售价派生和追加食材标签，再处理肉覆盖素、饱腹覆盖下酒、重油覆盖清淡、大份覆盖小巧，最后检测流行状态。这样可以检查一份方案为何达标，而不只是得到一个分数。

### 2. 为候选简化设定条件

枚举会产生多种相似组合，所以我进一步定义了子集过滤、高级食材替代和等价食材去重：

| 设计 | 必须保留的条件 | 取舍 |
| --- | --- | --- |
| 加料子集过滤 | 同一道料理存在加料更少的合格子集；可选是否同时比较得分 | 达标后减少冗余，或保留额外得分 |
| 高级食材过滤 | 低级食材的标签集合是高级食材标签集合的真子集，且完整替代方案合法、存在 | 用方案可行性判断能否替代，不直接按等级删除 |
| 等价食材去重 | 仅对追加食材按相同标签集合分组，基础配方保持不变 | 减少重复候选，同时保留配方约束 |

这一步把“优化一下”具体化为可验收条件：替代食材看起来相似，还需要检查替代后的整份料理是否成立。这些筛选策略保留在网页中供使用者选择。

筛选开关也在表达偏好：不考虑得分时，允许删除已被更少加料满足的冗余方案；考虑得分时，还要确认替代方案分数不低。它们会改变保留的候选集合，不能一概称为对所有后续目标都保优的加速。同标签食材的供给表现也可能不同，需要另外检查。

### 3. 将食材取得条件转为比较指标

我手工记录了价格、每日供给、委托等数据，并计算经验期望。标签决定方案能否满足偏好；供给数量则用于比较持续制作时的资源压力。

早期我考虑枚举多套料理如何覆盖标签、承担不同标签的订单，先比较总食材数期望，再比较供给最紧张的食材。随后讨论将这个过程改写为“每个标签保留最少食材候选，再组合求余量”，要求简化计算而保持目标和结果一致。

将这一按标签版本的需求结合旧代码整理成数学形式：假设该顾客日订单量为 $K$，在 $m>0$ 个参与规划的标签方案之间均分；$u_i$ 是这些方案中食材 $i$ 的累计用量，$q_i$ 是其日供给估计，则：

$$
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
$$

当时的两阶段要求是：**先最小化预期食材件数 $E_{\mathrm{old}}$，再在这些最少件数方案中最大化最低余量 $R_{\mathrm{old}}$**。每个标签保留所有并列最少候选，供第二阶段组合选择。我还讨论了把第二阶段改写为“能否让最低余量至少达到 $\lambda$”：较高门槛可行，较低门槛也可行，因此可以用可行性判定配合二分搜索。二分减少的是门槛搜索次数，内部的组合可行性判定仍有计算成本。

这里的均分是建模假设，并非实测订单概率；旧代码实际将 $m$ 取为有可行候选的标签数。没有任何可行标签时直接返回无方案结果，不计算 $K/m$。该多方案模型属于历史分支，当前主流程已经改为每客单方案。两阶段公式与 $\lambda$ 推导见[数学建模说明](docs/design.md#数学建模从历史多方案到当前单方案)。

价格记录和历史利润表是相关的数据工作；最终规划目标中的“少用食材”指件数，不能解释为最低采购金额。

### 4. 从“每标签一套”改为“每顾客一套”

之后，我把推荐单位改成顾客：为每位稀客选择一份覆盖多个喜好的料理，让结果可以按顾客组织成备菜参考表。

这一变化重新定义了优化对象。原来需要在多套标签方案之间分配订单，现在直接比较一份料理的喜好覆盖、总食材件数和供给余量。输出也随之变为每客一行，并保留基础配方、加料和命中标签，便于检查。

### 5. 让覆盖收益封顶，再加入厨具限制

单方案最初优先覆盖更多喜好，后来我明确提出“达到三个即可”。这让模型在达标后优先节省食材，而不为第四个喜好继续增加用量。

例如，两份都合法的方案中，A 命中三个喜好、用两份食材；B 命中四个喜好、用三份食材。覆盖收益封顶后两者相同，模型选择 A。这是工具设定的收益边界，不是对完整游戏评价机制的结论。

进一步加入厨具限制后，单客好方案还必须放到共同的设备条件下比较。当前实现先计算每客在每种厨具下的最佳候选，再枚举可用厨具中的指定数量组合，比较这些组合能提供的逐客方案。这样能明确展示设备选择带来的覆盖范围变化。

完整的需求转述和角色验收过程见[需求演进复盘](docs/prompt-journey.md)。

## 在 CPU 上缩短求解时间

原型开发时没有可用的 GPU，我也希望程序能在已有电脑上完成求解。历史 prompt 反复要求“提高计算速度但是不改变结果”，并用具体角色、过滤开关和版本对比追查卡顿。运行本项目不需要 GPU。

结合原型代码，可以把这条求解改进线分为三类；它们分属不同阶段，并非同一版本同时启用：

| 方法 | 原型中的用途 |
| --- | --- |
| 减少重复候选与计算 | 按标签集合分组加料、枚举无序重复组合；旧多方案版每道料理生成一次候选，再按命中标签分桶，保留并列最少件数方案 |
| 缩小需要搜索的组合 | 部分原型使用得分上界剪枝；旧多方案第二阶段用 λ 判定、容量剪枝和状态缓存，寻找最好的最低余量 |
| 复用子问题与 CPU 并行 | 厨具版预计算每客每厨具最佳候选；根网页版按料理分块，最多使用 8 个 Web Worker，并分批回传结果 |

这些实现由 AI 辅助完成；我的要求是说明优化依据，保持已确定的规则、目标顺序和应保留的候选，再用同条件结果检查。历史多方案的 λ 主流程与最终单方案流程分别记录；没有用未留存的基准宣称加速倍数。

长计算还需要可观察：我要求显示处理阶段、实际完成数，也通过版本对比追查卡顿发生在求解还是导出。多字段流行、筛选策略和厨具条件作为输入，便于比较条件变化。具体的取舍与纠错过程见[CPU 求解复盘](docs/prompt-journey.md#并行主线在-cpu-上求得更快同时保持结果)。

## 当前规划目标

Python 默认最低标签分为 `3`，每客假设日订单量 `K=5`，最终命中厌恶的方案被排除。合格候选按以下顺序比较，前一项优先于后一项：

1. 最大化 `min(命中喜好数, 3)`。
2. 最小化基础配方与加料的总食材件数。
3. 最大化所用食材中的最低日供给余量。
4. 用售价、名称等固定次序处理平局，保持结果可复现。

用数学表达，设 $p$ 为一份料理与加料方案，$h_g(p)$ 为它命中顾客 $g$ 的喜好数，$c_i(p)$ 为食材 $i$ 的用量（包括基础配方与加料）。$q_i$ 是日供给估计，$K$ 是为这位顾客假设的日订单量。总食材件数和最低供给余量分别为：

$$
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
$$

令 $\mathcal F_g$ 为该顾客的可行候选集：使用已拥有料理和可用厨具，满足五格、加料禁忌与标签门槛，并且最终没有厌恶标签。当前单客目标是：

$$
\underset{p\in\mathcal F_g}{\operatorname{lex\,max}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
$$

**词典序**就是依次比较：前一项相同，才比较后一项。在覆盖收益相同的前提下，余量再高也不能抵消多用一份食材；三项都相同才使用售价与名称处理平局。这与把指标乘权重后加总不同。

“最低标签分”和“覆盖收益封顶”是两个独立概念：最低分可配置，决定能否入选；当前覆盖上限固定为 3，决定目标收益。例如将最低分设为 4，仍须命中至少四个喜好才能入选，但覆盖收益仍封顶为 3。基础用量与整数加料变量、标签约束和厨具目标的完整表达见[数学建模说明](docs/design.md#数学建模从历史多方案到当前单方案)。

默认门槛下，各合格方案的封顶覆盖均为三。因此厨具组合首先争取让更多顾客有方案，再减少件数、改善余量。若降低最低分，这一解释应改为比较覆盖总量。

**余量是逐客比较指标，可以为负。**不同顾客没有共同扣减同一份库存，因此它不能保证整晚所有方案同时可供给。网页的采购推荐使用 TDQ（日供给量）排序，和这里的需求扣减模型不同。

## 用参数变化检查设计

公开样例包含 12 种食材、8 道料理和 3 位虚构顾客。以下均为合成案例，用于复现模型行为，不是游戏实测收益：

| 条件变化 | 程序结果 | 设计含义 |
| --- | --- | --- |
| 基线：三种厨具、K=5、无流行 | 三位顾客均有方案，三份代表料理合计用四份食材 | 让每项推荐能落到配方、标签与用量 |
| 厨具从三种减为一种 | 选中料理台，两位顾客有方案，匠人无解 | 设备条件限制了可覆盖的顾客范围 |
| K 从 5 增至 15 | 匠人的肉片余量从 9 降至 −1，方案仍被返回 | 负余量是压力信号，当前没有库存硬约束 |
| 将流行厌恶附着到“下酒” | 匠人由烤串改为烤串＋谷物 | “饱腹”先覆盖“下酒”，避免触发流行厌恶，同时增加一份食材 |

基线三份代表料理的件数合计不等于整日备货量；恰选三种厨具时，平局结果中也可能含未被最终料理使用的厨具。输入、逐客结果和解释见[四组案例](docs/case-study.md)及 [examples/](examples/)。

![网页选择合成顾客旅人后，显示家常饭及果盘加料候选、分数和最终标签](docs/images/demo.jpg)

## 项目架构

系统在本机运行：**网页直接读取文件并在浏览器中计算；Python 通过独立 CLI 读取 JSON、执行规划并导出报告。两者之间没有 API 调用。**

| 部分 | 职责与入口 |
| --- | --- |
| 浏览器工具 | [index.html](index.html) 与 [web/app.js](web/app.js)：数据解析、参数输入、CPU Web Worker 枚举、候选筛选和 CSV／XLSX 导出 |
| 数据导入 | [tools/prepare_data.py](tools/prepare_data.py)：XLSX 转标准 JSON，按名称关联商贩平均进价并记录审计 |
| Python 规划器 | [src/mystia_planner/](src/mystia_planner/)：数据对象、规则、组合搜索、厨具比较、CLI 与 JSON／CSV 输出 |
| 演示与验证 | [data/](data/)、[examples/](examples/)、[tests/](tests/)：合成输入、可复现结果和回归用例 |

网页使用喜好命中减厌恶命中的净分；Python 进一步将厌恶作为硬排除。两端的用途和目标不同，不要求输出逐条一致。系统边界、运行单元、组件职责和完整数据流见[架构说明](docs/architecture.md)。

## 运行与复现

### 网页体验

下载仓库后保持目录结构，打开根目录 `index.html`，默认样例会自动载入。选择顾客后点击“开始计算”；可开启“加料子集过滤”“等价食材去重”减少候选，再调整标签条件比较结果。

若浏览器限制本地文件 Worker，在仓库根目录运行：

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 `http://127.0.0.1:8000`。文件只在当前浏览器处理，不需登录、CDN 或计算后端。本地验证使用 HTTP 方式；双击方式未自动验证。筛选和导出细节见[网页指南](docs/web-guide.md)。

### Python 规划

需要 Python 3.10 或更新版本；JSON 规划及合成案例仅使用标准库。

```sh
# 重新生成文中四组案例
python tools/reproduce_examples.py

# 自定义厨具数量，生成完整报告
python tools/run_planner.py --input data/demo.json --cookware-count 3 --output outputs/my-plan.json

# 查看顾客、流行、厨具排除、最低分和订单量参数
python tools/run_planner.py --help
```

### 导入游戏数据

网页可直接读取 XLSX 或标准 JSON。为 Python 准备数据并记录价格关联修正时，使用：

```sh
python -m pip install -r requirements.txt
python tools/prepare_data.py my-workbook.xlsx --output local-data/game-data.json --report local-data/import-report.json
python tools/run_planner.py --input local-data/game-data.json --cookware-count 3 --output outputs/game-plan.json
```

输入需要 `食材`、`料理`、`稀客`、`食材merchant_data` 四张表，格式见 [demo.json](data/demo.json)。导入工具读取 Excel 缓存值，按名称关联平均进价，未知价格保留 `null`；原工作簿不被改写。`local-data/` 和 `outputs/` 默认不提交。

## 验证与适用范围

```sh
python tools/run_checks.py
node --test tests/web-regression.cjs
```

本地已通过 31 项 Python 测试和 11 项网页测试。Python 测试包括 90 组固定种子小输入与独立具体食材穷举的对照；网页测试执行实际 Worker，覆盖禁忌、停止计算、零阈值与空筛选导出等边界。Node.js 仅用于测试。

另外完成了本地真实数据的 58 位顾客默认参数规划与逐条规则复核。该原始数据不随公开包分发；公开可复现部分以合成样例为准。GitHub CI 配置已准备，尚未在远程运行。详见[验证记录](docs/verification.md)。

当前边界：预算仅展示；未联合优化酒水、完整满意度、现金利润、订单概率或跨顾客共享库存。期望值缺少完整原始采样记录，不据此报告统计显著性或游戏收益提升。

## 个人工作、数据来源与协作

| 内容 | 归属 |
| --- | --- |
| 需求、规则语义、筛选条件、目标优先级、厨具约束、角色案例验收 | 作者主导 |
| 价格、日供给、委托相关记录与经验期望 | 作者在游戏中手工记录和整理 |
| 历史标签数据 | 来自 [AnYiEE/touhou-mystia-izakaya-assistant](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant) |
| 大量代码实现与部分调试 | AI 辅助 |
| 模块整理、合成演示、来源审计、回归检查与已记录修复 | 本次作品集整理，采用 AI 协助；不追溯为历史已完成的成果 |

历史上，我用茨木华扇检查版本结果差异，用古明地恋比较厨具配置，也检查过森近霖之助在特定流行条件下的无解情况。这些要求推动了固定修改基准、区分排版与算法变化、解释具体输入输出的验收方式。

公开包使用合成数据，不附游戏美术、完整游戏数据库或原始聊天。字段来源与期望口径见[数据说明](docs/data-provenance.md)，整理变更见[变更记录](CHANGELOG.md)。SheetJS CE 0.20.3 随附其许可；本项目代码尚未单独选定开源许可证，完整归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目为非官方个人工具。

---

<a id="english"></a>

# Mystia Menu Optimizer

[中文](#chinese) | **English**

The README is bilingual. The interface, sample labels, and detailed documentation currently use Chinese.

**Turn meal preparation needs into an optimization problem, and search for dish plans under explicit objectives and constraints.**

This personal project grew out of playing *Touhou Mystia's Izakaya*. I wanted a program that would help me find optimal solutions: define what makes a dish “best” through objective functions and constraints, then let the program search. As I clarified the requirements, that definition changed—from optimizing expected ingredient use and supply across several tag-specific plans, to preference coverage in a single plan per guest, and finally to capped coverage and choices under limited cookware.

The project includes a **browser tool for individual guest queries** and a **Python batch planner**. My work focused on defining requirements, clarifying rules, recording in-game prices and supply, setting objective priorities, and validating results through specific cases. Code implementation and some debugging were AI-assisted.

[Problem](#the-problem) · [Design process](#design-process) · [CPU solving](#reducing-cpu-solve-time) · [Current objectives](#current-planning-objectives) · [Cases](#checking-the-design-through-parameter-changes) · [Architecture](#project-architecture) · [Running the project](#running-and-reproducing-results)

## The problem

Choosing a dish for a guest involves the base recipe, added ingredients, tag coverage, trends, and recipe restrictions. Once a dish meets the requirements, there are still choices to make: whether matching another preference is worth an extra ingredient, whether a scarce ingredient has a substitute, and whether the dishes can all be made with the same set of cookware.

Three concepts are useful for reading the rest of this document:

- **Rare guests (`稀客`)**: this version plans only for guests in the input data's `稀客` table. Ordinary guests are outside its scope.
- **Tag score**: each distinct final tag adds one point if the guest likes it and subtracts one if the guest dislikes it. Duplicate tags count only once. The browser filters by the net score; Python first excludes any plan that matches a dislike, so its default three-point threshold requires at least three liked tags.
- **Trend attachment**: the user specifies which tags trigger a trend. When a dish's final tags include a trigger, the tool adds `流行·喜爱` or `流行·厌恶`, then scores the added tag against that guest's preferences. These Chinese strings are the actual tag names used by the tool.

The tool separates these decisions into three levels:

| Decision | Inputs | Output |
| --- | --- | --- |
| Check feasibility | Guest, tag threshold, trend settings, required and excluded tags | Base dishes and added-ingredient combinations that meet the rules, with their final tags |
| Compare plans per guest | Preference coverage, ingredient units, daily supply, and assumed order volume | One plan per guest, selected using explicit priorities |
| Choose a cookware set | Available cookware, exclusions, and permitted cookware count | Selected cookware, the resulting plans per guest, and guests with no feasible plan |

The browser explores multiple candidates at the first level. Python recommends plans per guest and compares cookware sets. These are two independent ways to use the project.

## Design process

The following account organizes key decisions from historical prompts by how the problem evolved. There were branches and revisions, so it is not an exact development timeline. The intention to find optimal solutions remained consistent; the search space, evaluation criteria, and available resources changed.

| Stage | What “optimal” meant at that point | What changed |
| --- | --- | --- |
| Feasible enumeration and return comparisons | List legal dishes and added ingredients that meet the threshold; an early request also proposed ranking by actual profit | The initial query and return-comparison concept; profit is not an objective in the current main workflow |
| Candidate simplification | Define when a qualifying plan can be replaced by a subset of its additions or by lower-grade ingredients | Rules and conditions for retaining candidates |
| Multiple plans by tag | Minimize expected ingredient units, then maximize the minimum supply slack | Combinations of plans and assignment of tag-specific orders |
| One plan per guest | Maximize the liked tags covered by one plan, then compare ingredient units and supply slack | The decision unit and objective priorities |
| Coverage capped at 3 | After matching three liked tags, prefer fewer ingredient units, then compare supply slack | No further objective benefit from the fourth or subsequent liked tags |
| Limited cookware | Compare guest plans under a shared cookware set; at the default three-point threshold, first give more guests a feasible plan | Extend individual guest choices to a shared equipment constraint |

A separate line of iteration pursued **faster solving with the model and results unchanged**. Historical discussions of equivalent reformulations, λ feasibility checks, and binary search belong to this line. Formatting changes were also required to preserve algorithmic results. This needs to be distinguished from deliberately changing the definition of “optimal.”

### 1. Make the rules for a qualifying dish explicit

The initial requirement was to enumerate dishes and added ingredients that reach a three-point tag threshold for a specified rare guest. I clarified the rules one by one: base-recipe ingredients count toward ingredient usage and slots, but do not contribute their tags again; added ingredients may repeat, with each copy occupying a slot but its tags counted only once; a dish may contain at most five ingredient units in total; recipe restrictions apply only to added ingredients.

The earliest prompt also asked for results to be “ranked by actual profit.” That was part of the starting requirements. The later main workflow explicitly uses preference coverage, ingredient units, and supply slack. Neither the early intention nor the historical profit tables establish that the current program optimizes profit.

Tag processing also follows a defined order. The tool first combines tags from the dish, cookware, selling price, and added ingredients. It then applies the overrides `肉` over `素` (meat over vegetarian), `饱腹` over `下酒` (filling over suitable with alcohol), `重油` over `清淡` (heavy oil over light), and `大份` over `小巧` (large over small portions), before checking trends. This makes it possible to inspect why a plan qualifies, rather than receiving only a score. The Chinese names are retained here to match the input tags.

### 2. Define when candidates may be simplified

Enumeration produces many similar combinations. I therefore specified conditions for subset filtering, higher-grade ingredient replacement, and equivalent-ingredient deduplication:

| Design | Required conditions | Tradeoff |
| --- | --- | --- |
| Added-ingredient subset filtering | The same dish has a qualifying subset with fewer added ingredients; score comparison can also be enabled | Remove redundancy after reaching the threshold, or preserve additional score |
| Higher-grade ingredient filtering | The lower-grade ingredient's tag set is a strict subset of the higher-grade ingredient's tag set, and a complete, legal replacement plan exists | Check whether the whole replacement plan is feasible, rather than removing ingredients based on grade alone |
| Equivalent-ingredient deduplication | Group only added ingredients with identical tag sets; leave the base recipe unchanged | Reduce duplicate candidates while retaining recipe constraints |

This turned “optimize it” into verifiable conditions. Similar-looking substitute ingredients are not enough: the entire replacement dish must remain valid. These filtering strategies remain available as user options in the browser.

The filter switches also encode preferences. Without score comparison, a plan can be removed if fewer additions already meet the requirements. With score comparison, the replacement must also score at least as highly. These switches change the retained candidate set, so they cannot all be described as speedups that preserve optimality for every later objective. Ingredients with identical tags may also have different supply characteristics, which require a separate check.

### 3. Turn ingredient availability into comparison metrics

I manually recorded prices, daily supply, commission-related data, and other information, then calculated empirical expectations. Tags determine whether a plan satisfies preferences; supply quantities help compare the resource pressure of making it repeatedly.

Early on, I considered enumerating how several dishes could cover tags and handle orders associated with different tags, comparing expected total ingredient use first and the most constrained ingredient's supply second. I then discussed reformulating this as “retain the minimum-ingredient candidates for each tag, then combine them to optimize slack,” with the requirement that the simpler computation preserve the objectives and results.

The following mathematical form reconstructs that tag-based version from its requirements and old code. Assume the guest has $K$ daily orders, divided equally among $m>0$ participating tag-specific plans. Let $u_i$ be the total use of ingredient $i$ across those plans, and $q_i$ its estimated daily supply:

$$
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
$$

The two-stage requirement was to **first minimize expected ingredient units $E_{\mathrm{old}}$, then maximize the minimum slack $R_{\mathrm{old}}$ among those minimum-ingredient solutions**. All candidates tied for the fewest ingredient units were retained for each tag, allowing the second stage to choose among combinations. I also discussed reformulating the second stage as “can the minimum slack reach at least $\lambda$?” If a higher threshold is feasible, a lower threshold is feasible too, allowing feasibility checks to be combined with binary search. Binary search reduces the number of threshold probes; the combinatorial feasibility check within each probe still has a computational cost.

The equal split is a modeling assumption, not a measured order probability. The old code set $m$ to the number of tags with feasible candidates. If no tag had a feasible candidate, it returned no plan without calculating $K/m$. This multiple-plan model is a historical branch; the current main workflow uses one plan per guest. See the [mathematical model notes (Chinese)](docs/design.md#数学建模从历史多方案到当前单方案) for the two-stage formulas and the $\lambda$ derivation.

Price records and historical profit tables are related data work. In the final planning objectives, “fewer ingredients” means fewer units, not the lowest purchase cost.

### 4. Move from one plan per tag to one plan per guest

I then changed the recommendation unit to the guest: select one dish that covers several of a rare guest's preferences, so the output can serve as a preparation reference organized by guest.

This redefined the optimization problem. Instead of allocating orders across several tag-specific plans, the program now directly compares a single dish's preference coverage, total ingredient units, and supply slack. The output became one row per guest, retaining the base recipe, added ingredients, and matched tags for inspection.

### 5. Cap the benefit of coverage, then add cookware limits

The single-plan model initially prioritized matching as many preferences as possible. I later specified that “three is enough.” Once that threshold is met, the model can prioritize saving ingredients instead of adding more to match a fourth preference.

For example, suppose two plans are legal: A matches three liked tags using two ingredient units, while B matches four using three units. With the coverage benefit capped, both receive the same coverage value, so the model chooses A. This is a benefit boundary defined for the tool, not a claim about the game's complete evaluation system.

With cookware limits added, strong individual plans also have to be compared under shared equipment conditions. The current implementation first computes the best candidate for each guest on each type of cookware, then enumerates sets of the specified size from the available cookware and compares the guest plans each set can provide. This exposes how equipment choices change the range of guests the planner can cover.

See the [requirements retrospective (Chinese)](docs/prompt-journey.md) for the fuller account of requirements and character-based validation.

## Reducing CPU solve time

I did not have a GPU available during prototyping, and wanted the program to solve the problem on the computer I already had. Historical prompts repeatedly asked to “improve computation speed without changing results,” using specific characters, filter switches, and version comparisons to investigate stalls. This project does not require a GPU.

The prototype code shows three categories of solver improvements. They belong to different stages and were not all enabled in the same version:

| Method | Use in the prototypes |
| --- | --- |
| Reduce duplicate candidates and computation | Group added ingredients by tag set and enumerate unordered combinations with repetition; in the old multiple-plan version, generate candidates once per dish, group them by matched tag, and retain all ties for the fewest ingredient units |
| Narrow the combination search | Some prototypes use score upper bounds for pruning; the old multiple-plan second stage uses λ feasibility checks, capacity pruning, and state caching to seek the best minimum slack |
| Reuse subproblems and parallelize on the CPU | The cookware version precomputes the best candidate for each guest and cookware type; the root-level web tool divides work by dish across up to eight Web Workers and returns results in batches |

These implementations were AI-assisted. My requirements were to explain the basis for each optimization, preserve the agreed rules, objective order, and candidates that needed to be retained, and compare results under identical conditions. The historical multiple-plan λ workflow and the final single-plan workflow are documented separately. No speedup factor is claimed without a retained benchmark.

Long computations also need observable progress. I requested processing stages and actual completion counts, and used version comparisons to investigate whether stalls occurred during solving or export. Trend settings across multiple fields, filtering strategies, and cookware conditions are exposed as inputs so that changes can be compared. The [CPU solver retrospective (Chinese)](docs/prompt-journey.md#并行主线在-cpu-上求得更快同时保持结果) records the specific tradeoffs and corrections.

## Current planning objectives

Python defaults to a minimum tag score of `3` and an assumed daily order volume of `K=5` per guest. Plans whose final tags match any dislike are excluded. Qualifying candidates are compared in the following order, with each item taking priority over the next:

1. Maximize `min(number of liked tags matched, 3)`.
2. Minimize the total ingredient units in the base recipe and additions.
3. Maximize the minimum daily supply slack among the ingredients used.
4. Break ties using fixed ordering by selling price, name, and other fields, keeping results reproducible.

Formally, let $p$ be a dish-and-additions plan, $h_g(p)$ the number of liked tags it matches for guest $g$, and $c_i(p)$ the use of ingredient $i$, including both the base recipe and additions. Let $q_i$ be estimated daily supply and $K$ the assumed daily order volume for this guest. Total ingredient units and minimum supply slack are:

$$
L(p)=\sum_i c_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
$$

Let $\mathcal F_g$ be the guest's feasible candidate set: plans using owned recipes and available cookware, satisfying the five-slot limit, added-ingredient restrictions, and tag threshold, with no disliked final tags. The current single-guest objective is:

$$
\underset{p\in\mathcal F_g}{\operatorname{lex\,max}}
\left(\min(h_g(p),3),\;-L(p),\;R(p)\right)
$$

**Lexicographic order** means comparing the criteria in sequence: only a tie on an earlier criterion allows the next one to decide. At equal coverage benefit, no amount of extra supply slack can compensate for using one additional ingredient unit. Selling price and name break ties only when all three criteria are equal. This differs from a weighted sum of the metrics.

The **minimum tag score** and the **coverage benefit cap** are separate concepts. The minimum score is configurable and determines eligibility; the current coverage cap is fixed at 3 and determines objective benefit. For example, setting the minimum score to 4 still requires at least four liked tags to qualify, while the coverage benefit remains capped at 3. See the [mathematical model notes (Chinese)](docs/design.md#数学建模从历史多方案到当前单方案) for the full formulation of base ingredient use, integer addition variables, tag constraints, and cookware objectives.

At the default threshold, every qualifying plan has capped coverage of three. Cookware selection therefore first seeks to give more guests a feasible plan, then reduce ingredient units and improve slack. With a lower minimum score, the first criterion should instead be understood as comparing total coverage.

**Supply slack is a per-guest comparison metric and may be negative.** Different guests do not draw down a shared inventory, so the result does not guarantee that all plans can be supplied simultaneously over an entire evening. The browser's purchasing recommendations rank by TDQ (daily supply quantity), which differs from the demand-subtraction model used here.

## Checking the design through parameter changes

The public sample contains 12 ingredients, eight dishes, and three fictional guests. All cases below use synthetic data to reproduce model behavior; they are not measured in-game returns:

| Condition | Program result | Design implication |
| --- | --- | --- |
| Baseline: three cookware types, K=5, no trends | All three guests have a plan; the three representative dishes use four ingredient units in total | Each recommendation can be traced to its recipe, tags, and quantities |
| Reduce cookware from three types to one | Select `料理台` (cooking station); two guests have plans, while `匠人` (artisan) has none | Equipment limits which guests can be covered |
| Increase K from 5 to 15 | The artisan's slack for `肉片` drops from 9 to −1, but the plan is still returned | Negative slack signals pressure; inventory is not currently a hard constraint |
| Attach `流行·厌恶` to `下酒` | The artisan's recommendation changes from `烤串` to `烤串` + `谷物` | `饱腹` first overrides `下酒`, preventing the disliked trend from triggering, at the cost of one extra ingredient unit |

The baseline total for the three representative dishes is not the amount needed for a full day. When selecting exactly three cookware types, a tied result may also include cookware unused by the final dishes. See the [four cases (Chinese)](docs/case-study.md) and [examples/](examples/) for inputs, per-guest results, and explanations.

![The browser shows 家常饭 and 果盘 candidates with added ingredients, scores, and final tags for the synthetic guest 旅人](docs/images/demo.jpg)

## Project architecture

The system runs locally: **the web tool reads files directly and computes in the browser; Python uses a separate CLI to read JSON, run planning, and export reports. There are no API calls between them.**

| Component | Responsibilities and entry points |
| --- | --- |
| Browser tool | [index.html](index.html) and [web/app.js](web/app.js): data parsing, parameter entry, CPU Web Worker enumeration, candidate filtering, and CSV/XLSX export |
| Data import | [tools/prepare_data.py](tools/prepare_data.py): convert XLSX to standard JSON, associate average purchase prices from merchants by name, and record an audit |
| Python planner | [src/mystia_planner/](src/mystia_planner/): data objects, rules, combination search, cookware comparison, CLI, and JSON/CSV output |
| Demonstration and verification | [data/](data/), [examples/](examples/), and [tests/](tests/): synthetic inputs, reproducible results, and regression cases |

The browser uses the net score of liked tags minus disliked tags; Python additionally makes any dislike a hard exclusion. The two tools have different purposes and objectives, so their outputs are not required to match candidate for candidate. See the [architecture notes (Chinese)](docs/architecture.md) for system boundaries, runtime components, responsibilities, and the complete data flow.

## Running and reproducing results

### Try the browser tool

Download the repository, keep its directory structure, and open `index.html` at the root. The default sample loads automatically. Select a guest and click `开始计算` (start calculation). Enable `加料子集过滤` (added-ingredient subset filtering) and `等价食材去重` (equivalent-ingredient deduplication) to reduce candidates, then change tag conditions to compare results.

If the browser restricts Workers when opening local files, run this command from the repository root:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Visit `http://127.0.0.1:8000`. Files are processed only in the current browser; no login, CDN, or computation backend is required. Local verification used HTTP; opening the file directly by double-clicking has not been automatically verified. See the [web guide (Chinese)](docs/web-guide.md) for filtering and export details.

### Run the Python planner

Python 3.10 or later is required. JSON planning and the synthetic cases use only the standard library.

```sh
# Regenerate the four cases described above
python tools/reproduce_examples.py

# Choose a cookware count and generate a complete report
python tools/run_planner.py --input data/demo.json --cookware-count 3 --output outputs/my-plan.json

# View parameters for guests, trends, cookware exclusions, minimum score, and order volume
python tools/run_planner.py --help
```

### Import game data

The browser can read XLSX or standard JSON directly. To prepare data for Python and record corrections to price associations, use:

```sh
python -m pip install -r requirements.txt
python tools/prepare_data.py my-workbook.xlsx --output local-data/game-data.json --report local-data/import-report.json
python tools/run_planner.py --input local-data/game-data.json --cookware-count 3 --output outputs/game-plan.json
```

The input requires four tables named exactly `食材`, `料理`, `稀客`, and `食材merchant_data`; see [demo.json](data/demo.json) for the format. The importer reads Excel's cached values, associates average purchase prices by name, and retains `null` for unknown prices. It does not rewrite the source workbook. `local-data/` and `outputs/` are excluded from version control by default.

## Verification and scope

```sh
python tools/run_checks.py
node --test tests/web-regression.cjs
```

Local checks passed 31 Python tests and 11 web tests. The Python tests include comparisons on 90 fixed-seed small inputs against an independent exhaustive search over individual ingredients. The web tests execute the actual Worker and cover edge cases such as ingredient restrictions, stopping computation, a zero threshold, and exporting an empty filtered result. Node.js is used only for testing.

Planning with default parameters and a rule-by-rule review were also completed locally for 58 guests using real game data. That source data is not distributed with the public package; the publicly reproducible evidence is the synthetic sample. GitHub CI configuration is prepared but has not yet run remotely. See the [verification record (Chinese)](docs/verification.md).

Current limits: the budget is displayed only. The planner does not jointly optimize drinks, overall satisfaction, cash profit, order probabilities, or inventory shared across guests. Complete original sampling records are unavailable for the empirical expectations, so they are not used to claim statistical significance or improved in-game returns.

## My work, data sources, and collaboration

| Work | Attribution |
| --- | --- |
| Requirements, rule semantics, filtering conditions, objective priorities, cookware constraints, and character-based validation | Author-led |
| Prices, daily supply, commission-related records, and empirical expectations | Manually recorded and organized by the author in the game |
| Historical tag data | From [AnYiEE/touhou-mystia-izakaya-assistant](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant) |
| A substantial portion of code implementation and some debugging | AI-assisted |
| Module organization, synthetic demonstrations, source auditing, regression checks, and documented fixes | Completed for this portfolio preparation with AI assistance; not presented as work already completed during the original development |

During development, I used Kasen Ibaraki (`茨木华扇`) to check differences between versions, Koishi Komeiji (`古明地恋`) to compare cookware configurations, and Rinnosuke Morichika (`森近霖之助`) to investigate a no-solution case under particular trend conditions. These requests shaped a validation process that used a fixed baseline for changes, distinguished formatting edits from algorithm changes, and explained specific inputs and outputs.

The public package uses synthetic data and does not include game art, the complete game database, or original chat logs. See the [data notes (Chinese)](docs/data-provenance.md) for field sources and expectation definitions, and the [changelog (Chinese)](CHANGELOG.md) for changes made during portfolio preparation. SheetJS CE 0.20.3 is bundled with its license. An open-source license has not yet been selected separately for this project's own code; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution. This is an unofficial personal tool.
