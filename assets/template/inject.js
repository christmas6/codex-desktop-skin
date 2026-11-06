// Original implementation inspired by the CDP theming approach studied in
// Codex AutoSkin / Codex Dream Skin. This file does not include their code.
(async function applyNightCity(config) {
  const root = document.documentElement;
  if (window.__nightCity) window.__nightCity.restore();
  const style = document.createElement('style');
  style.id = 'nc-style';
  style.textContent = config.css;
  const background = document.createElement('div');
  background.id = 'nc-background';
  background.setAttribute('aria-hidden', 'true');
  const video = document.createElement('video');
  video.muted = true;
  video.defaultMuted = true;
  video.loop = true;
  video.autoplay = false;
  video.playsInline = true;
  video.preload = 'auto';
  video.poster = config.poster;
  const objectUrl = URL.createObjectURL(new Blob(window.__nightCityChunks, {type: 'video/mp4'}));
  delete window.__nightCityChunks;
  video.src = objectUrl;
  background.append(video);
  const controls = document.createElement('details');
  controls.id = 'nc-controls';
  controls.innerHTML = '<summary title="夜之城动态主题设置">◈ 夜之城</summary><section><strong>夜之城 · 动态主题</strong><label>背景亮度<input aria-label="背景亮度" type="range" min="20" max="100" value="70"></label><button type="button" data-action="pause">暂停动态背景</button><button type="button" data-action="restore">恢复原界面</button><small>静音循环 · 切到后台自动暂停</small></section>';
  const pauseButton = controls.querySelector('[data-action="pause"]');
  let userPaused = false;
  let restored = false;
  const initialBrightness = root.style.getPropertyValue('--nc-wallpaper');
  const initialPriority = root.style.getPropertyPriority('--nc-wallpaper');
  const oldAttribute = root.getAttribute('data-night-city');
  const cleanup = () => {
    if (restored) return;
    restored = true;
    observer.disconnect();
    document.removeEventListener('visibilitychange', visibility);
    video.pause();
    video.removeAttribute('src');
    video.load();
    URL.revokeObjectURL(objectUrl);
    background.remove(); controls.remove(); style.remove();
    if (oldAttribute === null) root.removeAttribute('data-night-city');
    else root.setAttribute('data-night-city', oldAttribute);
    if (initialBrightness) root.style.setProperty('--nc-wallpaper', initialBrightness, initialPriority);
    else root.style.removeProperty('--nc-wallpaper');
    delete window.__nightCity;
  };
  const visibility = () => {
    if (document.hidden || userPaused) video.pause();
    else video.play().catch(e => {
      if (!document.hidden && e.name !== 'AbortError') pauseButton.textContent = '点击播放背景';
    });
  };
  const observer = new MutationObserver(() => {
    if (restored) return;
    if (!background.isConnected) document.body.prepend(background);
    if (!style.isConnected) document.head.append(style);
    if (!controls.isConnected) document.body.append(controls);
  });
  window.__nightCity = {video, restore: cleanup, version: 1};
  controls.querySelector('input').addEventListener('input', e => {
    root.style.setProperty('--nc-wallpaper', String(Number(e.target.value) / 100));
  });
  pauseButton.addEventListener('click', () => {
    userPaused = !userPaused;
    pauseButton.textContent = userPaused ? '继续播放背景' : '暂停动态背景';
    visibility();
  });
  controls.querySelector('[data-action="restore"]').addEventListener('click', cleanup);
  root.setAttribute('data-night-city', 'v1');
  document.head.append(style);
  document.body.prepend(background);
  document.body.append(controls);
  document.addEventListener('visibilitychange', visibility);
  observer.observe(document.body, {childList: true});
  await new Promise((resolve, reject) => {
    if (video.readyState >= 1) return resolve();
    const timer = setTimeout(() => reject(new Error('视频载入超时')), 10000);
    video.addEventListener('loadedmetadata', () => { clearTimeout(timer); resolve(); }, {once:true});
    video.addEventListener('error', () => { clearTimeout(timer); reject(new Error(video.error?.message || '视频载入失败')); }, {once:true});
  });
  if (document.hidden) {
    video.pause();
    return {applied: true, playing: false, backgroundPaused: true, width: video.videoWidth, height: video.videoHeight};
  }
  try {
    await video.play();
    visibility();
  } catch (e) {
    if (!document.hidden && e.name !== 'AbortError') pauseButton.textContent = '点击播放背景';
    return {applied: true, playing: false, backgroundPaused: document.hidden, reason: String(e)};
  }
  return {applied: true, playing: !video.paused, width: video.videoWidth, height: video.videoHeight};
})
