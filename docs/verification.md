# 验证记录

下表记录本次整理在 Windows、Python 3.12.14、Node.js 24.19.0 环境下完成的本地验证。首次公开提交 `fb8371c` 的 [GitHub Actions 检查](https://github.com/Mingcode123/Mystia-Menu-Optimizer/actions/runs/41001697587) 也已于 2026-10-30 通过，Python 检查、网页回归和示例复现检查均成功；后续提交状态以 [Actions](https://github.com/Mingcode123/Mystia-Menu-Optimizer/actions) 为准。

| 范围 | 方法 | 结果 |
| --- | --- | --- |
| Python 规则、规划与 CLI | `python tools/run_checks.py` | 31 项通过，其中导入工具 4 项、规划与 CLI 27 项 |
| 小规模解的对照 | 固定种子生成 90 组输入，对比独立的具体食材多重组合穷举 | 覆盖、件数、余量和确定性结果一致；另覆盖跨组分配与厨具组合 |
| 网页回归 | `node --test tests/web-regression.cjs`，执行实际 Worker 和导入函数 | 11 项通过 |
| 合成示例 | 重建四组 JSON 与基线 CSV | 结果可复现，案例文档中的数值与输出一致 |
| 界面 | 内置浏览器通过本地 HTTP 打开页面，载入样例、筛选并计算 | 显示 3 条旅人候选；已保存 [截图](images/demo.jpg)。内置浏览器策略不允许 file 协议，因此未自动验证双击打开方式 |
| 历史 XLSX 导入 | 仅本地读取源表，按名称关联 | 62 食材、164 料理、58 顾客；修正 61 条采购价关联，3 条未知价保持 null，1 条特殊料理不参与 Python 规划 |
| 真实数据规划 | 本地导入数据、58 位顾客、3 厨具、最低分 3、每客日单量 5、无流行 | 58 位均有方案；逐条复算基础配方、五格限制、禁忌、最终标签、得分、食材计数与余量通过 |

真实数据结果选中料理台、油锅、煮锅。原游戏输入和逐客输出不在公开包中，因此这项兼容性记录不是公开可复现样例；公开可复现部分以 `data/demo.json` 和 `examples/` 为准。供给余量是逐客指标，不表示整晚所有方案能够同时按库存制作。

重点回归包括：禁忌标签与名称分别处理、等价成员替换仍合法、重复基础配方占格、覆盖后触发流行、零阈值、停止时终止全部 Worker、忽略过期消息、空筛选不导出隐藏结果、采购价跨表错位、组内分配考虑基础用量及无解显式报告。

没有完成或不作推断的事项：所有浏览器和设备兼容性、任意参数组合的性能保证、全游戏版本准确性、实际游戏收益对照、联合库存最优、采样显著性，以及 Pages 部署。测试通过说明这些软件规则与用例一致，不替代游戏内验证。

CI 使用官方 [checkout](https://github.com/actions/checkout)、[setup-python](https://github.com/actions/setup-python) 和 [setup-node](https://github.com/actions/setup-node) 执行同一组检查，并检查示例重建是否产生文件差异。

文档展示另作核对：2026-10-30 使用 GitHub Markdown 接口检查 README、数学建模说明与需求复盘中的 118 个公式，均被识别，HTML 实体解码后 TeX 内容保持一致。该检查验证 Markdown 解析；公式最终排版仍由页面渲染器完成。公开架构页的图例与四张视图也已在内置浏览器中实际加载，未见 Mermaid 语法报错。
