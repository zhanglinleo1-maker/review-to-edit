# review-to-edit · 映记剪辑协作 Skill

从素材回顾与讲解资料出发，检查证据、制定故事与带图脚本、制作粗剪，并按目标软件交付可编辑工程。作者：[zhanglinleo1-maker](https://github.com/zhanglinleo1-maker)。

## 映记应用下载

- [映记发布与下载仓库](https://github.com/zhanglinleo1-maker/yingji-releases)
- [映记安装包与版本说明](https://github.com/zhanglinleo1-maker/yingji-releases/releases)

映记负责素材回顾、录音、识别与资料交接；本Skill指导支持Skill的Agent完成创作与剪辑。使用本Skill不自动取得素材、云服务或编辑器权限。

## 安装与开始使用

把本仓库作为名为 `review-to-edit` 的Skill安装到支持 `SKILL.md` 的Agent环境，保留references和scripts目录；也可让Agent先读取本仓库SKILL.md及其引用。可从本仓库Releases下载完整ZIP。

示例：使用review-to-edit。资料入口是……，这是新项目。先检查资料、提出方向并集中确认需求；不生成声音、视频或工程，不调用付费模型。已有想法是……。

- [Skill入口](SKILL.md)
- [完整详细规则](docs/AI粗剪执行详细规则.md)
- [素材整理与剪辑协作规则](docs/AI素材整理与剪辑协作规则.md)
- [可选个人风格案例](references/personal-healing-narration.md)：个人参考，非通用默认。

脚本确认后，尚未选定审阅载体时展示Demo／可编辑工程两条路线及推荐；已有选择或明确委托不重复询问。本机剪映兼容草稿在已获相应交付授权、目录可靠且权限允许时新增落地，并保留独立副本。不会覆盖已有草稿、修改根索引或自动接管编辑器。

## 版本与能力边界

此公开版基于v0.5.11，公开发布标识为 `v0.5.11-public.1`。仅清理个人措辞和内部版本记录；未添加新的流程或审批。不附历史素材、个人录音、账号或模型权重。

Skill不是一键剪辑软件，不自带TTS/BGM服务、剪辑软件、全格式导出器或安装器。工程组件只处理约定的JSON登记与检查；文档、结构校验与实际编辑器验收分开记录。部分方法经验来自特定剪映版本，不保证所有软件和版本兼容。

## 许可与来源

Skill指令、此仓库文档与自有辅助组件采用[MIT许可证](LICENSE)：允许使用、修改和再分发（包括商业使用），须保留作者版权声明与许可文本。原始来源：https://github.com/zhanglinleo1-maker/review-to-edit 。欢迎在衍生版本说明来源及修改。

MIT不自动适用于映记应用本体、品牌LOGO、用户素材、第三方软件或服务；各自权利和许可单独适用。本仓库不包含映记整个应用项目，也不公开任何私有仓库历史。
