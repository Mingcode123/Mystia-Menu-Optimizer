# 第三方组件、数据与图像来源

本文件说明公开包内的软件、运行数据和图像来源。各部分分别保留其归属和适用范围，本项目代码尚未单独选定开源许可证。

## SheetJS Community Edition 0.20.3

[HTML/xlsx.full.min.js](HTML/xlsx.full.min.js) 用于原网页读取和写出 XLSX。文件沿用原完整构建，未移除版权标记。

- 项目与文档：[SheetJS](https://sheetjs.com/)、[官方许可证说明](https://docs.sheetjs.com/docs/miscellany/license/)。
- 许可证：[Apache License 2.0 完整文本](licenses/SheetJS-LICENSE.txt)。
- 归属：[SheetJS-NOTICE.txt](licenses/SheetJS-NOTICE.txt)。
- SHA-256：`cc015130aa8521e7f088f88898eba949ccdcbfb38df0bd129b44b7273c3a6f41`。

完整构建中还包含下列组件，它们不属于本项目原创代码：

| 组件 | 文件中版本 | 上游 |
| --- | --- | --- |
| CFB | 1.2.2 | [SheetJS/js-cfb](https://github.com/SheetJS/js-cfb)，Apache-2.0 |
| CRC32 | 1.2.0 | [SheetJS/js-crc32](https://github.com/SheetJS/js-crc32)，Apache-2.0 |
| cptable | 1.15.0 | [SheetJS/js-codepage](https://github.com/SheetJS/js-codepage)，Apache-2.0 |

Python、openpyxl、pandas 通过运行环境或依赖安装提供，其许可随各自软件分发。

## 游戏、标签与运行工作簿

研究对象为[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/__Touhou_Mystias_Izakaya/)。游戏名称、角色和美术等原始内容的相关权利归各自权利人。本项目与游戏官方没有隶属关系。

作者确认，历史工作簿的标签资料来自 [AnYiEE/touhou-mystia-izakaya-assistant](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)。保留的上游下载快照版本字段为 `1.11.18`，其软件声明使用 AGPL-3.0-only；[完整许可文本](licenses/AnYiEE-AGPL-3.0.txt) 随附。实际导入标签的精确历史提交未完整留存，不能据此推定所有配方、价格或其他字段均来自同一仓库。

[东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) 是作者工作簿的七表运行数据快照。价格、日供给和委托相关记录包含作者的手工采集与经验计算；原观测次数、日期和完整采样过程未完整保存。快照保留原缓存值，不修正采购价或 Owned；Icon 列清空，公式、原图像映射表、笔记及私人路径不随快照分发。

来源哈希和制作范围见[工作簿审计](data/workbook-provenance.json)，字段及经验口径见[数据来源说明](docs/data-provenance.md)。审计用于说明数据容器，不是新的规划程序。

## 随包图像

[HTML/icon_map.js](HTML/icon_map.js) 与 [HTML/izakaya_icons_pack/](HTML/izakaya_icons_pack/) 提供原名称映射、58 张稀客头像和 163 张料理图片。映射文件和所需 PNG 从原目录原样复制，沿用原相对路径。

这些图标的像素与上游快照的 `customer_rare.png`、`recipe.png` sprite 对照一致。图像不计作本项目原创资产。上游[项目说明](https://izakaya.cc/about) 将游戏素材与软件许可分别声明；本说明同样不将软件 AGPL 许可证解释为游戏美术的统一授权。图像只用于识别角色与料理，不参与模型计算。

完整原工作簿、上游整套仓库、原始游戏备份、无关素材、第三方攻略和原始聊天不随包提供。

## 作者与 AI 协作

作者提出游玩需求、规则语义、目标顺序、约束及迭代方向，手工整理经营记录，并以具体角色和输出核对实现。大量程序实现、算法推导和部分调试使用 AI 辅助。此次公开文件整理选取原程序及其依赖，补充运行快照与说明文档。

第三方库、上游标签资料及游戏美术不归为作者原创成果。代码、数据采集、标签资料和美术来源按实际内容分别说明，不将“文件整理”视为重新授予第三方内容许可。
