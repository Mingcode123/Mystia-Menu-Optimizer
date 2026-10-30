# 验证记录

下表记录本次整理在 Windows、Python 3.12.14、Node.js 24.19.0 环境下完成的本地验证。首次公开提交 `fb8371c` 的 [GitHub Actions 检查](https://github.com/Mingcode123/Mystia-Menu-Optimizer/actions/runs/41001697587) 也已于 2026-10-30 通过，Python 检查、网页回归和示例复现检查均成功；后续提交状态以 [Actions](https://github.com/Mingcode123/Mystia-Menu-Optimizer/actions) 为准。

| 范围 | 方法 | 结果 |
| --- | --- | --- |
| Python 规则、规划与 CLI | `python tools/run_checks.py` | 31 项通过，其中导入工具 4 项、规划与 CLI 27 项 |
| 小规模解的对照 | 固定种子生成 90 组输入，对比独立的具体食材多重组合穷举 | 覆盖、件数、余量和确定性结果一致；另覆盖跨组分配与厨具组合 |
| 网页回归 | `node --test tests/web-regression.cjs`，执行实际 Worker 和导入函数 | 13 项通过；新增默认真实数据、两种数据切换检查，并验证头像／料理映射及图片存在 |
| 合成示例 | 重建四组 JSON 与基线 CSV | 结果可复现，案例文档中的数值与输出一致 |
| 真实数据界面 | 内置浏览器通过本地 HTTP 打开页面，检查角色列表，搜索并选择博丽灵梦后计算 | 58 位稀客头像全部加载；灵梦头像和结果中的料理图片正常显示。最低分 3、开启加料子集过滤与等价食材去重时生成 3,937 条候选 |
| 合成界面留档 | 早期合成数据筛选与计算 | 当时显示 3 条旅人候选；保留 [历史截图](images/demo.jpg)，不作为当前默认数据界面的截图 |
| 历史 XLSX 导入 | 仅本地读取源表，按名称关联 | 62 食材、164 料理、58 顾客；修正 61 条采购价关联，3 条未知价保持 null，1 条特殊料理不参与 Python 规划 |
| 真实数据规划 | 本地导入数据、58 位顾客、3 厨具、最低分 3、每客日单量 5、无流行 | 58 位均有方案；逐条复算基础配方、五格限制、禁忌、最终标签、得分、食材计数与余量通过 |

本次真实数据接入另从原工作簿重新导出，四表内容与先前本地核验版本一致。发布输入为 [data/game.json](../data/game.json)，导入修正见 [game-import-report.json](../data/game-import-report.json)。重新运行三厨具、最低分 3、每客日单量 5、无流行的规划，58 位顾客均有方案，选中料理台、油锅、煮锅。完整结果随 [game-plan.json](../examples/game-plan.json) 和 [game-plan.csv](../examples/game-plan.csv) 提供，`tools/reproduce_examples.py` 同时重建四组合成案例及该游戏快照结果。供给余量是逐客指标，不表示整晚所有方案能够同时按库存制作。

重点回归包括：禁忌标签与名称分别处理、等价成员替换仍合法、重复基础配方占格、覆盖后触发流行、零阈值、停止时终止全部 Worker、忽略过期消息、空筛选不导出隐藏结果、采购价跨表错位、组内分配考虑基础用量及无解显式报告。

没有完成或不作推断的事项：所有浏览器和设备兼容性、双击 HTML 的 file 协议运行、任意参数组合的性能保证、全游戏版本准确性、实际游戏收益对照、联合库存最优、采样显著性，以及 Pages 部署。测试通过说明这些软件规则与用例一致，不替代游戏内验证。

CI 使用官方 [checkout](https://github.com/actions/checkout)、[setup-python](https://github.com/actions/setup-python) 和 [setup-node](https://github.com/actions/setup-node) 执行同一组检查，并检查示例重建是否产生文件差异。

文档展示另作核对：2026-10-30 重写 README 后，使用 GitHub Markdown 接口检查 README 的 48 个公式、数学建模说明的 65 个公式和需求复盘的 9 个公式，共 122 个，均被识别，HTML 实体解码后 TeX 内容保持一致。该检查验证 Markdown 解析；公式最终排版仍由页面渲染器完成。公开架构页的图例与四张视图此前已在内置浏览器中实际加载，未见 Mermaid 语法报错。

此前 README 结构改写检查了中英章节、公式、运行命令和文档链接的一致性，并通过独立读者审阅。本次真实数据与图片接入后重新运行 31 项 Python 检查和 13 项网页检查；Python 求解器与网页 Worker 计算代码保持不变。
