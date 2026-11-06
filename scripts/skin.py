"""Session-only Codex desktop theme controller; Python standard library only."""
import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp_client import CDP, targets


def connect(port=None):
    if port is None:
        command = r'''Get-CimInstance Win32_Process -Filter "Name = 'ChatGPT.exe'" | ForEach-Object { $m = [regex]::Match($_.CommandLine, '--remote-debugging-port[= ](\d+)'); if ($m.Success) { $m.Groups[1].Value } } | Sort-Object -Unique'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True, text=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        ports = [int(s) for s in result.stdout.split() if s.isdigit()]
    else:
        ports = [port]
    matches = []
    for candidate in ports:
        try:
            matches.extend(t for t in targets(candidate) if t.get('type') == 'page' and t.get('url', '').startswith('app://-/index.html') and 'initialRoute' not in t['url'])
        except (OSError, ValueError):
            continue
    if len(matches) != 1:
        raise RuntimeError(f'Expected one main Codex page, found {len(matches)}. Open the existing debug-enabled launcher, or specify --port. No app restart performed.')
    return CDP(matches[0]['webSocketDebuggerUrl'])


STATUS = '''(() => {
 const s=window.__nightCity,v=s?.video,css=e=>e?{backgroundImage:getComputedStyle(e).backgroundImage,backgroundColor:getComputedStyle(e).backgroundColor}:null;
 const editor=document.querySelector('.ProseMirror'),r=editor?.getBoundingClientRect();
 const hit=r&&r.width&&r.height?document.elementFromPoint(r.left+r.width/2,r.top+r.height/2):null;
 const control=document.querySelector('#nc-controls');
 return {active:!!s,visible:!document.hidden,
 video:v?{width:v.videoWidth,height:v.videoHeight,duration:v.duration,time:v.currentTime,paused:v.paused,muted:v.muted,loop:v.loop,readyState:v.readyState,error:v.error?.message??null}:null,
 layers:document.querySelectorAll('#nc-background').length,
 controls:control?{display:getComputedStyle(control).display,rects:control.getClientRects().length}:null,
 editor:{exists:!!editor,editable:editor?.isContentEditable??false,hit:!!hit&&(hit===editor||editor.contains(hit))},
 composer:css(document.querySelector('[class*="ComposerLayoutRoot"]')),
 fades:[...document.querySelectorAll('[class*="background-"][class*="fade-"]')].map(css)};
})()'''


def local_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'Missing or out-of-directory theme file: {name}')
    return path


def apply(client, root):
    config = json.loads(local_file(root, 'theme.json').read_text(encoding='utf-8'))
    video = local_file(root, config['video'])
    poster = local_file(root, config['poster'])
    css = local_file(root, 'theme.css').read_text(encoding='utf-8')
    script = local_file(root, 'inject.js').read_text(encoding='utf-8')
    if not 0 < video.stat().st_size <= 100 * 1024 * 1024:
        raise ValueError('Prepared MP4 must be nonempty and at most 100 MiB; compress it first.')
    client.evaluate('window.__nightCityChunks=[]; true')
    try:
        with video.open('rb') as stream:
            while chunk := stream.read(512 * 1024):
                encoded = base64.b64encode(chunk).decode('ascii')
                client.evaluate('window.__nightCityChunks.push(Uint8Array.from(atob(' + json.dumps(encoded) + '),c=>c.charCodeAt(0)));true')
        cfg = {'css': css, 'poster': 'data:image/jpeg;base64,' + base64.b64encode(poster.read_bytes()).decode('ascii')}
        result = client.evaluate(script + '(' + json.dumps(cfg) + ')')
        if not result or not result.get('applied'):
            raise RuntimeError('Theme injection did not complete')
        return result
    except Exception:
        client.evaluate('window.__nightCity?.restore(); delete window.__nightCityChunks; true')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'apply', 'style', 'restore', 'screenshot'])
    parser.add_argument('--port', type=int)
    parser.add_argument('--theme-dir', type=Path)
    parser.add_argument('--output', type=Path, help='Required PNG path for screenshot')
    args = parser.parse_args()
    if args.action in ('apply', 'style') and args.theme_dir is None:
        parser.error('--theme-dir is required for apply/style')
    if args.action == 'screenshot' and args.output is None:
        parser.error('--output is required for screenshot')
    client = connect(args.port)
    try:
        if args.action == 'apply':
            apply(client, args.theme_dir.resolve())
        elif args.action == 'style':
            css = local_file(args.theme_dir.resolve(), 'theme.css').read_text(encoding='utf-8')
            result = client.evaluate('''(() => {const s=document.querySelector('#nc-style'),v=window.__nightCity?.video;if(!s||!v)throw Error('No active theme');const src=v.src;s.textContent=''' + json.dumps(css) + ''';return {sameVideoSource:src===v.src};})()''')
            if not result.get('sameVideoSource'):
                raise RuntimeError('Video source changed during stylesheet update')
        elif args.action == 'restore':
            client.evaluate('window.__nightCity?.restore(); delete window.__nightCityChunks; true')
        elif args.action == 'screenshot':
            if args.output.exists():
                raise FileExistsError(args.output)
            data = client.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(base64.b64decode(data['data']))
            print(json.dumps({'screenshot': str(args.output.resolve())}, ensure_ascii=False))
            return
        print(json.dumps(client.evaluate(STATUS), ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Operation failed: {exc}', file=sys.stderr)
        sys.exit(1)
