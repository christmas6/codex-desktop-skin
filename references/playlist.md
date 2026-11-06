# 多壁纸播放列表

## 创建与使用

每个 MP4 先准备成轻量播放副本，并提供对应 JPEG 封面。按用户给定顺序传入 `--video`、`--poster`；可选 `--css` 也须逐项对应。

```powershell
python -X utf8 .\scripts\create_theme.py --video .\sunset.mp4 .\city.mp4 --poster .\sunset.jpg .\city.jpg --css .\sunset.css .\city.css --output .\themes\my-playlist
python -X utf8 .\scripts\skin.py apply --theme-dir .\themes\my-playlist
```

默认按顺序播完一项再播放下一项，最后一项播完回到第一项。`--mode shuffle` 每次随机选择与当前不同的一项；不保证一轮内每项都恰好出现一次。`--interval 60` 在每项累计播放到 60 秒时提前切换，若视频更短，则播完即切换。可同时使用随机模式和定时切换。

后台或手动暂停时不累计播放时间，不自动切换。`next` / `previous` 是显式切换命令，即使暂停也可改变当前项，随后仍保持暂停。

```powershell
python -X utf8 .\scripts\skin.py next
python -X utf8 .\scripts\skin.py previous
python -X utf8 .\scripts\skin.py pause
python -X utf8 .\scripts\skin.py resume
python -X utf8 .\scripts\skin.py status
python -X utf8 .\scripts\skin.py restore
```

`status.playlist.index` 为从 0 开始的序号，另含 count、title、mode、intervalSeconds、userPaused 和 lastError。上一项优先使用实际播放历史，最多保存最近 100 次切换。

## 配置格式

`theme.json` 示例：

```json
{
  "name": "sunset-and-city",
  "playlist": [
    {"title": "海上落日", "video": "sunset.mp4", "poster": "sunset.jpg", "css": "sunset.css"},
    {"title": "夜之城", "video": "city.mp4", "poster": "city.jpg", "css": "city.css"}
  ],
  "playback": {"mode": "sequential", "intervalSeconds": null}
}
```

每项未指定 `css` 时使用目录中的 `theme.css`。切换时同时替换当前视频、封面与样式，不触碰编辑器。仍需保留目录根部 `theme.css` 和新版 `inject.js`。

旧的单视频配置 `{ "video": "background.mp4", "poster": "poster.jpg" }` 继续可用，仍单片循环。旧主题若要新增列表，须复制本技能最新的 `assets/template/inject.js` 至主题目录；仅更改 JSON 不足以升级旧引擎。

## 大小与运行约束

- 1–20 项，每个视频最多 100 MiB，列表视频总计最多 200 MiB；在传输前检查，超出时先压缩。
- 当前引擎一次载入全部列表视频为 Blob，内存开销高于压缩文件总大小；不要把数量上限当作推荐规模。
- 手动间隔为 1–86400 秒；不填写则按视频结束切换。
- `style --theme-dir ...` 读取当前项对应的 CSS 并更新该项运行时样式，视频源不变；修改其他项后重新 apply 加载全部配置。
- 切换为直接切换，不保证无缝视频转场，也未实现淡入淡出。
- 当前文件出错时可从 `lastError` 查看信息；不会无限跳过失败项形成重试循环。检查编码后重新应用或用 next 显式切换。
- restore 清除定时器、事件和所有 Blob URL；后台检测和手动暂停状态在整个列表内生效。

## 验证重点

用短的真实 MP4 在独立浏览器验证：自然结束前进、列表回环、随机不连续重复、定时切换、后台恢复、手动暂停、每项配色与完整清理。脚本回归测试：`python -m unittest discover -s tests -v`。

只更新技能功能时保留用户当前主题。用户要求应用列表时再切换当前界面；测试不得发送聊天消息。
