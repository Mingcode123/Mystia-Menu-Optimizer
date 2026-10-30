# 第三方组件、数据与素材声明

本文件记录仓库中第三方软件、游戏数据和图像素材的来源及适用声明。本项目代码尚未单独选定开源许可证；第三方内容的许可与归属按其来源分别列示。

## SheetJS Community Edition 0.20.3

[HTML/xlsx.full.min.js](HTML/xlsx.full.min.js) 用于网页读取和写出 XLSX。仓库分发 SheetJS 完整构建，并保留文件中的版权标记。

- 项目与文档：[SheetJS](https://sheetjs.com/)、[官方许可证说明](https://docs.sheetjs.com/docs/miscellany/license/)。
- 许可证：[Apache License 2.0 完整文本](licenses/SheetJS-LICENSE.txt)。
- 归属：[SheetJS-NOTICE.txt](licenses/SheetJS-NOTICE.txt)。
- SHA-256：`cc015130aa8521e7f088f88898eba949ccdcbfb38df0bd129b44b7273c3a6f41`。

完整构建包含以下第三方组件：

| 组件 | 文件中版本 | 上游 |
| --- | --- | --- |
| CFB | 1.2.2 | [SheetJS/js-cfb](https://github.com/SheetJS/js-cfb)，Apache-2.0 |
| CRC32 | 1.2.0 | [SheetJS/js-crc32](https://github.com/SheetJS/js-crc32)，Apache-2.0 |
| cptable | 1.15.0 | [SheetJS/js-codepage](https://github.com/SheetJS/js-codepage)，Apache-2.0 |

Python、openpyxl、pandas 通过运行环境或依赖安装提供，其许可随各自软件分发。

## 游戏、标签与运行工作簿

项目研究对象为[《东方夜雀食堂》](https://store.steampowered.com/app/1584090/__Touhou_Mystias_Izakaya/)。游戏名称、角色及美术等内容的相关权利归各自权利人。本项目为非官方个人项目。

作者确认，历史工作簿的标签资料来源于 [AnYiEE/touhou-mystia-izakaya-assistant](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)。留存的上游下载资料版本字段为 `1.11.18`，其软件许可声明为 AGPL-3.0-only；仓库附有[完整许可文本](licenses/AnYiEE-AGPL-3.0.txt)。实际导入标签对应的精确历史提交未完整留存。来源确认范围为标签资料，其他字段的来源与记录条件见[数据来源说明](docs/data-provenance.md)。

[东方夜雀食堂.xlsx](东方夜雀食堂.xlsx) 为作者提供的完整工作簿，包含 13 张工作表及其公式、缓存值、格式、图片、Icon 字段和元数据。价格、日供给及委托记录包含作者的手工采集和经验计算；完整观测次数、日期及采样过程未留存。

工作簿按原文件分发，文件哈希及一致性记录见[工作簿审计](data/workbook-provenance.json)。

## 图像素材

[HTML/icon_map.js](HTML/icon_map.js) 与 [HTML/izakaya_icons_pack/](HTML/izakaya_icons_pack/) 提供名称映射、58 张稀客头像和 163 张料理图片。映射文件与 PNG 来自作者留存的素材目录。

像素对照显示，这些图标与上游资料中的 `customer_rare.png`、`recipe.png` 图集一致。图像属于第三方游戏素材，用于角色与料理识别。上游[项目说明](https://izakaya.cc/about) 对游戏素材和软件许可作分别声明；AGPL 软件许可不构成游戏美术的统一授权。

仓库分发范围包括完整工作簿和上述网页素材。上游完整仓库、游戏备份、第三方攻略及原始聊天未纳入分发范围。

## 作者与 AI 协作

[README 图标流程图](docs/images/tag-example.png) 使用 OpenAI 内置图像生成工具制作，以原工作簿和代码核对的饭团案例为依据，并参考作者留存素材包中的饭团、蜂蜜、猪肉、海苔及博丽灵梦图标。该图为 AI 生成的规则示意，非游戏截图，也非原图标的逐像素拼贴；参考图标涉及的游戏角色与美术归属沿用上述游戏素材声明。图像生成不改变参考素材的权利归属。

作者负责提出游玩需求、规则语义、目标顺序、约束及迭代方向，手工整理经营记录，并通过角色案例和程序输出检查实现。大量程序编码、算法推导及部分调试采用 AI 辅助。项目文档整理问题定义、设计决策、数学模型、架构、输入输出及验证范围。

第三方库、上游标签资料及游戏美术的归属独立于作者的数据采集、需求设计和项目整理工作。
