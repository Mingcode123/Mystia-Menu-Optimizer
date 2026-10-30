# 第三方组件与来源说明

本文件说明公开展示包中包含的第三方软件，以及项目开发时使用过的参考来源。本项目代码目前尚未额外授予开源许可证；第三方组件继续遵循各自的许可证。这里的依赖说明与来源致谢不构成对第三方内容的重新许可。

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

本公开包未附带这些游戏图标、sprite、完整上游仓库、原始游戏备份或第三方攻略资料。运行演示使用为本项目制作的合成数据，实际游戏工作簿由使用者自行导入。合成数据用于验证输入、计算和展示流程，不代表真实游戏的完整规则或数值。

历史 Excel 包含上游标签和作者手工记录、计算的数据，完整字段来源链与原始观测记录仍待补齐，因此不随本包分发。本说明不将相同的游戏事实或字段结构直接认定为代码复制，也不声称历史业务实现绝对独立于所有参考材料。若后续确认纳入了上游受许可约束的实现，应记录具体文件、使用方式和适用条件。

上游项目采用 AGPL 并不使这个仅在文档中引用它的展示包自动采用 AGPL；此处也不作“任何来源义务均已排除”的保证。应按实际纳入的内容确定各部分的许可范围。

## 个人贡献与 AI 协作

项目作者提出需求、游戏规则假设、约束和迭代方向，手工记录价格、供给与委托数据并计算期望，开发过程中使用 AI 辅助实现与调试。本次整理继续使用 AI 协助梳理架构、整理代码与说明、构造合成演示数据和执行验证。第三方库、上游提供的标签数据和游戏美术不计作作者原创成果；作者的采集、建模与计算工作另行说明。

