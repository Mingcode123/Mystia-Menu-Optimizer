<a id="chinese"></a>

# Mystia Menu Optimizer

**《东方夜雀食堂》备菜决策建模：偏好覆盖、食材供给与厨具配置**

**中文** | [English](#english)

历史版本：[v1.0.0 · Initial Release](https://github.com/Mingcode123/Mystia-Menu-Optimizer/releases/tag/v1.0.0)，提供完整源码与版本说明。

在[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/)中，同一位顾客可能接受多种料理与加料组合，而这些组合的用料、供给压力和所需厨具不同。备菜决策因此需要同时回答两个问题：哪些方案满足条件，以及在多个合格方案之间如何定义“更优”。

本项目将上述问题抽象为离散决策模型，明确配方与加料的可行域，并建立喜好覆盖、食材件数与最低供给余量的分层评价体系。模型经历了按喜好标签配置多套方案、每位顾客配置单套方案、覆盖收益封顶及共同厨具选择等调整。项目产出包括规则与数据定义、数学模型、设计决策说明，以及用于搜索候选和复核结果的程序。

作者的主要工作是提出游玩问题、梳理规则语义、记录供给与价格、确定目标和约束，并通过角色案例核对结果；代码实现、部分算法推导与调试使用 AI 辅助。本文重点说明这些建模选择及其影响，结果解释限定于给定数据、假设和实际保留的候选范围。

[数学模型](#zh-model) · [数据与建模依据](#zh-data) · [求解算法](#zh-algorithms) · [完整案例](#zh-verification) · [贡献与资料](#zh-sources)

**机制与术语** &nbsp; <a href="#zh-tag-figure"><img src="docs/images/jump-to-figure-zh.png" alt="直接看机制图" width="132" height="28" align="middle"></a>

制作与评价分为三个步骤：

1. **按配方确定料理。** 配方规定所需厨具和基础食材。例如，使用料理台和海苔×1可以制作饭团。饭团使用自身预设标签，海苔的标签不随基础配方自动加入。
2. **选择加料，形成方案。** 每份料理最多使用 5 件食材，基础食材与加料共同占用格子。饭团的海苔占 1 格，其余 4 格可加料，也可留空。若追加蜂蜜×1，就得到“饭团＋蜂蜜”的方案：总用料为 2 件，料理仍是饭团，蜂蜜带入「甜」标签。最终标签还需按覆盖等规则处理。
3. **将最终标签与顾客偏好匹配。** 每位顾客分别有喜爱、厌恶的标签。同名标签出现在方案中，即命中该项偏好；同一种标签只计一次。例如，图中饭团加蜂蜜对博丽灵梦命中「饱腹」「实惠」「甜」三项喜爱，没有命中厌恶，得分为 3−0=3。

| 术语 | 定义 |
| :---: | :---: |
| 食材（Ingredient） | 海苔、蜂蜜等制作材料；配方规定的用量计为基础食材，额外追加的部分计为加料。同种食材可以同时承担这两种用途。 |
| 料理（Dish） | 按配方制作的菜品，如饭团；具有自身预设标签、指定厨具和配方禁忌。 |
| 加料（Addition） | 满足基础配方后，在剩余格子中额外使用的食材，如饭团中的蜂蜜；合法加料保留所选料理，并带入食材标签。 |
| 方案（Plan） | 一次具体的制作选择：料理，以及加料的种类和数量；也允许不加料。基础食材与加料合计不超过 5 件，重复使用同种食材仍逐件占格。 |
| 标签（Tag） | 用于描述属性或制作方式的名称，如「甜」「饱腹」「料理台」；也是与顾客喜爱、厌恶进行匹配的单位。 |
| 得分（Score） | 针对指定顾客计算的“喜爱命中数 − 厌恶命中数”。它描述标签匹配情况；规划还需比较食材件数与供给，见[第一章](#zh-model)。 |

配方禁忌限制料理的制作，人物厌恶参与偏好评分。下图展示标签覆盖、禁忌冲突和流行对方案的影响，得分仅衡量标签匹配；完整游戏评价与利润在此评分范围之外。

<a id="zh-tag-figure"></a>

[![五节机制图：五格配方、喜好匹配、标签覆盖、配方禁忌与流行。蓝色表示料理标签，橙色表示食材标签，青绿色表示厨具标签，紫色表示人物喜爱，石板灰表示人物厌恶，浅红色表示配方禁忌。料理台与海苔×1仅满足饭团配方，占1格、余4格；加蜂蜜后占2格、余3格。料理标签不等于基础食材标签的并集，加料才带入标签。A、B均展示灵梦完整偏好：喜爱「高级」「饱腹」「甜」「不可思议」「实惠」「流行·喜爱」，厌恶「下酒」「昂贵」「流行·厌恶」。A：饭团加蜂蜜，命中「饱腹」「实惠」「甜」，3项喜爱减0项厌恶，得分3。B：饭团加猪肉，「肉」覆盖「素」，命中「饱腹」「实惠」，得分为2减0等于2。饭团无配方禁忌。C：蜂蜜的「甜」触发臭豆腐禁忌，其他搭配不能抵消；游戏结果为黑暗物质，Python nCookware在评分前排除。A、B、C无流行。独立流行情境中，当期触发标签随随机事件变化，人物对流行的偏好固定，程序读取输入条件；「甜」流行时，饭团加蜂蜜方案保留「甜」并获得「流行·喜爱」，对灵梦命中4项喜爱、0项厌恶，得分4。下方琪露诺喜爱「流行·厌恶」、厌恶「流行·喜爱」。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.png)

*图 1. 配方、加料与标签匹配机制。A、B、C 均无流行，末节以相同方案展示「甜」流行后的 4−0=4，再列琪露诺的流行偏好；本图为规则示意，游戏图标使用原像素。* [SVG 矢量原图](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example.svg)。标签依据[原工作簿](东方夜雀食堂.xlsx)；禁忌组合在游戏中产生黑暗物质，Python `nCookware` 在评分前排除，网页差异见[网页使用说明](docs/web-guide.md)。规则与素材来源见[第三方声明](THIRD_PARTY_NOTICES.md)。

备菜模型以方案、食材用量与标签匹配为基础，区分候选查询、规划目标和设备约束。五格与配方禁忌属于制作条件，得分门槛与无厌恶准入属于规划政策。

<a id="zh-model"></a>

## 1. 数学模型：从游戏决策到优化任务

### 1.1 通用符号与基础模型

备菜决策包含两个层次：确定一份料理的制作方案，以及在满足条件的方案之间作出选择。各版本共享食材用量与标签匹配的基本定义；候选生成规则、订单假设和优化目标分别由具体模型规定。

**对象与记号：** 令 $`g`$ 表示顾客(Guest)，$`d`$ 表示料理(Dish)，$`i`$ 表示食材(Ingredient)，$`t`$ 表示标签(Tag)，$`p`$ 表示制作方案(Plan)。

候选与偏好集合采用花体，向量采用粗体；下标标识对象，括号上标 $`(r)`$ 标识过滤阶段，正体角标标识固定类别。$`v`$ 为模型版本索引(Version)，$`\star`$ 标识按对应目标选出的最优保留方案。

| 符号 | 定义 | 单位或类型 |
| :---: | :---: | :---: |
| $`b_i(d)`$ | Base：料理配方规定的食材用量，给定参数 | 件／份 |
| $`a_i(p)`$、$`\mathbf A(p)`$ | Addition：追加食材的件数及完整加料向量，决策量 | 件／份；向量 |
| $`c_i(p)`$、$`C(p)`$ | Count：单种食材的总用量及方案的总食材件数 | 件／份 |
| $`T(i)`$、$`T(p)`$ | 食材自身的标签集合及方案的最终标签集合 | 集合 |
| $`\mathcal L_g,\mathcal D_g`$ | 顾客的喜爱、厌恶标签集合 | 集合 |
| $`H_g^{\mathrm L}(p),H_g^{\mathrm D}(p)`$ | 最终标签命中的喜爱、厌恶项数 | 项 |
| $`S_g(p),S_{\min}`$ | 方案净分、指定的最低净分 | 分 |
| $`R_{\mathrm T},E_{\mathrm T}`$ | 用户指定的必含、排除标签 | 集合 |
| $`q_i`$ | 食材的经验日供给量，来自工作簿 TDQ | 件／日 |
| $`K`$ | 每位顾客的假设日订单量；Python 规划默认取 5 | 单／日 |

**方案与制作约束：** 一份方案由所选料理与加料件数组成。基础食材和加料共同占用最多五个格子，重复使用同种食材逐件计数：

```math
\begin{gathered}
p=(d,\mathbf A),\quad \mathbf A=(a_i)_i,\quad a_i\in\mathbb Z_{\ge0},\\
c_i(p)=b_i(d)+a_i(p),\quad C(p)=\sum_i c_i(p)\le5.
\end{gathered}
```

基础食材满足配方并占用格数，其标签不自动并入料理；加料带入食材标签。$`T(p)`$ 表示当前版本依据料理、厨具、售价、加料及覆盖、流行等规则得到的最终标签集合，同名标签只保留一次。顾客对流行词条的喜恶固定，当期触发条件决定方案是否获得相应标签。配方禁忌与候选处理范围须按所用入口解释，HTML 与 Python 的具体行为见[网页使用说明](docs/web-guide.md)及[优化模型与算法边界](docs/design.md)。

**匹配与得分：** 喜爱命中数、厌恶命中数和净分定义为：

```math
\begin{gathered}
H_g^{\mathrm L}(p)=\left|T(p)\cap\mathcal L_g\right|,\\
H_g^{\mathrm D}(p)=\left|T(p)\cap\mathcal D_g\right|,\\
S_g(p)=H_g^{\mathrm L}(p)-H_g^{\mathrm D}(p)
\end{gathered}
```

净分描述方案与顾客偏好的匹配情况；是否达标、达标后如何比较，属于各版本的准入与评价政策。$`\mathrm{lex}`$ 表示词典序：先比较目标向量的第一项，只有相同时才比较下一项。

<details>
<summary>与机制图及补充文档的符号对照</summary>

| 本章记号 | 机制图及补充文档中的记号 | 含义 |
| :---: | :---: | :---: |
| $`a_i(p)`$ | $`x_i`$ | 加料件数 |
| $`C(p)`$ | $`L(p)`$ | 总食材件数 |
| $`\mathcal L_g,\mathcal D_g`$ | $`P_g,N_g`$ | 喜爱、厌恶集合 |
| $`H_g^{\mathrm L}(p),H_g^{\mathrm D}(p)`$ | $`h_g(p),a_g(p)`$ | 喜爱、厌恶命中数 |
| $`S_g(p),S_{\min}`$ | $`s_g(p),\tau`$ | 净分、最低净分 |

</details>

[![备菜决策模型流程：HTML查询达标候选；detailedPLAN按目标喜好标签配置多套方案，先最少预计日食材件数，再最大最低供给余量；singlePLAN改为每客一套方案，按喜爱命中、每份件数和供给余量比较；cover3将覆盖收益封顶为3。输出格式、固定厨具和共同厨具为独立扩展，箭头表示模型关系。](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution.png)

*图 2. 备菜决策的模型流程。主线展示决策对象、订单假设与目标顺序的变化；输出表达及两类厨具条件分别成支。箭头表示问题依赖，不表示程序调用或精确开发时间线。* [SVG 矢量原图](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution.svg).

### 1.2 HTML：定义方案、筛选候选与比较采购条件

#### 1.2.1 要解决的问题

给定一位稀客、已导入的料理与食材、当前流行条件，以及玩家指定的最低分和标签要求，网页**枚举每道料理的加料组合，筛选达标候选，再根据已启用的过滤与采购选项删减、排序。** 输出为候选方案表，每行记录一道料理及其加料种类、数量，并可为同一顾客保留多个备选方案。

网页提供以下选项：

| 网页选项 | 开启后的作用 | 作用范围 |
| :---: | :---: | :---: |
| 等价食材去重（仅加料） | 将标签相同且非空的食材归为一组，每组只枚举一个代表。 | 枚举前的加料食材池 |
| 食材高级过滤 | 删除可由指定基础加料方案替代的高级方案；对应替代方案须已在达标候选中，且不含高级加料。 | 同一道料理的达标候选 |
| 加料子集过滤 | 若已保留的达标方案中，每种加料件数均不多于当前方案，则删除当前方案。 | 同一道料理经过高级过滤后的候选 |
| 依采购推荐（按 TDQ） | 按食材有效供给值为方案排序，用 Top-N 确定保留范围，边界上的并列方案全部保留。 | 同一道料理经过前述过滤后的候选 |

两项过滤均可配合“考虑得分”：开启后，替代或子集方案的得分须不低于当前方案，才执行删除。

实际顺序为：**按料理排除禁用食材名 → 可选的等价去重 → 枚举加料 → 标签与分数准入 → 高级过滤 → 子集过滤 → 采购排名与输出。** 未启用的步骤直接跳过。

#### 1.2.2 准入条件与初始候选

**约束与判定：** 基础配方与加料总件数不超过五件；用户还可设置必含标签、排除标签和最低净分。基础配方不足五件、追加后总用料达到五件时，网页加入「大份」；料理自身已有的「大份」也会保留。

令 $`\mathcal B_d^{\mathrm{web}}`$ 为网页针对料理 $`d`$ 实际枚举的方案池；它受原配方处理及等价去重选项影响。未指定的标签条件取空集。进入后续过滤的达标候选为：

```math
\mathcal C_{g,d}^{(0)}=
\left\{p\in\mathcal B_d^{\mathrm{web}}:
S_g(p)\ge S_{\min},\quad R_{\mathrm T}\subseteq T(p),\quad E_{\mathrm T}\cap T(p)=\varnothing
\right\}
```

这是最低净分条件：门槛为 3 时，4 分、5 分仍可通过；喜爱命中也可以抵消厌恶扣分。原网页的配方处理范围与 Python 分支不同，见[网页使用说明](docs/web-guide.md)。该集合记为第 0 阶段的候选；后面的过滤只比较已通过本步的方案。

#### 1.2.3 等价去重：压缩加料食材池

**目的：** 将自身标签完全相同且非空的食材归为等价组，每组枚举一个代表，以减少重复的标签组合。等价关系仅由食材自身标签决定。

定义等价关系及等价组：

```math
i\sim j\quad\Longleftrightarrow\quad
i=j\ \lor\ \left(T(i)=T(j)\ne\varnothing\right),\qquad
E(i)=\{j:j\sim i\}
```

无标签食材各自成组，不合并为同一组。令 $`I_d`$ 为按该料理禁用食材名过滤后的加料池，则该料理可用的等价组为 $`E_d(i)=E(i)\cap I_d`$。开启去重时，每个非空组只选一个代表进入枚举池：优先采用原程序预设的代表名单，其次按中文名称顺序选择；未开启时枚举完整的 $`I_d`$。

等价去重在枚举前压缩**加料食材池**，基础配方保持原样，同一代表可重复追加。标签相同的食材即使供给量不同，也属于同一组；采购推荐阶段另行处理组内供给差异。

#### 1.2.4 食材高级过滤：比较指定的基础替代

**目的：** 在满足准入条件的前提下，优先保留由标签较少的食材构成的方案。“高级”是基于食材标签包含关系的分类，其判定仅使用标签集合。

在该料理实际用于枚举的食材池中，对食材 $`i`$ 寻找满足下式的基础替代 $`j`$：

```math
\varnothing\ne T(j)\subsetneq T(i)
```

原程序从识别出的替代项中选标签数最少者，同数量时按中文名称顺序选择，记为 $`B_d(i)`$（Base representative）；没有替代项时取 $`B_d(i)=i`$。将方案的**所有加料同时**映射到这些代表，得到基础加料向量：

```math
\begin{gathered}
a_j^{\mathrm{base}}(p)=\sum_{i:B_d(i)=j}a_i(p),\\
\mathbf A^{\mathrm{base}}(p)=(a_j^{\mathrm{base}}(p))_j,\\
p^{\mathrm{base}}=(d,\mathbf A^{\mathrm{base}}(p)).
\end{gathered}
```

当 $`\mathbf A^{\mathrm{base}}(p)\ne \mathbf A(p)`$ 时，该方案被视为含高级加料。开启高级过滤后，删除条件为：

```math
\begin{gathered}
\mathbf A^{\mathrm{base}}(p)\ne \mathbf A(p),\qquad p^{\mathrm{base}}\in\mathcal C_{g,d}^{(0)},\\
\mathbf A^{\mathrm{base}}(p^{\mathrm{base}})=\mathbf A(p^{\mathrm{base}}),\qquad
\left(F_{\mathrm U}=0\ \lor\ S_g(p^{\mathrm{base}})\ge S_g(p)\right).
\end{gathered}
```

$`F_{\mathrm U}`$ 是该过滤的“考虑得分”开关：开启为 1，关闭为 0。关闭时，只要对应的非高级基础方案也达标，就删除当前高级方案；开启时，还要求基础方案得分不低于当前方案。若基础方案未生成、未达标或不满足其他准入条件，则保留当前方案。

例如，某食材的标签为「甜」，另一食材为「甜」「高级」；只有前者被选为后者的基础代表、且整套替代方案达标时，后者方案才进入上述删除判断。比较范围限于**指定基础映射生成的整套加料替代**，基础配方保持原样。此步保留的集合记为 $`\mathcal C_{g,d}^{(1)}`$；未启用高级过滤时，它等于 $`\mathcal C_{g,d}^{(0)}`$。

#### 1.2.5 加料子集过滤：比较能否少加食材

**目的：** 若保留方案仅使用当前方案的一部分加料即可达标，则按用户政策省略更多加料的方案。比较采用食材的**件数向量**，逐项记录每种食材的追加数量：

```math
\mathbf A(p')\preceq \mathbf A(p)\quad\Longleftrightarrow\quad
\forall i,\ a_i(p')\le a_i(p)
```

输入为高级过滤之后的同料理候选 $`\mathcal C_{g,d}^{(1)}`$；先按加料件数升序、得分降序、加料名称键顺序排列。依次处理时，以 $`\mathcal K`$ 表示此前已保留的方案，当前方案的删除条件为：

```math
\exists p'\in\mathcal K:\quad
\mathbf A(p')\preceq \mathbf A(p)\quad\land\quad
\left(F_{\mathrm S}=0\ \lor\ S_g(p')\ge S_g(p)\right)
```

$`F_{\mathrm S}`$ 是子集过滤的“考虑得分”开关：关闭时，已保留的达标子集存在即可；开启时，子集得分还须不低于当前方案。未被删除的方案加入 $`\mathcal K`$，供后续比较。零加料方案若达标，也可以成为子集；实际判定包含向量相等的情形。

例如，“蜂蜜×1”是“蜂蜜×2”的加料子集，反向不成立。若两者均达标且前者已保留，关闭考虑得分时可删除后者；开启时需进一步比较净分。高级过滤比较相同件数下的食材身份替代；子集过滤比较减少既有加料用量的组合。两者均据比较结果删减候选，不改写保留方案。子集过滤后保留的集合记为 $`\mathcal C_{g,d}^{(2)}`$；未启用此项时，它等于 $`\mathcal C_{g,d}^{(1)}`$。

#### 1.2.6 采购推荐：按供给向量确定保留边界

**目的：** 在 $`\mathcal C_{g,d}^{(2)}`$ 中，优先考虑供给较充足的用料组合。此时还没有每日订单量假设，也不从供给中扣减消耗；比较在每道料理内部进行。

**有效供给值：** 沿用经验日供给量 $`q_i`$，令 $`M(i)\subseteq E(i)`$ 为程序全局分组记录中，与该食材对应且有已知供给值的成员。网页使用：

```math
\widetilde q_i=
\begin{cases}
\dfrac{1}{|M(i)|}\sum_{j\in M(i)}q_j,& |M(i)|>0,\\
q_i,& |M(i)|=0\text{ and }q_i\text{ is known},\\
0,&\text{otherwise}.
\end{cases}
```

单成员组有值时，上式就是自身供给；无组内记录时先回退到食材自身的供给记录，仍缺失才取 0。均值取自全局组，不只取该料理允许的成员；即使未开启等价去重，采购比较仍使用这一有效值。

**比较向量：** 每份方案中，每一件基础食材和加料各贡献一次有效供给值，按升序组成向量 $`\mathbf V(p)`$（Vector）：

```math
\mathbf V(p)=\mathrm{sort}_{\uparrow}
\left(\biguplus_i\{\widetilde q_i\}^{c_i(p)}\right)
```

这里 $`\biguplus`$ 表示保留重复元素的拼接，$`\{\widetilde q_i\}^{c_i(p)}`$ 表示该值重复 $`c_i(p)`$ 次。排名从最小分量开始比较，在第一个不同位置取值较大者优先；前缀相同时，将较短向量缺少的分量视为 $`+\infty`$。因此：

```math
(4,12)\succ(3,100),\qquad
(4,12)\succ(4,10),\qquad
(4)\succ(4,12)
```

该词典序规则从最低供给值开始逐项比较。原实现用 $`10^{-9}`$ 作为数值比较容差；向量并列时按加料件数、加料名称键稳定排序。

**Top-N 与并列：** 设过滤后有 $`m_{g,d}`$ 个候选，将其按上述顺序记为 $`p_1,\ldots,p_{m_{g,d}}`$，$`N\ge1`$ 为用户指定的排名阈值。为说明去重如何影响边界，定义方案权重 $`W(p)`$（Weight）：

```math
W(p)=
\begin{cases}
1,&\text{equivalence deduplication off},\\
\prod_{i:a_i(p)>0}|E_d(i)|^{a_i(p)},&\text{equivalence deduplication on}.
\end{cases}
```

无加料时空乘积为 1。边界位置记为 $`k_{\mathrm{cut}}`$，最终保留集合为：

```math
\begin{gathered}
k_{\mathrm{cut}}=\min\left\{k:\sum_{j=1}^{k}W(p_j)\ge N\right\},\\
\mathcal R_{g,d}=\{p_j:\mathbf V(p_j)\succeq \mathbf V(p_{k_{\mathrm{cut}}})\}
\end{gathered}
```

若累计权重不足 $`N`$，取 $`k_{\mathrm{cut}}=m_{g,d}`$；无候选时输出为空。未去重时，边界就是第 $`\min(N,m_{g,d})`$ 个方案；去重时按该料理可用等价组大小累积权重。**Top-N 的截点由累计方案权重确定，再保留供给向量不低于该截点的全部候选，包括所有并列项。最终输出行数由截点和并列情况共同决定。**

权重用于补偿等价去重对排名截点的影响，其乘积计算与无序方案计数存在差异。例如，同一两成员组重复追加两件时，权重为 $`2^2=4`$，而无序组合实际只有三种。因此，该权重不是去重前方案数的精确还原，开关去重前后的 Top-N 结果也未建立严格等价关系。

**输出名称：** 同时开启采购推荐与等价去重时，最终显示的加料还会替换为全局等价组中已知原始供给量最大的成员：

```math
i_{\mathrm{out}}\in\arg\max_{j\in M(i)}q_j
```

没有已知供给值时保留当前代表，并列按代表优先级与名称顺序处理。**排名采用组均值，输出名称采用组内最大值**，基础配方不替换。该输出步骤按全局组选择，未再次按料理禁用名单检查；使用条件见[网页使用说明](docs/web-guide.md)。

未启用采购推荐时，保留全部 $`\mathcal C_{g,d}^{(2)}`$。按输出名称替换前的方案表示，各过滤阶段满足：

```math
\mathcal C_{g,d}^{(0)}\supseteq\mathcal C_{g,d}^{(1)}\supseteq\mathcal C_{g,d}^{(2)}\supseteq\mathcal R_{g,d}
```

等价去重先压缩食材池，上述集合关系再描述枚举后的候选删减。HTML 模型由此包含**准入条件、两种方案删减政策、食材等价近似与采购排序**，输出满足用户条件的备选方案。后续 Python 版本在各自候选范围内引入自动选定方案的优化目标。

### 1.3 detailedPLAN：为各目标标签选择多套方案

**问题与变化：** `detailedPLAN.py` 将任务从返回候选推进为自动选定一组方案：针对一位顾客的每个可行目标喜好标签，分别准备应对方案。评价顺序改为**预计食材件数最少，其次最低供给余量最大**。

**约束与假设：** Python PLAN 在评分准入中增加“无厌恶命中”条件，因此沿用上一节的净分门槛即可得到：

```math
H_g^{\mathrm D}(p)=0,\qquad S_g(p)\ge S_{\min}
\quad\Longrightarrow\quad H_g^{\mathrm L}(p)\ge S_{\min}
```

配方禁忌、持有料理及候选规约按对应 Python 版本执行。各版本的候选集合分别由自身处理规则定义，HTML 与 Python 候选之间未规定包含关系。

**新增决策与订单假设：** 对目标标签 $`t\in \mathcal L_g`$，令 $`\mathcal C_{g,t}`$ 为包含该标签、通过准入，并按原程序逐料理、逐目标标签应用升级／子集过滤后汇集的候选。定义：

```math
J_g=\left\{t\in \mathcal L_g:\mathcal C_{g,t}\ne\varnothing\right\},\qquad
m_g=|J_g|,\qquad p_t\in\mathcal C_{g,t}\quad(t\in J_g)
```

决策为方案族 $`(p_t)_{t\in J_g}`$，同一方案可被多个标签选中。$`m_g`$ 按有候选的目标标签计数。沿用假设日订单量 $`K`$，并假设订单在这些目标标签间均分，每类承担 $`K/m_g`$ 单。若 $`m_g=0`$，不生成规划。

沿用 $`c_i(p)`$ 和原始日供给 $`q_i`$，令 $`u_i`$ 为各标签所选方案对食材的累计用量。预期日食材件数 $`E_{\mathrm{old}}`$ 与最低供给余量 $`R_{\mathrm{old}}`$ 为：

```math
\begin{gathered}
u_i=\sum_{t\in J_g}c_i(p_t),\\
E_{\mathrm{old}}=\frac{K}{m_g}\sum_i u_i,\\
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m_g}u_i\right)
\end{gathered}
```

后二者单位均为件／日。模型从日供给中扣除假设订单对应的食材消耗，以计算余量；订单均分属于建模假设，尚无对应的实测订单概率估计。

**目标函数：**

```math
\min_{\substack{p_t\in\mathcal C_{g,t}\\t\in J_g}}^{\mathrm{lex}}
\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

固定 $`m_g`$ 后，最少预期件数可按标签拆分，因此程序先保留每个标签全部并列最少件数候选，再比较组合的供给压力。最低余量相同时，继续比较完整的升序余量向量。旧分支的阈值二分与 DFS 用于这一组合求解；它们属于求解方法，目标仍是上式。

### 1.4 singlePLAN：将每标签方案改为每客一个方案

**问题与变化：** `singlePLAN.py` 将决策从方案族 $`(p_t)_{t\in J_g}`$ 改为单个 $`p`$：同一位顾客的全部假设订单采用这一套方案。同时，目标顺序改为**喜爱命中最多，其次食材件数最少，最后最低供给余量最大**。

**约束与假设：** 保留制作条件、净分门槛和无厌恶准入；决策变量改为一套方案 $`p`$，同一顾客的 $`K`$ 单全部使用它。

**用量与余量：** 同一方案承担该顾客的全部假设日订单，食材需求与余量为：

```math
\begin{gathered}
\frac{K}{m_g}\sum_{t\in J_g}c_i(p_t)
\quad\longrightarrow\quad Kc_i(p),\\
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
\end{gathered}
```

$`R(p)`$ 的单位仍为件／日。$`K`$ 固定时，最小化每份件数 $`C(p)`$ 等价于最小化该客人的日件数 $`KC(p)`$；原实现直接比较每份件数。

**目标函数：** 令 $`\mathcal C_g^{\mathrm{single}}`$ 表示该版本生成并保留的合格候选：

```math
\max_{p\in\mathcal C_g^{\mathrm{single}}}^{\mathrm{lex}}
\left(H_g^{\mathrm L}(p),\;-C(p),\;R(p)\right)
```

这一步同时改变了订单分配方式与第一优先级。此前先控制一组方案的预计消耗；现在先追求单份方案的更多喜爱命中，再在同覆盖下节约食材、缓解供给压力。三项均相同时，原程序依次用售价、料理名和加料字符串处理平局。

### 1.5 cover3：保留单方案，将喜好收益封顶为 3

**问题与变化：** `singlePLAN_cover3.py` 保留每客一套方案、全部订单复用以及同一余量计算，只调整第一目标：三项喜爱已经足够，额外命中不再提高优化优先级。

**约束与假设：** 沿用单客单方案、无厌恶准入、最低净分及假设订单量。覆盖收益封顶用于合格方案之间的排序，准入门槛保持原设定。

**新增效用与目标函数：** 以 $`U(h)`$ 表示命中数为 $`h`$ 时用于方案比较的覆盖收益（Utility），候选集合相应记为 $`\mathcal C_g^{\mathrm{cover3}}`$：

```math
\begin{gathered}
U(h)=\min(h,3),\\
\left(H_g^{\mathrm L}(p),-C(p),R(p)\right)
\quad\longrightarrow\quad
\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right)
\end{gathered}
```

```math
\max_{p\in\mathcal C_g^{\mathrm{cover3}}}^{\mathrm{lex}}
\left(U(H_g^{\mathrm L}(p)),\;-C(p),\;R(p)\right)
```

最终标签 $`T(p)`$、命中数 $`H_g^{\mathrm L}(p)`$ 和原始净分 $`S_g(p)`$ 沿用此前定义，封顶函数仅计算用于排序的收益。图 1 中「甜」流行时，饭团加蜂蜜对灵梦的原始得分为 4，而 $`U(4)=3`$。

门槛 $`S_{\min}`$ 控制能否进入候选，封顶函数 $`U`$ 控制进入后如何比较。在默认 $`S_{\min}=3`$ 且无厌恶的条件下，合格候选均有 $`U=3`$，因此该版本实际表达为：**先达标，再省料，再考虑供给余量**。准入门槛与收益上限独立设定，降低门槛时仍沿用原收益上限。

### 1.6 输出格式分支：mixedingredients

**问题与变化：** `singlePLAN_cover3_mixedingredients.py` 调整结果的阅读和使用方式，将基础食材与加料合写为 `Ingredient1` 至 `Ingredient5`，按原输出约定排列并保留表格合并。

该分支沿用 1.5 节的决策变量、目标及标签形成规则，仅合并展示基础与追加用量。$`p,c_i(p),C(p),T(p),H_g^{\mathrm L}(p),S_g(p),R(p),U(H_g^{\mathrm L}(p))`$ 的含义和计算保持原样，基础食材仍用于满足配方，加料带入食材标签。

### 1.7 固定厨具分支：limitedCookware

**问题与变化：** `singlePLAN_cover3_mixIng_limitedCookware.py` 在既定设备条件下为各客人选方案：由玩家指定排除哪些厨具，目标仍沿用 cover3。原文件默认排除烧烤架、蒸锅。

**约束与决策：** 令 $`\kappa(d)`$ 表示料理所需厨具，$`S_0`$ 表示排除指定设备后可用的厨具集合。以 $`v`$ 表示当前设备模型的版本，$`\mathcal C_g^v`$ 为该版本应用设备集合限制前的合格候选；定义限制操作：

```math
\mathcal C_g^v(S)=
\left\{p=(d,\mathbf A)\in\mathcal C_g^v:\kappa(d)\in S\right\}
```

本节取 $`v=\mathrm{limited}`$、$`S=S_0`$，在此子集中按 1.5 节的目标比较。$`S_0`$ 作为固定输入限定候选范围，形成独立于输出格式调整的设备约束分支。

### 1.8 共同厨具分支：nCookware

**问题与变化：** `singlePLAN_cover3_mixIng_nCookware.py` 将设备集合本身纳入决策：给定可用厨具数量，程序选择具体设备，并为各顾客配置一套可用方案。该分支与 `limitedCookware` 分别从输入数据出发，处理共同选择设备与固定排除设备两类配置任务。

**约束与决策：** 令 $`G`$ 为本次规划的顾客集合，$`H`$ 为已拥有料理对应的可用厨具集合，$`n`$ 为本次采用的厨具种类数。设备集合从固定 $`S_0`$ 改为待选择的 $`S`$：

```math
S\subseteq H,\qquad |S|=n
```

沿用 1.7 节的限制操作，此时 $`v=\mathrm{nCookware}`$。对给定 $`S`$，令 $`p_g^\star(S)`$ 为从 $`\mathcal C_g^v(S)`$ 中按 cover3 目标选出的方案；有方案的顾客构成 $`G_S`$，无方案人数为 $`z_S=|G\setminus G_S|`$。

**集合层目标：** 单客的评价顺序保留；新增外层比较，将各客评价汇总，并计入原程序的无解惩罚：

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\begin{gathered}
\sum_{g\in G_S}U(H_g^{\mathrm L}(p_g^\star(S))),\\
-\left[\sum_{g\in G_S}C(p_g^\star(S))+10^9z_S\right],\\
\sum_{g\in G_S}R(p_g^\star(S))-10^{18}z_S
\end{gathered}
\right)
```

在默认三分准入条件下，每位有方案的客人贡献 3 点封顶收益，第一项因而优先增加得到达标方案的客人数，再比较总用料与逐客余量。两项惩罚常数沿用原实现，用于评价存在无解客人的设备配置；这类配置仍可参与比较。

厨具集合在顾客之间共同选择，$`R(p)`$ 按每位顾客的假设订单独立计算。该模型未设置将所有顾客消耗合并扣减的共享库存约束。程序先复用每客每厨具的最佳保留候选，再枚举设备组合；旧多方案分支则在单客内部按标签均分订单并求解方案组合。

### 1.9 版本关系与适用范围

这条主线保留 1 个 HTML 和 6 个 PLAN 文件。目标依次由达标候选查询、多标签方案组合、单客覆盖优先，发展到三项封顶与共同厨具配置；其中 `mixedingredients` 改变输出表达，`limitedCookware` 改变给定约束。基础得分、利润、普客及酒水分析是独立辅助支线。

以上数学记号贯穿各版本，候选集合由对应版本的规则确定。标签等价代表与中性补位截断限制了实际搜索范围，因此最优性结论限定于保留候选，尚无覆盖全部合法食材组合的全局最优性证明。供给余量作为允许负值的排序指标使用，模型未设库存或顾客预算硬约束；售价参与平局处理，利润属于独立分析支线。各阶段的取舍依据见第 2 章，候选规约与求解细节见[优化模型与算法边界](docs/design.md)。

<a id="zh-evolution"></a>
<a id="zh-data"></a>

## 2. 数据与建模依据

### 2.1 数据来源与质量

根目录工作簿共 13 张表。按 `nCookware` 的解析口径，其中包含 62 条食材记录、164 道料理记录和 58 位稀客；163 道料理标记为持有。

| 数据类别 | 来源 | 用途 |
| :---: | :---: | :---: |
| 配方、厨具、标签与人物偏好 | 历史工作簿；标签资料来自 AnYiEE 的项目 | 确定配方与标签匹配规则 |
| 价格、日供给与委托记录 | 作者在游戏中手工记录，并整理经验期望 | 日供给用于资源评价；价格用于独立经济分析 |
| 流行、持有料理与厨具条件 | 工作簿记录及运行时输入 | 定义本次查询或规划的情境 |

`Total Daily Quantity` 对应第一章的给定供给参数 $`q_i`$。独立价格分析采用数量加权口径：对食材 $`i`$，令 $`\mathcal O_i`$ 为纳入计算的渠道记录集合，$`\pi_{i\ell}`$ 为记录 $`\ell`$ 的单位采购价，$`w_{i\ell}`$ 为对应数量，则：

```math
\bar\pi_i=
\frac{\sum_{\ell\in\mathcal O_i}w_{i\ell}\pi_{i\ell}}
{\sum_{\ell\in\mathcal O_i}w_{i\ell}},
\qquad \sum_{\ell\in\mathcal O_i}w_{i\ell}>0.
```

$`\pi_{i\ell}`$ 与 $`\bar\pi_i`$ 的单位为游戏货币／件，$`w_{i\ell}`$ 的单位为件；价格和数量须对应同一来源范围。若委托数量计入分母且无对应现金支出，该部分在此口径下计为零现金采购成本。该口径未计入时间与机会成本。

完整采样日期、次数和来源版本未留存，采购价公式还存在按行关联错位及部分错误缓存的风险。现有数据用于描述历史经验条件，尚不足以估计可靠的需求分布、置信区间或缺货概率。字段与估计口径见[数据来源说明](docs/data-provenance.md)。

### 2.2 建模选择的依据

早期需求包含按实际利润排序。后续 PLAN 主线围绕喜好满足、食材消耗和供给压力建立评价，价格与利润保留为独立分析支线；历史需求与取舍过程见[需求与设计决策演进](docs/prompt-journey.md)。

| 选择 | 依据与适用条件 |
| :---: | :---: |
| 食材件数与供给分别计量 | 件数对应制作中的实际用量；同件数食材的采购金额与取得难度可能不同，因此另用日供给评价资源压力。 |
| 覆盖封顶与明确优先级 | 表达达到目标偏好后节约用料的备菜需求。封顶值与比较顺序由项目需求设定，其对其他备菜偏好的适用性仍待验证。 |
| 每客日订单默认 5 | 用于将单份用量换算为日需求，属于情境假设；现有记录缺少实测订单概率，历史模型的订单均分也基于假设。 |

PLAN 主线聚焦料理与加料，酒水、完整满意度和现金利润尚未联合建模；顾客预算为展示字段。各版本的决策量、目标变化及候选范围见第一章。

<a id="zh-algorithms"></a>

## 3. 求解算法与计算优化

程序在第一章定义的候选范围内执行枚举、剪枝和目标比较。本章区分给定食材池上的完整枚举、候选生成前的规约，以及保留候选上的精确比较。以下采用基础配方使用 1–5 件食材、供给值有限的正常数据条件。

### 3.1 给定食材池的组合枚举

对顾客 $`g`$ 和料理 $`d`$，令实际枚举食材池为 $`(i_1,\ldots,i_{n_{g,d}})`$，$`n_{g,d}`$ 为池大小。基础配方使用 1–5 件食材，剩余格数为 $`s_d`$。追加 $`k`$ 件时，DFS 按非递减索引选择食材，允许重复同一种食材，并使每个多重集只生成一次。剪枝前的组合数为：

```math
\begin{gathered}
s_d=5-\sum_i b_i(d),\qquad 0\le k\le s_d,\\
1\le j_1\le\cdots\le j_k\le n_{g,d}\quad(k\ge1),\\
N_{g,d}=\sum_{k=0}^{s_d}\binom{n_{g,d}+k-1}{k}
=\binom{n_{g,d}+s_d}{s_d}\quad(n_{g,d}\ge1).
\end{gathered}
```

空池只可能生成零加料组合。网页在必含标签指定「大份」且料理原标签未含「大份」时，将枚举限制为 $`k=s_d`$。网页按料理静态分块，最多使用 8 个 Web Worker 并行；各 Python 入口使用 CPU 求解。上述计数针对筛选、去重后的池，实际输出还受准入与后续过滤影响。


#### 标签集合的位集求值

网页 Worker 的枚举保持原有顺序，标签判定使用预编译位集。令 $`\mathcal T`$ 为本次计算涉及的全部规范化标签，为每个标签分配唯一位置。任意标签集合 $`X\subseteq\mathcal T`$ 对应指示向量：

```math
\begin{gathered}
\mathbf z(X)=\left(\mathbf 1_{\{t_j\in X\}}\right)_{j=1}^{|\mathcal T|},\\
\mathbf z(X\cup Y)=\mathbf z(X)\lor\mathbf z(Y),\qquad
\mathbf z(X\cap Y)=\mathbf z(X)\land\mathbf z(Y),\\
H_g^{\mathrm L}(p)=\sum_j z_j(T(p))z_j(\mathcal L_g),\qquad
H_g^{\mathrm D}(p)=\sum_j z_j(T(p))z_j(\mathcal D_g).
\end{gathered}
```

其中 $`\mathbf 1`$ 为事件指示量，$`\lor`$ 与 $`\land`$ 表示逐位或、与运算。实现以 32 位字数组保存这些向量，长度随标签数量增长；位计数给出交集大小。料理固定标签与食材位集预先构建。每个组合先求并集，在满足加料凑满五件的条件时补入「大份」，再依次执行四组覆盖、流行喜爱附加、流行厌恶附加、必含／排除判定及净分计算。

仅对达标组合构造用于展示的标签集合与候选对象，并保留原标签插入顺序和中文排序规则。高级过滤、子集过滤、采购向量与 Top-N 并列处理仍接收相同顺序的候选。主线程另缓存每行的检索文本，避免每次搜索重复拼接字符串。

<details>
<summary><strong>点击展开旧版全文 — v1.0.0 · Initial Release</strong></summary>

### 3.1 给定食材池的组合枚举

对顾客 $`g`$ 和料理 $`d`$，令实际枚举食材池为 $`(i_1,\ldots,i_{n_{g,d}})`$，$`n_{g,d}`$ 为池大小。基础配方使用 1–5 件食材，剩余格数为 $`s_d`$。追加 $`k`$ 件时，DFS 按非递减索引选择食材，允许重复同一种食材，并使每个多重集只生成一次。剪枝前的组合数为：

<div align="center">

$`\displaystyle \begin{gathered} s_d=5-\sum_i b_i(d),\qquad 0\le k\le s_d,\\ 1\le j_1\le\cdots\le j_k\le n_{g,d}\quad(k\ge1),\\ N_{g,d}=\sum_{k=0}^{s_d}\binom{n_{g,d}+k-1}{k} =\binom{n_{g,d}+s_d}{s_d}\quad(n_{g,d}\ge1). \end{gathered}`$

</div>

空池只可能生成零加料组合。网页在必含标签指定「大份」且料理原标签未含「大份」时，将枚举限制为 $`k=s_d`$。网页按料理静态分块，最多使用 8 个 Web Worker 并行；各 Python 入口使用 CPU 求解。上述计数针对筛选、去重后的池，实际输出还受准入与后续过滤影响。

</details>

### 3.2 Python DFS 的喜爱命中估计

原 Python 在搜索中估计剩余格子能带来的喜爱命中，提前终止估计值不足的分支。令 $`T_0(d)`$ 为料理、厨具和售价产生、尚未应用覆盖与流行规则的标签；$`\delta_\ell`$ 为第 $`\ell`$ 种食材的直接喜爱标签数，$`\Delta_j`$ 为从索引 $`j`$ 开始的最大增量：

```math
\begin{gathered}
\beta_{g,d}=|T_0(d)\cap\mathcal L_g|
+\eta_{\mathrm{large}}+\eta_{\mathrm L}+\eta_{\mathrm D},\\
\delta_\ell=|T(i_\ell)\cap\mathcal L_g|,\qquad
\Delta_j=\max_{\ell\ge j}\delta_\ell.
\end{gathered}
```

空后缀取 $`\Delta_{n_{g,d}+1}=0`$。三个 $`\eta`$ 均在相应条件满足时取 1，否则取 0：大份项要求顾客喜爱「大份」且有剩余格子；两个流行项分别要求顾客喜爱相应流行词条，且基础标签或枚举食材的直接标签能命中其锚点。状态 $`(j,r,\gamma)`$ 记录下一件的最小索引、还需选择的件数及累计估计；初始 $`\gamma=\beta_{g,d}`$，选择 $`\ell\ge j`$ 后转为 $`(\ell,r-1,\gamma+\delta_\ell)`$。

```math
B(j,r,\gamma)=\gamma+r\Delta_j,\qquad
B(j,r,\gamma) < S_{\min}\ \Longrightarrow\ \text{prune}.
```

料理级预检使用 $`\beta_{g,d}+s_d\Delta_1`$。该估计重复累计喜爱标签并忽略厌恶扣分；在所有可能新增喜爱均被初始项与增量覆盖时，它构成安全上界。原实现的流行可达性检查仅看直接标签，可能漏计凑满五件生成「大份」后触发的流行。相关食材筛选和最多三种中性补位也限制候选范围。叶节点仍须重新计算最终标签并检查厌恶与最低分，边界见[优化模型与算法边界](docs/design.md)。


#### 封顶收益下的食材件数界限

`cover3` 的第一目标至多为 3。设 $`q`$ 为已通过准入的当前方案，沿用本章最大化方向的目标向量 $`\mathbf f_g`$。若其收益已封顶，任何用料更多的方案都无法在词典序比较中胜出：

```math
U(H_g^{\mathrm L}(q))=3,\quad C(p)>C(q)
\quad\Longrightarrow\quad
\mathbf f_g(q)>_{\mathrm{lex}}\mathbf f_g(p).
```

搜索据此保留 $`C(p)\le C(q)`$ 的分支。相同件数的候选仍完整比较最低供给余量、售价、料理名和加料字符串，浮点比较规则保持原样。这一界限减少搜索访问量，候选的可行性定义与目标函数沿用第一章。

界限应用于两个层次：

1. **料理之间：** `nCookware` 的正常流程为每种厨具维护当前最佳方案；其他 `cover3` 入口及回退流程使用当前单客最佳方案。达到封顶收益后，以该方案的总件数限制后续料理的加料层数。
2. **同一道料理内部：** 按加料件数递增枚举。某一层出现封顶方案时，完整枚举该层，再停止访问更大件数层；保留候选随后按完整目标比较。低于封顶收益的方案不触发这一停止条件。

此优化用于四个 `singlePLAN_cover3*` 入口。默认候选池函数仍可返回完整原候选池；未封顶的 `singlePLAN` 和历史 `detailedPLAN` 保留各自搜索方式。针对重复料理名或含多重集键分隔符的食材名，程序沿用不加此界限的枚举，以保留既有缓存行为。Python 仍以 CPU 串行执行；该界限无需 GPU 或多进程。

<details>
<summary><strong>点击展开旧版全文 — v1.0.0 · Initial Release</strong></summary>

### 3.2 Python DFS 的喜爱命中估计

原 Python 在搜索中估计剩余格子能带来的喜爱命中，提前终止估计值不足的分支。令 $`T_0(d)`$ 为料理、厨具和售价产生、尚未应用覆盖与流行规则的标签；$`\delta_\ell`$ 为第 $`\ell`$ 种食材的直接喜爱标签数，$`\Delta_j`$ 为从索引 $`j`$ 开始的最大增量：

<div align="center">

$`\displaystyle \begin{gathered} \beta_{g,d}=|T_0(d)\cap\mathcal L_g| +\eta_{\mathrm{large}}+\eta_{\mathrm L}+\eta_{\mathrm D},\\ \delta_\ell=|T(i_\ell)\cap\mathcal L_g|,\qquad \Delta_j=\max_{\ell\ge j}\delta_\ell. \end{gathered}`$

</div>

空后缀取 $`\Delta_{n_{g,d}+1}=0`$。三个 $`\eta`$ 均在相应条件满足时取 1，否则取 0：大份项要求顾客喜爱「大份」且有剩余格子；两个流行项分别要求顾客喜爱相应流行词条，且基础标签或枚举食材的直接标签能命中其锚点。状态 $`(j,r,\gamma)`$ 记录下一件的最小索引、还需选择的件数及累计估计；初始 $`\gamma=\beta_{g,d}`$，选择 $`\ell\ge j`$ 后转为 $`(\ell,r-1,\gamma+\delta_\ell)`$。

<div align="center">

$`\displaystyle B(j,r,\gamma)=\gamma+r\Delta_j,\qquad B(j,r,\gamma) < S_{\min}\ \Longrightarrow\ \text{prune}.`$

</div>

料理级预检使用 $`\beta_{g,d}+s_d\Delta_1`$。该估计重复累计喜爱标签并忽略厌恶扣分；在所有可能新增喜爱均被初始项与增量覆盖时，它构成安全上界。原实现的流行可达性检查仅看直接标签，可能漏计凑满五件生成「大份」后触发的流行。相关食材筛选和最多三种中性补位也限制候选范围。叶节点仍须重新计算最终标签并检查厌恶与最低分，边界见[优化模型与算法边界](docs/design.md)。

</details>

### 3.3 单客候选的支配过滤与词典序选择

单客 `plan_for_guest` 缓存已生成候选的评价值，维护非支配前沿，并从中确定最佳方案。将三个目标统一写成最大化方向，候选 $`a`$ 支配 $`b`$ 的条件为：

```math
\begin{gathered}
\mathbf f_g(p)=\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right),\\
f_{g,j}(a)\ge f_{g,j}(b)\quad(j=1,2,3),\qquad
\exists j:\ f_{g,j}(a)>f_{g,j}(b).
\end{gathered}
```

其中 $`f_{g,j}`$ 为目标向量的第 $`j`$ 个分量。被支配者的词典序目标必然较差，因而可在保留候选内删除。未封顶的 `singlePLAN` 用 $`H_g^{\mathrm L}(p)`$ 替代 $`U(H_g^{\mathrm L}(p))`$。记 $`\mathrm{best}_g(\mathcal P)`$ 为从非空候选集 $`\mathcal P`$ 中按 $`\mathbf f_g`$ 选取方案的函数；三项全同后，依次采用售价降序、料理名升序、加料字符串升序的平局规则。`nCookware` 的正常路径直接扫描每厨具候选并保留 best，不构建该 Pareto 前沿。

<details>
<summary><strong>点击展开旧版全文 — v1.0.0 · Initial Release</strong></summary>

### 3.3 单客候选的支配过滤与词典序选择

单客 `plan_for_guest` 缓存已生成候选的评价值，维护非支配前沿，并从中确定最佳方案。将三个目标统一写成最大化方向，候选 $`a`$ 支配 $`b`$ 的条件为：

<div align="center">

$`\displaystyle \begin{gathered} \mathbf f_g(p)=\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right),\\ f_{g,j}(a)\ge f_{g,j}(b)\quad(j=1,2,3),\qquad \exists j:\ f_{g,j}(a)>f_{g,j}(b). \end{gathered}`$

</div>

其中 $`f_{g,j}`$ 为目标向量的第 $`j`$ 个分量。被支配者的词典序目标必然较差，因而可在保留候选内删除。未封顶的 `singlePLAN` 用 $`H_g^{\mathrm L}(p)`$ 替代 $`U(H_g^{\mathrm L}(p))`$。记 $`\mathrm{best}_g(\mathcal P)`$ 为从非空候选集 $`\mathcal P`$ 中按 $`\mathbf f_g`$ 选取方案的函数；三项全同后，依次采用售价降序、料理名升序、加料字符串升序的平局规则。`nCookware` 的正常路径直接扫描每厨具候选并保留 best，不构建该 Pareto 前沿。

</details>

### 3.4 历史多方案的阈值搜索与状态复用

`detailedPLAN` 需要为每个目标标签选择方案。固定 $`J_g`$、$`m_g>0`$ 与 $`K>0`$，令每标签订单份额 $`\alpha=K/m_g`$。每个标签从 $`\mathcal C_{g,t}`$ 中选择一个方案。由于第一目标按标签相加，可先保留各标签全部并列最少件数候选：

```math
\begin{gathered}
\mathcal M_{g,t}=\left\{p\in\mathcal C_{g,t}:C(p)=\min_{p'\in\mathcal C_{g,t}}C(p')\right\},\\
\min E_{\mathrm{old}}=\alpha\sum_{t\in J_g}\min_{p\in\mathcal C_{g,t}}C(p).
\end{gathered}
```

程序进一步合并总用量向量相同的候选。并列件数但用料不同的方案继续参与组合，因为它们对供给余量的影响不同。令 $`\lambda`$ 为最低日供给余量阈值（件／日），$`F_g(\lambda)\in\{0,1\}`$ 为可行指示量：从每个 $`\mathcal M_{g,t}`$ 选取一个方案，若存在组合使最低余量达到阈值，则取 1，否则取 0。利用用量的整数性，有限阈值条件可转换为容量上界：

```math
\begin{gathered}
u_i^{\max}(\lambda)=\left\lfloor\frac{q_i-\lambda}{\alpha}\right\rfloor,\\
R_{\mathrm{old}}\ge\lambda\ \Longleftrightarrow
\forall i,\ u_i=0\ \lor\ u_i\le u_i^{\max}(\lambda).
\end{gathered}
```

容量仅约束实际使用的食材。降低 $`\lambda`$ 会放宽所有容量，因此 $`\lambda_1\le\lambda_2`$ 时有 $`F_g(\lambda_2)=1\Rightarrow F_g(\lambda_1)=1`$。令 $`\mathcal I_g`$ 为保留候选可能使用的食材集合；每份至多五件使 $`u_i\le5m_g`$，故最低余量可在有限网格上搜索：

```math
\begin{gathered}
\Lambda_g=\{-\infty\}\cup\{q_i-\alpha u:i\in\mathcal I_g,\ u=0,\ldots,5m_g\},\\
\lambda^\star=\max\{\lambda\in\Lambda_g:F_g(\lambda)=1\}.
\end{gathered}
```

外层二分定位最高可行阈值。源码将网格值舍入到小数点后 10 位，并以 $`\lfloor(q_i-\lambda)/\alpha+10^{-12}\rfloor`$ 计算容量；$`-\infty`$ 为无容量限制的哨兵。上述等价推导采用精确算术，原实现的边界判定还受这些浮点处理影响。

每次阈值测试先删除单份即超容量的候选，再按候选数从少到多将 $`J_g`$ 中的标签排序为 $`t_1,\ldots,t_{m_g}`$。DFS 状态 $`(r,\mathbf u)`$ 表示已处理前 $`r`$ 个标签及其累计用量；记 $`\mathbf c(p)=(c_i(p))_i`$，选择下一标签方案后的转移为：

```math
(r,\mathbf u)\longrightarrow(r+1,\mathbf u+\mathbf c(p)).
```

任一已用食材超容量即剪枝；非负用量保证后续选择无法消除超额。相同状态具有相同的剩余问题，程序缓存其可行性；不同阈值分别建立缓存。二分减少阈值测试次数，单次判定仍包含组合搜索。

找到 $`\lambda^\star`$ 后，程序在其容量下进一步最大化实际使用食材的完整升序余量向量。令 $`\boldsymbol\Phi(r,\mathbf u)`$ 为该状态可达到的最佳终态向量；无可行后继时标记无解。以下最大值仅遍历满足容量的转移：

```math
\begin{gathered}
\boldsymbol\rho(\mathbf u)=\mathrm{sort}_{\uparrow}\big((q_i-\alpha u_i)_{i:u_i>0}\big),\\
\boldsymbol\Phi(m_g,\mathbf u)=\boldsymbol\rho(\mathbf u),\\
\boldsymbol\Phi(r,\mathbf u)=\max_{p\in\mathcal M_{g,t_{r+1}}}^{\mathrm{lex}}
\boldsymbol\Phi(r+1,\mathbf u+\mathbf c(p)).
\end{gathered}
```

每种实际使用的食材贡献一个分量。程序缓存最佳向量，再按固定候选顺序重建首个达到该向量的组合。变长向量按 Python 元组规则比较：首个不同分量较大者优先，完整前缀相同时较长者优先。缓存状态仍可能大量增长；该历史路线的阈值搜索未被 `nCookware` 正常主流程调用。

<details>
<summary><strong>点击展开旧版全文 — v1.0.0 · Initial Release</strong></summary>

### 3.4 历史多方案的阈值搜索与状态复用

`detailedPLAN` 需要为每个目标标签选择方案。固定 $`J_g`$、$`m_g>0`$ 与 $`K>0`$，令每标签订单份额 $`\alpha=K/m_g`$。每个标签从 $`\mathcal C_{g,t}`$ 中选择一个方案。由于第一目标按标签相加，可先保留各标签全部并列最少件数候选：

<div align="center">

$`\displaystyle \begin{gathered} \mathcal M_{g,t}=\left\{p\in\mathcal C_{g,t}:C(p)=\min_{p'\in\mathcal C_{g,t}}C(p')\right\},\\ \min E_{\mathrm{old}}=\alpha\sum_{t\in J_g}\min_{p\in\mathcal C_{g,t}}C(p). \end{gathered}`$

</div>

程序进一步合并总用量向量相同的候选。并列件数但用料不同的方案继续参与组合，因为它们对供给余量的影响不同。令 $`\lambda`$ 为最低日供给余量阈值（件／日），$`F_g(\lambda)\in\{0,1\}`$ 为可行指示量：从每个 $`\mathcal M_{g,t}`$ 选取一个方案，若存在组合使最低余量达到阈值，则取 1，否则取 0。利用用量的整数性，有限阈值条件可转换为容量上界：

<div align="center">

$`\displaystyle \begin{gathered} u_i^{\max}(\lambda)=\left\lfloor\frac{q_i-\lambda}{\alpha}\right\rfloor,\\ R_{\mathrm{old}}\ge\lambda\ \Longleftrightarrow \forall i,\ u_i=0\ \lor\ u_i\le u_i^{\max}(\lambda). \end{gathered}`$

</div>

容量仅约束实际使用的食材。降低 $`\lambda`$ 会放宽所有容量，因此 $`\lambda_1\le\lambda_2`$ 时有 $`F_g(\lambda_2)=1\Rightarrow F_g(\lambda_1)=1`$。令 $`\mathcal I_g`$ 为保留候选可能使用的食材集合；每份至多五件使 $`u_i\le5m_g`$，故最低余量可在有限网格上搜索：

<div align="center">

$`\displaystyle \begin{gathered} \Lambda_g=\{-\infty\}\cup\{q_i-\alpha u:i\in\mathcal I_g,\ u=0,\ldots,5m_g\},\\ \lambda^\star=\max\{\lambda\in\Lambda_g:F_g(\lambda)=1\}. \end{gathered}`$

</div>

外层二分定位最高可行阈值。源码将网格值舍入到小数点后 10 位，并以 $`\lfloor(q_i-\lambda)/\alpha+10^{-12}\rfloor`$ 计算容量；$`-\infty`$ 为无容量限制的哨兵。上述等价推导采用精确算术，原实现的边界判定还受这些浮点处理影响。

每次阈值测试先删除单份即超容量的候选，再按候选数从少到多将 $`J_g`$ 中的标签排序为 $`t_1,\ldots,t_{m_g}`$。DFS 状态 $`(r,\mathbf u)`$ 表示已处理前 $`r`$ 个标签及其累计用量；记 $`\mathbf c(p)=(c_i(p))_i`$，选择下一标签方案后的转移为：

<div align="center">

$`\displaystyle (r,\mathbf u)\longrightarrow(r+1,\mathbf u+\mathbf c(p)).`$

</div>

任一已用食材超容量即剪枝；非负用量保证后续选择无法消除超额。相同状态具有相同的剩余问题，程序缓存其可行性；不同阈值分别建立缓存。二分减少阈值测试次数，单次判定仍包含组合搜索。

找到 $`\lambda^\star`$ 后，程序在其容量下进一步最大化实际使用食材的完整升序余量向量。令 $`\boldsymbol\Phi(r,\mathbf u)`$ 为该状态可达到的最佳终态向量；无可行后继时标记无解。以下最大值仅遍历满足容量的转移：

<div align="center">

$`\displaystyle \begin{gathered} \boldsymbol\rho(\mathbf u)=\mathrm{sort}_{\uparrow}\big((q_i-\alpha u_i)_{i:u_i>0}\big),\\ \boldsymbol\Phi(m_g,\mathbf u)=\boldsymbol\rho(\mathbf u),\\ \boldsymbol\Phi(r,\mathbf u)=\max_{p\in\mathcal M_{g,t_{r+1}}}^{\mathrm{lex}} \boldsymbol\Phi(r+1,\mathbf u+\mathbf c(p)). \end{gathered}`$

</div>

每种实际使用的食材贡献一个分量。程序缓存最佳向量，再按固定候选顺序重建首个达到该向量的组合。变长向量按 Python 元组规则比较：首个不同分量较大者优先，完整前缀相同时较长者优先。缓存状态仍可能大量增长；该历史路线的阈值搜索未被 `nCookware` 正常主流程调用。

</details>

### 3.5 共同厨具的预计算与集合枚举

共同厨具求解先复用每客每厨具的最佳候选。取 $`v=\mathrm{nCookware}`$。对顾客 $`g`$、厨具 $`h`$ 和设备集合 $`S`$，沿用第一章的设备限制候选集与本章 best 函数；best 仅对非空集定义，下式只纳入存在候选的单厨具结果，第二式用于有解顾客：

```math
\begin{gathered}
p_{g,h}^{\star}=\mathrm{best}_g\left(\mathcal C_g^v(\{h\})\right),\\
p_g^{\star}(S)=\mathrm{best}_g\left(\{p_{g,h}^{\star}:h\in S\}\right).
\end{gathered}
```

固定 $`S`$ 后，各客方案与逐客供给独立，该集合内的无解惩罚为常量，有解顾客的候选集为各单厨具集合的并集。因此，先取每厨具 best 再比较具有相同最优目标；各客独立最优也给出汇总目标的最优值：

```math
\max_{(p_g)\in\prod_{g\in G_S}\mathcal C_g^v(S)}^{\mathrm{lex}}
\sum_{g\in G_S}\mathbf f_g(p_g)
=\sum_{g\in G_S}\mathbf f_g(p_g^{\star}(S)).
```

这一分解依赖固定设备集合、实际保留候选及无共享库存等跨客耦合约束。对 $`1\le n\le|H|`$，外层枚举全部 $`\binom{|H|}{n}`$ 个恰好含 $`n`$ 种厨具的集合，按第一章的汇总目标与无解惩罚比较；全部厨具可用且选满时只有一个集合。

令 $`N_{\mathrm{cand}}`$ 为所有顾客实际返回的候选总数。在单次指标求值成本固定的计量下，候选生成后的比较成本及 best 表容量分别为：

```math
O\left(N_{\mathrm{cand}}+\binom{|H|}{n}|G|n\right),\qquad O(|G||H|).
```

前者不含候选 DFS 的生成成本，后者仅计每客每厨具 best 表。相关筛选、等价代表与补位截断决定实际候选范围。单机对照见 3.6 节，跨设备性能尚未系统测量。具体调用关系见[系统架构](docs/architecture.md)，完整最优性边界见[优化模型与算法边界](docs/design.md)。

<details>
<summary><strong>点击展开旧版全文 — v1.0.0 · Initial Release</strong></summary>

### 3.5 共同厨具的预计算与集合枚举

共同厨具求解先复用每客每厨具的最佳候选。取 $`v=\mathrm{nCookware}`$。对顾客 $`g`$、厨具 $`h`$ 和设备集合 $`S`$，沿用第一章的设备限制候选集与本章 best 函数；best 仅对非空集定义，下式只纳入存在候选的单厨具结果，第二式用于有解顾客：

<div align="center">

$`\displaystyle \begin{gathered} p_{g,h}^{\star}=\mathrm{best}_g\left(\mathcal C_g^v(\{h\})\right),\\ p_g^{\star}(S)=\mathrm{best}_g\left(\{p_{g,h}^{\star}:h\in S\}\right). \end{gathered}`$

</div>

固定 $`S`$ 后，各客方案与逐客供给独立，该集合内的无解惩罚为常量，有解顾客的候选集为各单厨具集合的并集。因此，先取每厨具 best 再比较具有相同最优目标；各客独立最优也给出汇总目标的最优值：

<div align="center">

$`\displaystyle \max_{(p_g)\in\prod_{g\in G_S}\mathcal C_g^v(S)}^{\mathrm{lex}} \sum_{g\in G_S}\mathbf f_g(p_g) =\sum_{g\in G_S}\mathbf f_g(p_g^{\star}(S)).`$

</div>

这一分解依赖固定设备集合、实际保留候选及无共享库存等跨客耦合约束。对 $`1\le n\le|H|`$，外层枚举全部 $`\binom{|H|}{n}`$ 个恰好含 $`n`$ 种厨具的集合，按第一章的汇总目标与无解惩罚比较；全部厨具可用且选满时只有一个集合。

令 $`N_{\mathrm{cand}}`$ 为所有顾客实际返回的候选总数。在单次指标求值成本固定的计量下，候选生成后的比较成本及 best 表容量分别为：

<div align="center">

$`\displaystyle O\left(N_{\mathrm{cand}}+\binom{|H|}{n}|G|n\right),\qquad O(|G||H|).`$

</div>

前者不含候选 DFS 的生成成本，后者仅计每客每厨具 best 表。相关筛选、等价代表与补位截断决定实际候选范围；现有记录尚无统一性能基准或跨设备对照。具体调用关系见[系统架构](docs/architecture.md)，完整最优性边界见[优化模型与算法边界](docs/design.md)。

</details>

### 3.6 等价性验证与性能观测

性能优化以 `v1.0.0` 为对照，检查完整结果、行序与输出结构。Python 覆盖四个优化入口、门槛与流行边界、每客每厨具结果及共同配置；XLSX 逐成员比较仅规范化创建和修改时间，保留单元格、公式、样式、尺寸及合并范围检查。网页对照包括选项组合、全部角色、位集边界和流行链；完整工作簿的三次基准均得到相同的 145 行结果及顺序。

| 测量范围 | v1.0.0 中位数 | 当前实现中位数 | 中位数之比 |
| :---: | :---: | :---: | :---: |
| Python `nCookware` 完整运行：启动、读表、58 客规划、五厨具选择及写表 | 106.25 s | 4.15 s | 25.6× |
| 网页候选搜索内核：164 道料理、61 种食材、单 Worker 顺序执行 | 50.42 s | 19.52 s | 2.58× |

以上均为同一台 Windows 设备上的三次配对计时。Python 使用 3.12.14，固定最低分 3、每客日订单量 5、无流行喜爱、流行厌恶「水产」及全部五种厨具。网页内核使用 Node.js 24.22.1，固定博丽灵梦、最低分 3、无流行、四项主要过滤／采购选项均开启、两项“考虑得分”关闭、Top-N 为 3；该测量排除读表、Worker 启动与消息传递、DOM 渲染及浏览器调度。两行计时范围不同，不能直接比较其绝对速度；设备和后台负载也会影响观测值。

界面使用原游戏图标与像素边框整理分区，保留控件、说明文本和导出字段。“停止”操作改为立即终止当前 Worker 并失效旧消息，随后恢复操作按钮；完整计算结果的规则保持不变。验证条件、差分规模与未覆盖范围见[验证记录](docs/verification.md)。

<a id="zh-verification"></a>

## 4. 完整案例：「流行·厌恶」为「水产」时的稀客菜单

### 4.1 情境与数据来源

本例在「水产」触发「流行·厌恶」、五种厨具均可用的条件下，为稀客选择料理与加料。评价采用 cover3 模型：达到最低分且无厌恶命中后，依次比较封顶喜爱收益、食材件数和最低供给余量。

案例取自作者保存的[历史菜单存档](docs/case-study.md)，包含 58 条角色记录。文件名标注「流行·厌恶：水产」与五种厨具，其中的 `5` 表示厨具数量。

历史复现采用 v1.0.0 的程序及根目录 [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx)，每日订单 $`K=5`$、最低分 $`S_{\min}=3`$ 使用该版本默认值。展示中的料理、厨具和食材来自历史存档；评分与余量为这些明确条件下的补充核算。

<a id="zh-methods"></a>
<a id="zh-problem"></a>
<a id="zh-running"></a>

### 4.2 输入与运行

原工作簿提供食材标签、料理配方、顾客偏好和按名称关联的日供给。程序读取已保存的单元格结果；修改公式或其输入后，需在支持相应公式的电子表格软件中重算并保存。网页和 Python 分别解析这份工作簿，彼此独立运行。

以下命令从仓库根目录执行，完整依赖要求 Python 3.11 或更新版本：

```sh
python -m pip install -r requirements.txt
```

网页可用于检查单客候选。启动静态服务：

```sh
python -m http.server 8000 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8000>。页面自动读取同目录工作簿，也支持手动导入 XLSX；按人物、得分和筛选条件查询后，可导出 CSV 或含 `结果` 表的 XLSX。具体操作见[网页使用说明](docs/web-guide.md)。

本例的配餐入口为：

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

按控制台提示依次输入：

| 提示 | 本例输入 | 含义 |
| :---: | :---: | :---: |
| 流行喜爱锚点 | 直接按 Enter | 不设置流行喜爱条件 |
| 流行厌恶锚点 | 输入 `水产`，再按 Enter | 含「水产」的最终标签触发「流行·厌恶」 |
| 允许使用的厨具数量 | 输入 `5`，再按 Enter | 使用料理台、油锅、烧烤架、煮锅和蒸锅 |

默认输出位于 `稀客料理表/single_mixIng_nCookware/`，文件名按流行标签与所选厨具生成，含 14 列的 `Plans` 表，图标列为空占位。显式相对输入、输出路径以脚本目录 `Python/` 为基准解析。参数及字段见[输入输出规范](docs/input-output.md)；得分表和利润表由独立分析脚本生成。

<a id="zh-case-selection"></a>

#### 整张菜单的生成过程

程序以工作簿中已持有的 163 道料理与 58 位稀客为范围，在本例条件下为每位顾客选定一套方案。先为每客、每种厨具保存最佳候选，再在指定厨具集合内确定最终方案；输出时将基础食材与加料合并为总食材列。

[![整张历史菜单的生成过程及灵梦候选比较](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection.png)

[查看矢量图（SVG）](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection.svg)

图中灵梦的三个饭团组合用于展开准入与比较规则。零加料饭团只有 2 分，其搜索分支提前结束；蜂蜜与可可豆均达标，封顶收益和件数相同，最终由最低供给余量区分。完整搜索还比较其他料理。三项指标完全相同时，程序依次按售价降序、料理名称及加料字符串升序确定结果。

本例五种厨具全部可用，仅有一个设备配置；选择范围为原程序实际保留的候选，供给余量逐客核算。各阶段的候选总数未留存，图中不据此推算搜索规模。

### 4.3 历史结果展示

历史成品保存 58 位角色的料理、厨具及总食材列表，每份使用 1–3 件食材。五种厨具均有记录：料理台 24 条、煮锅 18 条、油锅 8 条、烧烤架 6 条、蒸锅 2 条。这里选择了全部五种厨具，未产生设备子集之间的取舍。在上述复现条件下，现存原程序重现了全部 58 条保存方案。

以下摘录 8 条代表性记录；完整 58 条记录及来源见[案例附录](docs/case-study.md)。

| 角色 | 料理 | 厨具 | 总食材 | 件数 | 原表行 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| <img src="HTML/izakaya_icons_pack/customer_rare/007_%E5%8D%9A%E4%B8%BD%E7%81%B5%E6%A2%A6.png" width="46" height="46" alt="博丽灵梦"><br>博丽灵梦 | <img src="HTML/izakaya_icons_pack/recipe/007_%E9%A5%AD%E5%9B%A2.png" width="52" height="52" alt="饭团"><br>饭团 | 料理台 | 蜂蜜、海苔 | 2 | 8 |
| <img src="HTML/izakaya_icons_pack/customer_rare/015_%E7%90%AA%E9%9C%B2%E8%AF%BA.png" width="46" height="46" alt="琪露诺"><br>琪露诺 | <img src="HTML/izakaya_icons_pack/recipe/032_%E5%87%89%E8%8F%9C%E9%9B%95%E8%8A%B1.png" width="52" height="52" alt="凉菜雕花"><br>凉菜雕花 | 料理台 | 蜂蜜、萝卜 | 2 | 13 |
| <img src="HTML/izakaya_icons_pack/customer_rare/000_%E8%8E%89%E6%A0%BC%E9%9C%B2.png" width="46" height="46" alt="莉格露"><br>莉格露 | <img src="HTML/izakaya_icons_pack/recipe/097_%E7%8B%AE%E5%AD%90%E5%A4%B4.png" width="52" height="52" alt="狮子头"><br>狮子头 | 煮锅 | 葡萄、牛肉、鸡蛋 | 3 | 2 |
| <img src="HTML/izakaya_icons_pack/customer_rare/004_%E4%B8%8A%E7%99%BD%E6%B3%BD%E6%85%A7%E9%9F%B3.png" width="46" height="46" alt="上白泽慧音"><br>上白泽慧音 | <img src="HTML/izakaya_icons_pack/recipe/007_%E9%A5%AD%E5%9B%A2.png" width="52" height="52" alt="饭团"><br>饭团 | 料理台 | 海苔 | 1 | 6 |
| <img src="HTML/izakaya_icons_pack/customer_rare/002_%E6%A9%99.png" width="46" height="46" alt="橙"><br>橙 | <img src="HTML/izakaya_icons_pack/recipe/049_%E8%9C%9C%E6%B1%81%E5%8F%89%E7%83%A7.png" width="52" height="52" alt="蜜汁叉烧"><br>蜜汁叉烧 | 烧烤架 | 蜂蜜、猪肉 | 2 | 4 |
| <img src="HTML/izakaya_icons_pack/customer_rare/011_%E7%BA%A2%E7%BE%8E%E9%93%83.png" width="46" height="46" alt="红美铃"><br>红美铃 | <img src="HTML/izakaya_icons_pack/recipe/011_%E7%82%92%E8%82%89%E4%B8%9D.png" width="52" height="52" alt="炒肉丝"><br>炒肉丝 | 油锅 | 南瓜、猪肉 | 2 | 12 |
| <img src="HTML/izakaya_icons_pack/customer_rare/016_%E5%9B%A0%E5%B9%A1%E5%B8%9D.png" width="46" height="46" alt="因幡帝"><br>因幡帝 | <img src="HTML/izakaya_icons_pack/recipe/100_%E6%A8%B1%E8%8A%B1%E5%B8%83%E4%B8%81.png" width="52" height="52" alt="樱花布丁"><br>樱花布丁 | 蒸锅 | 蜂蜜、桃子 | 2 | 17 |
| <img src="HTML/izakaya_icons_pack/customer_rare/005_%E8%8C%A8%E6%9C%A8%E5%8D%8E%E6%89%87.png" width="46" height="46" alt="茨木华扇"><br>茨木华扇 | <img src="HTML/izakaya_icons_pack/recipe/001_%E8%B1%86%E8%85%90%E5%91%B3%E5%99%8C.png" width="52" height="52" alt="豆腐味噌"><br>豆腐味噌 | 煮锅 | 萝卜、豆腐 | 2 | 7 |

总食材包含基础配方与加料，按历史表顺序列出；每个名称表示 1 件。角色与料理图标直接使用仓库中的原游戏素材。

### 4.4 从灵梦的原存方案到指标复核

历史第 8 行为博丽灵梦选择饭团与料理台，使用蜂蜜、海苔各一件。对照原配方，海苔是基础原料，蜂蜜为追加食材。

| 环节 | 原数据及规则 | 核算结果 |
| :---: | :---: | :---: |
| 基础料理 | 饭团自带「素」「家常」「饱腹」「和风」「实惠」；海苔用于满足配方，其「素」「鲜」不自动并入料理 | 命中灵梦喜爱「饱腹」「实惠」，厌恶 0，基础得分 2；原始得分表 `Scores!A987:F987` 保存相同结果 |
| 加入蜂蜜 | `食材!B39:G39` 中蜂蜜提供「甜」；料理台作为厨具标签参与最终标签形成 | 新增喜爱命中「甜」，总喜爱命中 3，厌恶 0 |
| 应用流行条件 | 最终标签不含「水产」，且未设置流行喜爱锚点 | 本方案不获得「流行·厌恶」或「流行·喜爱」 |

最终标签为「素」「家常」「饱腹」「和风」「实惠」「料理台」「甜」。令 $`g`$ 为博丽灵梦、$`p`$ 为饭团加蜂蜜，则：

```math
\begin{gathered}
H_g^{\mathrm L}(p)=3,\qquad H_g^{\mathrm D}(p)=0,\qquad S_g(p)=3-0=3,\\
C(p)=1+1=2,\qquad U(H_g^{\mathrm L}(p))=\min(3,3)=3.
\end{gathered}
```

原工作簿 `食材merchant_data` 的 `D6`、`D2` 分别保存海苔和蜂蜜的日供给 47、68 件。按每客每日 5 份、每份各用一件计算：

```math
R(p)=\min(47-5\times1,\ 68-5\times1)=42.
```

因此，该历史方案在本节条件下达到 3 分门槛，使用 2 件食材，最低日供给余量为 42 件。这里的余量按该顾客独立核算，未扣除其他顾客的用量；它是经验供给下的模型指标。

同一料理的两个达标候选可说明目标取舍。下表由原候选函数在本节条件下重新计算，两者均无厌恶命中：

| 方案 | 净分 $`S_g(p)`$ | 封顶收益 $`U(H_g^{\mathrm L}(p))`$ | 件数 $`C(p)`$ | 最低余量 $`R(p)`$（件／日） |
| :---: | :---: | :---: | :---: | :---: |
| 饭团＋蜂蜜 | 3 | 3 | 2 | 42 |
| 饭团＋可可豆 | 4 | 3 | 2 | 10 |

可可豆多命中一项喜爱，但封顶后两者的首项目标均为 3，食材件数也相同，因此由供给余量决定先后，蜂蜜方案优先。这组实际候选说明了从“尽量增加命中”转向“满足覆盖目标后节约资源”的选择依据。

### 4.5 验证范围

复现按角色姓名比较料理、厨具和总食材多重集，不比较食材排列及表格版式。原程序、输入工作簿和历史结果文件的运行前后哈希一致。全量核对及既有网页、发布副本检查见[验证记录](docs/verification.md)；目标封顶和候选压缩的说明性算例见[优化模型与算法边界](docs/design.md)。

<a id="zh-limits"></a>

复现一致性适用于上述输入与候选范围。游戏实测收益、与人工备菜的效果差异及跨顾客库存约束仍需独立验证。

<a id="zh-sources"></a>

## 5. 贡献与资料

本项目为非官方个人建模案例与辅助工具。

| 参与方 | 工作与归属 |
| :---: | :---: |
| 作者 | 提出游玩问题、梳理规则，确定决策单位、评价顺序及筛选与厨具条件；手工记录价格、供给和委托数据，并通过角色与参数案例验收结果 |
| AI 辅助 | 大量代码、算法推导和部分调试使用 AI 辅助；需求澄清、模型取舍与结果验收由作者负责 |
| 第三方资料 | 标签资料来自 [AnYiEE 的项目](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)；游戏图像归属、依赖许可及图示制作方式见[第三方声明](THIRD_PARTY_NOTICES.md) |

详细资料按用途分列：

| 文档 | 内容 |
| :---: | :---: |
| [完整历史菜单](docs/case-study.md) | 58 条保存方案、来源与复现核对 |
| [优化模型与算法边界](docs/design.md) | 变量、目标、集合评价与候选范围 |
| [需求与设计决策演进](docs/prompt-journey.md) | 历史需求、目标变化、取舍与案例依据 |
| [数据来源说明](docs/data-provenance.md) | 人工记录、上游资料及估计口径 |
| [验证记录](docs/verification.md) | 观测条件、复现核对与未覆盖范围 |
| [系统架构](docs/architecture.md) | 执行边界、数据流与文件职责 |
| [输入输出规范](docs/input-output.md) | 工作簿字段、参数、路径与输出格式 |
| [网页使用说明](docs/web-guide.md) | 操作步骤、筛选含义与边界行为 |

---

<a id="english"></a>

# Mystia Menu Optimizer

**Modeling meal-preparation decisions in Touhou Mystia's Izakaya: preference coverage, ingredient supply, and cookware configuration**

[中文](#chinese) | **English**

Historical version: [v1.0.0 · Initial Release](https://github.com/Mingcode123/Mystia-Menu-Optimizer/releases/tag/v1.0.0), including complete source and release notes.

In [Touhou Mystia's Izakaya](https://store.steampowered.com/app/1584090/), a guest may accept several combinations of dishes and additional ingredients, each with different ingredient requirements, supply pressure, and cookware needs. Meal preparation therefore involves two questions: which plans meet the requirements, and how to define a better choice among qualifying plans.

This project formulates these questions as a discrete decision model. It defines the feasible space of recipes and additions and establishes a hierarchical evaluation of preference coverage, ingredient units, and minimum supply slack. The model evolved from multiple plans assigned by liked tag to one plan per guest, capped coverage utility, and shared cookware selection. The project provides rule and data definitions, mathematical models, explanations of design decisions, and programs for candidate search and result checking.

The author's main work comprises identifying gameplay problems, clarifying rule semantics, recording supply and prices, specifying objectives and constraints, and checking results through character cases. Code implementation, some algorithm derivation, and debugging were AI-assisted. This document focuses on those modeling choices and their consequences. Interpretation of results is bounded by the given data, assumptions, and candidates actually retained.

[Mathematical model](#en-model) · [Data and modeling rationale](#en-data) · [Solution algorithms](#en-algorithms) · [Complete case study](#en-verification) · [Contributions and references](#en-sources)

**Mechanics and terminology** &nbsp; <a href="#en-tag-figure"><img src="docs/images/jump-to-figure-en.png" alt="Jump to diagram" width="156" height="28" align="middle"></a>

Preparation and evaluation follow three steps:

1. **Choose a dish through its recipe.** A recipe specifies the cookware and required ingredients. For example, a prep counter and seaweed×1 can make a rice ball. The rice ball uses its own preset tags; seaweed's tags are not automatically added through the base recipe.
2. **Choose additions to form a plan.** Each dish can use at most 5 ingredient units, with required ingredients and additions sharing those slots. The rice ball's seaweed occupies 1 slot; the remaining 4 may hold additions or stay empty. Adding honey×1 produces a rice-ball-with-honey plan: 2 units in total, still a rice ball, with honey contributing 「Sweet」. The final tags remain subject to overrides and other rules.
3. **Match the final tags against guest preferences.** Each guest has separate liked and disliked tags. A tag present in the plan matches the preference with the same name; each distinct tag counts once. In the figure, rice ball with honey matches Reimu's 「Filling」「Affordable」「Sweet」 and no dislikes, giving a score of 3−0=3.

| Term | Definition |
| :---: | :---: |
| Ingredient | A preparation material such as seaweed or honey. The recipe's specified quantity counts as required ingredients; any extra quantity counts as additions. The same ingredient can serve both roles. |
| Dish | A menu item made according to a recipe, such as rice ball, with its own preset tags, specified cookware, and recipe prohibitions. |
| Addition | An ingredient used in a remaining slot beyond the base recipe, such as honey added to rice ball; legal additions preserve the selected dish and contribute ingredient tags. |
| Plan | One concrete preparation choice: a dish and the types and quantities of its additions, which may also be omitted. Required ingredients and additions total at most 5 units; repeated use of one ingredient still occupies a slot per unit. |
| Tag | A name representing an attribute or preparation method, such as 「Sweet」「Filling」「Prep counter」; it is also the unit matched against guest likes and dislikes. |
| Score | Liked matches minus disliked matches for a specified guest. It describes tag matching; planning also compares ingredient units and supply, as defined in [Chapter 1](#en-model). |

Recipe prohibitions restrict dish preparation, while guest dislikes contribute to preference scoring. The figure shows how tag overrides, prohibition conflicts, and trends affect a plan. Its score measures tag matching; full in-game evaluation and profit are outside this scoring scope.

<a id="en-tag-figure"></a>

[![Five sections explain ingredient slots, preference matching, tag overrides, recipe prohibitions, and trends. Blue denotes dish tags, orange ingredient tags, teal cookware tags, purple guest likes, slate gray guest dislikes, and pale red recipe prohibitions. A prep counter and one seaweed satisfy only the rice-ball recipe: one slot filled and four empty; adding honey leaves two filled and three empty. Dish tags are not the union of required-ingredient tags; additions contribute tags. A and B show all Reimu food preferences: likes 「High-grade」「Filling」「Sweet」「Wondrous」「Affordable」「Liked trend」; dislikes 「Pub food」「Expensive」「Disliked trend」. A: rice ball with honey matches 「Filling」「Affordable」「Sweet」, scoring 3 liked minus 0 disliked matches = 3. B: rice ball with pork replaces 「Vegetarian」 with 「Meat」, matches 「Filling」「Affordable」, and scores 2 minus 0 = 2. Rice ball has no recipe prohibitions. C: honey triggers stinky tofu's 「Sweet」 prohibition, which other additions cannot cancel; the game produces Dark Matter, while Python nCookware excludes the plan before scoring. A, B, and C have no trends. The separate trend example distinguishes random trigger tags from fixed guest attitudes; the program reads supplied conditions. When 「Sweet」 is popular, rice ball with honey keeps 「Sweet」 and gains 「Liked trend」, matching 4 of Reimu's likes and 0 dislikes for a score of 4. Below, Cirno likes 「Disliked trend」 and dislikes 「Liked trend」.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.png)

*Figure 1. Recipes, additions, and tag matching. A, B, and C have no trends; the final section shows the same plan scoring 4−0=4 when 「Sweet」 is popular, followed by Cirno's trend preferences. This is a rule illustration using the original pixels of game icons.* [Vector SVG](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/53cee219714977bd0df5bd3f36ecc8880528f46c/docs/images/tag-example-en.svg). Tags follow the [original workbook](东方夜雀食堂.xlsx). A prohibited combination produces Dark Matter in the game; Python `nCookware` excludes it before scoring. Browser differences are described in the [browser guide (Chinese)](docs/web-guide.md). See the [third-party notices (Chinese)](THIRD_PARTY_NOTICES.md) for rule and artwork sources.

Preparation models build on plans, ingredient quantities, and tag matching, distinguishing candidate queries, planning objectives, and equipment constraints. The five-slot limit and recipe prohibitions are preparation conditions; the score threshold and zero-dislike eligibility are planning policies.

<a id="en-model"></a>

## 1. Mathematical model: from gameplay decisions to optimization

### 1.1 Common notation and base model

Preparation decisions have two levels: specifying how to prepare one dish and choosing among plans that satisfy the requirements. The versions share basic definitions of ingredient use and tag matching; each model specifies its own candidate-generation rules, order assumptions, and optimization objectives.

**Objects and notation:** Let $`g`$ denote a guest, $`d`$ a dish, $`i`$ an ingredient, $`t`$ a tag, and $`p`$ a preparation plan. Candidate and preference sets use calligraphic letters, and vectors use boldface. Subscripts identify objects, parenthesized superscripts $`(r)`$ identify filtering stages, and upright subscripts or superscripts identify fixed categories. $`v`$ indexes model versions, and $`\star`$ marks the best retained plan under the corresponding objective.

| Symbol | Definition | Unit or type |
| :---: | :---: | :---: |
| $`b_i(d)`$ | Base: ingredient quantity required by the dish's recipe; a given parameter | Units per serving |
| $`a_i(p)`$, $`\mathbf A(p)`$ | Addition: quantity of an added ingredient and the complete addition vector; decision variables | Units per serving; vector |
| $`c_i(p)`$, $`C(p)`$ | Count: total quantity of an ingredient and total ingredient count of the plan | Units per serving |
| $`T(i)`$, $`T(p)`$ | The ingredient's own tag set and the plan's final tag set | Sets |
| $`\mathcal L_g,\mathcal D_g`$ | The guest's liked and disliked tag sets | Sets |
| $`H_g^{\mathrm L}(p),H_g^{\mathrm D}(p)`$ | Counts of liked and disliked tags matched by the final tags | Matches |
| $`S_g(p),S_{\min}`$ | The plan's net score and the specified minimum net score | Points |
| $`R_{\mathrm T},E_{\mathrm T}`$ | Tags the user requires or excludes | Sets |
| $`q_i`$ | Empirical daily ingredient supply, from the workbook's TDQ field | Units per day |
| $`K`$ | Assumed daily order count per guest; the Python planners use 5 by default | Orders per day |

**Plans and preparation constraints:** A plan consists of a selected dish and its addition quantities. Base ingredients and additions together occupy at most five slots; repeated use of the same ingredient is counted unit by unit:

```math
\begin{gathered}
p=(d,\mathbf A),\quad \mathbf A=(a_i)_i,\quad a_i\in\mathbb Z_{\ge0},\\
c_i(p)=b_i(d)+a_i(p),\quad C(p)=\sum_i c_i(p)\le5.
\end{gathered}
```

Base ingredients satisfy the recipe and occupy slots, but their tags do not automatically transfer to the dish; additions introduce ingredient tags. $`T(p)`$ denotes the final tag set produced by the current version's rules for dishes, cookware, selling price, additions, overrides, and trends. Each distinct tag appears only once. A guest's trend preferences are fixed, while current trigger conditions determine whether a plan receives the corresponding tags. Recipe prohibitions and candidate-processing scope must be interpreted for the chosen entry point; HTML and Python behavior is detailed in the [web guide](docs/web-guide.md) and [optimization model and algorithm boundaries](docs/design.md).

**Matching and scoring:** Liked matches, disliked matches, and the net score are defined as:

```math
\begin{gathered}
H_g^{\mathrm L}(p)=\left|T(p)\cap\mathcal L_g\right|,\\
H_g^{\mathrm D}(p)=\left|T(p)\cap\mathcal D_g\right|,\\
S_g(p)=H_g^{\mathrm L}(p)-H_g^{\mathrm D}(p)
\end{gathered}
```

The net score describes how a plan matches a guest's preferences. Eligibility and comparison after qualification are determined by each version's admission and evaluation policies. $`\mathrm{lex}`$ denotes lexicographic order: compare the first objective-vector component, and consider the next only when the preceding components tie.

<details>
<summary>Notation correspondence with the mechanics figure and supplementary documents</summary>

| This chapter | Notation in the mechanics figure and supplementary documents | Meaning |
| :---: | :---: | :---: |
| $`a_i(p)`$ | $`x_i`$ | Addition count |
| $`C(p)`$ | $`L(p)`$ | Total ingredient count |
| $`\mathcal L_g,\mathcal D_g`$ | $`P_g,N_g`$ | Liked and disliked tag sets |
| $`H_g^{\mathrm L}(p),H_g^{\mathrm D}(p)`$ | $`h_g(p),a_g(p)`$ | Liked and disliked match counts |
| $`S_g(p),S_{\min}`$ | $`s_g(p),\tau`$ | Net score and minimum net score |

</details>

[![Preparation-model flow: HTML queries qualifying candidates; detailedPLAN assigns multiple plans by target liked tag, minimizing expected daily ingredient units before maximizing minimum supply slack; singlePLAN selects one plan per guest by liked matches, units per serving, and slack; cover3 caps coverage benefit at 3. Output formatting, fixed cookware, and shared cookware form separate extensions. Arrows show model relationships.](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution-en.png)

*Figure 2. Preparation-model flow. The main sequence shows changes in decision units, order assumptions, and objective priority; output presentation and the two cookware conditions form separate branches. Arrows indicate problem dependencies, not program calls or an exact development timeline.* [Vector SVG](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/3cb15df86ee619bd6ad67c045a98672e45b9be29/docs/images/model-evolution-en.svg).

### 1.2 HTML: defining plans, filtering candidates, and comparing procurement conditions

#### 1.2.1 Decision problem

Given a rare guest, imported dishes and ingredients, current trend conditions, and the player's minimum score and tag requirements, the webpage **enumerates additions for each dish, selects qualifying candidates, and removes or ranks them according to the enabled filtering and procurement options.** It returns a candidate table, with one dish and its addition types and quantities per row, and may retain several alternatives for the same guest.

The webpage provides the following options:

| Webpage option | Effect when enabled | Scope |
| :---: | :---: | :---: |
| Equivalent-ingredient deduplication (additions only) | Group ingredients with identical nonempty tag sets and enumerate one representative per class. | Addition ingredient pool before enumeration |
| Ingredient-upgrade filter | Remove an advanced plan when its designated base-addition alternative is already a qualified candidate and contains no advanced additions. | Qualified candidates for the same dish |
| Addition-subset filter | Remove the current plan if a previously retained qualified plan uses no more of any added ingredient. | Candidates for the same dish after the upgrade filter |
| Procurement recommendation (by TDQ) | Rank plans by effective ingredient supply, use Top-N to set the retention cutoff, and retain every plan tied at the cutoff. | Candidates for the same dish after the preceding filters |

Both filters have a “consider score” option. When enabled, removal also requires the replacement or subset plan to score at least as highly as the current plan.

The execution order is **exclude ingredient names forbidden by the dish → optional equivalence deduplication → enumerate additions → apply tag and score admission conditions → upgrade filter → subset filter → procurement ranking and output.** Disabled steps are skipped.

#### 1.2.2 Admission conditions and initial candidates

**Constraints and admission:** Base ingredients and additions together use at most five units. The user may also specify required tags, excluded tags, and a minimum net score. When the base recipe uses fewer than five units and additions bring the total to five, the webpage adds 「Large portion」; a dish’s existing 「Large portion」 tag is retained.

Let $`\mathcal B_d^{\mathrm{web}}`$ be the plan pool actually enumerated by the webpage for dish $`d`$; it depends on the original recipe handling and the equivalence-deduplication option. Unspecified tag requirements use empty sets. Qualified candidates entering the subsequent filters are:

```math
\mathcal C_{g,d}^{(0)}=
\left\{p\in\mathcal B_d^{\mathrm{web}}:
S_g(p)\ge S_{\min},\quad R_{\mathrm T}\subseteq T(p),\quad E_{\mathrm T}\cap T(p)=\varnothing
\right\}
```

This is a minimum net-score condition: a threshold of 3 also admits scores of 4 or 5, and liked matches can offset dislike penalties. The original webpage's recipe handling differs from the Python branches; see the [web guide](docs/web-guide.md). This is the stage-0 candidate set; subsequent filters compare only plans admitted at this step.

#### 1.2.3 Equivalence deduplication: reducing the addition ingredient pool

**Purpose:** Group ingredients with identical nonempty tag sets and enumerate one representative per class to reduce repeated tag combinations. Equivalence depends solely on the ingredients' own tags.

Define the equivalence relation and classes as:

```math
i\sim j\quad\Longleftrightarrow\quad
i=j\ \lor\ \left(T(i)=T(j)\ne\varnothing\right),\qquad
E(i)=\{j:j\sim i\}
```

Ingredients without tags form separate singleton classes. Let $`I_d`$ be the addition pool after excluding ingredient names forbidden by the dish. Its available equivalence classes are $`E_d(i)=E(i)\cap I_d`$. When deduplication is enabled, one representative from each nonempty class enters enumeration: the original program's preferred-name list takes priority, followed by Chinese name ordering. When disabled, the full $`I_d`$ is enumerated.

Equivalence deduplication compresses the **addition-ingredient pool** before enumeration. The base recipe is preserved, and a representative may be added multiple times. Ingredients with identical tags belong to the same class even when their supply quantities differ; procurement recommendation handles these supply differences separately.

#### 1.2.4 Ingredient-upgrade filter: comparing designated base alternatives

**Purpose:** Prefer plans using ingredients with fewer tags when those plans satisfy admission conditions. “Advanced” is a classification based on ingredient-tag inclusion, determined solely from tag sets.

Within the ingredient pool actually used to enumerate the dish, consider ingredient $`i`$ and seek a base alternative $`j`$ satisfying:

```math
\varnothing\ne T(j)\subsetneq T(i)
```

The original program selects the recognized alternative with the fewest tags, breaking ties by Chinese name order. Denote it by $`B_d(i)`$ (Base representative); if no alternative exists, set $`B_d(i)=i`$. Map **all additions simultaneously** to these representatives to obtain the base addition vector:

```math
\begin{gathered}
a_j^{\mathrm{base}}(p)=\sum_{i:B_d(i)=j}a_i(p),\\
\mathbf A^{\mathrm{base}}(p)=(a_j^{\mathrm{base}}(p))_j,\\
p^{\mathrm{base}}=(d,\mathbf A^{\mathrm{base}}(p)).
\end{gathered}
```

A plan is considered to contain advanced additions when $`\mathbf A^{\mathrm{base}}(p)\ne \mathbf A(p)`$. With the upgrade filter enabled, it is removed when:

```math
\begin{gathered}
\mathbf A^{\mathrm{base}}(p)\ne \mathbf A(p),\qquad p^{\mathrm{base}}\in\mathcal C_{g,d}^{(0)},\\
\mathbf A^{\mathrm{base}}(p^{\mathrm{base}})=\mathbf A(p^{\mathrm{base}}),\qquad
\left(F_{\mathrm U}=0\ \lor\ S_g(p^{\mathrm{base}})\ge S_g(p)\right).
\end{gathered}
```

$`F_{\mathrm U}`$ is this filter's “consider score” switch: 1 when enabled and 0 when disabled. When disabled, the existence of the corresponding qualified, nonadvanced base plan suffices to remove the advanced plan. When enabled, the base plan must also score at least as highly. The current plan remains if the base plan was not generated, failed the score threshold, or failed another admission condition.

For example, one ingredient may carry 「Sweet」, and another 「Sweet」「Premium」. The latter plan is evaluated for removal only if the former ingredient is its selected base representative and the complete replacement plan qualifies. The comparison is restricted to **the complete addition replacement produced by the designated base mapping**, with the base recipe preserved. Denote the retained set by $`\mathcal C_{g,d}^{(1)}`$; when the upgrade filter is disabled, it equals $`\mathcal C_{g,d}^{(0)}`$.

#### 1.2.5 Addition-subset filter: comparing smaller additions

**Purpose:** If a retained plan qualifies using only some of the current plan's additions, omit the larger addition plan according to the selected policy. The comparison uses **ingredient-count vectors**, whose components record the quantity of each added ingredient:

```math
\mathbf A(p')\preceq \mathbf A(p)\quad\Longleftrightarrow\quad
\forall i,\ a_i(p')\le a_i(p)
```

The input is the same-dish candidate set $`\mathcal C_{g,d}^{(1)}`$ remaining after the upgrade filter. They are sorted by ascending addition count, descending score, and addition-name key. During sequential processing, let $`\mathcal K`$ contain the previously retained plans. The current plan is removed when:

```math
\exists p'\in\mathcal K:\quad
\mathbf A(p')\preceq \mathbf A(p)\quad\land\quad
\left(F_{\mathrm S}=0\ \lor\ S_g(p')\ge S_g(p)\right)
```

$`F_{\mathrm S}`$ is the subset filter's “consider score” switch. When disabled, any retained qualifying subset suffices; when enabled, the subset must also score at least as highly. A plan that survives is added to $`\mathcal K`$ for subsequent comparisons. A qualifying plan with no additions can also serve as a subset; the implemented relation includes equal vectors.

For example, “honey ×1” is an addition subset of “honey ×2”, but not conversely. If both qualify and the former has been retained, the latter can be removed when score consideration is disabled; when enabled, their net scores must also be compared. The upgrade filter compares ingredient substitutions at an unchanged count; the subset filter compares combinations using smaller quantities of existing additions. Both remove candidates according to these comparisons without rewriting retained plans. Denote the subset-filtered set by $`\mathcal C_{g,d}^{(2)}`$; when this filter is disabled, it equals $`\mathcal C_{g,d}^{(1)}`$.

#### 1.2.6 Procurement recommendation: setting a cutoff by supply vectors

**Purpose:** Within $`\mathcal C_{g,d}^{(2)}`$, favor ingredient combinations with better availability. At this stage, no daily order volume is assumed and consumption is not deducted from supply. Comparisons remain within each dish.

**Effective supply:** Retaining empirical daily supply $`q_i`$, let $`M(i)\subseteq E(i)`$ denote the members associated with that ingredient in the program's global group records that have known supply values. The webpage uses:

```math
\widetilde q_i=
\begin{cases}
\dfrac{1}{|M(i)|}\sum_{j\in M(i)}q_j,& |M(i)|>0,\\
q_i,& |M(i)|=0\text{ and }q_i\text{ is known},\\
0,&\text{otherwise}.
\end{cases}
```

For a singleton class with a known value, this equals the ingredient's own supply. With no group record, it first falls back to the ingredient's own supply record, then to 0 if that is also missing. The mean uses the global class, not only members allowed for the current dish. Procurement comparisons use this effective value even when equivalence deduplication is disabled.

**Comparison vector:** Each unit of a base ingredient or addition contributes one effective supply value. Sorting these values in ascending order gives $`\mathbf V(p)`$ (Vector):

```math
\mathbf V(p)=\mathrm{sort}_{\uparrow}
\left(\biguplus_i\{\widetilde q_i\}^{c_i(p)}\right)
```

Here, $`\biguplus`$ denotes concatenation preserving repeated elements, and $`\{\widetilde q_i\}^{c_i(p)}`$ repeats that value $`c_i(p)`$ times. Ranking starts at the smallest component and favors the larger value at the first differing position. When prefixes match, missing components of the shorter vector are treated as $`+\infty`$. Thus:

```math
(4,12)\succ(3,100),\qquad
(4,12)\succ(4,10),\qquad
(4)\succ(4,12)
```

This lexicographic rule compares supply values component by component, starting with the lowest. The original implementation uses a numerical comparison tolerance of $`10^{-9}`$; vector ties are ordered stably by addition count and addition-name key.

**Top-N and ties:** Let $`m_{g,d}`$ be the number of filtered candidates. Write them in ranking order as $`p_1,\ldots,p_{m_{g,d}}`$, with $`N\ge1`$ the user-specified ranking threshold. To describe how deduplication affects the cutoff, define plan weight $`W(p)`$ (Weight):

```math
W(p)=
\begin{cases}
1,&\text{equivalence deduplication off},\\
\prod_{i:a_i(p)>0}|E_d(i)|^{a_i(p)},&\text{equivalence deduplication on}.
\end{cases}
```

With no additions, the empty product is 1. Denote the cutoff position by $`k_{\mathrm{cut}}`$. The retained set is:

```math
\begin{gathered}
k_{\mathrm{cut}}=\min\left\{k:\sum_{j=1}^{k}W(p_j)\ge N\right\},\\
\mathcal R_{g,d}=\{p_j:\mathbf V(p_j)\succeq \mathbf V(p_{k_{\mathrm{cut}}})\}
\end{gathered}
```

If cumulative weight is below $`N`$, use $`k_{\mathrm{cut}}=m_{g,d}`$; if there are no candidates, output is empty. Without deduplication, the cutoff is the $`\min(N,m_{g,d})`$-th plan. With deduplication, weights accumulate according to the sizes of the dish's available equivalence classes. **Top-N locates the cutoff using cumulative plan weight, then retains every candidate whose supply vector meets or exceeds that cutoff, including all ties. The cutoff and ties together determine the final row count.**

The weight compensates for the effect of equivalence deduplication on the ranking cutoff. Its product calculation differs from counting unordered plans: adding two units from the same two-member class gives weight $`2^2=4`$, whereas there are only three unordered combinations. The weight therefore does not exactly reconstruct the number of plans before deduplication, and strict equivalence of Top-N results with deduplication on and off has not been established.

**Output names:** When both procurement recommendation and equivalence deduplication are enabled, displayed additions are also replaced by the global equivalent with the highest known raw supply:

```math
i_{\mathrm{out}}\in\arg\max_{j\in M(i)}q_j
```

If no supply value is known, the current representative remains. Ties follow representative priority and name order. **Ranking uses the class mean; output names use the class maximum.** Base ingredients are not replaced. This output step selects from the global class without checking the dish's forbidden-name list again; see the conditions in the [web guide](docs/web-guide.md).

When procurement recommendation is disabled, retain all of $`\mathcal C_{g,d}^{(2)}`$. Representing plans before the output-name replacement, the filtering stages satisfy:

```math
\mathcal C_{g,d}^{(0)}\supseteq\mathcal C_{g,d}^{(1)}\supseteq\mathcal C_{g,d}^{(2)}\supseteq\mathcal R_{g,d}
```

Equivalence deduplication first reduces the ingredient pool; the set relations above describe candidate removal after enumeration. The HTML model combines **admission conditions, two candidate-removal policies, an ingredient-equivalence approximation, and procurement ranking** to return alternatives that satisfy the user's conditions. Subsequent Python versions introduce optimization objectives for automatically selecting plans within their respective candidate sets.

### 1.3 detailedPLAN: select plans for individual target tags

**Problem and change:** `detailedPLAN.py` advances from returning candidates to automatically selecting a collection of plans: one response plan for each feasible target liked tag of a guest. The evaluation order becomes **minimum expected ingredient units, followed by maximum minimum supply slack**.

**Constraints and assumptions:** Python PLAN adds a zero-disliked-match eligibility condition. Retaining the previous section's net-score threshold therefore gives:

```math
H_g^{\mathrm D}(p)=0,\qquad S_g(p)\ge S_{\min}
\quad\Longrightarrow\quad H_g^{\mathrm L}(p)\ge S_{\min}
```

Recipe prohibitions, dish ownership, and candidate reduction follow the corresponding Python version. Each version defines its candidate set through its own processing rules; no inclusion relation is specified between HTML and Python candidates.

**New decisions and order assumptions:** For a target tag $`t\in \mathcal L_g`$, let $`\mathcal C_{g,t}`$ contain eligible candidates that include the tag, collected after the original upgrade/subset filters are applied separately for each dish and target tag. Define:

```math
J_g=\left\{t\in \mathcal L_g:\mathcal C_{g,t}\ne\varnothing\right\},\qquad
m_g=|J_g|,\qquad p_t\in\mathcal C_{g,t}\quad(t\in J_g)
```

The decision is a family of plans $`(p_t)_{t\in J_g}`$, with several tags allowed to select the same plan. $`m_g`$ counts target tags that have candidates. Retain the assumed daily order count $`K`$ and distribute orders equally among these target tags, with $`K/m_g`$ orders assigned to each. If $`m_g=0`$, no plan is produced.

Retaining $`c_i(p)`$ and the original daily supply $`q_i`$, let $`u_i`$ be the cumulative use of an ingredient across the plans selected for the tags. Expected daily ingredient units $`E_{\mathrm{old}}`$ and minimum supply slack $`R_{\mathrm{old}}`$ are:

```math
\begin{gathered}
u_i=\sum_{t\in J_g}c_i(p_t),\\
E_{\mathrm{old}}=\frac{K}{m_g}\sum_i u_i,\\
R_{\mathrm{old}}=\min_{i:u_i>0}\left(q_i-\frac{K}{m_g}u_i\right)
\end{gathered}
```

Both latter quantities are measured in units per day. The model calculates slack by subtracting ingredient consumption under the assumed orders from daily supply. Equal allocation is a modeling assumption without a corresponding empirical estimate of order probabilities.

**Objective:**

```math
\min_{\substack{p_t\in\mathcal C_{g,t}\\t\in J_g}}^{\mathrm{lex}}
\left(E_{\mathrm{old}},\;-R_{\mathrm{old}}\right)
```

With $`m_g`$ fixed, minimizing expected units separates by tag. The program therefore retains every candidate tied for minimum units for each tag before comparing the supply pressure of their combinations. Ties in minimum slack are resolved by comparing the full ascending slack vector. Threshold binary search and DFS in this historical branch solve that combination problem; they are solution methods, while the objective remains the expression above.

### 1.4 singlePLAN: replace plans per tag with one plan per guest

**Problem and change:** `singlePLAN.py` replaces the family $`(p_t)_{t\in J_g}`$ with a single $`p`$: all assumed orders for the same guest use this one plan. The objective order also changes to **maximum liked matches, followed by minimum ingredient units, then maximum minimum supply slack**.

**Constraints and assumptions:** Retain preparation conditions, the minimum net score, and zero-dislike eligibility. The decision becomes one plan $`p`$, used for all $`K`$ orders from the same guest.

**Consumption and slack:** One plan serves all of the guest's assumed daily orders, giving the following ingredient demand and slack:

```math
\begin{gathered}
\frac{K}{m_g}\sum_{t\in J_g}c_i(p_t)
\quad\longrightarrow\quad Kc_i(p),\\
R(p)=\min_{i:c_i(p)>0}\left(q_i-Kc_i(p)\right)
\end{gathered}
```

$`R(p)`$ remains measured in units per day. For fixed $`K`$, minimizing units per serving $`C(p)`$ is equivalent to minimizing this guest's daily units $`KC(p)`$; the original implementation directly compares units per serving.

**Objective:** Let $`\mathcal C_g^{\mathrm{single}}`$ denote the eligible candidates generated and retained by this version:

```math
\max_{p\in\mathcal C_g^{\mathrm{single}}}^{\mathrm{lex}}
\left(H_g^{\mathrm L}(p),\;-C(p),\;R(p)\right)
```

This step changes both order allocation and the first priority. The earlier model first controls expected consumption across a collection of plans. This model first seeks more liked matches in one plan, then reduces ingredient units and supply pressure at equal coverage. When all three criteria tie, the original program uses selling price, dish name, and the additions string, in that order.

### 1.5 cover3: retain one plan and cap preference benefit at 3

**Problem and change:** `singlePLAN_cover3.py` retains one plan per guest, its reuse for all orders, and the same slack calculation. Only the first objective changes: three liked matches are sufficient, and additional matches no longer increase optimization priority.

**Constraints and assumptions:** Retain one plan per guest, zero-dislike eligibility, the minimum net score, and assumed order volume. Capped coverage benefit ranks eligible plans, while admission thresholds retain their existing settings.

**New utility and objective:** Let $`U(h)`$ denote the coverage utility used to compare plans with $`h`$ liked matches, with the corresponding candidate set denoted by $`\mathcal C_g^{\mathrm{cover3}}`$:

```math
\begin{gathered}
U(h)=\min(h,3),\\
\left(H_g^{\mathrm L}(p),-C(p),R(p)\right)
\quad\longrightarrow\quad
\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right)
\end{gathered}
```

```math
\max_{p\in\mathcal C_g^{\mathrm{cover3}}}^{\mathrm{lex}}
\left(U(H_g^{\mathrm L}(p)),\;-C(p),\;R(p)\right)
```

The final tags $`T(p)`$, match count $`H_g^{\mathrm L}(p)`$, and raw net score $`S_g(p)`$ retain their previous definitions; the capped function computes the benefit used for ranking. In Figure 1, when 「Sweet」 is popular, the rice-ball-and-honey plan scores 4 for Reimu, while $`U(4)=3`$.

The threshold $`S_{\min}`$ controls eligibility, while the capped function $`U`$ controls comparison after qualification. Under the default $`S_{\min}=3`$ and zero-dislike conditions, every eligible candidate has $`U=3`$. The policy therefore becomes **qualify first, then minimize ingredient units, then consider supply slack**. The admission threshold and benefit cap are set independently, so lowering the threshold retains the existing cap.

### 1.6 Output-format branch: mixedingredients

**Problem and change:** `singlePLAN_cover3_mixedingredients.py` changes how results are read and used. It combines base ingredients and additions into `Ingredient1` through `Ingredient5`, follows the original output ordering, and retains merged table cells.

This branch retains the decision variables, objective, and tag-formation rules of Section 1.5, combining base and additional quantities only for display. The meanings and calculations of $`p,c_i(p),C(p),T(p),H_g^{\mathrm L}(p),S_g(p),R(p),U(H_g^{\mathrm L}(p))`$ remain unchanged: base ingredients satisfy the recipe, and additions introduce ingredient tags.

### 1.7 Fixed-cookware branch: limitedCookware

**Problem and change:** `singlePLAN_cover3_mixIng_limitedCookware.py` selects plans for guests under predetermined equipment conditions. The player specifies which cookware to exclude, while the objective remains that of cover3. The original file excludes the grill and steamer by default.

**Constraints and decision:** Let $`\kappa(d)`$ denote the cookware required by a dish, and $`S_0`$ the cookware set available after specified exclusions. Let $`v`$ identify the current equipment-model version and $`\mathcal C_g^v`$ denote its eligible candidates before restriction to an equipment set. Define the restriction operation:

```math
\mathcal C_g^v(S)=
\left\{p=(d,\mathbf A)\in\mathcal C_g^v:\kappa(d)\in S\right\}
```

This section uses $`v=\mathrm{limited}`$ and $`S=S_0`$, comparing candidates in that subset by the objective in Section 1.5. $`S_0`$ is a fixed input restricting the candidate set, forming an equipment-constraint branch independent of the output-format adjustment.

### 1.8 Shared-cookware branch: nCookware

**Problem and change:** `singlePLAN_cover3_mixIng_nCookware.py` makes the equipment set itself a decision. Given the number of cookware types to use, the program selects the specific equipment and assigns an available plan to each guest. This branch and `limitedCookware` each start from the input data, addressing joint equipment selection and fixed equipment exclusion, respectively.

**Constraints and decision:** Let $`G`$ be the guests included in the current planning task, $`H`$ the available cookware associated with owned dishes, and $`n`$ the number of cookware types used in this task. The fixed equipment set $`S_0`$ becomes a set $`S`$ to be chosen:

```math
S\subseteq H,\qquad |S|=n
```

Retain the restriction operation from Section 1.7, now with $`v=\mathrm{nCookware}`$. For a given $`S`$, let $`p_g^\star(S)`$ be the plan selected from $`\mathcal C_g^v(S)`$ by the cover3 objective. Guests with a plan form $`G_S`$, and the number without one is $`z_S=|G\setminus G_S|`$.

**Set-level objective:** The single-guest evaluation order is retained. A new outer comparison aggregates guest evaluations and includes the original program's penalties for missing plans:

```math
\max_{S\subseteq H,\ |S|=n}^{\mathrm{lex}}
\left(
\begin{gathered}
\sum_{g\in G_S}U(H_g^{\mathrm L}(p_g^\star(S))),\\
-\left[\sum_{g\in G_S}C(p_g^\star(S))+10^9z_S\right],\\
\sum_{g\in G_S}R(p_g^\star(S))-10^{18}z_S
\end{gathered}
\right)
```

Under the default three-point eligibility condition, each guest with a plan contributes 3 units of capped benefit. The first criterion therefore prioritizes the number of guests receiving a qualifying plan, followed by total ingredient units and per-guest slack. The two penalty constants retain the original implementation's values and evaluate equipment configurations with missing guest plans; such configurations remain eligible for comparison.

The cookware set is chosen jointly across guests, and $`R(p)`$ is calculated independently from each guest's assumed orders. The model has no shared-inventory constraint aggregating consumption across all guests. The program reuses the best retained candidate for each guest and cookware type before enumerating equipment combinations. The historical multiple-plan branch instead distributes one guest's orders across tags and solves the resulting plan-combination problem.

### 1.9 Version relationships and scope

This main line retains 1 HTML file and 6 PLAN files. Its objectives progress from qualifying-candidate queries through tag-specific plan combinations and single-guest coverage priority to a three-match cap and shared cookware configuration. Within that progression, `mixedingredients` changes presentation and `limitedCookware` changes given constraints. Base-score, profit, regular-guest, and drink analyses are separate supporting branches.

The mathematical notation extends across versions, with candidate sets determined by each version's rules. Tag-equivalent representatives and neutral-filler cutoffs limit the actual search scope, so optimality conclusions apply to retained candidates; global optimality over all legal ingredient combinations has not been established. Supply slack is a ranking criterion that permits negative values, and the model has no hard inventory or guest-budget constraint. Selling price participates in tie-breaking; profit belongs to a separate analysis branch. Chapter 2 explains the tradeoffs at each stage; candidate reduction and solution details appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

<a id="en-evolution"></a>
<a id="en-data"></a>

## 2. Data and modeling rationale

### 2.1 Data sources and quality

The root workbook contains 13 sheets. As parsed by `nCookware`, it includes 62 ingredient records, 164 dish records, and 58 rare guests; 163 dishes are marked as owned.

| Data category | Source | Use |
| :---: | :---: | :---: |
| Recipes, cookware, tags, and guest preferences | Historical workbook; tag data came from AnYiEE's project | Define recipe and tag-matching rules |
| Prices, daily supply, and commission records | Manually recorded by the author during gameplay and compiled into empirical expectations | Daily supply supports resource evaluation; prices support separate economic analysis |
| Trends, owned dishes, and cookware conditions | Workbook records and runtime inputs | Define the scenario for the current query or planning task |

`Total Daily Quantity` supplies the given parameter $`q_i`$ from Chapter 1. The separate price analysis uses quantity weighting. For ingredient $`i`$, let $`\mathcal O_i`$ be the included procurement-channel records, $`\pi_{i\ell}`$ the unit purchase price in record $`\ell`$, and $`w_{i\ell}`$ the corresponding quantity. Then:

```math
\bar\pi_i=
\frac{\sum_{\ell\in\mathcal O_i}w_{i\ell}\pi_{i\ell}}
{\sum_{\ell\in\mathcal O_i}w_{i\ell}},
\qquad \sum_{\ell\in\mathcal O_i}w_{i\ell}>0.
```

$`\pi_{i\ell}`$ and $`\bar\pi_i`$ are measured in in-game currency per ingredient unit, and $`w_{i\ell}`$ in ingredient units. Prices and quantities must cover the same source scope. Commission quantities included in the denominator without a corresponding cash-payment term are assigned zero cash purchase cost under this convention. Time and opportunity costs are excluded.

Complete sampling dates, sample counts, and source versions were not retained, and purchase-price formulas carry risks from row-based association errors and some cached formula errors. The available data describe historical empirical conditions and are insufficient to estimate reliable demand distributions, confidence intervals, or shortage probabilities. Fields and estimation conventions are detailed in the [data provenance notes (Chinese)](docs/data-provenance.md).

### 2.2 Rationale for modeling choices

Early requirements included ranking by actual profit. The subsequent PLAN sequence evaluates preference satisfaction, ingredient consumption, and supply pressure, with price and profit retained as separate analyses. Historical requirements and tradeoffs are documented in the [requirements and design evolution (Chinese)](docs/prompt-journey.md).

| Choice | Rationale and applicable conditions |
| :---: | :---: |
| Measure ingredient units and supply separately | Unit counts represent the quantities used in preparation. Purchase costs and acquisition difficulty may vary among ingredients with equal counts, so daily supply provides a separate measure of resource pressure. |
| Cap coverage and specify priorities | Express the preparation preference for conserving ingredients after meeting the target preferences. The cap and comparison order follow the project requirements; their suitability for other preparation preferences remains to be evaluated. |
| Default to 5 daily orders per guest | Convert per-dish use into daily demand under a scenario assumption. The available records lack empirical order probabilities; equal order allocation in the historical model is also an assumption. |

The PLAN sequence focuses on dishes and additions. Drinks, full satisfaction, and cash profit have not been modeled jointly; guest budget is a display field. Chapter 1 defines each version's decisions, objective changes, and candidate scope.

<a id="en-algorithms"></a>

## 3. Solution algorithms and computational optimization

The programs enumerate, prune, and compare plans within the candidate scopes defined in Chapter 1. This chapter distinguishes complete enumeration within a given ingredient pool, reductions applied before candidate generation, and exact comparisons among retained candidates. The analysis assumes normal data: base recipes use 1–5 ingredient units and supply values are finite.

### 3.1 Enumerating combinations from a given ingredient pool

For guest $`g`$ and dish $`d`$, let the actual enumeration pool be $`(i_1,\ldots,i_{n_{g,d}})`$, with size $`n_{g,d}`$. A base recipe uses 1–5 ingredient units and leaves $`s_d`$ free slots. For $`k`$ additions, DFS selects nondecreasing indices, permitting repeated ingredients while generating each multiset once. Before pruning, the number of combinations is:

```math
\begin{gathered}
s_d=5-\sum_i b_i(d),\qquad 0\le k\le s_d,\\
1\le j_1\le\cdots\le j_k\le n_{g,d}\quad(k\ge1),\\
N_{g,d}=\sum_{k=0}^{s_d}\binom{n_{g,d}+k-1}{k}
=\binom{n_{g,d}+s_d}{s_d}\quad(n_{g,d}\ge1).
\end{gathered}
```

An empty pool can generate only the zero-addition combination. When 「Large portion」 is required and is absent from the dish's original tags, the webpage restricts enumeration to $`k=s_d`$. It partitions dishes into static batches and uses at most 8 Web Workers in parallel; the Python entry points use CPUs. These counts apply to filtered, deduplicated pools, with admission conditions and subsequent filters further restricting output.


#### Bitset evaluation of tag sets

The browser worker retains its original enumeration order, while tag checks use precompiled bitsets. Let $`\mathcal T`$ contain every normalized tag involved in a run, with a unique position assigned to each tag. Any tag set $`X\subseteq\mathcal T`$ has the indicator vector:

```math
\begin{gathered}
\mathbf z(X)=\left(\mathbf 1_{\{t_j\in X\}}\right)_{j=1}^{|\mathcal T|},\\
\mathbf z(X\cup Y)=\mathbf z(X)\lor\mathbf z(Y),\qquad
\mathbf z(X\cap Y)=\mathbf z(X)\land\mathbf z(Y),\\
H_g^{\mathrm L}(p)=\sum_j z_j(T(p))z_j(\mathcal L_g),\qquad
H_g^{\mathrm D}(p)=\sum_j z_j(T(p))z_j(\mathcal D_g).
\end{gathered}
```

Here $`\mathbf 1`$ is an event indicator; $`\lor`$ and $`\land`$ denote componentwise OR and AND. Arrays of 32-bit words store these vectors and grow with the number of tags; population counts give intersection sizes. Fixed dish tags and ingredient bitsets are prepared in advance. Each combination first applies union and adds 「Large portion」 when additions fill all five ingredient slots under the rule. It then applies the four overrides, liked-trend addition, disliked-trend addition, required/excluded checks, and net-score evaluation in that order.

Display tag sets and candidate objects are materialized only for qualifying combinations, preserving original tag insertion order and Chinese collation. Upgrade filtering, subset filtering, procurement vectors, and Top-N ties continue to receive candidates in the same order. The main thread also caches each row's search text to avoid repeated string construction.

<details>
<summary><strong>Click to expand the full text — v1.0.0 · Initial Release</strong></summary>

### 3.1 Enumerating combinations from a given ingredient pool

For guest $`g`$ and dish $`d`$, let the actual enumeration pool be $`(i_1,\ldots,i_{n_{g,d}})`$, with size $`n_{g,d}`$. A base recipe uses 1–5 ingredient units and leaves $`s_d`$ free slots. For $`k`$ additions, DFS selects nondecreasing indices, permitting repeated ingredients while generating each multiset once. Before pruning, the number of combinations is:

<div align="center">

$`\displaystyle \begin{gathered} s_d=5-\sum_i b_i(d),\qquad 0\le k\le s_d,\\ 1\le j_1\le\cdots\le j_k\le n_{g,d}\quad(k\ge1),\\ N_{g,d}=\sum_{k=0}^{s_d}\binom{n_{g,d}+k-1}{k} =\binom{n_{g,d}+s_d}{s_d}\quad(n_{g,d}\ge1). \end{gathered}`$

</div>

An empty pool can generate only the zero-addition combination. When 「Large portion」 is required and is absent from the dish's original tags, the webpage restricts enumeration to $`k=s_d`$. It partitions dishes into static batches and uses at most 8 Web Workers in parallel; the Python entry points use CPUs. These counts apply to filtered, deduplicated pools, with admission conditions and subsequent filters further restricting output.

</details>

### 3.2 The liked-match estimate in Python DFS

The original Python code estimates the liked matches that remaining slots can provide and terminates branches with insufficient estimates. Let $`T_0(d)`$ contain the dish, cookware, and price tags before overrides and trends; $`\delta_\ell`$ is the direct liked-tag count of ingredient $`\ell`$, and $`\Delta_j`$ is the largest increment available from index $`j`$ onward:

```math
\begin{gathered}
\beta_{g,d}=|T_0(d)\cap\mathcal L_g|
+\eta_{\mathrm{large}}+\eta_{\mathrm L}+\eta_{\mathrm D},\\
\delta_\ell=|T(i_\ell)\cap\mathcal L_g|,\qquad
\Delta_j=\max_{\ell\ge j}\delta_\ell.
\end{gathered}
```

Set $`\Delta_{n_{g,d}+1}=0`$ for the empty suffix. Each of the three $`\eta`$ terms equals 1 when its condition holds and 0 otherwise: the large-portion term requires the guest to like 「Large portion」 and free slots to remain; each trend term requires the guest to like that trend tag and a direct base or enumerated-ingredient tag to match its anchors. State $`(j,r,\gamma)`$ records the next minimum index, the remaining unit count, and the accumulated estimate. Initially, $`\gamma=\beta_{g,d}`$; choosing $`\ell\ge j`$ gives state $`(\ell,r-1,\gamma+\delta_\ell)`$.

```math
B(j,r,\gamma)=\gamma+r\Delta_j,\qquad
B(j,r,\gamma) < S_{\min}\ \Longrightarrow\ \text{prune}.
```

The dish-level precheck uses $`\beta_{g,d}+s_d\Delta_1`$. This estimate counts repeated liked tags and ignores dislike penalties. It is a safe upper bound when its initial terms and increments cover every possible newly acquired like. The original trend-reachability check uses only direct tags and can miss a trend triggered by 「Large portion」 generated when all five slots are filled. Relevant-ingredient filtering and the cutoff of at most three neutral fillers also limit the candidate scope. At each leaf, final tags are recalculated and checked for dislikes and the minimum score; details appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).


#### Ingredient-count bounds after reaching capped utility

The first objective of `cover3` is at most 3. Let $`q`$ be an admitted incumbent plan, using the maximization-oriented objective vector $`\mathbf f_g`$ defined in this chapter. Once its utility reaches the cap, any plan using more ingredients is worse in lexicographic order:

```math
U(H_g^{\mathrm L}(q))=3,\quad C(p)>C(q)
\quad\Longrightarrow\quad
\mathbf f_g(q)>_{\mathrm{lex}}\mathbf f_g(p).
```

Search therefore retains branches satisfying $`C(p)\le C(q)`$. Candidates with equal ingredient counts are still fully compared by minimum supply slack, selling price, dish name, and additions string, with the original floating-point comparisons. This bound reduces search visits; feasibility and objective definitions remain those of Chapter 1.

The bound operates at two levels:

1. **Across dishes:** the normal `nCookware` path maintains an incumbent for each cookware type; the other `cover3` entries and fallback path use the single-guest incumbent. Once utility reaches the cap, its total ingredient count bounds addition layers for subsequent dishes.
2. **Within a dish:** addition counts are enumerated in increasing order. When a layer contains a capped-utility plan, that layer is fully enumerated before larger layers are skipped; retained candidates are subsequently compared by the complete objective. Plans below the utility cap do not trigger this stopping condition.

This optimization applies to the four `singlePLAN_cover3*` entries. The candidate-pool function still returns the full original pool by default; uncapped `singlePLAN` and historical `detailedPLAN` retain their search methods. Inputs with duplicate dish names or ingredient names containing multiset-key delimiters use enumeration without this bound, preserving existing cache behavior. Python remains sequential on the CPU; the bound requires neither a GPU nor multiprocessing.

<details>
<summary><strong>Click to expand the full text — v1.0.0 · Initial Release</strong></summary>

### 3.2 The liked-match estimate in Python DFS

The original Python code estimates the liked matches that remaining slots can provide and terminates branches with insufficient estimates. Let $`T_0(d)`$ contain the dish, cookware, and price tags before overrides and trends; $`\delta_\ell`$ is the direct liked-tag count of ingredient $`\ell`$, and $`\Delta_j`$ is the largest increment available from index $`j`$ onward:

<div align="center">

$`\displaystyle \begin{gathered} \beta_{g,d}=|T_0(d)\cap\mathcal L_g| +\eta_{\mathrm{large}}+\eta_{\mathrm L}+\eta_{\mathrm D},\\ \delta_\ell=|T(i_\ell)\cap\mathcal L_g|,\qquad \Delta_j=\max_{\ell\ge j}\delta_\ell. \end{gathered}`$

</div>

Set $`\Delta_{n_{g,d}+1}=0`$ for the empty suffix. Each of the three $`\eta`$ terms equals 1 when its condition holds and 0 otherwise: the large-portion term requires the guest to like 「Large portion」 and free slots to remain; each trend term requires the guest to like that trend tag and a direct base or enumerated-ingredient tag to match its anchors. State $`(j,r,\gamma)`$ records the next minimum index, the remaining unit count, and the accumulated estimate. Initially, $`\gamma=\beta_{g,d}`$; choosing $`\ell\ge j`$ gives state $`(\ell,r-1,\gamma+\delta_\ell)`$.

<div align="center">

$`\displaystyle B(j,r,\gamma)=\gamma+r\Delta_j,\qquad B(j,r,\gamma) < S_{\min}\ \Longrightarrow\ \text{prune}.`$

</div>

The dish-level precheck uses $`\beta_{g,d}+s_d\Delta_1`$. This estimate counts repeated liked tags and ignores dislike penalties. It is a safe upper bound when its initial terms and increments cover every possible newly acquired like. The original trend-reachability check uses only direct tags and can miss a trend triggered by 「Large portion」 generated when all five slots are filled. Relevant-ingredient filtering and the cutoff of at most three neutral fillers also limit the candidate scope. At each leaf, final tags are recalculated and checked for dislikes and the minimum score; details appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

</details>

### 3.3 Dominance filtering and lexicographic selection for one guest

The single-guest `plan_for_guest` function caches the criteria of generated candidates, maintains a nondominated frontier, and selects the best plan. Writing all three criteria in the maximization direction, candidate $`a`$ dominates $`b`$ when:

```math
\begin{gathered}
\mathbf f_g(p)=\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right),\\
f_{g,j}(a)\ge f_{g,j}(b)\quad(j=1,2,3),\qquad
\exists j:\ f_{g,j}(a)>f_{g,j}(b).
\end{gathered}
```

Here $`f_{g,j}`$ is component $`j`$ of the objective vector. A dominated candidate has a strictly worse lexicographic objective and can therefore be removed within the retained candidate set. Uncapped `singlePLAN` uses $`H_g^{\mathrm L}(p)`$ in place of $`U(H_g^{\mathrm L}(p))`$. Define $`\mathrm{best}_g(\mathcal P)`$ to select a plan from nonempty candidate set $`\mathcal P`$ by $`\mathbf f_g`$. If all three criteria tie, it compares selling price in descending order, then dish name and addition string in ascending order. The normal `nCookware` path scans candidates directly to retain the best per cookware type, without constructing this Pareto frontier.

<details>
<summary><strong>Click to expand the full text — v1.0.0 · Initial Release</strong></summary>

### 3.3 Dominance filtering and lexicographic selection for one guest

The single-guest `plan_for_guest` function caches the criteria of generated candidates, maintains a nondominated frontier, and selects the best plan. Writing all three criteria in the maximization direction, candidate $`a`$ dominates $`b`$ when:

<div align="center">

$`\displaystyle \begin{gathered} \mathbf f_g(p)=\left(U(H_g^{\mathrm L}(p)),-C(p),R(p)\right),\\ f_{g,j}(a)\ge f_{g,j}(b)\quad(j=1,2,3),\qquad \exists j:\ f_{g,j}(a)>f_{g,j}(b). \end{gathered}`$

</div>

Here $`f_{g,j}`$ is component $`j`$ of the objective vector. A dominated candidate has a strictly worse lexicographic objective and can therefore be removed within the retained candidate set. Uncapped `singlePLAN` uses $`H_g^{\mathrm L}(p)`$ in place of $`U(H_g^{\mathrm L}(p))`$. Define $`\mathrm{best}_g(\mathcal P)`$ to select a plan from nonempty candidate set $`\mathcal P`$ by $`\mathbf f_g`$. If all three criteria tie, it compares selling price in descending order, then dish name and addition string in ascending order. The normal `nCookware` path scans candidates directly to retain the best per cookware type, without constructing this Pareto frontier.

</details>

### 3.4 Threshold search and state reuse for the historical multiple-plan model

`detailedPLAN` selects a plan for each target tag. With $`J_g`$, $`m_g>0`$, and $`K>0`$ fixed, define the order share per tag as $`\alpha=K/m_g`$. One plan is selected from $`\mathcal C_{g,t}`$ for each tag. The first objective adds across tags, so all tied minimum-unit candidates can be retained separately for each tag:

```math
\begin{gathered}
\mathcal M_{g,t}=\left\{p\in\mathcal C_{g,t}:C(p)=\min_{p'\in\mathcal C_{g,t}}C(p')\right\},\\
\min E_{\mathrm{old}}=\alpha\sum_{t\in J_g}\min_{p\in\mathcal C_{g,t}}C(p).
\end{gathered}
```

The program further merges candidates with identical total ingredient-count vectors. Plans with tied counts but different ingredients remain in the combination search because their supply effects differ. Let $`\lambda`$ be the minimum daily supply-slack threshold in units/day, and define the feasibility indicator $`F_g(\lambda)\in\{0,1\}`$. Select one plan from each $`\mathcal M_{g,t}`$: the indicator is 1 if some combination reaches the minimum-slack threshold, and 0 otherwise. Integer ingredient counts convert a finite threshold condition into capacity bounds:

```math
\begin{gathered}
u_i^{\max}(\lambda)=\left\lfloor\frac{q_i-\lambda}{\alpha}\right\rfloor,\\
R_{\mathrm{old}}\ge\lambda\ \Longleftrightarrow
\forall i,\ u_i=0\ \lor\ u_i\le u_i^{\max}(\lambda).
\end{gathered}
```

Capacity bounds apply only to used ingredients. Lowering $`\lambda`$ relaxes every capacity, so $`\lambda_1\le\lambda_2`$ implies $`F_g(\lambda_2)=1\Rightarrow F_g(\lambda_1)=1`$. Let $`\mathcal I_g`$ contain ingredients that can occur in retained candidates. The five-unit limit per plan gives $`u_i\le5m_g`$, allowing minimum slack to be searched on a finite grid:

```math
\begin{gathered}
\Lambda_g=\{-\infty\}\cup\{q_i-\alpha u:i\in\mathcal I_g,\ u=0,\ldots,5m_g\},\\
\lambda^\star=\max\{\lambda\in\Lambda_g:F_g(\lambda)=1\}.
\end{gathered}
```

The outer binary search locates the highest feasible threshold. The code rounds grid values to 10 decimal places and computes capacities with $`\lfloor(q_i-\lambda)/\alpha+10^{-12}\rfloor`$; $`-\infty`$ is the sentinel for unrestricted capacity. The equivalences above use exact arithmetic, while the original implementation's boundary decisions also reflect these floating-point operations.

Each threshold test first removes candidates that individually exceed capacity, then orders the tags in $`J_g`$ as $`t_1,\ldots,t_{m_g}`$ by increasing candidate count. DFS state $`(r,\mathbf u)`$ records the first $`r`$ processed tags and their accumulated ingredient counts. Writing $`\mathbf c(p)=(c_i(p))_i`$, choosing a plan for the next tag gives:

```math
(r,\mathbf u)\longrightarrow(r+1,\mathbf u+\mathbf c(p)).
```

A branch is pruned as soon as any used ingredient exceeds capacity; nonnegative counts ensure later choices cannot remove the excess. Identical states have identical remaining problems, so the program caches feasibility, with a separate cache for each threshold. Binary search reduces the number of threshold tests; each test still contains a combinatorial search.

After finding $`\lambda^\star`$, the program further maximizes the complete ascending slack vector of used ingredients under those capacities. Let $`\boldsymbol\Phi(r,\mathbf u)`$ be the best terminal vector reachable from the state; a state with no feasible successor is marked infeasible. The following maximum considers only capacity-compliant transitions:

```math
\begin{gathered}
\boldsymbol\rho(\mathbf u)=\mathrm{sort}_{\uparrow}\big((q_i-\alpha u_i)_{i:u_i>0}\big),\\
\boldsymbol\Phi(m_g,\mathbf u)=\boldsymbol\rho(\mathbf u),\\
\boldsymbol\Phi(r,\mathbf u)=\max_{p\in\mathcal M_{g,t_{r+1}}}^{\mathrm{lex}}
\boldsymbol\Phi(r+1,\mathbf u+\mathbf c(p)).
\end{gathered}
```

Each used ingredient type contributes one component. The program caches the best vector, then reconstructs the first combination attaining it in a fixed candidate order. Variable-length vectors follow Python tuple comparison: the larger first differing component wins; when one is a complete prefix of the other, the longer vector wins. The cached state set can still grow substantially. This historical threshold-search route is not called by the normal `nCookware` workflow.

<details>
<summary><strong>Click to expand the full text — v1.0.0 · Initial Release</strong></summary>

### 3.4 Threshold search and state reuse for the historical multiple-plan model

`detailedPLAN` selects a plan for each target tag. With $`J_g`$, $`m_g>0`$, and $`K>0`$ fixed, define the order share per tag as $`\alpha=K/m_g`$. One plan is selected from $`\mathcal C_{g,t}`$ for each tag. The first objective adds across tags, so all tied minimum-unit candidates can be retained separately for each tag:

<div align="center">

$`\displaystyle \begin{gathered} \mathcal M_{g,t}=\left\{p\in\mathcal C_{g,t}:C(p)=\min_{p'\in\mathcal C_{g,t}}C(p')\right\},\\ \min E_{\mathrm{old}}=\alpha\sum_{t\in J_g}\min_{p\in\mathcal C_{g,t}}C(p). \end{gathered}`$

</div>

The program further merges candidates with identical total ingredient-count vectors. Plans with tied counts but different ingredients remain in the combination search because their supply effects differ. Let $`\lambda`$ be the minimum daily supply-slack threshold in units/day, and define the feasibility indicator $`F_g(\lambda)\in\{0,1\}`$. Select one plan from each $`\mathcal M_{g,t}`$: the indicator is 1 if some combination reaches the minimum-slack threshold, and 0 otherwise. Integer ingredient counts convert a finite threshold condition into capacity bounds:

<div align="center">

$`\displaystyle \begin{gathered} u_i^{\max}(\lambda)=\left\lfloor\frac{q_i-\lambda}{\alpha}\right\rfloor,\\ R_{\mathrm{old}}\ge\lambda\ \Longleftrightarrow \forall i,\ u_i=0\ \lor\ u_i\le u_i^{\max}(\lambda). \end{gathered}`$

</div>

Capacity bounds apply only to used ingredients. Lowering $`\lambda`$ relaxes every capacity, so $`\lambda_1\le\lambda_2`$ implies $`F_g(\lambda_2)=1\Rightarrow F_g(\lambda_1)=1`$. Let $`\mathcal I_g`$ contain ingredients that can occur in retained candidates. The five-unit limit per plan gives $`u_i\le5m_g`$, allowing minimum slack to be searched on a finite grid:

<div align="center">

$`\displaystyle \begin{gathered} \Lambda_g=\{-\infty\}\cup\{q_i-\alpha u:i\in\mathcal I_g,\ u=0,\ldots,5m_g\},\\ \lambda^\star=\max\{\lambda\in\Lambda_g:F_g(\lambda)=1\}. \end{gathered}`$

</div>

The outer binary search locates the highest feasible threshold. The code rounds grid values to 10 decimal places and computes capacities with $`\lfloor(q_i-\lambda)/\alpha+10^{-12}\rfloor`$; $`-\infty`$ is the sentinel for unrestricted capacity. The equivalences above use exact arithmetic, while the original implementation's boundary decisions also reflect these floating-point operations.

Each threshold test first removes candidates that individually exceed capacity, then orders the tags in $`J_g`$ as $`t_1,\ldots,t_{m_g}`$ by increasing candidate count. DFS state $`(r,\mathbf u)`$ records the first $`r`$ processed tags and their accumulated ingredient counts. Writing $`\mathbf c(p)=(c_i(p))_i`$, choosing a plan for the next tag gives:

<div align="center">

$`\displaystyle (r,\mathbf u)\longrightarrow(r+1,\mathbf u+\mathbf c(p)).`$

</div>

A branch is pruned as soon as any used ingredient exceeds capacity; nonnegative counts ensure later choices cannot remove the excess. Identical states have identical remaining problems, so the program caches feasibility, with a separate cache for each threshold. Binary search reduces the number of threshold tests; each test still contains a combinatorial search.

After finding $`\lambda^\star`$, the program further maximizes the complete ascending slack vector of used ingredients under those capacities. Let $`\boldsymbol\Phi(r,\mathbf u)`$ be the best terminal vector reachable from the state; a state with no feasible successor is marked infeasible. The following maximum considers only capacity-compliant transitions:

<div align="center">

$`\displaystyle \begin{gathered} \boldsymbol\rho(\mathbf u)=\mathrm{sort}_{\uparrow}\big((q_i-\alpha u_i)_{i:u_i>0}\big),\\ \boldsymbol\Phi(m_g,\mathbf u)=\boldsymbol\rho(\mathbf u),\\ \boldsymbol\Phi(r,\mathbf u)=\max_{p\in\mathcal M_{g,t_{r+1}}}^{\mathrm{lex}} \boldsymbol\Phi(r+1,\mathbf u+\mathbf c(p)). \end{gathered}`$

</div>

Each used ingredient type contributes one component. The program caches the best vector, then reconstructs the first combination attaining it in a fixed candidate order. Variable-length vectors follow Python tuple comparison: the larger first differing component wins; when one is a complete prefix of the other, the longer vector wins. The cached state set can still grow substantially. This historical threshold-search route is not called by the normal `nCookware` workflow.

</details>

### 3.5 Precomputation and enumeration for shared cookware

Shared cookware selection reuses the best candidate for each guest and cookware type. Set $`v=\mathrm{nCookware}`$. For guest $`g`$, cookware $`h`$, and equipment set $`S`$, use Chapter 1's equipment-restricted candidate sets and this chapter's best function. The best function is defined only for nonempty sets: only existing single-cookware results enter these expressions, and the second applies to guests with feasible plans:

```math
\begin{gathered}
p_{g,h}^{\star}=\mathrm{best}_g\left(\mathcal C_g^v(\{h\})\right),\\
p_g^{\star}(S)=\mathrm{best}_g\left(\{p_{g,h}^{\star}:h\in S\}\right).
\end{gathered}
```

For fixed $`S`$, plans and supply calculations are independent across guests, the missing-plan penalty for that set is constant, and each feasible guest's candidate set is the union of single-cookware sets. Selecting the best per cookware type before comparing them therefore preserves the optimal objective. Independent guest optima also attain the best aggregate objective:

```math
\max_{(p_g)\in\prod_{g\in G_S}\mathcal C_g^v(S)}^{\mathrm{lex}}
\sum_{g\in G_S}\mathbf f_g(p_g)
=\sum_{g\in G_S}\mathbf f_g(p_g^{\star}(S)).
```

This decomposition requires a fixed equipment set, the retained candidate scopes, and no shared inventory or other coupling constraints across guests. For $`1\le n\le|H|`$, the outer search enumerates all $`\binom{|H|}{n}`$ sets containing exactly $`n`$ cookware types and compares them by Chapter 1's aggregate objective and missing-plan penalties. Selecting all available cookware yields one set.

Let $`N_{\mathrm{cand}}`$ be the total number of candidates actually returned across all guests. Treating each criterion evaluation as constant cost, comparison work after candidate generation and the size of the best table are, respectively:

```math
O\left(N_{\mathrm{cand}}+\binom{|H|}{n}|G|n\right),\qquad O(|G||H|).
```

The first expression excludes candidate-generation DFS, and the second counts only the guest-by-cookware best table. Relevant-ingredient filtering, equivalence representatives, and filler cutoffs determine the actual candidate scope. Section 3.6 reports a single-machine comparison; cross-device performance has not been systematically measured. Call relationships appear in the [architecture guide (Chinese)](docs/architecture.md), with the full optimality boundaries in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

<details>
<summary><strong>Click to expand the full text — v1.0.0 · Initial Release</strong></summary>

### 3.5 Precomputation and enumeration for shared cookware

Shared cookware selection reuses the best candidate for each guest and cookware type. Set $`v=\mathrm{nCookware}`$. For guest $`g`$, cookware $`h`$, and equipment set $`S`$, use Chapter 1's equipment-restricted candidate sets and this chapter's best function. The best function is defined only for nonempty sets: only existing single-cookware results enter these expressions, and the second applies to guests with feasible plans:

<div align="center">

$`\displaystyle \begin{gathered} p_{g,h}^{\star}=\mathrm{best}_g\left(\mathcal C_g^v(\{h\})\right),\\ p_g^{\star}(S)=\mathrm{best}_g\left(\{p_{g,h}^{\star}:h\in S\}\right). \end{gathered}`$

</div>

For fixed $`S`$, plans and supply calculations are independent across guests, the missing-plan penalty for that set is constant, and each feasible guest's candidate set is the union of single-cookware sets. Selecting the best per cookware type before comparing them therefore preserves the optimal objective. Independent guest optima also attain the best aggregate objective:

<div align="center">

$`\displaystyle \max_{(p_g)\in\prod_{g\in G_S}\mathcal C_g^v(S)}^{\mathrm{lex}} \sum_{g\in G_S}\mathbf f_g(p_g) =\sum_{g\in G_S}\mathbf f_g(p_g^{\star}(S)).`$

</div>

This decomposition requires a fixed equipment set, the retained candidate scopes, and no shared inventory or other coupling constraints across guests. For $`1\le n\le|H|`$, the outer search enumerates all $`\binom{|H|}{n}`$ sets containing exactly $`n`$ cookware types and compares them by Chapter 1's aggregate objective and missing-plan penalties. Selecting all available cookware yields one set.

Let $`N_{\mathrm{cand}}`$ be the total number of candidates actually returned across all guests. Treating each criterion evaluation as constant cost, comparison work after candidate generation and the size of the best table are, respectively:

<div align="center">

$`\displaystyle O\left(N_{\mathrm{cand}}+\binom{|H|}{n}|G|n\right),\qquad O(|G||H|).`$

</div>

The first expression excludes candidate-generation DFS, and the second counts only the guest-by-cookware best table. Relevant-ingredient filtering, equivalence representatives, and filler cutoffs determine the actual candidate scope. Uniform performance benchmarks and cross-device comparisons remain unavailable. Call relationships appear in the [architecture guide (Chinese)](docs/architecture.md), with the full optimality boundaries in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

</details>

### 3.6 Equivalence checks and performance observations

Performance optimization is compared against `v1.0.0` using complete results, row order, and output structure. Python checks cover the four optimized entries, threshold and trend boundaries, guest-by-cookware results, and shared configurations. XLSX members are compared with only creation and modification times normalized, retaining checks of cells, formulas, styles, dimensions, and merges. Browser checks cover option combinations, all guests, bitset boundaries, and trend chains; all three full-workbook benchmark runs produce the same 145 rows in the same order.

| Measurement scope | v1.0.0 median | Current median | Ratio of medians |
| :---: | :---: | :---: | :---: |
| Complete Python `nCookware` run: startup, workbook read, 58-guest planning, five-cookware selection, and workbook write | 106.25 s | 4.15 s | 25.6× |
| Browser candidate-search kernel: 164 dishes, 61 ingredients, sequential execution of one worker | 50.42 s | 19.52 s | 2.58× |

Each row reports three paired timings on the same Windows machine. Python 3.12.14 uses minimum score 3, five daily orders per guest, no liked trend, the Aquatic disliked trend, and all five cookware types. The browser kernel runs under Node.js 24.22.1 for Reimu, minimum score 3, no trends, all four primary filtering/procurement options enabled, both score-aware options disabled, and Top-N 3. This measurement excludes workbook loading, worker startup and message passing, DOM rendering, and browser scheduling. The two rows have different timing scopes and do not support a direct comparison of absolute speed; hardware and background workloads also affect observations.

The interface uses original game icons and pixel borders to organize panels while retaining controls, explanatory text, and export fields. Stop now terminates current workers immediately, invalidates stale messages, and restores controls; completed calculations retain their result rules. Conditions, differential-test counts, and untested scope appear in the [verification record (Chinese)](docs/verification.md).

<a id="en-verification"></a>

## 4. Complete case: rare-guest menus with 「Disliked trend」 set to 「Aquatic」

### 4.1 Scenario and data sources

This case selects dishes and additions for rare guests when 「Aquatic」 triggers 「Disliked trend」 and all five cookware types are available. It applies the cover3 model: after meeting the minimum score with no disliked matches, candidates are compared by capped preference benefit, ingredient units, and minimum supply slack, in that order.

The case uses the author's [historical menu archive](docs/case-study.md), containing 58 guest records. Its filename identifies 「Disliked trend: Aquatic」 and five cookware types; the `5` denotes the cookware count.

Historical reproduction uses the v1.0.0 program and the root [东方夜雀食堂.xlsx](东方夜雀食堂.xlsx), with that version's defaults of daily orders $`K=5`$ and minimum score $`S_{\min}=3`$. Displayed dishes, cookware, and ingredients come from the historical archive; scores and slack are supplementary calculations under these explicit conditions.

<a id="en-methods"></a>
<a id="en-problem"></a>
<a id="en-running"></a>

### 4.2 Inputs and execution

The original workbook supplies ingredient tags, recipes, guest preferences, and daily supply matched by ingredient name. Programs read saved cell results. After changing formulas or their inputs, recalculate and save the workbook in spreadsheet software supporting those formulas. The browser and Python parse this workbook independently.

Run the following commands from the repository root. The complete dependencies require Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
```

The browser can inspect candidates for an individual guest. Start the static service:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Visit <http://127.0.0.1:8000>. The page automatically reads the workbook from the same directory and also accepts manual XLSX imports. Query by guest, score, and filter conditions, then export CSV or XLSX containing the `结果` sheet. See the [browser guide (Chinese)](docs/web-guide.md) for operations.

Use this planning entry point for the case:

```sh
python Python/singlePLAN_cover3_mixIng_nCookware.py
```

Respond to the console prompts in this order:

| Prompt | Input for this case | Meaning |
| :---: | :---: | :---: |
| Liked-trend anchors | Press Enter without typing | No liked-trend condition |
| Disliked-trend anchors | Type `水产`, then press Enter | Final tags containing 「Aquatic」 trigger 「Disliked trend」 |
| Allowed cookware count | Type `5`, then press Enter | Use the prep counter, frying pan, grill, pot, and steamer |

By default, output goes to `稀客料理表/single_mixIng_nCookware/`. Its filename encodes the trend tags and selected cookware, and its `Plans` sheet contains 14 columns with empty icon placeholders. Explicit relative input and output paths are resolved from the script directory, `Python/`. Parameters and fields appear in the [input/output reference (Chinese)](docs/input-output.md); separate analysis scripts produce the score and profit tables.

<a id="en-case-selection"></a>

#### How the complete menu is generated

The program uses the workbook's 163 owned dishes and 58 rare guests to select one plan per guest under this case's settings. It first stores the best candidate for each guest and cookware type, then selects the final plan within the specified equipment set. Base ingredients and additions are combined into the total-ingredients columns for output.

[![Complete historical-menu selection flow and Reimu candidate comparison](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection-en.png)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection-en.png)

[View vector figure (SVG)](https://raw.githubusercontent.com/Mingcode123/Mystia-Menu-Optimizer/ebba2fd8d7b5ff273eeea0e290101d5a98a3f3d6/docs/images/case-selection-en.svg)

The three Reimu rice-ball combinations illustrate eligibility and comparison. The rice ball without additions scores only 2, so its search branch ends early. Honey and cocoa both qualify, tie on capped benefit and ingredient count, and are separated by minimum supply slack. The full search also compares other dishes. When all three criteria tie, the program uses selling price in descending order, followed by dish name and the additions string in ascending order.

All five cookware types are available in this case, leaving one equipment configuration. Selection covers candidates retained by the original program, with supply slack calculated independently per guest. Candidate counts at intermediate stages were not recorded, so the diagram does not infer search size from them.

### 4.3 Historical results

The historical artifact stores dishes, cookware, and total ingredient lists for 58 guests, using 1–3 ingredient units per plan. All five cookware types appear: 24 prep-counter records, 18 pot records, 8 frying-pan records, 6 grill records, and 2 steamer records. All five types are selected in this case, so there is no trade-off between equipment subsets. Under the reproduction settings above, the existing original program reproduced all 58 stored plans.

The following table presents 8 representative records. All 58 records and their sources appear in the [case appendix (Chinese)](docs/case-study.md).

| Guest | Dish | Cookware | Total ingredients | Units | Source row |
| :---: | :---: | :---: | :---: | :---: | :---: |
| <img src="HTML/izakaya_icons_pack/customer_rare/007_%E5%8D%9A%E4%B8%BD%E7%81%B5%E6%A2%A6.png" width="46" height="46" alt="博丽灵梦"><br>博丽灵梦 | <img src="HTML/izakaya_icons_pack/recipe/007_%E9%A5%AD%E5%9B%A2.png" width="52" height="52" alt="饭团"><br>饭团 | 料理台 | 蜂蜜、海苔 | 2 | 8 |
| <img src="HTML/izakaya_icons_pack/customer_rare/015_%E7%90%AA%E9%9C%B2%E8%AF%BA.png" width="46" height="46" alt="琪露诺"><br>琪露诺 | <img src="HTML/izakaya_icons_pack/recipe/032_%E5%87%89%E8%8F%9C%E9%9B%95%E8%8A%B1.png" width="52" height="52" alt="凉菜雕花"><br>凉菜雕花 | 料理台 | 蜂蜜、萝卜 | 2 | 13 |
| <img src="HTML/izakaya_icons_pack/customer_rare/000_%E8%8E%89%E6%A0%BC%E9%9C%B2.png" width="46" height="46" alt="莉格露"><br>莉格露 | <img src="HTML/izakaya_icons_pack/recipe/097_%E7%8B%AE%E5%AD%90%E5%A4%B4.png" width="52" height="52" alt="狮子头"><br>狮子头 | 煮锅 | 葡萄、牛肉、鸡蛋 | 3 | 2 |
| <img src="HTML/izakaya_icons_pack/customer_rare/004_%E4%B8%8A%E7%99%BD%E6%B3%BD%E6%85%A7%E9%9F%B3.png" width="46" height="46" alt="上白泽慧音"><br>上白泽慧音 | <img src="HTML/izakaya_icons_pack/recipe/007_%E9%A5%AD%E5%9B%A2.png" width="52" height="52" alt="饭团"><br>饭团 | 料理台 | 海苔 | 1 | 6 |
| <img src="HTML/izakaya_icons_pack/customer_rare/002_%E6%A9%99.png" width="46" height="46" alt="橙"><br>橙 | <img src="HTML/izakaya_icons_pack/recipe/049_%E8%9C%9C%E6%B1%81%E5%8F%89%E7%83%A7.png" width="52" height="52" alt="蜜汁叉烧"><br>蜜汁叉烧 | 烧烤架 | 蜂蜜、猪肉 | 2 | 4 |
| <img src="HTML/izakaya_icons_pack/customer_rare/011_%E7%BA%A2%E7%BE%8E%E9%93%83.png" width="46" height="46" alt="红美铃"><br>红美铃 | <img src="HTML/izakaya_icons_pack/recipe/011_%E7%82%92%E8%82%89%E4%B8%9D.png" width="52" height="52" alt="炒肉丝"><br>炒肉丝 | 油锅 | 南瓜、猪肉 | 2 | 12 |
| <img src="HTML/izakaya_icons_pack/customer_rare/016_%E5%9B%A0%E5%B9%A1%E5%B8%9D.png" width="46" height="46" alt="因幡帝"><br>因幡帝 | <img src="HTML/izakaya_icons_pack/recipe/100_%E6%A8%B1%E8%8A%B1%E5%B8%83%E4%B8%81.png" width="52" height="52" alt="樱花布丁"><br>樱花布丁 | 蒸锅 | 蜂蜜、桃子 | 2 | 17 |
| <img src="HTML/izakaya_icons_pack/customer_rare/005_%E8%8C%A8%E6%9C%A8%E5%8D%8E%E6%89%87.png" width="46" height="46" alt="茨木华扇"><br>茨木华扇 | <img src="HTML/izakaya_icons_pack/recipe/001_%E8%B1%86%E8%85%90%E5%91%B3%E5%99%8C.png" width="52" height="52" alt="豆腐味噌"><br>豆腐味噌 | 煮锅 | 萝卜、豆腐 | 2 | 7 |

Total ingredients include the base recipe and additions, in the historical sheet order; each listed name represents one unit. Guest and dish icons use the original game assets in this repository. Game names retain their dataset spelling.

### 4.4 Checking Reimu's stored plan against the source data

Historical row 8 selects a rice ball and the prep counter for Hakurei Reimu, using one honey and one seaweed. The original recipe identifies seaweed as the base ingredient and honey as the addition.

| Stage | Source data and rule | Calculated result |
| :---: | :---: | :---: |
| Base dish | The rice ball has 「Vegetarian」「Home-style」「Filling」「Japanese-style」「Affordable」. Seaweed satisfies the recipe; its 「Vegetarian」「Fresh」 tags do not automatically transfer to the dish | Reimu likes 「Filling」「Affordable」; 0 dislikes and base score 2. The original score table stores the same result in `Scores!A987:F987` |
| Add honey | Honey supplies 「Sweet」 in `食材!B39:G39`; the prep counter also contributes its cookware tag to the final tag set | 「Sweet」 adds one liked match, bringing the total to 3 likes and 0 dislikes |
| Apply the trend condition | The final tags do not contain 「Aquatic」, and no liked-trend anchor is set | This plan gains neither 「Disliked trend」 nor 「Liked trend」 |

The final tags are 「Vegetarian」「Home-style」「Filling」「Japanese-style」「Affordable」「Prep counter」「Sweet」. Let $`g`$ denote Hakurei Reimu and $`p`$ the rice ball with honey:

```math
\begin{gathered}
H_g^{\mathrm L}(p)=3,\qquad H_g^{\mathrm D}(p)=0,\qquad S_g(p)=3-0=3,\\
C(p)=1+1=2,\qquad U(H_g^{\mathrm L}(p))=\min(3,3)=3.
\end{gathered}
```

Cells `D6` and `D2` of the original workbook's `食材merchant_data` sheet store daily supplies of 47 seaweed and 68 honey units. At five orders per guest per day, using one unit of each ingredient per order:

```math
R(p)=\min(47-5\times1,\ 68-5\times1)=42.
```

Under these conditions, the historical plan meets the 3-point threshold, uses 2 ingredient units, and has minimum daily supply slack of 42 units. Slack is calculated for this guest independently, without deducting other guests' use; it is a model metric based on empirical supply.

Two eligible candidates for the same dish illustrate the objective tradeoff. The original candidate function recalculated the following plans under this case's conditions; neither has disliked matches:

| Plan | Net score $`S_g(p)`$ | Capped benefit $`U(H_g^{\mathrm L}(p))`$ | Units $`C(p)`$ | Minimum slack $`R(p)`$ (units/day) |
| :---: | :---: | :---: | :---: | :---: |
| Rice ball + honey | 3 | 3 | 2 | 42 |
| Rice ball + cocoa beans | 4 | 3 | 2 | 10 |

Cocoa beans produce one more liked match, but both plans have capped benefit 3 and use two ingredient units. Supply slack therefore determines their order, favoring honey. These actual candidates illustrate the shift from maximizing matches to conserving resources after meeting the coverage target.

### 4.5 Verification scope

Reproduction compares dish, cookware, and total ingredient multiset by guest name, excluding ingredient order and worksheet layout. Hashes of the original program, input workbook, and historical result file were unchanged before and after execution. The full comparison and existing browser and distributed-file checks appear in the [verification record (Chinese)](docs/verification.md); explanatory examples for objective capping and candidate compression appear in the [optimization model and algorithm boundaries (Chinese)](docs/design.md).

<a id="en-limits"></a>

Reproducibility applies to the stated inputs and candidate scope. Gameplay returns, effectiveness compared with manual preparation, and inventory constraints across guests require independent verification.

<a id="en-sources"></a>

## 5. Contributions and references

This is an unofficial personal modeling case study and supporting tool.

| Contributor | Work and attribution |
| :---: | :---: |
| Author | Identified gameplay problems, clarified rules, and specified decision units, evaluation order, filters, and cookware conditions; manually recorded prices, supply, and commission data, and evaluated results through character and parameter cases |
| AI assistance | Much of the code, algorithm derivation, and some debugging were AI-assisted; the author clarified requirements, selected model tradeoffs, and evaluated results |
| Third-party material | Tag data came from [AnYiEE's project](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant); game artwork attribution, dependency licenses, and figure production are described in the [third-party notices (Chinese)](THIRD_PARTY_NOTICES.md) |

Detailed references are organized by purpose:

| Document | Content |
| :---: | :---: |
| [Complete historical menu](docs/case-study.md) | 58 stored plans, source records, and reproduction checks |
| [Optimization model and algorithm boundaries (Chinese)](docs/design.md) | Variables, objectives, set evaluation, and candidate scope |
| [Requirements and design retrospective (Chinese)](docs/prompt-journey.md) | Historical requirements, objective changes, tradeoffs, and case evidence |
| [Data provenance (Chinese)](docs/data-provenance.md) | Manual observations, upstream material, and estimation conventions |
| [Verification record (Chinese)](docs/verification.md) | Observation conditions, reproduction checks, and untested scope |
| [System architecture (Chinese)](docs/architecture.md) | Execution boundaries, data flows, and file responsibilities |
| [Input/output reference (Chinese)](docs/input-output.md) | Workbook fields, options, paths, and output formats |
| [Browser guide (Chinese)](docs/web-guide.md) | Operations, filter semantics, and boundary behavior |
