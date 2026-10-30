# 架构与执行路径

## 系统边界

项目提供两个独立的本地执行入口：浏览器中的原网页程序，以及 `Python/` 下各自运行的原始脚本。它们读取 Excel 工作簿，没有彼此调用的 API，也没有计算服务器。浏览器的 HTTP 服务仅传输静态文件。

```text
东方夜雀食堂.xlsx ──→ 浏览器 SheetJS ──→ 主线程解析 ──→ Web Workers
                                                          │
HTML/icon_map.js + HTML/izakaya_icons_pack/ ──→ 显示                 候选／筛选／导出
                                                          │
                                                  CSV 或单表 XLSX

东方夜雀食堂.xlsx ──→ Python 原脚本 ──→ 原交互与候选搜索 ──→ 规划 XLSX
                      │
                      └──→ 基础得分／利润／菜单分析（独立入口）
```

## 文件与职责

| 文件或目录 | 职责 |
| --- | --- |
| [index.html](../index.html) | 完整原网页：结构、样式、主线程、解析、Worker 源码字符串、筛选与导出 |
| [HTML/xlsx.full.min.js](../HTML/xlsx.full.min.js) | 随包 SheetJS，读取及写出工作簿 |
| [HTML/icon_map.js](../HTML/icon_map.js)、[HTML/izakaya_icons_pack/](../HTML/izakaya_icons_pack/) | 名称到稀客头像、料理图片的显示映射 |
| [东方夜雀食堂.xlsx](../东方夜雀食堂.xlsx) | 七表运行快照，保留原程序所读缓存值 |
| [Python/](../Python/) | 11 个原始 Python 文件，按用途保留独立入口 |
| [data/workbook-provenance.json](../data/workbook-provenance.json) | 运行快照的来源、哈希和制作范围审计 |

架构中的解析、搜索、筛选和导出是逻辑职责，不表示它们被拆成独立文件。发布 `index.html` 是原 `INDEX.html` 的完整副本，只将入口文件名改为小写；其原有相对资源目录保留。完整文件对照范围见[验证记录](verification.md)。

## 网页执行

1. 页面请求同目录 `东方夜雀食堂.xlsx`，也允许用户从原文件选择器载入 XLSX。
2. SheetJS 将工作表交给原解析函数，构建食材、料理、稀客与供给数据。
3. 用户选择稀客和条件后，主线程按料理分块，创建最多 8 个 CPU Web Worker。
4. Worker 枚举追加食材、计算标签并执行所选过滤，分批回传结果和进度。
5. 主线程维护结果、筛选和排序状态，按原规则生成 CSV 或 `结果` 工作表。

Worker 通过脚本字符串和 Blob URL 创建，消息只在当前浏览器内传递。原“停止”机制发送消息；同步搜索繁忙时不能保证及时处理。筛选与导出还有空集合回退行为，不应把界面按钮的存在解释为已满足强取消或空导出保证。

头像与料理图片不进入标签枚举或 TDQ 比较，也不嵌入导出的八列候选表。工作簿不需要图像映射 sheet。详细字段和边界见[输入输出](input-output.md)及[网页指南](web-guide.md)。

## Python 执行

### nCookware 主入口

[Python/singlePLAN_cover3_mixIng_nCookware.py](../Python/singlePLAN_cover3_mixIng_nCookware.py) 在一个文件中保留数据对象、Excel 解析、标签处理、候选生成、厨具比较、交互和 XLSX 写出。

```text
解析原参数 → 切换到脚本目录 → openpyxl读取Excel缓存值
          → 流行喜爱／厌恶输入 → 厨具数量输入
          → 每客每厨具候选 → 枚举共同厨具集合
          → 自动文件名 → Plans十四列工作簿
```

其正常主流程调用 `choose_best_cookware_combo_global()`。脚本中仍保留旧多方案函数；文件头或函数存在本身不能证明它们参与本次主入口运行。

候选搜索采用原 DFS、等价代表和相关加料筛选。原始 TDQ 用于等价成员偏好，基础耗用在候选余量中汇总；它没有改为完整的组内容量分配求解器。中性补位最多前三项仍保留。详细目标与实现范围见[设计说明](design.md)。

### 其他入口

`detailedPLAN.py`、`singlePLAN.py`、覆盖封顶及厨具分支各自保留规划与输出逻辑。`base_score.py`、`Export_Profit.py` 和 `Classes/夜雀食堂料理推荐.py` 是独立分析工具，不能将整个目录视为一个统一 CLI 的多个别名。

Python 通过 `openpyxl` 读写规划工作簿，利润与类菜单还使用 `pandas`。原脚本直接操作 Excel，没有运行时 JSON 协议、转换器或浏览器后台服务。

## 数据与输出边界

公开工作簿是原缓存值的数据容器，保留七张程序使用的表。公式、原图像映射表、笔记及私有路径不随快照分发，Icon 列清空；不修正历史采购价、不变更 `Owned`。该处理不意味着重新验证全部游戏事实。

输出路径和表结构由各原入口决定。`Plans` 的图标列为空占位，网页显示图片来自独立资源，二者不是同一种图像输出流程。原程序对异常数据的容错、跳过与默认值也各不相同，不能从一个入口的成功运行推定另一入口接受相同文件。

## 一致性核对

原程序发布副本按源码、资源路径、工作簿缓存值和同条件输出分别核对。检查事实见[验证记录](verification.md)；源代码一致与小规模运行一致，不等同于全数据规模的最优性或性能保证。
