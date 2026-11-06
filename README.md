# Codex Desktop Skin · Codex 桌面换肤技能

一个面向 **Windows Codex 桌面端**的社区 Skill：让 Codex 根据本地视频或截图制作、调整动态壁纸皮肤，并验证实际界面效果。

它既包含供 Codex 阅读的操作方法，也包含可执行的本地脚本和 CSS/JavaScript 模板。安装后可以直接用中文提出换肤需求。它采用当前应用的本地 CDP 调试会话，不修改应用安装包。

## 能做什么

| 功能 | 说明 |
| --- | --- |
| 动态壁纸 | 本地 MP4 静音循环，切后台自动暂停，回到前台继续 |
| 配色适配 | 根据壁纸调整文字、按钮、侧栏、菜单及强调色 |
| 磨砂输入框 | 半透明背景、背景模糊、圆角及清晰的输入文字 |
| 局部调整 | 按截图隐藏主题浮窗、调整透明度或修复底部接缝 |
| 原生按钮排查 | 区分 Windows 窗口按钮和页面元素，改善对比度 |
| 样式热更新 | 只替换 CSS，保留视频源和已有输入内容 |
| 恢复界面 | 移除注入背景、样式、监听器并释放 Blob 资源 |

内置青蓝色模板是起点，Codex 可以按新壁纸调整。已在海上落日素材上验证紫粉配色。仓库不附带壁纸视频、音乐、聊天截图或第三方媒体。

## 环境与支持范围

- Windows，Python **3.10+**，脚本只使用 Python 标准库。
- 需要 Codex 桌面端已有的、仅在本机开放的 Chromium DevTools Protocol（CDP）调试会话。
- 准备播放副本和封面时需要 FFmpeg；仓库不捆绑 FFmpeg。
- 已验证环境：Windows Store Codex **26.1103.3517.0** 配合支持调试的启动器。其他版本或安装渠道请先检查，不保证相同 DOM 选择器一直有效。
- 本项目是社区方案，不是 OpenAI 官方插件或官方主题接口。

## 安装 Skill

1. 下载本仓库的 ZIP 并解压，或通过 Git 克隆仓库。
2. 把包含 `SKILL.md` 的整个仓库目录放入 Codex 的 `skills/codex-desktop-skin` 目录。
3. 默认位置是 `%USERPROFILE%\.codex\skills\codex-desktop-skin`；配置了 `CODEX_HOME` 时则使用其下的 `skills` 目录。

也可以在**仓库根目录**打开 PowerShell 后执行：

```powershell
$skillRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillDestination = Join-Path $skillRoot 'skills\codex-desktop-skin'
if (Test-Path -LiteralPath $skillDestination) { throw '技能已存在，请先检查再更新。' }
New-Item -ItemType Directory -Path $skillDestination -Force | Out-Null
foreach ($entry in @('SKILL.md', 'agents', 'scripts', 'references', 'assets')) {
    Copy-Item -LiteralPath (Join-Path (Get-Location) $entry) -Destination $skillDestination -Recurse
}
```

如果技能列表未更新，重新打开 Codex 或新建聊天再调用。

## 让 Codex 帮你换肤

在 Codex 中输入，并提供可读取的本地文件路径：

```text
使用 $codex-desktop-skin，把背景换成我提供的 MP4，配色跟壁纸一致，保留透明磨砂输入框。
```

后续可以继续说：

```text
使用 $codex-desktop-skin，输入框再透明一点，文字保持清晰。
使用 $codex-desktop-skin，按这张截图修复底部的横向分界线。
使用 $codex-desktop-skin，恢复原界面。
```

Skill 会引导 Codex 检查素材、制作轻量播放副本、生成主题、应用背景并验证，不会自动关闭或重启当前客户端。

## 手动使用脚本

以下 PowerShell 命令均在仓库根目录执行；示例文件名需要替换为你自己的素材。

### 1. 检查连接

```powershell
python -X utf8 .\scripts\skin.py status
```

脚本自动从 `ChatGPT.exe` 进程查找 `--remote-debugging-port`，也可以手动指定：

```powershell
python -X utf8 .\scripts\skin.py status --port 9222
```

若找不到页面，先确认当前安装渠道的 Codex 启动器支持并启用了本地远程调试。Electron 启动参数通常形如 `--remote-debugging-address=127.0.0.1 --remote-debugging-port=9222`，但启动方式取决于安装渠道；已运行的实例可能不会接受新参数。不要把调试端口暴露到公网。

### 2. 准备 MP4 与 JPEG 封面

保留原始文件，在新目录生成 1080p、24 fps、静音副本：

```powershell
New-Item -ItemType Directory -Path .\work -Force | Out-Null
ffmpeg -hide_banner -nostdin -i .\source.mp4 -map 0:v:0 -vf "scale='min(1920,iw)':-2,fps=24" -an -c:v libx264 -preset veryfast -crf 25 -maxrate 2000k -bufsize 4000k -pix_fmt yuv420p -movflags +faststart -threads 4 .\work\prepared.mp4
ffmpeg -hide_banner -nostdin -ss 0 -i .\source.mp4 -frames:v 1 -q:v 3 -update 1 .\work\poster.jpg
```

当前脚本要求播放文件不超过 **100 MiB**。更长的视频需进一步降低码率；竖屏视频应按实际尺寸约束宽高。上面的命令不自动覆盖已有文件。

### 3. 生成并应用主题

```powershell
python -X utf8 .\scripts\create_theme.py --video .\work\prepared.mp4 --poster .\work\poster.jpg --output .\themes\my-theme
python -X utf8 .\scripts\skin.py apply --theme-dir .\themes\my-theme
```

生成的目录包含 `theme.json`、`theme.css`、`inject.js`、`background.mp4`、`poster.jpg`。只应用自己生成或已审阅的主题目录，`inject.js` 会在应用页面内执行。

### 4. 修改样式、查看状态与恢复

修改生成目录中的 `theme.css` 后：

```powershell
python -X utf8 .\scripts\skin.py style --theme-dir .\themes\my-theme
python -X utf8 .\scripts\skin.py status
python -X utf8 .\scripts\skin.py screenshot --output .\screenshots\preview.png
python -X utf8 .\scripts\skin.py restore
```

截图必须使用新文件名。截图会包含当前应用界面，默认留在本地；仓库忽略 `screenshots/`、`themes/`、`work/` 与音视频文件。

## 常见问题

**关闭或刷新后皮肤消失？** 当前实现只作用于当前页面会话，完整刷新或重新启动后需要再次应用；没有安装开机常驻程序。

**窗口在后台时 `paused: true`？** 这是节能行为。回到前台后应自动继续，除非用户手动暂停。

**右上角三个窗口按钮看不清？** 它们可能是 Windows 原生控件，不能只靠页面 CSS 任意改色。在已验证版本中，客户端“设置 → 外观 → 深色”使用白色图标。外观设置会保存；`restore` 不会撤销该设置，需要手动切回原模式。

**还有一条底部横线？** 渐变层可能是输入框 footer 外的兄弟节点。应检查实际 DOM、计算样式和截图，不能以选择器没有匹配为成功依据。详见[案例说明](references/case-study.md)。

**支持照片和 MP3 吗？** 当前引擎直接支持 MP4。照片可先转换为静态 MP4，再实际验证；MP3 背景音乐尚未实现。

## 文件结构

```text
SKILL.md                  Codex 技能入口
agents/openai.yaml        技能展示信息与调用提示
scripts/skin.py           检查、应用、更新样式、截图与恢复
scripts/cdp_client.py     本机 WebSocket/CDP 客户端
scripts/create_theme.py   生成主题目录
assets/template/          CSS 与注入脚本模板
references/workflow.md    详细制作与验证流程
references/case-study.md  已验证的修复案例
```

## 参考与许可

本项目参考以下仓库介绍的 CDP 换肤思路，仓库中的脚本和模板为本项目独立实现：

- [Codex AutoSkin](https://github.com/Finderchangchang/codex-autoskin)
- [Codex Dream Skin](https://github.com/Fei-Away/Codex-Dream-Skin)
- [HeiGe Codex Skin Studio](https://github.com/HeiGeAi/heige-codex-skin-studio)
- [Codex Dynamic Skin](https://github.com/CCDawn/Codex-Dynamic-Skin)

代码与文档采用 [MIT License](LICENSE)。壁纸、音乐与其他第三方素材不包含在此授权中，请自行准备有权使用的素材。
