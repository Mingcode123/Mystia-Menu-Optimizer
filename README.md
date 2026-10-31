<a id="chinese"></a>

# Mystia Menu Optimizer

**《东方夜雀食堂》备菜决策建模：偏好覆盖、食材供给与厨具配置**

**中文** | [English](#english)

在[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/)中，同一位顾客可能接受多种料理与加料组合，而这些组合的用料、供给压力和所需厨具不同。备菜决策因此需要同时回答两个问题：哪些方案满足条件，以及在多个合格方案之间如何定义“更优”。

本项目将上述问题抽象为离散决策模型，明确配方与加料的可行域，并建立喜好覆盖、食材件数与最低供给余量的分层评价体系。模型经历了按喜好标签配置多套方案、每位顾客配置单套方案、覆盖收益封顶及共同厨具选择等调整。项目产出包括规则与数据定义、数学模型、设计决策说明，以及用于搜索候选和复核结果的程序。

作者的主要工作是提出游玩问题、梳理规则语义、记录供给与价格、确定目标和约束，并通过角色案例核对结果；代码实现、部分算法推导与调试使用 AI 辅助。本文重点说明这些建模选择及其影响，结果解释限定于给定数据、假设和实际保留的候选范围。

[数学模型](#zh-model) · [设计依据与演进](#zh-evolution) · [数据与假设](#zh-data) · [案例与验证](#zh-verification) · [求解与复现](#zh-methods) · [局限](#zh-limits) · [贡献与文档](#zh-sources)

**机制与术语** &nbsp; <a href="#zh-tag-figure"><img src="docs/images/jump-to-figure-zh.png" alt="直接看机制图" width="132" height="28" align="middle"></a>

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

第一章从网页的方案定义与查询条件开始，依次说明多方案、单方案与覆盖封顶的数学变化，再分别介绍输出格式和两类厨具分支。五格与配方禁忌属于制作条件，得分门槛与无厌恶准入属于规划政策。

<a id="zh-model"></a>

## 1. 数学模型：从游戏决策到优化任务

### 1.1 模型演进总览

项目持续研究的是如何选择备菜方案；随需求明确而改变的，是**选一个什么对象、哪些方案可以进入比较，以及“更优”按什么顺序判断**。网页首先提供达标候选查询；Python 规划进一步定义多标签方案组合、每客单方案、覆盖收益封顶和共同厨具配置。HTML 与 Python 是共享工作簿的独立入口，图中的箭头表示决策定义的递进，不表示前后端调用或精确开发时间线。

[![模型演进：网页按喜好减厌恶的净分筛选多个候选；历史多方案为每个可行喜好标签选方案，先最少预期件数再最大最低供给余量；单客模型改为先最大喜好覆盖、再最少件数和最大余量；cover3把覆盖收益封顶为3；厨具模型从固定排除扩展到选择恰好n种共同设备。排版修改、CPU提速和利润分析另行区分。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.png)

*图 2. 决策单位、目标与约束的演进。箭头按问题依赖组织；每种模型的“最优”仅针对其评价政策和保留候选成立。* [SVG 矢量原图](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution.svg)。

以下以 HTML 为起点，按 `detailedPLAN`、`singlePLAN`、`cover3` 的顺序展开，再单列输出格式、固定厨具与共同厨具分支。每节先说明决策问题和相对上一模型的变化，再定义新增量与公式；已有符号保持原义，候选集合按对应实现区分。

### 1.2 HTML：定义方案、筛选候选与比较采购条件

#### 1.2.1 要解决的问题

给定一位稀客、已导入的料理与食材、当前流行条件，以及玩家指定的最低分和标签要求，网页需要回答：**每道料理可以怎样加料，哪些组合达标，哪些组合可以省略，以及哪些组合的食材较易采购。** 输出为候选方案表，每行是一道料理及其加料种类、数量；这一阶段允许保留多行，不要求为顾客确定唯一方案。

四个选项分别对应不同的决策依据：

| 选项 | 要解决的问题 | 比较对象 |
| --- | --- | --- |
| 等价食材去重（仅加料） | 标签相同的食材是否需要分别枚举？ | 枚举前的加料食材池 |
| 食材高级过滤 | 标签更少的食材能形成达标方案时，是否仍保留其“高级”替代？ | 同一道料理的达标方案与指定的基础替代方案 |
| 加料子集过滤 | 少加一些已有食材仍能达标时，是否保留加料更多的方案？ | 同一道料理中，已经保留的方案与当前方案 |
| 依采购推荐 | 达标方案之间，哪些方案所需食材的供给条件更好？ | 同一道料理经过前述过滤后的候选 |

实际顺序为：**按料理排除禁用食材名 → 可选的等价去重 → 枚举加料 → 标签与分数准入 → 高级过滤 → 子集过滤 → 采购排名与输出。** 未启用的步骤直接跳过。下面先建立共同模型，再逐项定义这些规则。

#### 1.2.2 共同模型：方案、标签与准入

符号尽量对应英文含义：$`g`$ 为 Guest，$`d`$ 为 Dish，$`i`$ 为 Ingredient，$`p`$ 为 Plan。固定顾客 $`g`$ 后，决策是选择料理 $`d`$ 及加料向量 $`a`$：

```math
p=(d,a),\qquad a_i\in\mathbb Z_{\ge0},\qquad
c_i(p)=b_i(d)+a_i,\qquad C(p)=\sum_i c_i(p)\le5
```

| 符号 | 英文对应与含义 | 单位 |
| --- | --- | --- |
| $`b_i(d)`$ | Base：料理配方规定的食材用量，是给定参数 | 件／份 |
| $`a_i`$、$`A(p)=(a_i)_i`$ | Addition：追加该食材的件数，以及完整加料向量，是决策量 | 件／份 |
| $`c_i(p)`$、$`C(p)`$ | Count：该食材的总用量、方案的总食材件数 | 件／份 |
| $`T_I(i)`$、$`T(p)`$ | Tag：食材自身的标签集合、方案的最终标签集合 | 集合 |
| $`\mathcal L_g,\mathcal D_g`$ | Likes / Dislikes：顾客的喜爱、厌恶标签集合 | 集合 |
| $`H_g^{L}(p),H_g^{D}(p)`$ | Hit：最终标签命中的喜爱、厌恶项数 | 项 |
| $`S_g(p),S_{\min}`$ | Score：方案净分、玩家指定的最低净分 | 分 |
| $`R_T,E_T`$ | Required / Excluded Tags：用户要求必含、排除的标签 | 集合 |

比较多个方案时，将其中的加料件数写作 $`a_i(p)`$。基础食材满足配方并占用格数，其标签不自动并入料理；加料才带入食材标签。$`T(p)`$ 由料理、厨具、售价及加料产生的标签经覆盖与流行规则处理后得到，同名标签只保留一次。基础配方不足五件、追加后总用料达到五件时，网页还加入「大份」；料理自身已有的「大份」也会保留。顾客偏好中的流行词条是固定偏好；当前流行的触发条件影响方案是否获得相应标签。评分为：

```math
H_g^{L}(p)=\left|T(p)\cap\mathcal L_g\right|,\qquad
H_g^{D}(p)=\left|T(p)\cap\mathcal D_g\right|,\qquad
S_g(p)=H_g^{L}(p)-H_g^{D}(p)
```

令 $`\mathcal B_d^{\mathrm{web}}`$ 为网页针对料理 $`d`$ 实际枚举的方案池；它受原配方处理及等价去重选项影响。未指定的标签条件取空集。进入后续过滤的达标候选为：

```math
\mathcal C_{g,d}^{0}=
\left\{p\in\mathcal B_d^{\mathrm{web}}:
S_g(p)\ge S_{\min},\quad R_T\subseteq T(p),\quad E_T\cap T(p)=\varnothing
\right\}
```

这是最低净分条件：门槛为 3 时，4 分、5 分仍可通过；喜爱命中也可以抵消厌恶扣分。原网页的配方处理范围与 Python 分支不同，见[网页使用说明](docs/web-guide.md)。后面的过滤只比较已通过本步的候选。

#### 1.2.3 等价去重：压缩加料食材池

**目的。** 如果两种食材提供完全相同的非空标签，先只枚举一个代表，减少重复的标签组合。这里的等价依据是食材自身标签，不是售价、供给量或方案最终标签。

定义等价关系及等价组：

```math
i\sim j\quad\Longleftrightarrow\quad
i=j\ \lor\ \left(T_I(i)=T_I(j)\ne\varnothing\right),\qquad
E(i)=\{j:j\sim i\}
```

无标签食材各自成组，不合并为同一组。令 $`I_d`$ 为按该料理禁用食材名过滤后的加料池，则该料理可用的等价组为 $`E_d(i)=E(i)\cap I_d`$。开启去重时，每个非空组只选一个代表进入枚举池：优先采用原程序预设的代表名单，其次按中文名称顺序选择；未开启时枚举完整的 $`I_d`$。

该步骤只压缩**加料**的选项，基础配方不变；同一个代表仍可追加多件。它发生在枚举之前，因此不能将其理解为“生成全部方案后，再按最终标签合并”。供给不同但标签相同的食材也会归为一组，后续采购计算需另外定义。

#### 1.2.4 食材高级过滤：比较指定的基础替代

**目的。** 若额外标签并非达标所必需，可以优先保留由标签更少的食材构成的方案。“高级”在此按标签包含关系定义，不代表食材价格、稀有度或游戏等级。

在该料理实际用于枚举的食材池中，对食材 $`i`$ 寻找满足下式的基础替代 $`j`$：

```math
\varnothing\ne T_I(j)\subsetneq T_I(i)
```

原程序从识别出的替代项中选标签数最少者，同数量时按中文名称顺序选择，记为 $`B_d(i)`$（Base representative）；没有替代项时取 $`B_d(i)=i`$。将方案的**所有加料同时**映射到这些代表，得到基础加料向量：

```math
\bar a_j(p)=\sum_{i:B_d(i)=j}a_i,\qquad
\bar A(p)=(\bar a_j(p))_j,\qquad p_B=(d,\bar A(p))
```

当 $`\bar A(p)\ne A(p)`$ 时，该方案被视为含高级加料。开启高级过滤后，删除条件为：

```math
\bar A(p)\ne A(p),\qquad
p_B\in\mathcal C_{g,d}^{0},\qquad \bar A(p_B)=A(p_B),\qquad
\left(F_U=0\ \lor\ S_g(p_B)\ge S_g(p)\right)
```

$`F_U`$ 是该过滤的“考虑得分”开关：开启为 1，关闭为 0。关闭时，只要对应的非高级基础方案也达标，就删除当前高级方案；开启时，还要求基础方案得分不低于当前方案。若基础方案未生成、未达标或不满足其他准入条件，则保留当前方案。

例如，某食材的标签为「甜」，另一食材为「甜」「高级」；只有前者确实被选为后者的基础代表、且替代后的整套方案达标时，后者方案才进入上述删除判断。这是**指定基础映射的比较**，不是穷举所有部分替换，也不改变基础配方。

#### 1.2.5 加料子集过滤：比较能否少加食材

**目的。** 若保留方案仅使用当前方案的一部分加料即可达标，则按用户政策省略更多加料的方案。这里比较食材的**件数向量**，不是食材名称集合或标签集合：

```math
A(p')\preceq A(p)\quad\Longleftrightarrow\quad
\forall i,\ a_i(p')\le a_i(p)
```

输入为高级过滤之后的同料理候选；先按加料件数升序、得分降序、加料名称键顺序排列。依次处理时，以 $`\mathcal K`$ 表示此前已保留的方案，当前方案的删除条件为：

```math
\exists p'\in\mathcal K:\quad
A(p')\preceq A(p)\quad\land\quad
\left(F_S=0\ \lor\ S_g(p')\ge S_g(p)\right)
```

$`F_S`$ 是子集过滤的“考虑得分”开关：关闭时，已保留的达标子集存在即可；开启时，子集得分还须不低于当前方案。未被删除的方案加入 $`\mathcal K`$，供后续比较。零加料方案若达标，也可以成为子集；实际判定包含向量相等的情形。

例如，“蜂蜜×1”是“蜂蜜×2”的加料子集，反向不成立。若两者均达标且前者已保留，关闭考虑得分时可删除后者；开启时需进一步比较净分。高级过滤比较相同件数下的食材身份替代；子集过滤比较减少既有加料用量的组合。两者均据比较结果删减候选，不改写保留方案。

#### 1.2.6 采购推荐：按供给向量确定保留边界

**目的。** 对前述过滤后留下的方案，优先考虑供给较充足的用料组合。此时还没有每日订单量假设，也不从供给中扣减消耗；比较在每道料理内部进行。

**有效供给值。** 令 $`q_i`$ 为食材的经验日供给量（Quantity，TDQ，件／日），$`M(i)\subseteq E(i)`$ 为程序全局分组记录中，与该食材对应且有已知供给值的成员。网页使用：

```math
\widetilde q_i=
\begin{cases}
\dfrac{1}{|M(i)|}\sum_{j\in M(i)}q_j,& |M(i)|>0,\\
q_i,& |M(i)|=0\text{ and }q_i\text{ is known},\\
0,&\text{otherwise}.
\end{cases}
```

单成员组有值时，上式就是自身供给；无组内记录时先回退到食材自身的供给记录，仍缺失才取 0。均值取自全局组，不只取该料理允许的成员；即使未开启等价去重，采购比较仍使用这一有效值。

**比较向量。** 每份方案中，每一件基础食材和加料各贡献一次有效供给值，按升序组成向量 $`V(p)`$（Vector）：

```math
V(p)=\mathrm{sort}_{\uparrow}
\left(\biguplus_i\{\widetilde q_i\}^{c_i(p)}\right)
```

这里 $`\biguplus`$ 表示保留重复元素的拼接，$`\{\widetilde q_i\}^{c_i(p)}`$ 表示该值重复 $`c_i(p)`$ 次。排名从最小分量开始比较，在第一个不同位置取值较大者优先；前缀相同时，将较短向量缺少的分量视为 $`+\infty`$。因此：

```math
(4,12)\succ(3,100),\qquad
(4,12)\succ(4,10),\qquad
(4)\succ(4,12)
```

这是一种优先比较最低供给值的词典序规则，不是最大化供给总和。原实现用 $`10^{-9}`$ 作为数值比较容差；向量并列时按加料件数、加料名称键稳定排序。

**Top-N 与并列。** 将候选按上述顺序记为 $`p_1,\ldots,p_m`$，$`N\ge1`$ 为用户指定的排名阈值。为说明去重如何影响边界，定义方案权重 $`W(p)`$（Weight）：

```math
W(p)=
\begin{cases}
1,&\text{equivalence deduplication off},\\
\prod_{i:a_i>0}|E_d(i)|^{a_i},&\text{equivalence deduplication on}.
\end{cases}
```

无加料时空乘积为 1。边界位置及最终保留集合为：

```math
k^*=\min\left\{k:\sum_{r=1}^{k}W(p_r)\ge N\right\},\qquad
\mathcal R_{g,d}=\{p_r:V(p_r)\succeq V(p_{k^*})\}
```

若累计权重不足 $`N`$，取 $`k^*=m`$；无候选时输出为空。未去重时，边界就是第 $`\min(N,m)`$ 个方案；去重时按该料理可用等价组大小累积权重。**Top-N 用于确定供给向量边界，并列全部保留，因此输出行数不一定为 N，也不是取 N 个不同向量组。**

权重是原程序的阈值补偿规则，不能一般性地解释为精确还原去重前的方案数。例如，同一两成员组重复追加两件时，权重为 $`2^2=4`$，但无序组合实际只有三种。因此不据此宣称开关去重前后的 Top-N 结果严格等价。

**输出名称。** 同时开启采购推荐与等价去重时，最终显示的加料还会替换为全局等价组中已知原始供给量最大的成员：

```math
i_{\mathrm{out}}\in\arg\max_{j\in M(i)}q_j
```

没有已知供给值时保留当前代表，并列按代表优先级与名称顺序处理。**排名采用组均值，输出名称采用组内最大值**，基础配方不替换。该输出步骤按全局组选择，未再次按料理禁用名单检查；使用条件见[网页使用说明](docs/web-guide.md)。

由此，HTML 阶段的模型完整地分为**准入条件、两种方案删减政策、食材等价近似与采购排序**。后续 Python 版本将进一步定义自动选定方案的目标，而非直接把这套网页过滤流程视为唯一的最优解定义。

<details>
<summary>与既有图稿及补充说明的符号对照</summary>

本章使用英文含义较直观的记号；既有图稿及部分补充文档仍沿用旧记号，对应关系如下，模型含义不变。

| 本章记号 | 既有记号 | 含义 |
| --- | --- | --- |
| $`a_i`$ | $`x_i`$ | 加料件数 |
| $`C(p)`$ | $`L(p)`$ | 总食材件数 |
| $`\mathcal L_g,\mathcal D_g`$ | $`P_g,N_g`$ | 喜爱、厌恶集合 |
| $`H_g^{L}(p),H_g^{D}(p)`$ | $`h_g(p),a_g(p)`$ | 喜爱、厌恶命中数 |
| $`S_g(p),S_{\min}`$ | $`s_g(p),\tau`$ | 净分、最低净分 |

</details>

### 1.3 detailedPLAN：为各目标标签选择多套方案

**问题与变化。** `detailedPLAN.py` 将任务从返回候选推进为自动选定一组方案：针对一位顾客的每个可行目标喜好标签，分别准备应对方案。评价顺序改为**预计食材件数最少，其次最低供给余量最大**。

Python PLAN 在评分准入中增加“无厌恶命中”条件，因此沿用上一节的净分门槛即可得到：

```math
H_g^{D}(p)=0,\qquad S_g(p)\geS_{\min}
\quad\Longrightarrow\quad H_g^{L}(p)\geS_{\min}
```

配方禁忌、持有料理及候选规约按对应 Python 版本执行。HTML 与 Python 的处理并不完全相同，因此下文分别定义各版本的候选集合，不把 Python 结果直接视为网页结果的子集。

**新增决策与订单假设。** 对目标标签 $`t\in \mathcal L_g`$，令 $`\mathcal C_{g,t}`$ 为包含该标签、通过准入，并按原程序逐料理、逐目标标签应用升级／子集过滤后汇集的候选。定义：

```math
J_g=\left\{t\in \mathcal L_g:\mathcal C_{g,t}\ne\varnothing\right\},\qquad
m=|J_g|,\qquad p_t\in\mathcal C_{g,t}\quad(t\in J_g)
```

决策现在是方案族 $`(p_t)_{t\in J_g}`$。同一方案可被多个标签选中；$`m`$ 统计有候选的目标标签数，不是不同菜品数。引入假设日订单量 $`K`$（单／日，默认 5），并假设订单在这些目标标签间均分，每类承担 $`K/m`$ 单。若 $`m=0`$，不生成规划。

沿用 $`c_i(p)`$ 和原始日供给 $`q_i`$，令 $`u_i`$ 为各标签所选方案对食材的累计用量。预期日食材件数 $`E_{\mathrm{old}}`$ 与最低供给余量 $`R_{\mathrm{old}}`$ 为：

```math
u_i=\sum_{t\in J_g}c_i(p_t),\qquad
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

后二者单位均为件／日。与网页比较供给值不同，这里开始扣除假设订单对应的消耗；均分是假设，尚无对应的实测订单概率估计。

**目标函数。**

```math
\min_{\substack{p_t\in\mathcal C_{g,t}\\t\in J_g}}^{\mathrm{lex}}
\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

$`\mathrm{lex}`$ 表示词典序：先比较第一项，仅在相同时比较第二项。固定 $`m`$ 后，最少预期件数可按标签拆分，因此程序先保留每个标签全部并列最少件数候选，再比较组合的供给压力。最低余量相同时，继续比较完整的升序余量向量。旧分支的阈值二分与 DFS 用于这一组合求解；它们属于求解方法，目标仍是上式。

### 1.4 singlePLAN：将每标签方案改为每客一个方案

**问题与变化。** `singlePLAN.py` 将决策从方案族 $`(p_t)_{t\in J_g}`$ 改为单个 $`p`$：同一位顾客的全部假设订单采用这一套方案。同时，目标顺序改为**喜爱命中最多，其次食材件数最少，最后最低供给余量最大**。

**用量模型的改动。** 沿用方案、标签、净分与无厌恶准入的定义。每日消耗不再按标签分配，食材需求与余量改为：

```math
\frac{K}{m}\sum_{t\in J_g}c_i(p_t)
\quad\longrightarrow\quad Kc_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

$`R(p)`$ 的单位仍为件／日。$`K`$ 固定时，最小化每份件数 $`C(p)`$ 等价于最小化该客人的日件数 $`KC(p)`$；原实现直接比较每份件数。

**目标函数。** 令 $`\mathcal C_g^{\mathrm{single}}`$ 表示该版本生成并保留的合格候选：

```math
\max_{p\in\mathcal C_g^{\mathrm{single}}}^{\mathrm{lex}}
\left(H_g^{L}(p),\;-C(p),\;R(p)\right)
```

这一步同时改变了订单分配方式与第一优先级。此前先控制一组方案的预计消耗；现在先追求单份方案的更多喜爱命中，再在同覆盖下节约食材、缓解供给压力。三项均相同时，原程序依次用售价、料理名和加料字符串处理平局。

### 1.5 cover3：保留单方案，将喜好收益封顶为 3

**问题与变化。** `singlePLAN_cover3.py` 保留每客一套方案、全部订单复用以及同一余量计算，只调整第一目标：三项喜爱已经足够，额外命中不再提高优化优先级。

**新增效用与目标函数。** 以 $`U(h)`$ 表示命中数为 $`h`$ 时用于方案比较的覆盖收益（Utility），候选集合相应记为 $`\mathcal C_g^{\mathrm{cover3}}`$：

```math
U(h)=\min(h,3),\qquad
\left(H_g^{L}(p),-C(p),R(p)\right)
\quad\longrightarrow\quad
\left(U(H_g^{L}(p)),-C(p),R(p)\right)
```

```math
\max_{p\in\mathcal C_g^{\mathrm{cover3}}}^{\mathrm{lex}}
\left(U(H_g^{L}(p)),\;-C(p),\;R(p)\right)
```

变化只作用于比较收益，不改写最终标签 $`T(p)`$、命中数 $`H_g^{L}(p)`$ 或原始净分 $`S_g(p)`$。图 1 中「甜」流行时，饭团加蜂蜜对灵梦的原始得分为 4，而 $`U(4)=3`$。

门槛 $`S_{\min}`$ 控制能否进入候选，封顶函数 $`U`$ 控制进入后如何比较。在默认 $`S_{\min}=3`$ 且无厌恶的条件下，合格候选均有 $`U=3`$，因此该版本实际表达为：**先达标，再省料，再考虑供给余量**。降低门槛也不会自动改变收益上限。

### 1.6 输出格式分支：mixedingredients

**问题与变化。** `singlePLAN_cover3_mixedingredients.py` 调整结果的阅读和使用方式，将基础食材与加料合写为 `Ingredient1` 至 `Ingredient5`，按原输出约定排列并保留表格合并。

该分支沿用 1.5 节的决策与目标。$`p,c_i(p),C(p),T(p),H_g^{L}(p),S_g(p),R(p),U(H_g^{L}(p))`$ 的含义和计算不变；基础与追加用量合并展示不会使基础食材标签重新加入料理。它是输出表达的调整，不增加新的优化变量或目标。

### 1.7 固定厨具分支：limitedCookware

**问题与变化。** `singlePLAN_cover3_mixIng_limitedCookware.py` 在既定设备条件下为各客人选方案：由玩家指定排除哪些厨具，目标仍沿用 cover3。原文件默认排除烧烤架、蒸锅。

**新增条件。** 令 $`\kappa(d)`$ 表示料理所需厨具，$`S_0`$ 表示排除指定设备后可用的厨具集合。为后续设备分支统一记号，以 $`v`$ 标记具体版本，$`\mathcal C_g^{(v)}`$ 为该版本应用设备集合限制前的合格候选；定义限制操作：

```math
\mathcal C_g^{(v)}(S)=
\left\{p=(d,a)\in\mathcal C_g^{(v)}:\kappa(d)\in S\right\}
```

本节取 $`v=\mathrm{limited}`$、$`S=S_0`$，在此子集中按 1.5 节的目标比较。$`S_0`$ 是给定条件，不参与优化；这是一条约束分支，与输出格式调整分开。

### 1.8 共同厨具分支：nCookware

**问题与变化。** `singlePLAN_cover3_mixIng_nCookware.py` 将设备集合本身纳入决策：给定可用厨具数量，程序选择具体设备，并为各顾客配置一套可用方案。它与固定排除分支是两种设备配置方式，输入不需要先经过 `limitedCookware`。

**新增决策变量。** 令 $`G`$ 为本次规划的顾客集合，$`H`$ 为已拥有料理对应的可用厨具集合，$`n`$ 为本次采用的厨具种类数。设备集合从固定 $`S_0`$ 改为待选择的 $`S`$：

```math
S\subseteq H,\qquad |S|=n
```

沿用 1.7 节的限制操作，此时 $`v=\mathrm{nCookware}`$。对给定 $`S`$，令 $`p_g^*(S)`$ 为从 $`\mathcal C_g^{(v)}(S)`$ 中按 cover3 目标选出的方案；有方案的顾客构成 $`G_S`$，无方案人数为 $`z_S=|G\setminus G_S|`$。

**集合层目标。** 单客的评价顺序保留；新增外层比较，将各客评价汇总，并计入原程序的无解惩罚：

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\sum_{g\in G_S}U(H_g^{L}(p_g^*(S))),\;
-\left[\sum_{g\in G_S}C(p_g^*(S))+10^9z_S\right],\;
\sum_{g\in G_S}R(p_g^*(S))-10^{18}z_S
\right)
```

在默认三分准入条件下，每位有方案的客人贡献 3 点封顶收益，第一项因而优先增加得到达标方案的客人数，再比较总用料与逐客余量。两项惩罚常数来自原实现，并不意味着所有客人都必须有方案。

共同选择的是厨具，$`R(p)`$ 仍按每位顾客的假设订单独立计算；未汇总所有人的食材消耗后共同扣减库存。程序先复用每客每厨具的最佳保留候选，再枚举设备组合，这与旧多方案的订单均分及组合求解属于不同层次。

### 1.9 版本关系与适用范围

这条主线保留 1 个 HTML 和 6 个 PLAN 文件。目标依次由达标候选查询、多标签方案组合、单客覆盖优先，发展到三项封顶与共同厨具配置；其中 `mixedingredients` 改变输出表达，`limitedCookware` 改变给定约束。基础得分、利润、普客及酒水分析是独立辅助支线。

以上数学记号连续沿用，但候选集合须按对应版本解释。标签等价代表与中性补位截断限制了实际搜索范围，保留候选中的最优不构成全部合法食材组合上的全局最优性证明。供给余量可为负，是排序指标而非库存硬约束；顾客预算未作为求解约束，售价的平局规则也不构成利润目标。各阶段的取舍依据见第 2 章，候选规约与求解细节见[优化模型与算法边界](docs/design.md)。

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

**Mechanics and terminology** &nbsp; <a href="#en-tag-figure"><img src="docs/images/jump-to-figure-en.png" alt="Jump to diagram" width="156" height="28" align="middle"></a>

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

Chapter 1 begins with browser plan definitions and query conditions, then develops the mathematical changes for multiple plans, a single plan, and capped coverage. Output formatting and the two cookware branches are explained separately. The five-slot limit and recipe prohibitions are preparation conditions; the score threshold and zero-dislike eligibility are planning policies.

<a id="en-model"></a>

## 1. Mathematical model: from gameplay decisions to optimization

### 1.1 Overview of model evolution

The continuing problem is how to choose preparation plans. What changes as requirements become explicit is **the decision unit, eligibility for comparison, and the ordered definition of a better result**. The browser first provides qualifying-candidate queries; Python planning defines tag-specific plan combinations, one plan per guest, capped coverage utility, and shared cookware selection. HTML and Python are independent entry points sharing a workbook. Arrows represent dependencies between decision definitions, not frontend/backend calls or a precisely dated development timeline.

[![Model evolution: the browser filters several candidates by liked minus disliked matches; the historical model selects a plan per feasible liked tag, first minimizing expected units and then maximizing minimum supply slack; the single-guest model prioritizes liked coverage, units, and slack; cover3 caps coverage benefit at 3; cookware configuration moves from fixed exclusions to selecting exactly n shared types. Presentation changes, CPU acceleration, and profit analysis are distinguished.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.png)

*Figure 2. Evolution of decision units, objectives, and constraints. Arrows follow problem dependencies; optimality is relative to each model's evaluation policy and retained candidates.* [Vector SVG](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/model-evolution-en.svg).

The following sections start with HTML, continue through `detailedPLAN`, `singlePLAN`, and `cover3`, then separate output formatting, fixed cookware, and shared cookware into distinct branches. Each section first states the decision problem and its change from the preceding model, then defines new quantities and equations. Existing symbols retain their meanings, while candidate sets are distinguished by implementation.

### 1.2 HTML: defining plans, filtering candidates, and comparing procurement conditions

#### 1.2.1 Decision problem

Given a rare guest, imported dishes and ingredients, current trend conditions, and the player's minimum score and tag requirements, the webpage determines **how each dish can be supplemented, which combinations qualify, which can be omitted, and which use ingredients with better availability.** It returns a candidate table, with one dish and its addition types and quantities per row. This stage may retain multiple rows; it does not require a unique plan for the guest.

The four options apply distinct decision criteria:

| Option | Decision question | Comparison scope |
| --- | --- | --- |
| Equivalent-ingredient deduplication (additions only) | Must ingredients with identical tags be enumerated separately? | Addition ingredient pool before enumeration |
| Ingredient-upgrade filter | Should an “advanced” alternative remain when ingredients with fewer tags can form a qualifying plan? | Qualified plans for the same dish and their designated base alternatives |
| Addition-subset filter | Should a plan with more additions remain when fewer of those ingredients suffice? | Previously retained plans and the current plan for the same dish |
| Procurement recommendation | Which qualifying plans require ingredients with better supply conditions? | Candidates for the same dish after the preceding filters |

The execution order is **exclude ingredient names forbidden by the dish → optional equivalence deduplication → enumerate additions → apply tag and score admission conditions → upgrade filter → subset filter → procurement ranking and output.** Disabled steps are skipped. The common model is defined first, followed by each rule.

#### 1.2.2 Common model: plans, tags, and admission

Symbols follow their English meanings where possible: $`g`$ denotes Guest, $`d`$ Dish, $`i`$ Ingredient, and $`p`$ Plan. For a fixed guest $`g`$, the decision selects a dish $`d`$ and an addition vector $`a`$:

```math
p=(d,a),\qquad a_i\in\mathbb Z_{\ge0},\qquad
c_i(p)=b_i(d)+a_i,\qquad C(p)=\sum_i c_i(p)\le5
```

| Symbol | English meaning and definition | Unit |
| --- | --- | --- |
| $`b_i(d)`$ | Base: ingredient quantity required by the dish's recipe; a given parameter | Units per serving |
| $`a_i`$, $`A(p)=(a_i)_i`$ | Addition: quantity of the added ingredient and the complete addition vector; decision variables | Units per serving |
| $`c_i(p)`$, $`C(p)`$ | Count: total quantity of an ingredient and total ingredient count of the plan | Units per serving |
| $`T_I(i)`$, $`T(p)`$ | Tag: the ingredient's own tag set and the plan's final tag set | Sets |
| $`\mathcal L_g,\mathcal D_g`$ | Likes / Dislikes: the guest's liked and disliked tag sets | Sets |
| $`H_g^{L}(p),H_g^{D}(p)`$ | Hit: counts of liked and disliked tags matched by the final tags | Matches |
| $`S_g(p),S_{\min}`$ | Score: the plan's net score and the player's minimum net score | Points |
| $`R_T,E_T`$ | Required / Excluded Tags: tags the user requires or excludes | Sets |

When comparing multiple plans, write their addition quantities as $`a_i(p)`$. Base ingredients satisfy the recipe and occupy slots; their tags do not automatically transfer to the dish. Additions introduce ingredient tags. $`T(p)`$ combines tags derived from the dish, cookware, selling price, and additions, then applies override and trend rules; each distinct tag appears only once. When a base recipe uses fewer than five units and additions bring the total to five, the webpage also adds 「Large portion」; a dish's existing 「Large portion」 tag is retained. A guest's trend preferences are fixed, while current trend triggers determine whether a plan receives the corresponding trend tags. The score is:

```math
H_g^{L}(p)=\left|T(p)\cap\mathcal L_g\right|,\qquad
H_g^{D}(p)=\left|T(p)\cap\mathcal D_g\right|,\qquad
S_g(p)=H_g^{L}(p)-H_g^{D}(p)
```

Let $`\mathcal B_d^{\mathrm{web}}`$ be the plan pool actually enumerated by the webpage for dish $`d`$; it depends on the original recipe handling and the equivalence-deduplication option. Unspecified tag requirements use empty sets. Qualified candidates entering the subsequent filters are:

```math
\mathcal C_{g,d}^{0}=
\left\{p\in\mathcal B_d^{\mathrm{web}}:
S_g(p)\ge S_{\min},\quad R_T\subseteq T(p),\quad E_T\cap T(p)=\varnothing
\right\}
```

This is a minimum net-score condition: a threshold of 3 also admits scores of 4 or 5, and liked matches can offset dislike penalties. The original webpage's recipe handling differs from the Python branches; see the [web guide](docs/web-guide.md). Subsequent filters compare only candidates admitted at this step.

#### 1.2.3 Equivalence deduplication: reducing the addition ingredient pool

**Purpose.** When two ingredients provide exactly the same nonempty tag set, enumerate a single representative to reduce repeated tag combinations. Equivalence is based on the ingredients' own tags, not their price, supply, or the plan's final tags.

Define the equivalence relation and classes as:

```math
i\sim j\quad\Longleftrightarrow\quad
i=j\ \lor\ \left(T_I(i)=T_I(j)\ne\varnothing\right),\qquad
E(i)=\{j:j\sim i\}
```

Ingredients without tags form separate singleton classes. Let $`I_d`$ be the addition pool after excluding ingredient names forbidden by the dish. Its available equivalence classes are $`E_d(i)=E(i)\cap I_d`$. When deduplication is enabled, one representative from each nonempty class enters enumeration: the original program's preferred-name list takes priority, followed by Chinese name ordering. When disabled, the full $`I_d`$ is enumerated.

This step reduces **addition** choices only; the base recipe remains unchanged, and a representative may still be added multiple times. It occurs before enumeration, rather than merging fully generated plans by their final tags. Ingredients with identical tags but different supply quantities still share a class, so procurement comparisons require a separate definition.

#### 1.2.4 Ingredient-upgrade filter: comparing designated base alternatives

**Purpose.** When extra tags are unnecessary for qualification, prefer retaining plans made with ingredients carrying fewer tags. “Advanced” is defined here by tag inclusion, not ingredient price, rarity, or game level.

Within the ingredient pool actually used to enumerate the dish, consider ingredient $`i`$ and seek a base alternative $`j`$ satisfying:

```math
\varnothing\ne T_I(j)\subsetneq T_I(i)
```

The original program selects the recognized alternative with the fewest tags, breaking ties by Chinese name order. Denote it by $`B_d(i)`$ (Base representative); if no alternative exists, set $`B_d(i)=i`$. Map **all additions simultaneously** to these representatives to obtain the base addition vector:

```math
\bar a_j(p)=\sum_{i:B_d(i)=j}a_i,\qquad
\bar A(p)=(\bar a_j(p))_j,\qquad p_B=(d,\bar A(p))
```

A plan is considered to contain advanced additions when $`\bar A(p)\ne A(p)`$. With the upgrade filter enabled, it is removed when:

```math
\bar A(p)\ne A(p),\qquad
p_B\in\mathcal C_{g,d}^{0},\qquad \bar A(p_B)=A(p_B),\qquad
\left(F_U=0\ \lor\ S_g(p_B)\ge S_g(p)\right)
```

$`F_U`$ is this filter's “consider score” switch: 1 when enabled and 0 when disabled. When disabled, the existence of the corresponding qualified, nonadvanced base plan suffices to remove the advanced plan. When enabled, the base plan must also score at least as highly. The current plan remains if the base plan was not generated, failed the score threshold, or failed another admission condition.

For example, one ingredient may carry 「Sweet」, and another 「Sweet」「Premium」. The latter plan is evaluated for removal only if the former ingredient is its selected base representative and the complete replacement plan qualifies. This compares a **designated base mapping**; it does not enumerate every partial substitution or alter the base recipe.

#### 1.2.5 Addition-subset filter: comparing smaller additions

**Purpose.** If a retained plan qualifies using only some of the current plan's additions, omit the larger addition plan according to the selected policy. The comparison concerns **ingredient-count vectors**, not sets of ingredient names or tags:

```math
A(p')\preceq A(p)\quad\Longleftrightarrow\quad
\forall i,\ a_i(p')\le a_i(p)
```

The input consists of same-dish candidates remaining after the upgrade filter. They are sorted by ascending addition count, descending score, and addition-name key. During sequential processing, let $`\mathcal K`$ contain the previously retained plans. The current plan is removed when:

```math
\exists p'\in\mathcal K:\quad
A(p')\preceq A(p)\quad\land\quad
\left(F_S=0\ \lor\ S_g(p')\ge S_g(p)\right)
```

$`F_S`$ is the subset filter's “consider score” switch. When disabled, any retained qualifying subset suffices; when enabled, the subset must also score at least as highly. A plan that survives is added to $`\mathcal K`$ for subsequent comparisons. A qualifying plan with no additions can also serve as a subset; the implemented relation includes equal vectors.

For example, “honey ×1” is an addition subset of “honey ×2”, but not conversely. If both qualify and the former has been retained, the latter can be removed when score consideration is disabled; when enabled, their net scores must also be compared. The upgrade filter compares ingredient substitutions at an unchanged count; the subset filter compares combinations using smaller quantities of existing additions. Both remove candidates according to these comparisons without rewriting retained plans.

#### 1.2.6 Procurement recommendation: setting a cutoff by supply vectors

**Purpose.** Among plans surviving the preceding filters, favor ingredient combinations with better availability. At this stage, no daily order volume is assumed and consumption is not deducted from supply. Comparisons remain within each dish.

**Effective supply.** Let $`q_i`$ be an ingredient's empirical daily supply (Quantity, TDQ, units per day), and $`M(i)\subseteq E(i)`$ the members associated with that ingredient in the program's global group records that have known supply values. The webpage uses:

```math
\widetilde q_i=
\begin{cases}
\dfrac{1}{|M(i)|}\sum_{j\in M(i)}q_j,& |M(i)|>0,\\
q_i,& |M(i)|=0\text{ and }q_i\text{ is known},\\
0,&\text{otherwise}.
\end{cases}
```

For a singleton class with a known value, this equals the ingredient's own supply. With no group record, it first falls back to the ingredient's own supply record, then to 0 if that is also missing. The mean uses the global class, not only members allowed for the current dish. Procurement comparisons use this effective value even when equivalence deduplication is disabled.

**Comparison vector.** Each unit of a base ingredient or addition contributes one effective supply value. Sorting these values in ascending order gives $`V(p)`$ (Vector):

```math
V(p)=\mathrm{sort}_{\uparrow}
\left(\biguplus_i\{\widetilde q_i\}^{c_i(p)}\right)
```

Here, $`\biguplus`$ denotes concatenation preserving repeated elements, and $`\{\widetilde q_i\}^{c_i(p)}`$ repeats that value $`c_i(p)`$ times. Ranking starts at the smallest component and favors the larger value at the first differing position. When prefixes match, missing components of the shorter vector are treated as $`+\infty`$. Thus:

```math
(4,12)\succ(3,100),\qquad
(4,12)\succ(4,10),\qquad
(4)\succ(4,12)
```

This lexicographic rule prioritizes the lowest supply values rather than maximizing total supply. The original implementation uses a numerical comparison tolerance of $`10^{-9}`$; vector ties are ordered stably by addition count and addition-name key.

**Top-N and ties.** Write the ordered candidates as $`p_1,\ldots,p_m`$, with $`N\ge1`$ the user-specified ranking threshold. To describe how deduplication affects the cutoff, define plan weight $`W(p)`$ (Weight):

```math
W(p)=
\begin{cases}
1,&\text{equivalence deduplication off},\\
\prod_{i:a_i>0}|E_d(i)|^{a_i},&\text{equivalence deduplication on}.
\end{cases}
```

With no additions, the empty product is 1. The cutoff position and retained set are:

```math
k^*=\min\left\{k:\sum_{r=1}^{k}W(p_r)\ge N\right\},\qquad
\mathcal R_{g,d}=\{p_r:V(p_r)\succeq V(p_{k^*})\}
```

If cumulative weight is below $`N`$, use $`k^*=m`$; if there are no candidates, output is empty. Without deduplication, the cutoff is the $`\min(N,m)`$-th plan. With deduplication, weights accumulate according to the sizes of the dish's available equivalence classes. **Top-N determines a supply-vector cutoff, and all ties are retained. The output therefore need not contain N rows, nor does the rule select N distinct vector groups.**

The weight is the original program's cutoff-compensation rule, not a generally exact reconstruction of the number of plans before deduplication. For example, adding two units from the same two-member class gives weight $`2^2=4`$, whereas there are only three unordered combinations. Strict equivalence of Top-N results with deduplication on and off is therefore not claimed.

**Output names.** When both procurement recommendation and equivalence deduplication are enabled, displayed additions are also replaced by the global equivalent with the highest known raw supply:

```math
i_{\mathrm{out}}\in\arg\max_{j\in M(i)}q_j
```

If no supply value is known, the current representative remains. Ties follow representative priority and name order. **Ranking uses the class mean; output names use the class maximum.** Base ingredients are not replaced. This output step selects from the global class without checking the dish's forbidden-name list again; see the conditions in the [web guide](docs/web-guide.md).

The HTML model therefore comprises **admission conditions, two candidate-removal policies, an ingredient-equivalence approximation, and procurement ranking**. Subsequent Python versions introduce objectives for selecting plans automatically, rather than treating this webpage filtering pipeline as the sole definition of optimality.

<details>
<summary>Notation correspondence with existing figures and supplementary documents</summary>

This chapter uses symbols with more direct English associations. Existing figures and some supplementary documents retain earlier symbols; the following correspondence preserves their model meanings.

| This chapter | Earlier notation | Meaning |
| --- | --- | --- |
| $`a_i`$ | $`x_i`$ | Addition count |
| $`C(p)`$ | $`L(p)`$ | Total ingredient count |
| $`\mathcal L_g,\mathcal D_g`$ | $`P_g,N_g`$ | Liked and disliked tag sets |
| $`H_g^{L}(p),H_g^{D}(p)`$ | $`h_g(p),a_g(p)`$ | Liked and disliked match counts |
| $`S_g(p),S_{\min}`$ | $`s_g(p),\tau`$ | Net score and minimum net score |

</details>

### 1.3 detailedPLAN: select plans for individual target tags

**Problem and change.** `detailedPLAN.py` advances from returning candidates to automatically selecting a collection of plans: one response plan for each feasible target liked tag of a guest. The evaluation order becomes **minimum expected ingredient units, followed by maximum minimum supply slack**.

Python PLAN adds a zero-disliked-match eligibility condition. Retaining the previous section's net-score threshold therefore gives:

```math
H_g^{D}(p)=0,\qquad S_g(p)\geS_{\min}
\quad\Longrightarrow\quad H_g^{L}(p)\geS_{\min}
```

Recipe prohibitions, dish ownership, and candidate reduction follow the corresponding Python version. HTML and Python do not process every condition identically, so their candidate sets are defined separately below; Python results are not assumed to be a subset of browser results.

**New decisions and order assumptions.** For a target tag $`t\in \mathcal L_g`$, let $`\mathcal C_{g,t}`$ contain eligible candidates that include the tag, collected after the original upgrade/subset filters are applied separately for each dish and target tag. Define:

```math
J_g=\left\{t\in \mathcal L_g:\mathcal C_{g,t}\ne\varnothing\right\},\qquad
m=|J_g|,\qquad p_t\in\mathcal C_{g,t}\quad(t\in J_g)
```

The decision is now a family of plans $`(p_t)_{t\in J_g}`$. Several tags may select the same plan; $`m`$ counts target tags with candidates, not distinct dishes. Introduce the assumed daily order count $`K`$, in orders per day (default 5), and assume that orders are distributed equally among these target tags, with $`K/m`$ orders assigned to each. If $`m=0`$, no plan is produced.

Retaining $`c_i(p)`$ and the original daily supply $`q_i`$, let $`u_i`$ be the cumulative use of an ingredient across the plans selected for the tags. Expected daily ingredient units $`E_{\mathrm{old}}`$ and minimum supply slack $`R_{\mathrm{old}}`$ are:

```math
u_i=\sum_{t\in J_g}c_i(p_t),\qquad
E_{\mathrm{old}}=\frac{K}{m}\sum_i u_i,\qquad
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m}u_i\right)
```

Both latter quantities are measured in units per day. Unlike the browser's comparison of supply values, this model subtracts consumption implied by assumed orders. Equal allocation is an assumption without a corresponding empirical estimate of order probabilities.

**Objective.**

```math
\min_{\substack{p_t\in\mathcal C_{g,t}\\t\in J_g}}^{\mathrm{lex}}
\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

$`\mathrm{lex}`$ denotes lexicographic order: compare the first criterion, and consider the second only when the first ties. With $`m`$ fixed, minimizing expected units separates by tag. The program therefore retains every candidate tied for minimum units for each tag before comparing the supply pressure of their combinations. Ties in minimum slack are resolved by comparing the full ascending slack vector. Threshold binary search and DFS in this historical branch solve that combination problem; they are solution methods, while the objective remains the expression above.

### 1.4 singlePLAN: replace plans per tag with one plan per guest

**Problem and change.** `singlePLAN.py` replaces the family $`(p_t)_{t\in J_g}`$ with a single $`p`$: all assumed orders for the same guest use this one plan. The objective order also changes to **maximum liked matches, followed by minimum ingredient units, then maximum minimum supply slack**.

**Change in the consumption model.** Plan, tag, net-score, and zero-dislike eligibility definitions are retained. Daily consumption is no longer distributed by tag; ingredient demand and slack become:

```math
\frac{K}{m}\sum_{t\in J_g}c_i(p_t)
\quad\longrightarrow\quad Kc_i(p),\qquad
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
```

$`R(p)`$ remains measured in units per day. For fixed $`K`$, minimizing units per serving $`C(p)`$ is equivalent to minimizing this guest's daily units $`KC(p)`$; the original implementation directly compares units per serving.

**Objective.** Let $`\mathcal C_g^{\mathrm{single}}`$ denote the eligible candidates generated and retained by this version:

```math
\max_{p\in\mathcal C_g^{\mathrm{single}}}^{\mathrm{lex}}
\left(H_g^{L}(p),\;-C(p),\;R(p)\right)
```

This step changes both order allocation and the first priority. The earlier model first controls expected consumption across a collection of plans. This model first seeks more liked matches in one plan, then reduces ingredient units and supply pressure at equal coverage. When all three criteria tie, the original program uses selling price, dish name, and the additions string, in that order.

### 1.5 cover3: retain one plan and cap preference benefit at 3

**Problem and change.** `singlePLAN_cover3.py` retains one plan per guest, its reuse for all orders, and the same slack calculation. Only the first objective changes: three liked matches are sufficient, and additional matches no longer increase optimization priority.

**New utility and objective.** Let $`U(h)`$ denote the coverage utility used to compare plans with $`h`$ liked matches, with the corresponding candidate set denoted by $`\mathcal C_g^{\mathrm{cover3}}`$:

```math
U(h)=\min(h,3),\qquad
\left(H_g^{L}(p),-C(p),R(p)\right)
\quad\longrightarrow\quad
\left(U(H_g^{L}(p)),-C(p),R(p)\right)
```

```math
\max_{p\in\mathcal C_g^{\mathrm{cover3}}}^{\mathrm{lex}}
\left(U(H_g^{L}(p)),\;-C(p),\;R(p)\right)
```

The change affects only comparison benefit; it does not redefine the final tags $`T(p)`$, match count $`H_g^{L}(p)`$, or raw net score $`S_g(p)`$. In Figure 1, when 「Sweet」 is popular, the rice-ball-and-honey plan scores 4 for Reimu, while $`U(4)=3`$.

The threshold $`S_{\min}`$ controls eligibility, while the capped function $`U`$ controls comparison after qualification. Under the default $`S_{\min}=3`$ and zero-dislike conditions, every eligible candidate has $`U=3`$. The policy therefore becomes **qualify first, then minimize ingredient units, then consider supply slack**. Lowering the threshold does not automatically change the benefit cap.

### 1.6 Output-format branch: mixedingredients

**Problem and change.** `singlePLAN_cover3_mixedingredients.py` changes how results are read and used. It combines base ingredients and additions into `Ingredient1` through `Ingredient5`, follows the original output ordering, and retains merged table cells.

This branch retains the decisions and objective of Section 1.5. The meanings and calculations of $`p,c_i(p),C(p),T(p),H_g^{L}(p),S_g(p),R(p),U(H_g^{L}(p))`$ remain unchanged. Displaying base and additional quantities together does not add base-ingredient tags to the dish. This is a presentation change with no new optimization variable or objective.

### 1.7 Fixed-cookware branch: limitedCookware

**Problem and change.** `singlePLAN_cover3_mixIng_limitedCookware.py` selects plans for guests under predetermined equipment conditions. The player specifies which cookware to exclude, while the objective remains that of cover3. The original file excludes the grill and steamer by default.

**New condition.** Let $`\kappa(d)`$ denote the cookware required by a dish, and $`S_0`$ the cookware set available after specified exclusions. To use consistent notation for the equipment branches, let $`v`$ identify the particular version and $`\mathcal C_g^{(v)}`$ denote its eligible candidates before restriction to an equipment set. Define the restriction operation:

```math
\mathcal C_g^{(v)}(S)=
\left\{p=(d,a)\in\mathcal C_g^{(v)}:\kappa(d)\in S\right\}
```

This section uses $`v=\mathrm{limited}`$ and $`S=S_0`$, comparing candidates in that subset by the objective in Section 1.5. $`S_0`$ is given rather than optimized. This is a constraint branch, separate from the output-format adjustment.

### 1.8 Shared-cookware branch: nCookware

**Problem and change.** `singlePLAN_cover3_mixIng_nCookware.py` makes the equipment set itself a decision. Given the number of cookware types to use, the program selects the specific equipment and assigns an available plan to each guest. This and fixed exclusion are two equipment-configuration approaches; input does not need to pass through `limitedCookware` first.

**New decision variable.** Let $`G`$ be the guests included in the current planning task, $`H`$ the available cookware associated with owned dishes, and $`n`$ the number of cookware types used in this task. The fixed equipment set $`S_0`$ becomes a set $`S`$ to be chosen:

```math
S\subseteq H,\qquad |S|=n
```

Retain the restriction operation from Section 1.7, now with $`v=\mathrm{nCookware}`$. For a given $`S`$, let $`p_g^*(S)`$ be the plan selected from $`\mathcal C_g^{(v)}(S)`$ by the cover3 objective. Guests with a plan form $`G_S`$, and the number without one is $`z_S=|G\setminus G_S|`$.

**Set-level objective.** The single-guest evaluation order is retained. A new outer comparison aggregates guest evaluations and includes the original program's penalties for missing plans:

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\sum_{g\in G_S}U(H_g^{L}(p_g^*(S))),\;
-\left[\sum_{g\in G_S}C(p_g^*(S))+10^9z_S\right],\;
\sum_{g\in G_S}R(p_g^*(S))-10^{18}z_S
\right)
```

Under the default three-point eligibility condition, each guest with a plan contributes 3 units of capped benefit. The first criterion therefore prioritizes the number of guests receiving a qualifying plan, followed by total ingredient units and per-guest slack. The two penalty constants come from the original implementation; they do not require every guest to have a plan.

Cookware is chosen jointly, while $`R(p)`$ is still calculated independently using each guest's assumed orders. Ingredient consumption is not aggregated across all guests and deducted from shared inventory. The program reuses the best retained candidate for each guest and cookware type before enumerating equipment combinations. This is a different decision level from equal order allocation and combination search in the historical multiple-plan model.

### 1.9 Version relationships and scope

This main line retains 1 HTML file and 6 PLAN files. Its objectives progress from qualifying-candidate queries through tag-specific plan combinations and single-guest coverage priority to a three-match cap and shared cookware configuration. Within that progression, `mixedingredients` changes presentation and `limitedCookware` changes given constraints. Base-score, profit, regular-guest, and drink analyses are separate supporting branches.

The mathematical notation is reused continuously, but candidate sets must be interpreted for the corresponding version. Tag-equivalent representatives and neutral-filler cutoffs limit the actual search scope. Optimality among retained candidates does not establish global optimality over all legal ingredient combinations. Supply slack can be negative and is a ranking criterion rather than a hard inventory constraint. Guest budgets are not solver constraints, and selling-price tie-breaking does not define a profit objective. Chapter 2 explains the tradeoffs at each stage; candidate reduction and solution details appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

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
