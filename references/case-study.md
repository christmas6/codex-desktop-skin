# 夜之城案例：用户反馈与最终修复

以下为开发验证案例的视觉选择。复用方法，具体颜色和隐藏项目以当前请求为准。

## 上游研究

考察了以下开源仓库的 README/相关实现，归纳本机 CDP 注入路线：

- https://github.com/Finderchangchang/codex-autoskin
- https://github.com/Fei-Away/Codex-Dream-Skin
- https://github.com/HeiGeAi/heige-codex-skin-studio
- https://github.com/CCDawn/Codex-Dynamic-Skin

HeiGe README 提到 Store/MSIX 真机兼容尚未验证，不能以仓库存在替代本机验证。官方文档当时读取返回 403，未据此确立官方任意音视频主题支持。实现采用自己的本地脚本，不修改应用安装包。

## 素材与首次应用

最初的桌面快捷方式未取得有效素材；后来用户提供实际 MP4。源视频约 757 MiB、3840×2160、29.97 fps、约 199.9 秒，含 AAC 音轨。生成 1920×1080、24 fps、无音轨的完整播放副本，19,982,757 字节，约 19 MiB；封面取 35 秒。

本地 CDP 上传成功后生成 Blob 视频，壁纸使用 cover 填充，增加冷色遮罩，侧栏与菜单使用深青色，正文浅蓝白。切后台自动暂停、回到前台恢复。一次错误曾把后台播放失败当作“用户主动暂停”，修正为仅用户按钮改变手动暂停标记。

WebSocket 握手曾遇到 `HTTP/1.1 101 WebSocket Protocol Handshake`。应检查状态码 101 和准确的 Sec-WebSocket-Accept，不依赖 reason phrase 恰好为 Switching Protocols。

## 反馈一：隐藏“◈ 夜之城”悬浮控件

需求是隐藏主题浮窗。最终 `#nc-controls { display:none !important; }`，验证 display none、零 client rect。保留脚本恢复入口，而不是删除恢复能力。此偏好已作为当前模板默认值。

## 反馈二：三个原生窗口按钮不可见、配色违和

需求是让三个窗口按钮清晰可见，并与壁纸协调。右上角最小化、最大化、关闭属于 Windows 原生覆盖层，DOM CSS 无法直接改这些图标。

初次给按钮下方加浅色 138×36 背板，用户认为违和，因此移除。最终通过客户端“设置 → 外观 → 深色”得到白色图标，无额外背板。研究到的 `setTitleBarOverlay` 行为为深色模式白图标、浅色模式 #1f1f1f；没有确认任意单独图标配色 API。

必要时的 UI 操作线索：确认 Codex 是前台后 Ctrl+, 打开设置；查找“外观 / Appearance”按钮，选择 `input[name="appearance-theme"][aria-label="深色"]`（英文 Dark）；可检查 `window.electronBridge.getSystemThemeVariant()` 为 dark；通过“返回应用 / Back to app”返回。界面可能被用户中途关闭，必须重新检查，不使用陈旧节点。

原模式为浅色。这个改动写入客户端设置，不属于 CSS 恢复范围；后续如需完整恢复，要另外切回记录的模式。原生按钮截图用 Windows 屏幕捕获，不能只看 CDP 页面截图。

## 反馈三：底部违和，输入框改透明磨砂

需求是使用透明磨砂输入框，并让界面与壁纸协调。最终保留浮动输入框，选择器为 `[class*="ComposerLayoutRoot"]`：

- 渐变底 `rgba(29,58,70,.32)` 至 `rgba(6,22,32,.38)`。
- `backdrop-filter: blur(22px) saturate(125%)`，圆角 20px。
- 极淡内阴影描边，聚焦时稍加强。原生规则可能强制 border none，故 inset shadow 比只设置 border 更可靠。
- body/input/footer 子层透明，附件卡片用半透明青色，占位文字保证可见。

检查 `.ProseMirror` 编辑能力与命中测试，没有发送测试聊天。修改直接替换样式，视频 Blob 源保持不变。

## 反馈四：清理底部残留分界线

最初只清理 footer 内背景，底部仍有横向接缝。实际存在两层：

1. `[class*="background-"][class*="surface-"]` 底部不透明底板。
2. `[class*="background-"][class*="fade-"]` 上方约 32px 渐变。它是 footer 外的兄弟节点，footer 子查询找不到它。

最终清理：

```css
html[data-night-city] [data-thread-scroll-footer="true"],
html[data-night-city] [data-thread-scroll-footer="true"]::before,
html[data-night-city] [data-thread-scroll-footer="true"]::after,
html[data-night-city] [class*="background-"][class*="fade-"],
html[data-night-city] [data-thread-scroll-footer="true"] [class*="background-"][class*="surface-"] {
  background: transparent !important;
  box-shadow: none !important;
}
```

最后全局定位实际 fade 节点，验证 backgroundImage 为 none、backgroundColor 为 rgba(0,0,0,0)，并看实际截图确认壁纸连续。注意 Composer 自身的淡描边是用户所要磨砂框的一部分，不能为了去横线一起抹掉。

模板的 fade 选择器是当前版本的经验选择器。新版若复用相似类名，先检查匹配节点范围，再决定是否改用更具体的结构关系。

## 已支持与边界

已实测本机视频背景、隐藏浮窗、客户端深色原生按钮、磨砂输入框、底部接缝修复、后台暂停和恢复。当前技能附带的是这些结果的模板与通用化脚本。未实现 MP3 背景音乐；照片转换流程需按新素材实际验证。没有安装启动持久化服务，没有把用户的视频和私人截图打包进技能。
