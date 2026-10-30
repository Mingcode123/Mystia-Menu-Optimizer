<a id="chinese"></a>

# Mystia Menu Optimizer

**面向顾客偏好、食材供给与厨具约束的料理规划工具**

**中文** | [English](#english)

在[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/)中，玩家通过料理与加料满足顾客偏好。**一个方案由基础料理及追加食材组成**。标签是“甜”“饱腹”等属性；方案的最终标签与人物喜好取交集，得到命中项。流行随机事件改变当期触发标签，角色对流行的态度固定；配方禁忌规定不能追加的标签，与人物厌恶分属不同规则。本项目比较喜好覆盖、食材件数与供给余量，寻找给定条件下的优先方案。

[![完整标签与方案匹配：紫色为人物偏好，蓝色为料理属性，橙色为食材标签。灵梦料理喜好为高级、饱腹、甜、不可思议、实惠、流行·喜爱；厌恶为下酒、昂贵、流行·厌恶。前三例无流行，两个流行词条未启用。方案框包含基础料理和加料。A：饭团无禁忌，加蜂蜜后最终标签为素、家常、饱腹、和风、实惠、料理台、甜；命中饱腹、实惠、甜，3项喜好、0项厌恶、2件食材。B：饭团无禁忌，加猪肉使肉覆盖素，最终标签为家常、饱腹、和风、实惠、料理台、肉；命中饱腹和实惠，低于3项门槛。C：配方禁忌是不能追加的标签，不是人物厌恶。蜂蜜的甜命中臭豆腐的甜、果味禁忌列表，游戏中制成黑暗物质；Python nCookware 在评分前排除该组合。基础配方原料标签另列，计用量但不重复叠加。流行补充：当期触发标签可随随机事件变化，角色对流行·喜爱与流行·厌恶的态度固定；例如本期甜受欢迎，含甜方案追加流行·喜爱，命中灵梦的该项喜好。程序读取输入的流行标签，不生成随机事件。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/584efd7381bef933d149ebcb899a6b9ca0a70bca/docs/images/tag-example.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/584efd7381bef933d149ebcb899a6b9ca0a70bca/docs/images/tag-example.png)

*参考游戏图标生成的规则示意，非游戏截图。* 完整标签依据[原工作簿](东方夜雀食堂.xlsx)；前三例均无流行，流行补充带为独立情境。禁忌冲突在游戏中产生黑暗物质，**Python `nCookware` 则在评分前排除该组合**；网页处理差异见[网页使用说明](docs/web-guide.md)。规则依据见[机制与素材来源](THIRD_PARTY_NOTICES.md)，目标顺序与求解范围见[模型说明](docs/design.md)。

项目以 Excel 为输入，提供网页查询与 Python 规划。第一章以 `singlePLAN_cover3_mixIng_nCookware.py`（简称 `nCookware`）为例定义数学模型。

[数学模型](#zh-model) · [功能范围](#zh-problem) · [设计演进](#zh-evolution) · [系统与算法](#zh-methods) · [运行方法](#zh-running) · [验证结果](#zh-verification) · [局限](#zh-limits) · [贡献与文档](#zh-sources)

<a id="zh-model"></a>

## 1. 数学模型：从游戏决策到优化任务

### 1.1 问题抽象

本模型的决策对象是一份基础料理及其追加食材组合；在厨具配置层面，还需选择一组共同可用的设备。游戏中的备菜需求对应以下数学任务：

| 备菜需求 | 数学表达 | 模型中的作用 |
| --- | --- | --- |
| 为指定顾客选择合适的料理 | 根据最终标签计算喜好与厌恶命中 | 确定候选准入与覆盖收益 |
| 在制作规则内配置配方和加料 | 整数用量、五格上限、配方禁忌与标签覆盖关系 | 构成可行性条件 |
| 达标后减少重复制作的食材消耗 | 最小化每份方案的食材件数 | 第二优先级目标 |
| 降低对供给紧张食材的依赖 | 最大化实际使用食材中的最低供给余量 | 第三优先级目标 |
| 在有限厨具配置下安排各客方案 | 选择指定数量的共同厨具，汇总逐客评价 | 设备集合决策 |

喜好覆盖采用封顶收益，达到 3 项后不再因额外命中增加该项效用。食材件数衡量单位数量，供给余量衡量假设日需求后的资源压力；两者分别对应不同的备菜取舍。供给在此作为比较指标，未设为必须满足的库存硬约束。模型范围集中在料理与设备选择，未联合描述酒水、完整满意度或现金利润。

### 1.2 符号、参数与决策变量

以下符号描述单客模型与厨具配置；历史多方案模型的专用符号在 1.6 节定义。

| 符号 | 类型 | 含义与单位 |
| --- | --- | --- |
| $`g, i, d`$ | 索引 | 分别表示顾客、食材与基础料理 |
| $`p=(d,x)`$ | 决策方案 | 基础料理及追加食材向量，共同确定一份料理方案 |
| $`x_i`$ | 决策变量 | 每份料理追加该食材的件数，取非负整数 |
| $`b_i(d)`$ | 配方参数 | 基础料理中该食材的固定用量，单位为件／份料理 |
| $`c_i(p)`$ | 派生用量 | 基础配方与加料合计的食材用量，单位为件／份料理 |
| $`T(p)`$ | 派生集合 | 处理料理、厨具、售价、加料、覆盖与流行后的最终标签集合 |
| $`P_g, N_g`$ | 顾客参数 | 经流行条件处理后的喜好标签集合与厌恶标签集合 |
| $`h_g(p), a_g(p)`$ | 评价量 | 分别为喜好与厌恶命中的标签数量 |
| $`\tau`$ | 准入参数 | 最低喜好命中数；`nCookware` 默认值为 3 |
| $`K`$ | 需求参数 | 每位顾客的假设日订单量，单位为单／日，默认值为 5 |
| $`q_i`$ | 供给参数 | 食材的经验日供给量，单位为件／日，对应 Total Daily Quantity（TDQ） |
| $`L(p)`$ | 评价量 | 每份方案的食材总件数，重复用料重复计数 |
| $`R(p)`$ | 评价量 | 实际使用食材中的最低供给余量，单位为件／日 |
| $`U(h)`$ | 效用函数 | 喜好命中数经上限 3 截断后的覆盖收益 |
| $`\mathcal C_g`$ | 候选集合 | 实现在给定输入与条件下为顾客生成并保留的候选 |
| $`H, S, n`$ | 集合与参数 | 可用厨具集合、所选共同厨具集合及指定的厨具种类数 |

其中，基础料理选择、追加用量和共同厨具集合属于决策；配方、顾客标签、供给估计和订单假设作为给定输入。最终标签与评价指标由这些输入和决策计算得到。

### 1.3 用量、标签与可行性

食材总用量和件数定义为：

```math
c_i(p)=b_i(d)+x_i,\qquad x_i\in\mathbb Z_{\ge0},\qquad
L(p)=\sum_i c_i(p)
```

基础配方计入食材用量与格数，其食材标签不再次叠加；追加食材标签按集合合并。相同食材可以重复加入，但相同标签仅计一次。经过标签覆盖和流行处理后，喜好与厌恶命中数为：

```math
h_g(p)=\left|T(p)\cap P_g\right|,\qquad
a_g(p)=\left|T(p)\cap N_g\right|
```

`nCookware` 的规则模型要求满足五格限制、最低喜好门槛及无厌恶命中：

```math
L(p)\le5,\qquad h_g(p)\ge\tau,\qquad a_g(p)=0
```

候选还受已拥有料理、配方禁忌及可用厨具条件限制。流行喜爱与厌恶分别由指定标签触发；未指定某方向的触发标签时，该方向的流行标签从顾客偏好与厌恶中移除。浏览器查询采用净分筛选，其评价量为 $`h_g(p)-a_g(p)`$，与本节单客规划的准入条件不同。

### 1.4 单客目标函数

每位顾客的假设订单均采用同一方案。食材的日需求为每份用量乘以日订单量，最低供给余量及覆盖收益定义为：

```math
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right),\qquad
U(h)=\min(h,3)
```

单客方案按以下词典序目标比较：

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(U(h_g(p)),\;-L(p),\;R(p)\right)
```

比较顺序依次为最大覆盖收益、最少食材件数、最大最低供给余量。后续指标仅在前序指标相同时参与比较，三个指标之间没有加权补偿；三项均相同时，以售价、料理名和加料字符串处理平局。

最低门槛与覆盖上限具有不同作用：前者控制候选准入，后者定义效用。在默认门槛 3 下，合格候选的覆盖收益均为 3，因此后续比较主要取决于食材件数和最低供给余量。余量可为负，表示对应假设需求超过经验日供给。

### 1.5 共同厨具配置与求解范围

可用厨具来自已拥有料理对应的设备。所选集合满足：

```math
S\subseteq H,\qquad |S|=n
```

`nCookware` 先计算每客每厨具的最佳保留候选，再枚举共同厨具集合。集合评价依次使用覆盖收益总和、食材件数总和、逐客最低供给余量之和，并对无解顾客设置惩罚。在默认三分门槛下，第一项等价于优先增加有解顾客数。食材用量仍按顾客独立核算，未共同扣减库存。

标签等价代表选择与中性补位截断会限制 $`\mathcal C_g`$。因此，候选集内的目标比较尚不构成全部合法食材组合上的全局最优性证明。集合目标、平局规则与反例见[优化模型与算法边界](docs/design.md)。

### 1.6 历史多方案模型

早期按喜好标签配置多个方案。设日订单量 $`K`$ 在 $`m>0`$ 个具有可行候选的喜好标签方案之间均分，$`u_i`$ 表示所选方案对食材 $`i`$ 的累计用量，$`q_i`$ 沿用上述日供给定义。预期食材件数与最低供给余量分别为：

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

该模型先最小化 $`E_{\mathrm{old}}`$，再在并列组合中最大化 $`R_{\mathrm{old}}`$。订单均分属于模型假设，缺少对应的实测概率估计；没有可行标签时不生成方案。单客模型改变了决策单位与评价顺序，相关设计过程见第 3 章。

<a id="zh-problem"></a>

## 2. 功能范围与执行入口

系统提供以下执行入口，分别支持候选查询、逐客规划和独立分析。各入口共享工作簿数据，但采用不同的评价规则。

| 入口 | 主要用途 | 输出 |
| --- | --- | --- |
| 浏览器查询 | 枚举单个稀客的料理与加料组合，支持标签、得分与替代策略筛选 | 候选表、CSV、单表 XLSX |
| Python PLAN 系列 | 按标签或按顾客生成方案，比较食材件数、供给余量与厨具配置 | 规划 XLSX |
| 得分与利润脚本 | 分析基础料理得分、价格及利润梯度 | 独立分析工作簿 |

浏览器采用“喜好命中数减厌恶命中数”的净分。`nCookware` 排除最终标签命中厌恶的候选，并使用分层优化目标。两类入口的候选范围和评价规则分别定义。

<a id="zh-evolution"></a>

## 3. 需求与设计演进

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

<a id="zh-methods"></a>

## 4. 系统结构与 CPU 求解方法

浏览器和 Python 脚本是两个独立执行入口，共享 Excel 数据文件。浏览器的 HTTP 服务仅提供静态文件；候选计算由浏览器 CPU 完成。Python 脚本直接读写工作簿。系统的数据流与文件职责见[架构说明](docs/architecture.md)。

| 计算环节 | 实现方法 | 适用范围 |
| --- | --- | --- |
| 网页加料枚举 | 按料理静态分块，使用最多 8 个 Web Worker，结合重复组合枚举和候选过滤 | 浏览器查询 |
| Python 候选生成 | 标签等价分组、相关加料筛选、深度优先搜索（DFS）及得分上界 | PLAN 分支；代表选择与中性补位最多三项影响候选范围 |
| 多标签方案组合 | 以 $`\lambda`$ 表示最低供给余量门槛，进行可行性判定；使用二分、DFS、容量剪枝和状态缓存 | 历史多方案分支 |
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

In [*Touhou Mystia's Izakaya*](https://store.steampowered.com/app/1584090/), players choose dishes and additions to satisfy guest preferences. **A plan consists of a base dish and additional ingredients**. Tags are attributes such as sweet or filling; intersecting the plan's final tags with the guest's likes gives the matched tags. Random trend events change the current trigger tags, while each guest's attitude toward trends remains fixed; recipe prohibitions restrict added tags and are distinct from guest dislikes. This project compares preference coverage, ingredient units, and supply slack to rank plans under given conditions.

[![Complete tags and plan matching: purple identifies guest preferences, blue recipe attributes, and orange ingredient tags. Reimu likes high-grade, filling, sweet, wondrous, affordable, and liked trend; she dislikes pub food, expensive, and disliked trend. The first three examples have no trends, so both trend entries are inactive. Each plan frame contains its base dish and additions. A: Rice ball has no prohibitions. Adding honey produces vegetarian, homestyle, filling, Japanese, affordable, prep counter, and sweet; filling, affordable, and sweet give 3 liked matches, 0 disliked matches, and 2 ingredient units. B: Rice ball has no prohibitions. Pork overrides vegetarian, leaving homestyle, filling, Japanese, affordable, prep counter, and meat. Only filling and affordable match, below threshold 3. C: Recipe prohibitions restrict added tags and differ from guest dislikes. Honey's sweet tag matches stinky tofu's prohibition list of sweet and fruity, producing Dark Matter in the game; Python nCookware excludes the combination before scoring. Required-ingredient tags are listed separately; their units count without adding their tags again. Trend note: current trigger tags can change through random events, while each guest's attitude toward liked trend and disliked trend stays fixed. For example, if sweet is currently popular, a plan containing sweet gains liked trend and matches that preference of Reimu. The program reads supplied trend tags rather than generating random events.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/584efd7381bef933d149ebcb899a6b9ca0a70bca/docs/images/tag-example.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/584efd7381bef933d149ebcb899a6b9ca0a70bca/docs/images/tag-example.png)

*Rule illustration generated with game icons as references, not a game screenshot.* Complete tag lists come from the [original workbook](东方夜雀食堂.xlsx); the first three examples have no trends, and the trend note is a separate scenario. A forbidden-tag conflict produces Dark Matter in the game; **Python `nCookware` excludes the combination before scoring**. Browser behavior differs as documented in the [browser guide](docs/web-guide.md). See the [mechanism and artwork sources](THIRD_PARTY_NOTICES.md) for rule references and the [model documentation](docs/design.md) for objective priorities and solution scope.

The project takes Excel input and provides browser queries and Python planning. Chapter 1 defines the mathematical model using `singlePLAN_cover3_mixIng_nCookware.py` (`nCookware` for short).

[Mathematical model](#en-model) · [Functional scope](#en-problem) · [Design evolution](#en-evolution) · [System and algorithms](#en-methods) · [Usage](#en-running) · [Verification](#en-verification) · [Limitations](#en-limits) · [Contributions and documentation](#en-sources)

<a id="en-model"></a>

## 1. Mathematical model: from gameplay decisions to optimization

### 1.1 Problem abstraction

The decision unit is a base dish with a combination of additional ingredients. At the cookware level, a common equipment set must also be selected. Meal-preparation requirements map to mathematical tasks as follows:

| Preparation requirement | Mathematical representation | Role in the model |
| --- | --- | --- |
| Choose a suitable dish for a guest | Count liked and disliked tags in the final tag set | Determine eligibility and coverage benefit |
| Configure recipes and additions within preparation rules | Integer quantities, a five-slot limit, recipe restrictions, and tag overrides | Define feasibility conditions |
| Reduce ingredient use in repeated preparation after qualification | Minimize ingredient units per plan | Second-priority objective |
| Reduce dependence on ingredients with tight supply | Maximize minimum supply slack over ingredients used | Third-priority objective |
| Plan for guests under limited cookware | Select a specified number of shared cookware types and aggregate guest evaluations | Equipment-set decision |

Preference coverage has capped utility: matching more than 3 liked tags does not increase that benefit. Ingredient units measure quantity, while supply slack measures resource pressure under assumed daily demand. They represent distinct preparation tradeoffs. Supply is a comparison criterion rather than a hard inventory constraint. The model focuses on dishes and equipment and does not jointly represent drinks, full satisfaction, or cash profit.

### 1.2 Notation, parameters, and decision variables

The following notation describes the single-guest model and cookware configuration. Symbols specific to the historical multiple-plan model are defined in Section 1.6.

| Symbol | Type | Meaning and units |
| --- | --- | --- |
| $`g, i, d`$ | Indices | Guest, ingredient, and base dish, respectively |
| $`p=(d,x)`$ | Decision plan | A base dish and an additional-ingredient vector defining one recipe plan |
| $`x_i`$ | Decision variable | Nonnegative integer quantity of an additional ingredient per plan, in units |
| $`b_i(d)`$ | Recipe parameter | Fixed quantity of that ingredient in the base recipe, in units per dish |
| $`c_i(p)`$ | Derived quantity | Total use of that ingredient in the base recipe and additions, in units per dish |
| $`T(p)`$ | Derived set | Final tags after processing dish, cookware, price, additions, overrides, and trends |
| $`P_g, N_g`$ | Guest parameters | Liked-tag and disliked-tag sets after trend-condition processing |
| $`h_g(p), a_g(p)`$ | Evaluation quantities | Counts of liked and disliked tags matched, respectively |
| $`\tau`$ | Eligibility parameter | Minimum liked-tag count; the `nCookware` default is 3 |
| $`K`$ | Demand parameter | Assumed orders per guest per day; the default is 5 |
| $`q_i`$ | Supply parameter | Empirical ingredient supply in units per day, recorded as Total Daily Quantity (TDQ) |
| $`L(p)`$ | Evaluation quantity | Total ingredient units per plan, including repeated use |
| $`R(p)`$ | Evaluation quantity | Minimum supply slack over ingredients used, in units per day |
| $`U(h)`$ | Utility function | Coverage benefit obtained by capping the liked-tag count at 3 |
| $`\mathcal C_g`$ | Candidate set | Candidates generated and retained for a guest under the given inputs and conditions |
| $`H, S, n`$ | Sets and parameter | Available cookware, selected shared cookware, and the specified number of cookware types |

The base dish, additional quantities, and shared cookware set are decisions. Recipes, guest tags, supply estimates, and assumed orders are given inputs. Final tags and evaluation quantities are computed from those inputs and decisions.

### 1.3 Quantities, tags, and feasibility

Total use of each ingredient and the ingredient-unit count are defined as:

```math
c_i(p)=b_i(d)+x_i,\qquad x_i\in\mathbb Z_{\ge0},\qquad
L(p)=\sum_i c_i(p)
```

Base ingredients contribute to quantities and occupied slots without adding their tags again. Additional-ingredient tags are merged as a set. An ingredient may be added repeatedly, while each distinct tag counts once. After tag overrides and trend processing, liked and disliked matches are:

```math
h_g(p)=\left|T(p)\cap P_g\right|,\qquad
a_g(p)=\left|T(p)\cap N_g\right|
```

The `nCookware` rule model requires the five-slot limit, the minimum liked-tag threshold, and no disliked-tag matches:

```math
L(p)\le5,\qquad h_g(p)\ge\tau,\qquad a_g(p)=0
```

Candidates are also restricted by owned dishes, recipe prohibitions, and available cookware. Liked and disliked trends are triggered by separately specified tags. When no trigger is supplied for a trend direction, that trend tag is removed from guest preference and dislike sets. The browser instead filters on the net score $`h_g(p)-a_g(p)`$, which differs from the single-guest planning eligibility conditions in this section.

### 1.4 Single-guest objective

One plan serves all assumed orders for a guest. Daily ingredient demand is per-dish use multiplied by daily orders. Minimum supply slack and coverage benefit are:

```math
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right),\qquad
U(h)=\min(h,3)
```

Single-guest plans are compared using the lexicographic objective:

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(U(h_g(p)),\;-L(p),\;R(p)\right)
```

The criteria maximize coverage benefit, minimize ingredient units, and maximize minimum supply slack, in that order. A later criterion is considered only when earlier criteria tie, with no weighted compensation between them. Selling price, dish name, and the additions string resolve remaining ties.

The minimum threshold controls eligibility, while the coverage cap defines utility. At the default threshold of 3, qualifying candidates all have a coverage benefit of 3, so subsequent comparisons primarily depend on ingredient units and minimum supply slack. Negative slack indicates that the corresponding assumed demand exceeds empirical daily supply.

### 1.5 Shared cookware and solution scope

Available cookware is determined by the equipment associated with owned dishes. The selected set satisfies:

```math
S\subseteq H,\qquad |S|=n
```

`nCookware` first computes the best retained candidate for each guest and cookware type, then enumerates shared cookware sets. It compares total coverage benefit, total ingredient units, and the sum of per-guest minimum supply slack values, with penalties for guests lacking a feasible plan. At the default three-point threshold, the first criterion prioritizes the number of guests with a plan. Ingredient demand remains independently accounted for per guest, without joint inventory deductions.

Equivalent-ingredient representative selection and the neutral-filler cutoff restrict $`\mathcal C_g`$. Objective comparison within this set therefore does not establish global optimality over all legal ingredient combinations. The set-level objective, tie-breaking rules, and a counterexample appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

### 1.6 Historical multiple-plan model

An earlier model assigns multiple plans by liked tag. Assume daily orders $`K`$ are distributed equally among $`m>0`$ tag-specific plans with feasible candidates. Let $`u_i`$ denote total use of ingredient $`i`$ across the selected plans; $`q_i`$ retains the daily-supply definition above. Expected ingredient units and minimum supply slack are:

```math
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

This model first minimizes $`E_{\mathrm{old}}`$, then maximizes $`R_{\mathrm{old}}`$ among ties. Equal order allocation is a modeling assumption without a corresponding measured probability estimate. No plan is produced when no tag has a feasible candidate. The single-guest model changes both the decision unit and the evaluation order; Chapter 3 describes that design evolution.

<a id="en-problem"></a>

## 2. Functional scope and entry points

The following entry points support candidate queries, guest-specific planning, and separate analyses. They share workbook data but use distinct evaluation rules.

| Entry point | Main purpose | Output |
| --- | --- | --- |
| Browser query | Enumerate dishes and additions for one rare guest, with tag, score, and substitution filters | Candidate table, CSV, single-sheet XLSX |
| Python PLAN scripts | Produce tag-specific or guest-specific plans and compare ingredient units, supply slack, and cookware configurations | Planning XLSX |
| Score and profit scripts | Analyze base-dish scores, prices, and profit tiers | Separate analysis workbooks |

The browser uses a net score: liked tags matched minus disliked tags matched. `nCookware` excludes candidates whose final tags match dislikes and applies a hierarchical objective. The two entry points define their candidate spaces and evaluation rules separately.

<a id="en-evolution"></a>

## 3. Requirements and design evolution

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
