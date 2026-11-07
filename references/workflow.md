# 制作与验证流程

## 1. 检查素材、当前界面与上游方法

使用用户给定路径检查实际文件。`.lnk` 只通过 `WScript.Shell.CreateShortcut(...).TargetPath` 读取目标，不执行。不存在时先说明实际情况；不要猜测素材已获得。图片、MP4、MP3 的能力不同：本模板仅直接播放静音 MP4，照片可转换，音频播放需另行实现。

如果任务要求调查 GitHub，用可用 GitHub 插件读取 README 与相关源码，记录确切仓库和方法，不能只凭搜索摘要断言兼容。原有研究来源见案例，不必每次重复搜索。不要直接运行陌生安装器；本方案自己生成本地注入文件。

运行 `skin.py status` 检查当前主题。自动发现只输出进程中的 `--remote-debugging-port` 数字，不泄露完整命令行。目标为 `type=page`、URL 前缀 `app://-/index.html` 且不含 `initialRoute`；必须唯一。没有现成调试会话时检查用户原有启动器与安装方式，再决定下一步，不自动杀进程或重启。

兼容实测为 Windows Store Codex 26.1103.3517.0 与本机中文启动器。应用更新可能更改 DOM。后续版本先检查节点和样式，再使用模板；这不是官方主题插件 API。

## 2. 准备轻量播放文件

用 FFmpeg/ffprobe 检查时长、分辨率、帧率、编码与音轨。保留原始素材，另外生成播放副本。不要把用户的大型壁纸或截图装进技能。

典型压缩命令（输入和输出路径作为独立参数传给进程）：

```text
ffmpeg -hide_banner -nostdin -i SOURCE -map 0:v:0
 -vf "scale='min(1920,iw)':-2,fps=24" -an
 -c:v libx264 -preset veryfast -crf 25
 -maxrate 2000k -bufsize 4000k -pix_fmt yuv420p
 -movflags +faststart -threads 4 OUTPUT.mp4
```

输出使用新路径，不加覆盖已有文件的 `-y`。竖屏素材可改为同时约束宽高并保持比例，避免无谓放大。检查完整时长、偶数尺寸及播放效果；当前控制器限制准备后的 MP4 在 100 MiB 内。大文件应先压缩，不能把原始几百 MiB 数据直接塞入 renderer。

封面示例：`ffmpeg -ss 35 -i SOURCE -frames:v 1 -q:v 3 poster.jpg`，时间点必须在素材范围内。照片可用 `-loop 1 -i PHOTO -t 1 -vf "scale='min(1920,iw)':-2,fps=1" -an -c:v libx264 -pix_fmt yuv420p still.mp4`，并生成 JPEG 封面；转换后验证，不能直接将 PNG 当视频。

优先使用已安装 FFmpeg。确需下载工具时使用可信发布源并校验散列，不捆绑进技能。此用户的 FFmpeg 曾从校验过的 imageio-ffmpeg 包取得，但临时路径不构成永久依赖。

用 `create_theme.py` 复制模板、播放副本和封面到新主题目录。它检查容器头、大小与 JPEG 标记，不能代替完整解码验证。`theme.json` 中 `video` 和 `poster` 为主题目录内相对路径；CSS/JS 从目录加载。模板是独立实现，只参考上游 CDP 思路，不包含上游代码。

## 3. 注入和生命周期

`skin.py apply --theme-dir ...` 通过 512 KiB base64 块传输视频，renderer 内转 Uint8Array，再生成 MP4 Blob URL；无需额外媒体服务器。`inject.js` 在应用前恢复旧实例，避免重复背景。多视频的配置、总大小限制和切换方式见 [播放列表](playlist.md)。

原生命名空间为 `window.__nightCity`、`#nc-background`、`#nc-style`、`#nc-controls` 和根节点 `data-night-city`。沿用命名可直接更新现有夜之城主题。应用的主题目录应是自己生成或已审阅的目录，因为其中 JS 会在当前页面执行。

视频 `muted=true`，单视频 `loop=true`；多视频关闭单片循环，由结束事件切换至下一项。`document.hidden` 时暂停；回到前台后，仅非手动暂停时恢复。后台 `AbortError` 不应设置为用户手动暂停，也不是视频损坏。不要在后台循环强制播放。

恢复操作断开 MutationObserver、移除 visibilitychange 监听、暂停并清空视频、释放 Blob URL、删除注入节点和运行状态、还原原根属性与内联亮度。它不撤销另行修改的客户端深色设置。

## 4. 局部调整

从壁纸提取基色与强调色，给正文、占位文字、菜单和代码区域保留可读对比度。不要把所有元素一律透明，也不要用一个全局文本色掩盖图标问题。夜之城模板的青蓝色仅为此用户案例的起点。

后续反馈通常只需改 `theme.css` 并运行 `style`：替换 `#nc-style.textContent`，验证视频源未变化。这样不重新传输、不重置播放、不丢编辑器内容。不要使用整页 reload 来应用 CSS。

针对浮窗、磨砂框、原生按钮、顶部黑框及上下接缝，读取 [案例修复](case-study.md)。只改用户指出的区域，检查实际 DOM 和伪元素及相邻层，不因一次选择器零命中就认定问题消失。

## 5. 验证与交付

- `status` 检查单一背景层、视频尺寸/时长、静音循环与错误状态。前台相隔短时间检查 currentTime 增长；后台 paused=true 合理。
- 隐藏浮窗检查 computed display 为 none，client rects 为 0。模板默认隐藏，但其他用户可要求显示。
- 输入框检查 `.ProseMirror` 仍可编辑，`elementFromPoint` 命中编辑器或其子节点，磨砂背景透明度适当；不发送测试消息。
- 顶部检查标题表面、包含它的 header 和独立 `MainContentTopFade`（含伪元素），确认背景透明、渐变和模糊已清除；标题可能挂载在表面外，应检查实际可见文字的 color 与 -webkit-text-fill-color。模板标题色可自定义，不沿用其他用户的个人色值。
- 底部渐变检查实际节点的 backgroundImage 为 none、颜色透明，并查看截图；如 fades 数组为空，需重新定位，不能直接宣布成功。
- CDP 截图直接调用 `Page.captureScreenshot`，不要等待后台会被暂停的 requestAnimationFrame。截图可能包含聊天隐私，仅本地保存。
- 原生标题栏按钮可能不出现在 CDP 截图里，应使用 Windows 屏幕捕获检查；操作前确认前台目标，避免把快捷键发到其他应用。
- 最小化/被遮挡的窗口不能只靠 `Page.bringToFront` 保证恢复。需要实际查看时可用 Windows `ShowWindowAsync(hwnd,9)`、`SetForegroundWindow`；随后重新检查 visibility。

首次应用在用户允许的环境中验证恢复与重应用。单纯创建技能或只改 CSS 时，不额外 apply/restore 当前主题。交付主题文件、截图、调用方式与恢复命令；说明会话作用域和外观设置的持久性，不声称已安装自动启动。
