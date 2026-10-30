# 第三方组件与来源说明

本文件说明公开展示包中的第三方软件、游戏数据与图标来源。本项目代码目前尚未单独选定开源许可证；第三方内容保留各自的归属和许可范围。软件许可证、游戏美术和作者的采集记录分别说明。

## 随包提供的软件

### SheetJS Community Edition 0.20.3

`web/vendor/xlsx.full.min.js` 用于在浏览器中读取 Excel 工作簿。它是 SheetJS 的第三方库，整理时按原文件复制，未修改、重新压缩或移除其中的版权标记。

- 项目与文档：[SheetJS](https://sheetjs.com/)、[官方许可证说明](https://docs.sheetjs.com/docs/miscellany/license/)
- 许可证：Apache License 2.0，完整文本见 [licenses/SheetJS-LICENSE.txt](licenses/SheetJS-LICENSE.txt)
- 归属声明：见 [licenses/SheetJS-NOTICE.txt](licenses/SheetJS-NOTICE.txt)
- 本地文件 SHA256：`cc015130aa8521e7f088f88898eba949ccdcbfb38df0bd129b44b7273c3a6f41`

版本号取自库的 `XLSX.version`。文件头保留了 `xlsx.js (C) 2013-present SheetJS`。完整构建还包含 SheetJS 的容器、校验和与代码页处理组件，不能将这些内嵌组件视作本项目实现：

| 内嵌组件 | 本地可识别版本 | 上游与许可 |
| --- | --- | --- |
| CFB | 1.2.2 | [SheetJS/js-cfb](https://github.com/SheetJS/js-cfb)，[Apache-2.0](https://github.com/SheetJS/js-cfb/blob/master/LICENSE) |
| CRC32 | 1.2.0 | [SheetJS/js-crc32](https://github.com/SheetJS/js-crc32)，[Apache-2.0](https://github.com/SheetJS/js-crc32/blob/master/LICENSE) |
| 代码页表 `cptable` | 1.15.0 | [SheetJS/js-codepage](https://github.com/SheetJS/js-codepage)，[Apache-2.0](https://github.com/SheetJS/js-codepage/blob/master/LICENSE) |

上述组件作为原始 SheetJS 完整构建的一部分保留。归属文件补充 CFB 和 CRC32 上游版权标记，不改写库文件。今后更新依赖时，应同时更新版本、哈希和归属记录。

Python 运行时及通过依赖管理器安装的软件不包含在本仓库中，其许可随相应软件分发，不受本项目代码的许可状态影响。

## 游戏与历史参考项目

项目研究的游戏为 [《东方夜雀食堂》](https://store.steampowered.com/app/1584090/__Touhou_Mystias_Izakaya/)。游戏名称、角色、美术与其他原始游戏内容的相关权利归各自权利人。本项目是个人辅助工具与作品集展示，与游戏官方没有隶属关系。

项目作者确认，历史工作簿中的标签数据来自 [AnYiEE 的东方夜雀食堂小助手](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant)。本地留存快照的版本字段为 `1.11.18`，其源代码声明使用 [AGPL-3.0-only](https://github.com/AnYiEE/touhou-mystia-izakaya-assistant/blob/master/LICENSE)。这项来源确认针对标签数据，不据此推定全部配方或其他字段都来自同一仓库。历史本地图标与该项目整理的游戏 sprite 内容一致；游戏美术权利与上游软件许可证应分开理解，参见 [上游项目说明](https://izakaya.cc/about)。

对于游戏内价格和供给的波动，项目作者说明自己手动记录并计算期望值，涉及 `Total Daily Quantity`、`commission`、`Buy Price1`、`Daily Quantity1`、`Sell Price`、`Buy Price` 等数量、委托与价格字段。这部分数据采集和期望计算属于作者的项目工作。现有材料尚未完整记录原始观测次数、观测时间和采样过程，不能将这些期望值描述为经过独立验证的游戏常数。

## 随包提供的游戏数据与图标

| 发布文件 | 来源与整理方式 |
| --- | --- |
| [data/game.json](data/game.json) | 从作者提供的 `东方夜雀食堂.xlsx` 提取食材、料理、稀客和食材供给四表；标签来源为上述 AnYiEE 项目，价格与供给记录由作者整理，其他字段不统一声明原创 |
| [web/game-data.js](web/game-data.js) | 上述 JSON 的脚本副本，通过 [tools/sync_demo.py](tools/sync_demo.py) 生成 |
| [data/game-import-report.json](data/game-import-report.json) | 记录源工作簿哈希、按名称关联的价格修正、未知值与不可规划料理 |
| [web/icon-map.js](web/icon-map.js)、[web/icons/](web/icons/) | 从作者提供的原图标包选取稀客和料理两类：58 张稀客头像、163 张料理图片，PNG 原样复制，映射改用仓库相对路径 |

来自上游的标签资料保留 AnYiEE 的来源与 AGPL-3.0-only 许可说明；完整上游许可证附于 [licenses/AnYiEE-AGPL-3.0.txt](licenses/AnYiEE-AGPL-3.0.txt)。该文本取自作者保留的上游 `1.11.18` 下载快照；工作簿当年实际导入标签的精确提交未留存。数据处理保留为可读 JSON，转换规则、修改记录和原文件哈希见[数据说明](docs/data-provenance.md)及导入审计。

图标像素已与该上游快照的 `customer_rare.png`、`recipe.png` sprite 对照一致。游戏美术及角色相关权利属于原权利人，图标不计作本项目原创资产。上游在[项目说明](https://izakaya.cc/about)中将游戏素材与软件许可分开声明；此处同样不将软件 AGPL 许可证解释为游戏美术的统一授权。图片仅在界面中识别角色与料理，不参与模型计算。

完整原工作簿、上游整个仓库、原始游戏备份和第三方攻略不随包提供。`data/demo.json` 及其浏览器副本仍为独立合成数据，用于受控案例与回归，不代表真实游戏数值。各字段的来源、经验估计方法和未完整记录的采样信息见[数据来源说明](docs/data-provenance.md)。

## 个人贡献与 AI 协作

项目作者提出需求、游戏规则假设、约束和迭代方向，手工记录价格、供给与委托数据并计算期望，开发过程中使用 AI 辅助实现与调试。本次整理继续使用 AI 协助梳理架构、整理代码与说明、构造合成演示数据和执行验证。第三方库、上游提供的标签数据和游戏美术不计作作者原创成果；作者的采集、建模与计算工作另行说明。

