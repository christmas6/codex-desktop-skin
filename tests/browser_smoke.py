import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode=True
repo=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Real H.264 playlist checks in an isolated headless browser')
parser.add_argument('--browser',required=True,type=Path)
parser.add_argument('--ffmpeg',required=True,type=Path)
parser.add_argument('--work-dir',type=Path,default=repo/'work/playlist-browser-test')
args=parser.parse_args()
sys.path.insert(0,str(repo/'scripts'))
import skin
from cdp_client import CDP,targets

work=args.work_dir.resolve()/('run-'+str(time.time_ns()))
work.mkdir(parents=True)
ffmpeg=args.ffmpeg.resolve()
for index,color in enumerate(('red','blue','green')):
    video=work/f'clip-{index}.mp4'
    if not video.exists():
        subprocess.run([str(ffmpeg),'-hide_banner','-nostdin','-loglevel','error','-f','lavfi','-i',f'color=c={color}:s=320x180:r=12','-t','3','-an','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
    poster=work/f'poster-{index}.jpg'
    if not poster.exists():
        subprocess.run([str(ffmpeg),'-hide_banner','-nostdin','-loglevel','error','-i',str(video),'-frames:v','1','-update','1',str(poster)],check=True)
theme=work/'theme'
if not theme.exists():
    subprocess.run([sys.executable,str(repo/'scripts/create_theme.py'),'--video',*[str(work/f'clip-{i}.mp4') for i in range(3)],'--poster',*[str(work/f'poster-{i}.jpg') for i in range(3)],'--output',str(theme)],check=True)
else:
    import shutil
    shutil.copy2(repo/'assets/template/inject.js',theme/'inject.js')
cfg_path=theme/'theme.json'
original=json.loads(cfg_path.read_text())
for i,item in enumerate(original['playlist']):
    item['css']=f'theme-{i}.css'
    (theme/item['css']).write_text(f':root {{ --playlist-test: {i}; }}',encoding='utf-8')
cfg_path.write_text(json.dumps(original),encoding='utf-8')
profile=work/('profile-'+str(time.time_ns()))
process=subprocess.Popen([str(args.browser.resolve()),'--headless=new','--disable-gpu','--no-first-run','--disable-extensions','--disable-background-networking','--autoplay-policy=no-user-gesture-required','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
client=None
checks=[]
def check(label,condition):
    if not condition:
        raise AssertionError(label)
    checks.append(label)
    print('PASS '+label,flush=True)
def wait_for(expression,timeout=7):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=client.evaluate(expression)
        if result:
            return result
        time.sleep(.1)
    raise AssertionError('Browser condition timed out: '+expression)
def apply(config):
    cfg_path.write_text(json.dumps(config),encoding='utf-8')
    return skin.apply(client,theme)
try:
    deadline=time.monotonic()+15
    while not (profile/'DevToolsActivePort').exists():
        if time.monotonic()>deadline:
            raise RuntimeError('Headless Edge did not start')
        time.sleep(.1)
    port=int((profile/'DevToolsActivePort').read_text().splitlines()[0])
    page=next(t for t in targets(port) if t['type']=='page')
    client=CDP(page['webSocketDebuggerUrl'])
    client.evaluate('''document.body.innerHTML='<div class="ProseMirror" contenteditable="true">draft stays here</div>';window.createdURLs=[];window.revokedURLs=[];const make=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);URL.createObjectURL=b=>{const u=make(b);createdURLs.push(u);return u};URL.revokeObjectURL=u=>{revokedURLs.push(u);return revoke(u)};true''')
    apply(original)
    check('playlist disables single-video loop',client.evaluate('!window.__nightCity.video.loop'))
    wait_for('window.__nightCity.playlistStatus().index===1')
    check('natural ended advances and changes CSS',client.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--playlist-test').trim()==='1'"))
    client.evaluate('window.__nightCity.pause();window.__nightCity.next();true')
    check('manual next preserves manual pause',client.evaluate('window.__nightCity.playlistStatus().index===2 && window.__nightCity.video.paused'))
    client.evaluate('window.__nightCity.next();true')
    check('last item wraps to first',client.evaluate('window.__nightCity.playlistStatus().index===0'))
    client.evaluate('window.__nightCity.previous();true')
    check('previous returns to prior item',client.evaluate('window.__nightCity.playlistStatus().index===2'))
    client.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});window.__nightCity.resume();document.dispatchEvent(new Event("visibilitychange"));true')
    check('hidden document stays paused',client.evaluate('window.__nightCity.video.paused'))
    client.evaluate('delete document.hidden;document.dispatchEvent(new Event("visibilitychange"));true')
    wait_for('window.__nightCity.video.currentTime>.1 && !window.__nightCity.video.paused')
    check('visible document resumes playback',True)
    shuffle=json.loads(json.dumps(original));shuffle['playback']['mode']='shuffle'
    apply(shuffle)
    check('shuffle avoids immediate repeats',client.evaluate('''(() => {const s=window.__nightCity;s.pause();for(let i=0;i<30;i++){const old=s.playlistStatus().index;s.next();if(old===s.playlistStatus().index)return false;}return true})()'''))
    timed=json.loads(json.dumps(original));timed['playback']['intervalSeconds']=1
    apply(timed)
    wait_for('window.__nightCity.playlistStatus().index===1',timeout=2.5)
    check('interval advances before 3-second clip ends',True)
    client.evaluate('window.__nightCity.pause();true')
    paused_index=client.evaluate('window.__nightCity.playlistStatus().index')
    time.sleep(1.3)
    check('manual pause stops interval switching',client.evaluate('window.__nightCity.playlistStatus().index')==paused_index)
    client.evaluate('window.__nightCity.restore();true')
    check('restore removes theme and revokes every Blob',client.evaluate("!window.__nightCity && !document.querySelector('#nc-background') && createdURLs.length===revokedURLs.length"))
    time.sleep(.4)
    check('restore remains clean after interval tick',client.evaluate('!window.__nightCity'))
    single={'video':original['playlist'][0]['video'],'poster':original['playlist'][0]['poster']}
    apply(single)
    check('single-video manifest still loops',client.evaluate('window.__nightCity.video.loop && window.__nightCity.playlistStatus().count===1'))
    client.evaluate('''(() => {
      const baseline=document.createElement('style');
      baseline.textContent=`#fixture-header,#fixture-surface { background:#201020; border:1px solid black; box-shadow:0 2px 4px black; backdrop-filter:blur(10px) }
        #fixture-fade,#fixture-fade::before,#fixture-fade::after { content:''; background:linear-gradient(#201020,transparent); border:1px solid black; box-shadow:0 2px 4px black; backdrop-filter:blur(10px) }
        #fixture-title,#fixture-title span { color:#123456; -webkit-text-fill-color:#123456 }`;
      document.head.prepend(baseline);
      const host=document.createElement('section');host.id='header-fixture';
      host.innerHTML='<header id="fixture-header"><div id="fixture-surface" data-testid="app-shell-header-context-menu-surface"></div><div class="Toolbar-test @container/app-shell-header-toolbar"><div id="fixture-title" class="font-medium truncate"><span>Visible title outside surface</span></div></div></header><div id="fixture-fade" class="MainContentTopFade-test"></div>';
      document.body.append(host);return true;
    })()''')
    check('header and surface have no separate background or border',client.evaluate('''['fixture-header','fixture-surface'].every(id=>{
      const s=getComputedStyle(document.getElementById(id));return s.backgroundColor==='rgba(0, 0, 0, 0)' && s.backgroundImage==='none' && s.boxShadow==='none' && s.borderBottomWidth==='0px';
    }) && getComputedStyle(document.getElementById('fixture-surface')).backdropFilter==='none' '''))
    check('top fade and both pseudo elements are clear',client.evaluate('''['','::before','::after'].every(p=>{
      const s=getComputedStyle(document.getElementById('fixture-fade'),p||null);return s.backgroundImage==='none' && s.backgroundColor==='rgba(0, 0, 0, 0)' && s.boxShadow==='none' && s.borderBottomWidth==='0px' && s.backdropFilter==='none';
    })'''))
    check('visible title and child default to body ink',client.evaluate('''[document.getElementById('fixture-title'),document.querySelector('#fixture-title span')].every(el=>{
      const s=getComputedStyle(el);return s.color==='rgb(227, 243, 246)' && s.webkitTextFillColor===s.color;
    })'''))
    client.evaluate("document.getElementById('nc-style').textContent+='\\nhtml[data-night-city] { --nc-title-color: #a8d8ea; }';true")
    check('custom title color reaches actual visible text',client.evaluate('''[document.getElementById('fixture-title'),document.querySelector('#fixture-title span')].every(el=>{
      const s=getComputedStyle(el);return s.color==='rgb(168, 216, 234)' && s.webkitTextFillColor===s.color;
    })'''))
    client.evaluate('window.__nightCity.restore();true')
    check('restore returns original header and title styles',client.evaluate("getComputedStyle(document.getElementById('fixture-surface')).backgroundColor==='rgb(32, 16, 32)' && getComputedStyle(document.querySelector('#fixture-title span')).color==='rgb(18, 52, 86)'"))
    check('draft content unchanged',client.evaluate("document.querySelector('.ProseMirror').textContent==='draft stays here'"))
    (work/'validation.json').write_text(json.dumps({'checks':checks,'passed':len(checks),'browser':'Microsoft Edge headless','realH264Playback':True},ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    if client:
        try:
            client.call('Browser.close')
        except Exception:
            pass
        client.close()
    if process.poll() is None:
        process.terminate()
