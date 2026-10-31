<a id="chinese"></a>

# Mystia Menu Optimizer

**《东方夜雀食堂》备菜决策建模：偏好覆盖、食材供给与厨具配置**

**中文** | [English](#english)

在[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/)中，同一位顾客可能接受多种料理与加料组合，而这些组合的用料、供给压力和所需厨具不同。备菜决策因此需要同时回答两个问题：哪些方案满足条件，以及在多个合格方案之间如何定义“更优”。

本项目将上述问题抽象为离散决策模型，明确配方与加料的可行域，并建立喜好覆盖、食材件数与最低供给余量的分层评价体系。模型经历了按喜好标签配置多套方案、每位顾客配置单套方案、覆盖收益封顶及共同厨具选择等调整。项目产出包括规则与数据定义、数学模型、设计决策说明，以及用于搜索候选和复核结果的程序。

作者的主要工作是提出游玩问题、梳理规则语义、记录供给与价格、确定目标和约束，并通过角色案例核对结果；代码实现、部分算法推导与调试使用 AI 辅助。本文重点说明这些建模选择及其影响，结果解释限定于给定数据、假设和实际保留的候选范围。

[数学模型](#zh-model) · [设计依据与演进](#zh-evolution) · [数据与假设](#zh-data) · [案例与验证](#zh-verification) · [求解与复现](#zh-methods) · [局限](#zh-limits) · [贡献与文档](#zh-sources)

**机制与术语** &nbsp; <a href="#zh-tag-figure"><img src="docs/images/jump-to-figure-zh.png" alt="看机制图" width="104" height="28" align="middle"></a>

制作与评价分为三个步骤：

1. **按配方确定料理。** 配方规定所需厨具和基础食材。例如，使用料理台和海苔×1可以制作饭团。饭团使用自身预设标签，海苔的标签不随基础配方自动加入。
2. **选择加料，形成方案。** 每份料理最多使用 5 件食材，基础食材与加料共同占用格子。饭团的海苔占 1 格，其余 4 格可加料，也可留空。若追加蜂蜜×1，就得到“饭团＋蜂蜜”的方案：总用料为 2 件，料理仍是饭团，蜂蜜带入「甜」标签。最终标签还需按覆盖等规则处理。
3. **将最终标签与顾客偏好匹配。** 每位顾客分别有喜爱、厌恶的标签。同名标签出现在方案中，即命中该项偏好；同一种标签只计一次。例如，图中饭团加蜂蜜对博丽灵梦命中「饱腹」「实惠」「甜」三项喜爱，没有命中厌恶，得分为 3−0=3。

| 术语 | 定义 |
| --- | --- |
| 食材（Ingredient） | 海苔、蜂蜜等制作材料；配方规定的用量计为基础食材，额外追加的部分计为加料。同种食材可以同时承担这两种用途。 |
| 料理（Dish） | 按配方制作的菜品，如饭团；具有自身预设标签、指定厨具和配方禁忌。 |
| 加料（Addition） | 满足基础配方后，在剩余格子中额外使用的食材，如饭团中的蜂蜜；合法加料保留所选料理，并带入食材标签。 |
| 方案（Plan） | 一次具体的制作选择：料理，以及加料的种类和数量；也允许不加料。基础食材与加料合计不超过 5 件，重复使用同种食材仍逐件占格。 |
| 标签（Tag） | 用于描述属性或制作方式的名称，如「甜」「饱腹」「料理台」；也是与顾客喜爱、厌恶进行匹配的单位。 |
| 得分（Score） | 针对指定顾客计算的“喜爱命中数 − 厌恶命中数”。它描述标签匹配情况；规划还需比较食材件数与供给，见[第一章](#zh-model)。 |

配方禁忌属于料理的制作限制，人物厌恶属于顾客偏好，两者作用不同。下图进一步展示标签覆盖、禁忌冲突和流行如何影响方案；这里的得分不等同于完整游戏评价或利润。

<a id="zh-tag-figure"></a>

[![五节机制图：五格配方、喜好匹配、标签覆盖、配方禁忌与流行。蓝色表示料理标签，橙色表示食材标签，青绿色表示厨具标签，紫色表示人物喜爱，石板灰表示人物厌恶，浅红色表示配方禁忌。料理台与海苔×1仅满足饭团配方，占1格、余4格；加蜂蜜后占2格、余3格。料理标签不等于基础食材标签的并集，加料才带入标签。A、B均展示灵梦完整偏好：喜爱「高级」「饱腹」「甜」「不可思议」「实惠」「流行·喜爱」，厌恶「下酒」「昂贵」「流行·厌恶」。A：饭团加蜂蜜，命中「饱腹」「实惠」「甜」，3项喜爱减0项厌恶，得分3。B：饭团加猪肉，「肉」覆盖「素」，命中「饱腹」「实惠」，得分为2减0等于2。饭团无配方禁忌。C：蜂蜜的「甜」触发臭豆腐禁忌，其他搭配不能抵消；游戏结果为黑暗物质，Python nCookware在评分前排除。A、B、C无流行。独立流行情境中，当期触发标签随随机事件变化，人物对流行的偏好固定，程序读取输入条件；「甜」流行时，饭团加蜂蜜方案保留「甜」并获得「流行·喜爱」，对灵梦命中4项喜爱、0项厌恶，得分4。下方琪露诺喜爱「流行·厌恶」、厌恶「流行·喜爱」。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.png)

*图 1. 配方、加料与标签匹配机制。A、B、C 均无流行，末节以相同方案展示「甜」流行后的 4−0=4，再列琪露诺的流行偏好；本图为规则示意，游戏图标使用原像素。* [SVG 矢量原图](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.svg)。标签依据[原工作簿](东方夜雀食堂.xlsx)；禁忌组合在游戏中产生黑暗物质，Python `nCookware` 在评分前排除，网页差异见[网页使用说明](docs/web-guide.md)。规则与素材来源见[第三方声明](THIRD_PARTY_NOTICES.md)。

第一章以单客方案与共同厨具配置模型为主体，对应实现简称 `nCookware`；历史多方案模型用于说明决策单位与目标的变化。五格与配方禁忌属于制作条件，喜好门槛与无厌恶准入属于规划政策。

<a id="zh-model"></a>

## 1. 数学模型：从游戏决策到优化任务

### 1.1 模型演进总览

项目持续研究的是如何选择备菜方案；随需求明确而改变的，是**选一个什么对象、哪些方案可以进入比较，以及“更优”按什么顺序判断**。网页首先提供达标候选查询；Python 规划进一步定义多标签方案组合、每客单方案、覆盖收益封顶和共同厨具配置。HTML 与 Python 是共享工作簿的独立入口，图中的箭头表示决策定义的递进，不表示前后端调用或精确开发时间线。

[![模型演进：网页按喜好减厌恶的净分筛选多个候选；历史多方案为每个可行喜好标签选方案，先最少预期件数再最大最低供给余量；单客模型改为先最大喜好覆盖、再最少件数和最大余量；cover3把覆盖收益封顶为3；厨具模型从固定排除扩展到选择恰好n种共同设备。排版修改、CPU提速和利润分析另行区分。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.png)

*图 2. 决策单位、目标与约束的演进。箭头按问题依赖组织；每种模型的“最优”仅针对其评价政策和保留候选成立。* [SVG 矢量原图](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.svg)。

从网页到规划层，关键变化是从返回合格候选，推进到按明确的目标顺序选定规划方案。从多方案到单方案，订单分配和决策单位同时改变；从未封顶到 `cover3`，改变的是第 4 项及更多喜好命中的边际收益；从固定厨具到 `nCookware`，设备集合成为新增决策变量。以下先完整定义单客与共同厨具模型，再对照历史多方案和网页筛选，避免混用各分支的目标。

### 1.2 问题抽象

本模型的决策对象是一份基础料理及其追加食材组合；在厨具配置层面，还需选择一组共同可用的设备。游戏中的备菜需求对应以下数学任务：

| 备菜需求 | 数学表达 | 模型中的作用 |
| --- | --- | --- |
| 为指定顾客选择合适的料理 | 根据最终标签计算喜好与厌恶命中 | 确定候选准入与覆盖收益 |
| 在制作规则内配置配方和加料 | 整数用量、五格上限、配方禁忌与标签覆盖关系 | 构成可行性条件 |
| 达标后减少重复制作的食材消耗 | 最小化每份方案的食材件数 | 第二优先级目标 |
| 降低对供给紧张食材的依赖 | 最大化实际使用食材中的最低供给余量 | 第三优先级目标 |
| 在有限厨具配置下安排各客方案 | 选择指定数量的共同厨具，汇总逐客评价 | 设备集合决策 |

喜好覆盖采用封顶收益，达到 3 项后不再因额外命中增加该项效用。食材件数衡量单位数量，供给余量衡量假设日需求后的资源压力；两者分别对应不同的备菜取舍。供给在此作为比较指标，未设为必须满足的库存硬约束。模型范围集中在料理与设备选择，未联合描述酒水、完整满意度或现金利润。

### 1.3 符号、参数与决策变量

以下符号描述单客模型与厨具配置；历史多方案模型的专用符号在 1.7 节定义。

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
| $`s_g(p)`$ | 评价量 | 偏好净分，即喜好命中数减厌恶命中数 |
| $`\kappa(d)`$ | 配方参数 | 制作料理所需的厨具 |
| $`\tau`$ | 准入参数 | 最低喜好命中数；`nCookware` 默认值为 3 |
| $`K`$ | 需求参数 | 每位顾客的假设日订单量，单位为单／日，默认值为 5 |
| $`q_i`$ | 供给参数 | 食材的经验日供给量，单位为件／日，对应 Total Daily Quantity（TDQ） |
| $`L(p)`$ | 评价量 | 每份方案的食材总件数，重复用料重复计数 |
| $`R(p)`$ | 评价量 | 实际使用食材中的最低供给余量，单位为件／日 |
| $`U(h)`$ | 效用函数 | 喜好命中数经上限 3 截断后的覆盖收益 |
| $`\mathcal C_g`$ | 候选集合 | 实现在给定输入与条件下为顾客生成并保留的候选 |
| $`H, S, n`$ | 集合与参数 | 可用厨具集合、所选共同厨具集合及指定的厨具种类数 |

其中，基础料理选择、追加用量和共同厨具集合属于决策；配方、顾客标签、供给估计和订单假设作为给定输入。最终标签与评价指标由这些输入和决策计算得到。

### 1.4 用量、标签与可行性

食材总用量和件数定义为：

```math
c_i(p)=b_i(d)+x_i,\qquad x_i\in\mathbb Z_{\ge0},\qquad
L(p)=\sum_i c_i(p)
```

基础配方计入食材用量与格数，其食材标签不再次叠加；追加食材标签按集合合并。相同食材可以重复加入，但相同标签仅计一次。经过标签覆盖和流行处理后，喜好与厌恶命中数为：

```math
h_g(p)=\left|T(p)\cap P_g\right|,\qquad
a_g(p)=\left|T(p)\cap N_g\right|,\qquad
s_g(p)=h_g(p)-a_g(p)
```

`nCookware` 的规则模型要求满足五格限制、最低喜好门槛及无厌恶命中：

```math
L(p)\le5,\qquad h_g(p)\ge\tau,\qquad a_g(p)=0
```

候选还受已拥有料理、配方禁忌及可用厨具条件限制。流行喜爱与厌恶分别由指定标签触发；未指定某方向的触发标签时，该方向的流行标签从顾客偏好与厌恶中移除。浏览器查询采用净分筛选，其评价量为 $`h_g(p)-a_g(p)`$，与本节单客规划的准入条件不同。

### 1.5 单客目标函数

每位顾客的假设订单均采用同一方案。食材的日需求为每份用量乘以日订单量，最低供给余量及覆盖收益定义为：

```math
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right),\qquad
U(h)=\min(h,3)
```

未封顶的 `singlePLAN` 首先追求更多喜好命中：

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(h_g(p),\;-L(p),\;R(p)\right)
```

`cover3` 及后续分支将第一项改为封顶效用，得到：

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(U(h_g(p)),\;-L(p),\;R(p)\right)
```

比较顺序依次为最大覆盖收益、最少食材件数、最大最低供给余量。后续指标仅在前序指标相同时参与比较，三个指标之间没有加权补偿；三项均相同时，以售价、料理名和加料字符串处理平局。

最低门槛与覆盖上限具有不同作用：前者控制候选准入，后者定义效用。在默认门槛 3 下，合格候选的覆盖收益均为 3，因此后续比较主要取决于食材件数和最低供给余量。余量可为负，表示对应假设需求超过经验日供给。

例如，图 1 的饭团加蜂蜜在「甜」触发流行喜爱时，原始得分为 4，封顶效用仍为 3。封顶不删除第 4 个命中标签，也不把原始得分改成 3；它只改变方案比较的收益定义。

### 1.6 共同厨具配置与求解范围

可用厨具来自已拥有料理对应的设备。所选集合满足：

```math
S\subseteq H,\qquad |S|=n
```

`nCookware` 先计算每客每厨具的最佳保留候选，再枚举共同厨具集合。集合评价依次使用覆盖收益总和、食材件数总和、逐客最低供给余量之和，并对无解顾客设置惩罚。在默认三分门槛下，第一项等价于优先增加有解顾客数。食材用量仍按顾客独立核算，未共同扣减库存。

令 $`\mathcal C_g(S)=\{p\in\mathcal C_g:\kappa(d)\in S\}`$，$`p_g^*(S)`$ 为其中按单客目标选出的方案；$`G_S`$ 为有方案的顾客集合，$`z_S`$ 为无方案顾客数。原程序的集合评价写为：

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\sum_{g\in G_S}U(h_g(p_g^*(S))),\;
-\left[\sum_{g\in G_S}L(p_g^*(S))+10^9z_S\right],\;
\sum_{g\in G_S}R(p_g^*(S))-10^{18}z_S
\right)
```

两项常数来自原实现的无解惩罚；模型并不要求所有顾客必须有方案。其可分解结构来自“给定共同厨具后，各客独立评价”的设定。`limitedCookware` 分支仅从给定集合中排除指定设备，没有把设备集合本身作为优化变量。

标签等价代表选择与中性补位截断会限制 $`\mathcal C_g`$。因此，候选集内的目标比较尚不构成全部合法食材组合上的全局最优性证明。集合目标、平局规则与反例见[优化模型与算法边界](docs/design.md)。

### 1.7 历史多方案模型

历史 `detailedPLAN` 按喜好标签配置多个方案。对每个具有候选的目标喜好标签 $`t`$，在包含该标签且通过准入的子池中执行原食材升级与追加子集过滤，从保留候选中选择方案 $`p_t`$；同一料理方案可以承担多个标签的订单份额。设日订单量 $`K`$ 在 $`m>0`$ 个具有可行候选的喜好标签方案之间均分，$`u_i`$ 表示所选方案对食材 $`i`$ 的累计用量，$`q_i`$ 沿用上述日供给定义。预期食材件数与最低供给余量分别为：

```math
u_i=\sum_t c_i(p_t),\qquad
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

其目标为：

```math
\min_{(p_t)_t}^{\mathrm{lex}}\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

第一目标在固定标签数下可按标签拆分，所以程序先保留各标签全部并列最少件数方案；第二目标再比较组合的共同食材消耗；最低余量相同时，继续最大化完整的升序余量向量。对给定余量阈值 $`\lambda`$，判定是否存在组合使所有实际用料满足 $`q_i-(K/m)u_i\ge\lambda`$，据此采用二分与 DFS 搜索。这里最大化的是一位顾客的多方案组合余量，不是多个顾客共享库存的余量。订单均分属于模型假设，缺少对应的实测概率估计；没有可行标签时不生成方案。单客模型改变了决策单位与评价顺序，相关设计过程见第 2 章。

### 1.8 网页筛选与规划目标的区别

网页给定顾客、净分门槛和可选筛选条件，返回保留候选集合。令 $`\mathcal C_g^{\mathrm{web}}`$ 为网页按其枚举和过滤规则生成的候选，其核心得分条件为：

```math
\mathcal W_g(\tau)=\left\{p\in\mathcal C_g^{\mathrm{web}}:s_g(p)\ge\tau\right\}
```

这是候选筛选条件，而不是一个跨料理的唯一最优目标。网页允许用喜好命中抵消厌恶扣分，Python PLAN 则提前排除任何厌恶命中；两者的配方禁忌解析和持有条件也有差异。开启网页采购推荐后，在每道料理内部比较食材日供给的排序向量并保留不差于第 N 名阈值的全部候选及并列，尚未采用“日供给减假设消耗”的余量模型。具体排序与过滤规则见[优化模型与算法边界](docs/design.md)及[网页使用说明](docs/web-guide.md)。

<a id="zh-evolution"></a>

## 2. 模型设计依据与目标演进

### 2.1 从备菜问题到可比较的目标

项目起点是寻找满足顾客要求的备菜方案。随着规则和使用条件明确，“最优”的含义逐步落实为决策单位、准入条件和比较顺序。早期需求还包括按实际利润排序；后续规划主线采用食材件数与供给余量表达资源需求，普客、酒水、价格和利润保留为独立分析支线。

| 决策问题 | 模型调整 | 取舍依据与影响 |
| --- | --- | --- |
| 为多个喜好标签分别准备什么 | 每个可覆盖标签配置方案，按订单均分假设估计总用量；先最少预期件数，再最大最低供给余量 | 不同标签分别承担订单份额；并列最少件数的方案仍需保留，因为食材分配会影响供给压力 |
| 每位顾客固定准备什么 | 决策单位改为一位顾客的一套方案；先比较喜好覆盖，再比较件数与余量 | 需求明确改为每位稀客固定输出一套方案；不再按各标签均分订单，该方案承担全部假设订单，目标转向单份料理的覆盖与消耗 |
| 达标后是否继续追求更多命中 | 将覆盖收益封顶为 3 | 达标后优先控制用料；额外命中仍可存在，但不再增加第一目标收益 |
| 有限设备如何服务多位顾客 | 从指定厨具排除扩展到选择恰好 n 种共同厨具 | 单客方案需适配共同设备；默认门槛下，集合评价首先增加有合格方案的顾客数 |

这些阶段改变了优化问题的定义。将基础食材与加料合并到五个输出格，则属于结果表达调整，沿用既有目标。分支对应关系、历史需求和角色验收案例见[需求与设计决策演进](docs/prompt-journey.md)。

### 2.2 评价指标与取舍依据

覆盖、件数和供给余量表达不同偏好。以下选择构成模型的评价政策，其作用可以由目标函数直接解释。

| 选择 | 决策含义 | 代价与适用条件 |
| --- | --- | --- |
| 覆盖收益封顶 | 达到目标覆盖后，把资源节约作为主要比较依据 | 放弃用第一目标奖励第 4 项及更多命中；3 是本模型的效用设定，不能据此推断完整游戏评价 |
| 以食材件数衡量消耗 | 每件食材按相同数量单位计入基础配方与加料 | 件数相同不代表采购金额或取得难度相同，因此另设供给指标 |
| 比较最低供给余量 | 关注方案实际用料中余量最小的食材，识别需求下的供给瓶颈 | 余量允许为负；未估计缺货概率，也未作为必须满足的库存约束 |
| 采用词典序 | 后一指标只在前一指标相同时参与比较，保持明确的优先级 | 较高供给余量无法补偿较多用料；这是需求规定的排序方式，未通过实验确立为普遍最优的偏好表达 |

### 2.3 制作规则、准入与排序的分工

配方禁忌决定制作冲突；无厌恶命中和最低喜好门槛是规划模型的候选准入策略；通过准入后，才应用分层目标比较方案。浏览器查询另用喜好命中减厌恶命中的净分筛选候选。因此，图中的得分、规划准入与覆盖效用分别承担不同职责，不能将网页结果直接视为规划排名。

<a id="zh-data"></a>

## 3. 数据来源、参数估计与假设

规则资料、人工观测和模型设定在推理中具有不同地位。区分其来源，可以明确结果在哪些条件下成立。

| 类别 | 内容与依据 | 在模型中的作用 |
| --- | --- | --- |
| 规则与属性资料 | 历史工作簿中的配方、厨具、标签和人物偏好；标签资料来自 AnYiEE 的项目 | 确定制作条件、标签处理和偏好匹配 |
| 经验观测 | 作者手工记录价格、日供给及委托相关数据，并整理经验期望 | 日供给作为资源评价输入；价格用于独立经济分析 |
| 需求与情境假设 | 每客日订单默认 5；单客模型中这些订单使用同一方案；历史模型按可行标签均分订单 | 将单份配方用量转化为假设日需求 |
| 评价政策 | 喜好门槛、无厌恶准入、覆盖封顶、目标顺序及厨具数量 | 定义可接受方案和方案间的优先关系 |
| 派生指标 | 喜好与厌恶命中、食材件数、最低供给余量及集合汇总值 | 根据数据、假设和决策计算评价结果 |

工作簿按 `nCookware` 的解析口径包含 62 条食材记录、164 道料理记录和 58 位稀客，其中 163 道料理标记为持有。`Total Daily Quantity` 表示经验日供给；最低供给余量由它减去假设日需求后计算，不能解释为玩家实时库存。

价格波动通过历史记录与数量加权计算处理，但完整采样日期、次数和来源版本未留存。采购价公式还存在按行关联错位及部分错误缓存的风险。因此，现有价格和供给用于描述历史经验条件，尚不足以建立可靠的需求分布、置信区间或缺货概率。具体字段、估计口径与来源范围见[数据来源说明](docs/data-provenance.md)。

<a id="zh-verification"></a>

## 4. 案例分析与验证范围

以下案例分别解释规则准入、目标变化和候选简化的影响。其中的说明性比较与构造反例用于检验模型逻辑；已有程序运行记录另列于 4.4 节。

### 4.1 从机制图到候选准入

图 1 中，饭团加蜂蜜命中灵梦 3 项喜好、0 项厌恶；饭团加猪肉命中 2 项喜好、0 项厌恶。在默认 `nCookware` 条件下，前者满足喜好门槛，后者未达门槛。臭豆腐加蜂蜜触发配方禁忌，在该规划流程中于评分前排除。

独立流行情境中，同一份饭团加蜂蜜因「甜」触发「流行·喜爱」，命中 4 项喜好、0 项厌恶，原始得分为 4；总用料仍为 2 件，`cover3` 的效用仍为 3。此结果已用原工作簿与原候选生成函数分别在无流行和有流行条件下核对。

该例区分了制作冲突与偏好准入。通过门槛只表明候选可以参加后续比较，尚不能据此判定饭团加蜂蜜在全部候选中最优。

### 4.2 覆盖封顶如何改变选择

考虑两个均合法、无厌恶命中的说明性候选：

| 候选 | 喜好命中数 | 每份食材件数 | 未封顶覆盖优先 | 三分封顶后 |
| --- | --- | --- | --- | --- |
| P | 3 | 2 | 覆盖数低于 Q | 覆盖收益同为 3，因用料较少而优先 |
| Q | 4 | 3 | 因覆盖更多而优先 | 额外命中不增加覆盖收益，件数较多 |

这里的选择变化由效用定义直接产生。封顶把“继续增加命中”调整为“达标后控制消耗”；严格的目标顺序保证供给余量不会推翻件数上的优先关系。本例说明评价政策的影响，不代表实际游玩中的节省比例。

### 4.3 标签等价不代表资源效果等价

考虑食材 A、B 标签相同，日供给分别为 10、9 件。基础配方已使用 A×1，还需追加一件同类标签食材；假设每日制作 5 份，并且两种追加选择均合法。

| 追加选择 | 每份总用量 | 最低供给余量（件／日） |
| --- | --- | --- |
| A | A×2 | $`10-5\times2=0`$ |
| B | A×1、B×1 | $`\min(10-5,9-5)=4`$ |

两种选择的标签与件数相同，但计入基础配方耗用后，分散到 A、B 的供给余量更高。该构造反例说明：以原始日供给最高的食材代表整个标签等价组，可能遗漏资源目标更优的具体组合。它也解释了候选压缩与全局最优性之间的边界，完整讨论见[优化模型与算法边界](docs/design.md)。

### 4.4 已有运行证据与可支持的结论

| 已有核对 | 观测 | 支持的结论 |
| --- | --- | --- |
| 原函数流行对照 | 原工作簿、灵梦、饭团加蜂蜜；无流行为 3 分，「甜」流行为 4 分；均为 2 件食材、0 项厌恶，封顶效用均为 3 | 流行增加命中，覆盖封顶仅改变优化效用 |
| 完整工作簿网页案例 | 博丽灵梦、阈值 3，启用加料子集过滤与等价去重：生成 4,372 条候选，搜索「饭团」后为 59 行，XLSX 导出同为 59 行 | 指定条件下查询与导出行为一致 |
| 小规模 Python 对照 | 12 种食材、8 道料理、3 位顾客、5 种厨具；无流行、选择 3 种厨具。原件与副本共 4 次运行，XLSX 除时间元数据外一致 | 指定条件下发布副本保持原有计算行为 |

文件与原工作簿的逐字节校验、完整条件及导出结构见[验证记录](docs/verification.md)。现有核对支持复现一致性；尚未完成与人工备菜或其他策略的统一效果比较，也未完成 58 位顾客的 Python 全量输出对照。上述案例不构成实际收益提升、缺货风险下降或全局最优性的实证结论。

<a id="zh-methods"></a>

## 5. 求解方法与复现入口

### 5.1 使模型能够计算

程序承担候选生成、指标计算、方案比较与结果导出。开发中的效率问题集中在组合枚举和重复计算，提速要求是在既定规则与目标下保持结果含义。现有实现使用 CPU；网页和 Python 是共享工作簿的独立入口，其评价规则与候选范围分别定义。

| 计算环节 | 使用的方法 | 对求解范围的解释 |
| --- | --- | --- |
| 网页候选枚举 | 按料理静态分块，最多使用 8 个 Web Worker；枚举可重复加料组合并过滤 | 在浏览器 CPU 上计算，HTTP 服务只提供静态文件 |
| Python 候选生成 | 标签等价分组、相关加料筛选、DFS 与得分上界 | 等价代表选择和中性补位前三项截断会限制候选范围 |
| 历史多标签组合 | 以 $`\lambda`$ 为最低余量门槛，使用二分、DFS、容量剪枝和状态缓存 | 较高门槛可行意味着较低门槛可行；单次判定仍包含组合搜索 |
| 共同厨具比较 | 预计算并复用每客每厨具结果，再枚举设备集合 | 复用子问题减少重复计算，集合评价仍遵循既定目标 |

这些方法的适用分支和数据流见[系统架构](docs/architecture.md)。现有记录未提供统一性能基准或跨设备对照，因此仅说明求解方法及其边界。

<a id="zh-problem"></a>
<a id="zh-running"></a>

### 5.2 数据与执行方式

根目录 [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) 为完整原工作簿，共 13 张表。程序读取已保存的单元格结果；修改公式或其输入后，应先在支持相应公式的电子表格软件中重算并保存。

以下命令从仓库根目录执行，完整 Python 依赖要求 Python 3.11 或更新版本：

```sh
python -m pip install -r requirements.txt
```

浏览器用于按人物、得分和筛选条件检查候选，并导出 CSV 或单表 XLSX：

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8000>，页面自动读取同目录工作簿，也支持文件导入。具体操作与筛选边界见[网页使用说明](docs/web-guide.md)。

单客与共同厨具规划入口：

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

程序依次询问流行喜爱标签、流行厌恶标签和厨具数量。流行留空表示无对应条件；厨具数量留空表示使用全部可用类型。默认读取根目录工作簿，结果写入 `稀客料理表/single_mixIng_nCookware/`。显式相对输入、输出路径以脚本目录 `Python/` 为基准解析。完整参数、工作表字段与输出约定见[输入输出规范](docs/input-output.md)。

独立得分与利润脚本使用同一工作簿分析历史数据，其结果不作为上述规划目标的联合最优化输出。

<a id="zh-limits"></a>

## 6. 适用边界与讨论

本项目的结论适用于既有游戏规则下的备菜比较，模型的解释范围由评价政策、数据和候选生成共同决定。

- **目标范围**：覆盖封顶和严格优先级表达特定备菜偏好；PLAN 系列未联合建模酒水、完整满意度或现金利润，顾客预算为展示字段。
- **资源范围**：最低供给余量逐客独立核算，可以为负；共同厨具选择未建立多顾客共享库存约束，因此不能据此承诺整晚供给可行。
- **搜索范围**：标签等价代表选择与中性补位截断可能遗漏具体组合。目标比较限定于保留的候选，全部合法组合上的全局最优性尚未建立。
- **数据与验证**：历史采样和版本信息不完整，价格公式存在已知风险；缺少统一策略对照、真实订单分布和性能基准。参数变化的实际影响仍需在固定数据与明确条件下检验。
- **入口差异**：网页与 Python 的禁忌处理、得分筛选和等价替代等行为存在差异。使用时需按所选入口解释结果，具体触发条件见[网页使用说明](docs/web-guide.md)。

后续研究可围绕订单量与供给变化的敏感性、共享库存约束，以及候选压缩相对于完整小规模枚举的差异展开。这些属于待验证问题，不计入已完成结果。

<a id="zh-sources"></a>

## 7. 作者贡献、来源与补充文档

| 工作 | 贡献与归属 |
| --- | --- |
| 问题定义与模型选择 | 作者提出实际游玩问题，梳理既有规则语义，确定决策单位、评价顺序、筛选和厨具条件 |
| 数据记录与案例验收 | 作者手工记录价格、供给和委托相关数据，并通过具体角色与参数组合核对结果 |
| 实现与推导 | 大量代码、算法推导和部分调试使用 AI 辅助；作者负责需求澄清、取舍和结果验收 |
| 标签与图像 | 标签资料来自 [AnYiEE 的项目](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)；游戏图像归属、依赖许可和图示制作方式见[第三方声明](THIRD_PARTY_NOTICES.md) |

本项目为非官方个人建模案例与辅助工具。补充文档承载详细规则、实现和复现资料：

| 文档 | 内容 |
| --- | --- |
| [优化模型与算法边界](docs/design.md) | 变量、目标、集合评价与候选范围 |
| [需求与设计决策演进](docs/prompt-journey.md) | 从历史需求整理的目标变化、取舍与案例依据 |
| [数据来源说明](docs/data-provenance.md) | 人工记录、上游资料及估计口径 |
| [验证记录](docs/verification.md) | 观测条件、复现核对与未覆盖范围 |
| [系统架构](docs/architecture.md) | 执行边界、数据流与文件职责 |
| [输入输出规范](docs/input-output.md) | 工作簿结构、参数、路径与输出格式 |
| [网页使用说明](docs/web-guide.md) | 操作步骤、筛选含义与边界行为 |

---

<a id="english"></a>

# Mystia Menu Optimizer

**Modeling meal-preparation decisions in Touhou Mystia's Izakaya: preference coverage, ingredient supply, and cookware configuration**

[中文](#chinese) | **English**

In [Touhou Mystia's Izakaya](https://store.steampowered.com/app/1584090/), a guest may accept several combinations of dishes and additional ingredients, each with different ingredient requirements, supply pressure, and cookware needs. Meal preparation therefore involves two questions: which plans meet the requirements, and how to define a better choice among qualifying plans.

This project formulates these questions as a discrete decision model. It defines the feasible space of recipes and additions and establishes a hierarchical evaluation of preference coverage, ingredient units, and minimum supply slack. The model evolved from multiple plans assigned by liked tag to one plan per guest, capped coverage utility, and shared cookware selection. The project provides rule and data definitions, mathematical models, explanations of design decisions, and programs for candidate search and result checking.

The author's main work comprises identifying gameplay problems, clarifying rule semantics, recording supply and prices, specifying objectives and constraints, and checking results through character cases. Code implementation, some algorithm derivation, and debugging were AI-assisted. This document focuses on those modeling choices and their consequences. Interpretation of results is bounded by the given data, assumptions, and candidates actually retained.

[Mathematical model](#en-model) · [Design rationale and evolution](#en-evolution) · [Data and assumptions](#en-data) · [Cases and verification](#en-verification) · [Solution methods and reproduction](#en-methods) · [Limitations](#en-limits) · [Contributions and documentation](#en-sources)

**Mechanics and terminology** &nbsp; <a href="#en-tag-figure"><img src="docs/images/jump-to-figure-en.png" alt="View diagram" width="132" height="28" align="middle"></a>

Preparation and evaluation follow three steps:

1. **Choose a dish through its recipe.** A recipe specifies the cookware and required ingredients. For example, a prep counter and seaweed×1 can make a rice ball. The rice ball uses its own preset tags; seaweed's tags are not automatically added through the base recipe.
2. **Choose additions to form a plan.** Each dish can use at most 5 ingredient units, with required ingredients and additions sharing those slots. The rice ball's seaweed occupies 1 slot; the remaining 4 may hold additions or stay empty. Adding honey×1 produces a rice-ball-with-honey plan: 2 units in total, still a rice ball, with honey contributing 「Sweet」. The final tags remain subject to overrides and other rules.
3. **Match the final tags against guest preferences.** Each guest has separate liked and disliked tags. A tag present in the plan matches the preference with the same name; each distinct tag counts once. In the figure, rice ball with honey matches Reimu's 「Filling」「Affordable」「Sweet」 and no dislikes, giving a score of 3−0=3.

| Term | Definition |
| --- | --- |
| Ingredient | A preparation material such as seaweed or honey. The recipe's specified quantity counts as required ingredients; any extra quantity counts as additions. The same ingredient can serve both roles. |
| Dish | A menu item made according to a recipe, such as rice ball, with its own preset tags, specified cookware, and recipe prohibitions. |
| Addition | An ingredient used in a remaining slot beyond the base recipe, such as honey added to rice ball; legal additions preserve the selected dish and contribute ingredient tags. |
| Plan | One concrete preparation choice: a dish and the types and quantities of its additions, which may also be omitted. Required ingredients and additions total at most 5 units; repeated use of one ingredient still occupies a slot per unit. |
| Tag | A name representing an attribute or preparation method, such as 「Sweet」「Filling」「Prep counter」; it is also the unit matched against guest likes and dislikes. |
| Score | Liked matches minus disliked matches for a specified guest. It describes tag matching; planning also compares ingredient units and supply, as defined in [Chapter 1](#en-model). |

Recipe prohibitions are preparation restrictions of a dish, whereas dislikes belong to guest preferences. They have different effects. The figure further explains how tag overrides, prohibition conflicts, and trends affect a plan; the score here is not the complete in-game evaluation or profit.

<a id="en-tag-figure"></a>

[![Five sections explain ingredient slots, preference matching, tag overrides, recipe prohibitions, and trends. Blue denotes dish tags, orange ingredient tags, teal cookware tags, purple guest likes, slate gray guest dislikes, and pale red recipe prohibitions. A prep counter and one seaweed satisfy only the rice-ball recipe: one slot filled and four empty; adding honey leaves two filled and three empty. Dish tags are not the union of required-ingredient tags; additions contribute tags. A and B show all Reimu food preferences: likes 「High-grade」「Filling」「Sweet」「Wondrous」「Affordable」「Liked trend」; dislikes 「Pub food」「Expensive」「Disliked trend」. A: rice ball with honey matches 「Filling」「Affordable」「Sweet」, scoring 3 liked minus 0 disliked matches = 3. B: rice ball with pork replaces 「Vegetarian」 with 「Meat」, matches 「Filling」「Affordable」, and scores 2 minus 0 = 2. Rice ball has no recipe prohibitions. C: honey triggers stinky tofu's 「Sweet」 prohibition, which other additions cannot cancel; the game produces Dark Matter, while Python nCookware excludes the plan before scoring. A, B, and C have no trends. The separate trend example distinguishes random trigger tags from fixed guest attitudes; the program reads supplied conditions. When 「Sweet」 is popular, rice ball with honey keeps 「Sweet」 and gains 「Liked trend」, matching 4 of Reimu's likes and 0 dislikes for a score of 4. Below, Cirno likes 「Disliked trend」 and dislikes 「Liked trend」.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.png)

*Figure 1. Recipes, additions, and tag matching. A, B, and C have no trends; the final section shows the same plan scoring 4−0=4 when 「Sweet」 is popular, followed by Cirno's trend preferences. This is a rule illustration using the original pixels of game icons.* [Vector SVG](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.svg). Tags follow the [original workbook](东方夜雀食堂.xlsx). A prohibited combination produces Dark Matter in the game; Python `nCookware` excludes it before scoring. Browser differences are described in the [browser guide (Chinese)](docs/web-guide.md). See the [third-party notices (Chinese)](THIRD_PARTY_NOTICES.md) for rule and artwork sources.

Chapter 1 focuses on the single-guest and shared cookware models, whose implementation is abbreviated as `nCookware`. The historical multiple-plan model illustrates changes in the decision unit and objectives. The five-slot limit and recipe prohibitions are preparation conditions; the liked-tag threshold and zero-dislike eligibility are planning policies.

<a id="en-model"></a>

## 1. Mathematical model: from gameplay decisions to optimization

### 1.1 Overview of model evolution

The continuing problem is how to choose preparation plans. What changes as requirements become explicit is **the decision unit, eligibility for comparison, and the ordered definition of a better result**. The browser first provides qualifying-candidate queries; Python planning defines tag-specific plan combinations, one plan per guest, capped coverage utility, and shared cookware selection. HTML and Python are independent entry points sharing a workbook. Arrows represent dependencies between decision definitions, not frontend/backend calls or a precisely dated development timeline.

[![Model evolution: the browser filters several candidates by liked minus disliked matches; the historical model selects a plan per feasible liked tag, first minimizing expected units and then maximizing minimum supply slack; the single-guest model prioritizes liked coverage, units, and slack; cover3 caps coverage benefit at 3; cookware configuration moves from fixed exclusions to selecting exactly n shared types. Presentation changes, CPU acceleration, and profit analysis are distinguished.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.png)

*Figure 2. Evolution of decision units, objectives, and constraints. Arrows follow problem dependencies; optimality is relative to each model's evaluation policy and retained candidates.* [Vector SVG](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.svg).

Moving from browser queries to planning advances from returning eligible candidates to selecting planning solutions by an explicit objective order. Moving from multiple plans to one plan changes both order allocation and the decision unit. Moving from uncapped coverage to `cover3` changes the marginal benefit of a fourth or subsequent liked match. Moving from fixed cookware to `nCookware` makes the equipment set an additional decision variable. The following sections first define the single-guest and shared-cookware models, then contrast historical multiple-plan optimization and browser filtering so that their objectives remain distinct.

### 1.2 Problem abstraction

The decision unit is a base dish with a combination of additional ingredients. At the cookware level, a common equipment set must also be selected. Meal-preparation requirements map to mathematical tasks as follows:

| Preparation requirement | Mathematical representation | Role in the model |
| --- | --- | --- |
| Choose a suitable dish for a guest | Count liked and disliked tags in the final tag set | Determine eligibility and coverage benefit |
| Configure recipes and additions within preparation rules | Integer quantities, a five-slot limit, recipe restrictions, and tag overrides | Define feasibility conditions |
| Reduce ingredient use in repeated preparation after qualification | Minimize ingredient units per plan | Second-priority objective |
| Reduce dependence on ingredients with tight supply | Maximize minimum supply slack over ingredients used | Third-priority objective |
| Plan for guests under limited cookware | Select a specified number of shared cookware types and aggregate guest evaluations | Equipment-set decision |

Preference coverage has capped utility: matching more than 3 liked tags does not increase that benefit. Ingredient units measure quantity, while supply slack measures resource pressure under assumed daily demand. They represent distinct preparation tradeoffs. Supply is a comparison criterion rather than a hard inventory constraint. The model focuses on dishes and equipment and does not jointly represent drinks, full satisfaction, or cash profit.

### 1.3 Notation, parameters, and decision variables

The following notation describes the single-guest model and cookware configuration. Symbols specific to the historical multiple-plan model are defined in Section 1.7.

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
| $`s_g(p)`$ | Evaluation quantity | Preference net score: liked minus disliked matches |
| $`\kappa(d)`$ | Recipe parameter | Cookware required to prepare the dish |
| $`\tau`$ | Eligibility parameter | Minimum liked-tag count; the `nCookware` default is 3 |
| $`K`$ | Demand parameter | Assumed orders per guest per day; the default is 5 |
| $`q_i`$ | Supply parameter | Empirical ingredient supply in units per day, recorded as Total Daily Quantity (TDQ) |
| $`L(p)`$ | Evaluation quantity | Total ingredient units per plan, including repeated use |
| $`R(p)`$ | Evaluation quantity | Minimum supply slack over ingredients used, in units per day |
| $`U(h)`$ | Utility function | Coverage benefit obtained by capping the liked-tag count at 3 |
| $`\mathcal C_g`$ | Candidate set | Candidates generated and retained for a guest under the given inputs and conditions |
| $`H, S, n`$ | Sets and parameter | Available cookware, selected shared cookware, and the specified number of cookware types |

The base dish, additional quantities, and shared cookware set are decisions. Recipes, guest tags, supply estimates, and assumed orders are given inputs. Final tags and evaluation quantities are computed from those inputs and decisions.

### 1.4 Quantities, tags, and feasibility

Total use of each ingredient and the ingredient-unit count are defined as:

```math
c_i(p)=b_i(d)+x_i,\qquad x_i\in\mathbb Z_{\ge0},\qquad
L(p)=\sum_i c_i(p)
```

Base ingredients contribute to quantities and occupied slots without adding their tags again. Additional-ingredient tags are merged as a set. An ingredient may be added repeatedly, while each distinct tag counts once. After tag overrides and trend processing, liked and disliked matches are:

```math
h_g(p)=\left|T(p)\cap P_g\right|,\qquad
a_g(p)=\left|T(p)\cap N_g\right|,\qquad
s_g(p)=h_g(p)-a_g(p)
```

The `nCookware` rule model requires the five-slot limit, the minimum liked-tag threshold, and no disliked-tag matches:

```math
L(p)\le5,\qquad h_g(p)\ge\tau,\qquad a_g(p)=0
```

Candidates are also restricted by owned dishes, recipe prohibitions, and available cookware. Liked and disliked trends are triggered by separately specified tags. When no trigger is supplied for a trend direction, that trend tag is removed from guest preference and dislike sets. The browser instead filters on the net score $`h_g(p)-a_g(p)`$, which differs from the single-guest planning eligibility conditions in this section.

### 1.5 Single-guest objective

One plan serves all assumed orders for a guest. Daily ingredient demand is per-dish use multiplied by daily orders. Minimum supply slack and coverage benefit are:

```math
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right),\qquad
U(h)=\min(h,3)
```

The uncapped `singlePLAN` model first seeks more liked matches:

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(h_g(p),\;-L(p),\;R(p)\right)
```

The `cover3` and subsequent branches replace the first criterion with capped utility:

```math
\max_{p\in\mathcal C_g}^{\mathrm{lex}}
\left(U(h_g(p)),\;-L(p),\;R(p)\right)
```

The criteria maximize coverage benefit, minimize ingredient units, and maximize minimum supply slack, in that order. A later criterion is considered only when earlier criteria tie, with no weighted compensation between them. Selling price, dish name, and the additions string resolve remaining ties.

The minimum threshold controls eligibility, while the coverage cap defines utility. At the default threshold of 3, qualifying candidates all have a coverage benefit of 3, so subsequent comparisons primarily depend on ingredient units and minimum supply slack. Negative slack indicates that the corresponding assumed demand exceeds empirical daily supply.

For example, the rice-ball-and-honey plan in Figure 1 has a raw score of 4 when 「Sweet」 triggers the liked trend, while its capped utility remains 3. The cap neither removes the fourth matched tag nor changes the raw score to 3; it changes only the benefit used to compare plans.

### 1.6 Shared cookware and solution scope

Available cookware is determined by the equipment associated with owned dishes. The selected set satisfies:

```math
S\subseteq H,\qquad |S|=n
```

`nCookware` first computes the best retained candidate for each guest and cookware type, then enumerates shared cookware sets. It compares total coverage benefit, total ingredient units, and the sum of per-guest minimum supply slack values, with penalties for guests lacking a feasible plan. At the default three-point threshold, the first criterion prioritizes the number of guests with a plan. Ingredient demand remains independently accounted for per guest, without joint inventory deductions.

Let $`\mathcal C_g(S)=\{p\in\mathcal C_g:\kappa(d)\in S\}`$, with $`p_g^*(S)`$ the plan selected by the single-guest objective. Let $`G_S`$ contain guests with a plan and $`z_S`$ count guests without one. The original program evaluates sets as:

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\sum_{g\in G_S}U(h_g(p_g^*(S))),\;
-\left[\sum_{g\in G_S}L(p_g^*(S))+10^9z_S\right],\;
\sum_{g\in G_S}R(p_g^*(S))-10^{18}z_S
\right)
```

The constants are the original implementation's penalties for missing plans; feasibility for every guest is not required. Decomposition follows from independent guest evaluations once shared cookware is fixed. The `limitedCookware` branch only excludes specified equipment from a given set; it does not optimize the equipment set itself.

Equivalent-ingredient representative selection and the neutral-filler cutoff restrict $`\mathcal C_g`$. Objective comparison within this set therefore does not establish global optimality over all legal ingredient combinations. The set-level objective, tie-breaking rules, and a counterexample appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

### 1.7 Historical multiple-plan model

The historical `detailedPLAN` model assigns plans by liked tag. For each target liked tag $`t`$ with candidates, apply the original ingredient-upgrade and addition-subset filters to the eligible tag-specific pool, then select $`p_t`$ from its retained candidates; the same recipe plan may serve the order shares of several tags. Assume daily orders $`K`$ are distributed equally among $`m>0`$ tag-specific plans with feasible candidates. Let $`u_i`$ denote total use of ingredient $`i`$ across the selected plans; $`q_i`$ retains the daily-supply definition above. Expected ingredient units and minimum supply slack are:

```math
u_i=\sum_t c_i(p_t),\qquad
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

Its objective is:

```math
\min_{(p_t)_t}^{\mathrm{lex}}\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

At a fixed tag count, the first objective separates by tag, so all candidates tied for minimum units are retained for each tag. The second objective compares their combined ingredient use; ties in minimum slack are resolved by maximizing the full sorted slack vector. For a slack threshold $`\lambda`$, the program checks whether a combination satisfies $`q_i-(K/m)u_i\ge\lambda`$ for every ingredient used, using binary search and DFS. This maximizes slack across one guest's multiple plans, not shared inventory across guests. Equal order allocation is a modeling assumption without a corresponding measured probability estimate. No plan is produced when no tag has a feasible candidate. The single-guest model changes both the decision unit and the evaluation order; Chapter 2 describes that design evolution.

### 1.8 Browser filtering versus planning objectives

Given a guest, a net-score threshold, and optional filters, the browser returns retained candidates. Let $`\mathcal C_g^{\mathrm{web}}`$ denote candidates generated under its enumeration and filtering rules. The core score condition is:

```math
\mathcal W_g(\tau)=\left\{p\in\mathcal C_g^{\mathrm{web}}:s_g(p)\ge\tau\right\}
```

This defines a candidate filter, not a unique optimum across dishes. Browser queries allow liked matches to offset disliked matches, whereas Python PLAN excludes any disliked match before comparison; recipe-prohibition parsing and ownership conditions also differ. Optional browser procurement ranking compares sorted daily-supply vectors within each dish and keeps every candidate at least as good as the Nth-place threshold, including ties. It does not use supply minus assumed demand. Ranking and filtering details appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md) and [browser guide (Chinese)](docs/web-guide.md).

<a id="en-evolution"></a>

## 2. Model design rationale and objective evolution

### 2.1 From preparation problems to comparable objectives

The project began by seeking preparation plans that meet guest requirements. As rules and use conditions became clearer, the meaning of an optimal plan was progressively specified through the decision unit, eligibility conditions, and comparison order. Early requirements also included ranking by actual profit. The subsequent planning models express resource requirements through ingredient units and supply slack, while regular guests, drinks, prices, and profit remain separate analysis branches.

| Decision problem | Model change | Rationale and consequences |
| --- | --- | --- |
| What to prepare for several liked tags | Assign a plan to each coverable tag and estimate total use under equal order allocation; first minimize expected ingredient units, then maximize minimum supply slack | Different tags account for separate order shares; candidates tied for minimum units must still be retained because ingredient allocation affects supply pressure |
| What fixed plan to prepare for each guest | Change the decision unit to one plan per guest; compare preference coverage, then units and slack | The requirement explicitly became one fixed plan per rare guest; orders are no longer split by tag, and the chosen plan serves all assumed orders, shifting the objective to the coverage and consumption of one dish |
| Whether to pursue additional matches after qualification | Cap coverage benefit at 3 | Prioritize ingredient use after meeting the coverage target; additional matches may remain, but no longer increase the first objective |
| How limited equipment can serve several guests | Extend specified cookware exclusions to the selection of exactly n shared cookware types | Guest-specific plans must fit the common equipment set; at the default threshold, set evaluation first increases the number of guests with qualifying plans |

These stages change the definition of the optimization problem. Combining required ingredients and additions into five output slots changes result presentation while retaining the existing objective. Branch mappings, historical requirements, and character-based acceptance cases are described in the [requirements and design retrospective (Chinese)](docs/prompt-journey.md).

### 2.2 Evaluation criteria and tradeoffs

Coverage, ingredient units, and supply slack express different preferences. The following choices define the model's evaluation policy; their effects follow directly from the objective function.

| Choice | Decision meaning | Tradeoff and conditions |
| --- | --- | --- |
| Cap coverage benefit | Make resource conservation the main comparison criterion after reaching the coverage target | The first objective gives no further reward for a fourth or subsequent match; 3 is a utility setting in this model and does not establish the complete in-game evaluation rule |
| Measure consumption in ingredient units | Count each ingredient unit equally across the base recipe and additions | Equal quantities do not imply equal purchase costs or acquisition difficulty, so a separate supply criterion is included |
| Compare minimum supply slack | Focus on the ingredient with the least remaining supply among those used, identifying the bottleneck under assumed demand | Slack may be negative; it neither estimates shortage probability nor imposes a hard inventory constraint |
| Use lexicographic ordering | Consider each later criterion only when earlier criteria tie, preserving explicit priorities | Higher supply slack cannot compensate for using more ingredients; this order is specified by requirements and has not been experimentally established as a universally optimal representation of preferences |

### 2.3 Roles of preparation rules, eligibility, and ranking

Recipe prohibitions determine preparation conflicts. Zero disliked matches and a minimum liked-tag count are eligibility policies of the planning model. Only candidates that pass eligibility are compared using the hierarchical objective. Browser queries instead filter candidates by the net score of liked minus disliked matches. The figure's score, planning eligibility, and coverage utility thus serve different purposes; browser results cannot directly be interpreted as planning ranks.

<a id="en-data"></a>

## 3. Data sources, parameter estimates, and assumptions

Rule references, manual observations, and model settings have different roles in the reasoning. Distinguishing their sources makes the conditions supporting a result explicit.

| Category | Content and basis | Role in the model |
| --- | --- | --- |
| Rule and attribute data | Recipes, cookware, tags, and guest preferences in the historical workbook; tag data came from AnYiEE's project | Define preparation conditions, tag processing, and preference matching |
| Empirical observations | The author manually recorded prices, daily supply, and commission-related data and compiled empirical expectations | Daily supply is an input to resource evaluation; prices support separate economic analysis |
| Demand and scenario assumptions | The default is 5 orders per guest per day; the single-guest model uses one plan for those orders; the historical model distributes orders equally across feasible tags | Convert per-dish ingredient use into assumed daily demand |
| Evaluation policy | Liked-tag threshold, zero-dislike eligibility, coverage cap, objective order, and cookware count | Define acceptable plans and their priority relationships |
| Derived criteria | Liked and disliked matches, ingredient units, minimum supply slack, and set-level aggregates | Calculate evaluation results from data, assumptions, and decisions |

As parsed by `nCookware`, the workbook contains 62 ingredient records, 164 dish records, and 58 rare guests; 163 dishes are marked as owned. `Total Daily Quantity` represents empirical daily supply. Minimum supply slack subtracts assumed daily demand from that supply and cannot be interpreted as the player's current inventory.

Historical observations and quantity-weighted calculations account for price variation, but complete sampling dates, sample counts, and source versions were not retained. Purchase-price formulas also carry risks from row-based association errors and some cached formula errors. The available price and supply data therefore describe historical empirical conditions and are insufficient to establish reliable demand distributions, confidence intervals, or shortage probabilities. Fields, estimation conventions, and source coverage are detailed in the [data provenance notes (Chinese)](docs/data-provenance.md).

<a id="en-verification"></a>

## 4. Case analysis and verification scope

The following cases explain the effects of eligibility rules, objective changes, and candidate simplification. Illustrative comparisons and constructed counterexamples examine model logic; existing program-run records are presented separately in Section 4.4.

### 4.1 From the mechanism figure to candidate eligibility

In Figure 1, rice ball with honey matches 3 of Reimu's likes and 0 dislikes; rice ball with pork matches 2 likes and 0 dislikes. Under the default `nCookware` conditions, the former meets the liked-tag threshold and the latter does not. Stinky tofu with honey triggers a recipe prohibition and is excluded before scoring in this planning workflow.

In the separate trend scenario, the same rice ball with honey gains 「Liked trend」 because it contains 「Sweet」. It matches 4 likes and 0 dislikes, for a raw score of 4, while still using 2 ingredient units and retaining utility 3 under `cover3`. Both trend conditions were checked using the original workbook and candidate-generation functions.

This case distinguishes preparation conflicts from preference-based eligibility. Passing the threshold only permits a candidate to enter subsequent comparisons; it does not establish that rice ball with honey is optimal among all candidates.

### 4.2 How capped coverage changes the choice

Consider two illustrative candidates that are both legal and match no dislikes:

| Candidate | Liked matches | Ingredient units per dish | Uncapped coverage priority | After capping at 3 |
| --- | --- | --- | --- | --- |
| P | 3 | 2 | Lower coverage than Q | Both have coverage benefit 3; preferred for using fewer units |
| Q | 4 | 3 | Preferred for higher coverage | The extra match adds no coverage benefit, and ingredient use is higher |

The change in choice follows directly from the utility definition. Capping shifts the preference from continuing to add matches to controlling consumption after qualification. The strict objective order prevents supply slack from reversing the priority established by ingredient units. This example explains the evaluation policy and does not represent a measured saving rate during gameplay.

### 4.3 Tag equivalence does not imply equivalent resource effects

Consider ingredients A and B with identical tags and daily supplies of 10 and 9 units, respectively. The base recipe already uses A×1 and needs one additional ingredient with the same tag set. Assume 5 dishes are prepared per day and both additions are legal.

| Addition | Total use per dish | Minimum supply slack (units/day) |
| --- | --- | --- |
| A | A×2 | $`10-5\times2=0`$ |
| B | A×1, B×1 | $`\min(10-5,9-5)=4`$ |

The choices have identical tags and ingredient counts, but distributing use across A and B leaves greater minimum supply slack after accounting for the base recipe. This constructed counterexample shows that representing an entire tag-equivalent group by the ingredient with the highest raw daily supply can omit a concrete combination with a better resource objective. It also explains the boundary between candidate compression and global optimality; see the [optimization model and algorithm boundaries (Chinese)](docs/design.md) for the full discussion.

### 4.4 Existing run evidence and supported conclusions

| Existing check | Observation | Supported conclusion |
| --- | --- | --- |
| Trend comparison using original functions | Original workbook, Reimu, rice ball with honey: raw score 3 without trends and 4 with 「Sweet」 popular; both use 2 ingredient units, match 0 dislikes, and have capped utility 3 | The trend adds a match; the coverage cap affects only optimization utility |
| Browser case using the complete workbook | 博丽灵梦, threshold 3, addition-subset filtering and equivalent-ingredient deduplication enabled: 4,372 candidates; 59 rows after searching for 「饭团」, and 59 rows in the XLSX export | Query and export behavior agree under the specified conditions |
| Small Python comparison | 12 ingredients, 8 dishes, 3 guests, and 5 cookware types; no trends and 3 selected cookware types. Four runs across the original and copied programs produced matching XLSX contents except for time metadata | The distributed copy preserves the original computational behavior under the specified conditions |

Byte-level checks against the source files and original workbook, complete conditions, and export structures are documented in the [verification record (Chinese)](docs/verification.md). Existing checks support reproducibility of behavior. A controlled effectiveness comparison against manual preparation or other strategies has not been completed, nor has a full Python output comparison across all 58 guests. These cases do not establish empirical gains in actual returns, lower shortage risk, or global optimality.

<a id="en-methods"></a>

## 5. Solution methods and reproduction entry points

### 5.1 Making the model computable

Programs generate candidates, compute criteria, compare plans, and export results. Development-time efficiency concerns centered on combinatorial enumeration and repeated computation, with the requirement that acceleration preserve result meaning under fixed rules and objectives. Current implementations use CPUs. The browser and Python scripts are independent entry points sharing the workbook, with separately defined evaluation rules and candidate scopes.

| Computation | Methods used | Implications for solution scope |
| --- | --- | --- |
| Browser candidate enumeration | Static partitioning by dish across up to 8 Web Workers; enumeration of additions with repetition and candidate filtering | Computation runs on the browser CPU; the HTTP service only serves static files |
| Python candidate generation | Tag-equivalent grouping, relevant-addition filtering, DFS, and score upper bounds | Equivalent representative selection and the three-candidate neutral-filler cutoff restrict candidate scope |
| Historical multiple-tag combinations | Binary search, DFS, capacity pruning, and state caching with $`\lambda`$ as the minimum-slack threshold | Feasibility at a higher threshold implies feasibility at a lower threshold; each check still requires combinatorial search |
| Shared cookware comparison | Precompute and reuse per-guest, per-cookware results before enumerating equipment sets | Reusing subproblems reduces repeated computation while set evaluation follows the specified objective |

Applicable branches and data flows are described in the [system architecture (Chinese)](docs/architecture.md). The available records contain no uniform performance benchmark or cross-device comparison, so the discussion reports methods and their boundaries.

<a id="en-problem"></a>
<a id="en-running"></a>

### 5.2 Data and execution

The root [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) is the complete original workbook with 13 sheets. Programs read saved cell results. After changing formulas or their inputs, recalculate and save the workbook in spreadsheet software supporting those formulas before running the programs.

Run the following commands from the repository root. The complete Python dependencies require Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
```

The browser supports inspecting candidates by guest, score, and filter conditions and exporting CSV or single-sheet XLSX:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Visit <http://127.0.0.1:8000>. The page automatically reads the workbook from the same directory and also accepts file imports. Operations and filter boundaries are described in the [browser guide (Chinese)](docs/web-guide.md).

The single-guest and shared cookware planning entry point is:

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

The program requests liked-trend tags, disliked-trend tags, and a cookware count in sequence. An empty trend response specifies no corresponding condition; an empty cookware response selects all available types. It reads the root workbook by default and writes results to `稀客料理表/single_mixIng_nCookware/`. Explicit relative input and output paths are resolved from the script directory, `Python/`. Complete options, workbook fields, and output conventions are specified in the [input/output reference (Chinese)](docs/input-output.md).

Separate score and profit scripts analyze historical data from the same workbook. Their outputs are not joint optimization results for the planning objectives above.

<a id="en-limits"></a>

## 6. Scope and discussion

The project's conclusions apply to preparation comparisons under existing game rules. Evaluation policy, data, and candidate generation jointly determine the model's interpretive scope.

- **Objective scope:** capped coverage and strict priorities express particular preparation preferences. The PLAN series does not jointly model drinks, full satisfaction, or cash profit; guest budget is a display field.
- **Resource scope:** minimum supply slack is evaluated independently per guest and may be negative. Shared cookware selection has no joint inventory constraint across guests, so it cannot guarantee feasible supply for an entire evening.
- **Search scope:** tag-equivalent representative selection and the neutral-filler cutoff may omit concrete combinations. Objective comparison is restricted to retained candidates; global optimality over all legal combinations has not been established.
- **Data and verification:** historical sampling and version information are incomplete, and price formulas have known risks. Controlled strategy comparisons, actual order distributions, and performance benchmarks are unavailable. The practical effects of parameter changes still require evaluation with fixed data and explicit conditions.
- **Entry-point differences:** the browser and Python differ in prohibition handling, score filtering, equivalent substitutions, and other behavior. Results must be interpreted for the chosen entry point; specific trigger conditions are documented in the [browser guide (Chinese)](docs/web-guide.md).

Further study could examine sensitivity to order volumes and supply, shared inventory constraints, and differences between compressed candidates and complete enumeration on small instances. These remain questions for evaluation and are not included among completed results.

<a id="en-sources"></a>

## 7. Author contributions, sources, and supplementary documentation

| Work | Contribution and attribution |
| --- | --- |
| Problem definition and model choices | The author identified gameplay problems, clarified existing rule semantics, and specified decision units, evaluation order, filters, and cookware conditions |
| Data recording and case acceptance | The author manually recorded prices, supply, and commission-related data and checked results using specific characters and parameter combinations |
| Implementation and derivation | Much of the code, algorithm derivation, and some debugging were AI-assisted; the author clarified requirements, made tradeoffs, and evaluated results |
| Tags and images | Tag data came from [AnYiEE's project](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant); game artwork attribution, dependency licenses, and figure production are described in the [third-party notices (Chinese)](THIRD_PARTY_NOTICES.md) |

This is an unofficial personal modeling case study and supporting tool. Supplementary documents provide detailed rules, implementation information, and reproduction references:

| Document | Content |
| --- | --- |
| [Optimization model and algorithm boundaries (Chinese)](docs/design.md) | Variables, objectives, set evaluation, and candidate scope |
| [Requirements and design retrospective (Chinese)](docs/prompt-journey.md) | Objective changes, tradeoffs, and case evidence drawn from historical requirements |
| [Data provenance (Chinese)](docs/data-provenance.md) | Manual observations, upstream material, and estimation conventions |
| [Verification record (Chinese)](docs/verification.md) | Observation conditions, reproduction checks, and untested scope |
| [System architecture (Chinese)](docs/architecture.md) | Execution boundaries, data flows, and file responsibilities |
| [Input/output reference (Chinese)](docs/input-output.md) | Workbook structure, options, paths, and output formats |
| [Browser guide (Chinese)](docs/web-guide.md) | Operations, filter semantics, and boundary behavior |
