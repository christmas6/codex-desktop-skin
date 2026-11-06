// Independent, local CDP theming implementation. No upstream code included.
(async function applyDesktopSkin(config) {
  const root = document.documentElement;
  const specs = config.playlist || [{poster: config.poster, css: config.css}];
  const chunks = window.__nightCityPlaylistChunks || [window.__nightCityChunks];
  if (!specs.length || specs.length !== chunks.length || chunks.some(c => !c?.length)) throw Error('Playlist media is incomplete');
  const urls = [];
  try {
    for (const media of chunks) urls.push(URL.createObjectURL(new Blob(media, {type: 'video/mp4'})));
  } catch (error) {
    urls.forEach(url => URL.revokeObjectURL(url));
    throw error;
  }
  delete window.__nightCityChunks;
  delete window.__nightCityPlaylistChunks;
  if (window.__nightCity) window.__nightCity.restore();
  const style = document.createElement('style');
  style.id = 'nc-style';
  const background = document.createElement('div');
  background.id = 'nc-background';
  background.setAttribute('aria-hidden', 'true');
  const video = document.createElement('video');
  video.muted = true;
  video.defaultMuted = true;
  video.loop = specs.length === 1;
  video.autoplay = false;
  video.playsInline = true;
  video.preload = 'auto';
  background.append(video);
  const controls = document.createElement('details');
  controls.id = 'nc-controls';
  controls.innerHTML = '<summary title="壁纸设置">◈ 壁纸</summary><section><strong>动态壁纸</strong><label>背景亮度<input aria-label="背景亮度" type="range" min="20" max="100" value="70"></label><button type="button" data-action="previous">上一张</button><button type="button" data-action="next">下一张</button><button type="button" data-action="pause">暂停动态背景</button><button type="button" data-action="restore">恢复原界面</button><small>静音播放 · 后台自动暂停</small></section>';
  const pauseButton = controls.querySelector('[data-action="pause"]');
  let userPaused = false;
  let restored = false;
  let index = 0;
  let lastError = null;
  const history = [];
  const mode = config.playback?.mode || 'sequential';
  const interval = config.playback?.intervalSeconds || null;
  const initialBrightness = root.style.getPropertyValue('--nc-wallpaper');
  const initialPriority = root.style.getPropertyPriority('--nc-wallpaper');
  const oldAttribute = root.getAttribute('data-night-city');
  const visibility = () => {
    if (restored) return;
    if (document.hidden || userPaused) video.pause();
    else if (video.ended && specs.length > 1) next();
    else video.play().catch(error => {
      if (!restored && !document.hidden && error.name !== 'AbortError') {
        lastError = String(error);
        pauseButton.textContent = '点击播放背景';
      }
    });
  };
  const select = (target, remember = true) => {
    if (restored) return;
    if (remember) {
      history.push(index);
      if (history.length > 100) history.shift();
    }
    index = (target + specs.length) % specs.length;
    lastError = null;
    video.pause();
    video.poster = specs[index].poster;
    style.textContent = specs[index].css || config.css;
    video.src = urls[index];
    video.load();
    visibility();
  };
  const next = () => {
    const target = mode === 'shuffle' && specs.length > 1
      ? (index + 1 + Math.floor(Math.random() * (specs.length - 1))) % specs.length
      : (index + 1) % specs.length;
    select(target);
  };
  const previous = () => select(history.length ? history.pop() : index - 1, false);
  const ended = () => { if (!restored && !userPaused && !document.hidden) next(); };
  const failed = () => { lastError = video.error?.message || '视频载入失败'; };
  const observer = new MutationObserver(() => {
    if (restored) return;
    if (!background.isConnected) document.body.prepend(background);
    if (!style.isConnected) document.head.append(style);
    if (!controls.isConnected) document.body.append(controls);
  });
  // Playback time excludes background/manual pauses; short videos advance on ended.
  const timer = specs.length > 1 && interval ? setInterval(() => {
    if (!restored && !document.hidden && !userPaused && !video.paused && video.currentTime >= interval) next();
  }, 250) : null;
  const cleanup = () => {
    if (restored) return;
    restored = true;
    if (timer !== null) clearInterval(timer);
    observer.disconnect();
    document.removeEventListener('visibilitychange', visibility);
    video.removeEventListener('ended', ended);
    video.removeEventListener('error', failed);
    video.pause();
    video.removeAttribute('src');
    video.load();
    urls.forEach(url => URL.revokeObjectURL(url));
    background.remove(); controls.remove(); style.remove();
    if (oldAttribute === null) root.removeAttribute('data-night-city');
    else root.setAttribute('data-night-city', oldAttribute);
    if (initialBrightness) root.style.setProperty('--nc-wallpaper', initialBrightness, initialPriority);
    else root.style.removeProperty('--nc-wallpaper');
    delete window.__nightCity;
  };
  window.__nightCity = {
    video, restore: cleanup, version: 2, next, previous,
    pause() { userPaused = true; pauseButton.textContent = '继续播放背景'; visibility(); },
    resume() { userPaused = false; pauseButton.textContent = '暂停动态背景'; visibility(); },
    setStyle(css) { specs[index].css = css; style.textContent = css; },
    playlistStatus() { return {index, count: specs.length, title: specs[index].title || String(index + 1), mode, intervalSeconds: interval, userPaused, lastError}; }
  };
  controls.querySelector('input').addEventListener('input', event => root.style.setProperty('--nc-wallpaper', String(Number(event.target.value) / 100)));
  pauseButton.addEventListener('click', () => userPaused ? window.__nightCity.resume() : window.__nightCity.pause());
  controls.querySelector('[data-action="previous"]').addEventListener('click', previous);
  controls.querySelector('[data-action="next"]').addEventListener('click', next);
  controls.querySelector('[data-action="restore"]').addEventListener('click', cleanup);
  root.setAttribute('data-night-city', 'v2');
  document.head.append(style);
  document.body.prepend(background);
  document.body.append(controls);
  document.addEventListener('visibilitychange', visibility);
  video.addEventListener('ended', ended);
  video.addEventListener('error', failed);
  observer.observe(document.body, {childList: true});
  select(0, false);
  try {
    await new Promise((resolve, reject) => {
      if (video.readyState >= 1) return resolve();
      const finish = error => {
        clearTimeout(timeout);
        video.removeEventListener('loadedmetadata', loaded);
        video.removeEventListener('error', errorHandler);
        if (error) reject(error); else resolve();
      };
      const loaded = () => finish();
      const errorHandler = () => finish(Error(video.error?.message || '视频载入失败'));
      const timeout = setTimeout(() => finish(Error('视频载入超时')), 10000);
      video.addEventListener('loadedmetadata', loaded);
      video.addEventListener('error', errorHandler);
    });
    visibility();
    return {applied: true, playing: !video.paused, backgroundPaused: document.hidden, playlist: window.__nightCity.playlistStatus(), width: video.videoWidth, height: video.videoHeight};
  } catch (error) {
    cleanup();
    throw error;
  }
})
