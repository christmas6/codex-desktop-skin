"""Stage prepared MP4/JPEG files as a single wallpaper or playlist."""
import argparse
import json
import math
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, nargs='+', type=Path)
    parser.add_argument('--poster', required=True, nargs='+', type=Path)
    parser.add_argument('--css', nargs='+', type=Path, help='Optional per-video stylesheets, in the same order')
    parser.add_argument('--mode', choices=['sequential', 'shuffle'], default='sequential')
    parser.add_argument('--interval', type=float, help='Switch after this many seconds of active playback; default: on ended')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    videos, posters = [p.resolve() for p in args.video], [p.resolve() for p in args.poster]
    if not 1 <= len(videos) <= 20 or len(videos) != len(posters) or (args.css and len(args.css) != len(videos)):
        parser.error('Provide 1 to 20 videos with one poster and optional CSS per video, in matching order')
    if args.interval is not None and (not math.isfinite(args.interval) or not 1 <= args.interval <= 86400):
        parser.error('--interval must be 1 to 86400 seconds')
    for video in videos:
        if not video.is_file() or not 0 < video.stat().st_size <= 100 * 1024 * 1024:
            parser.error('Each video must be a prepared MP4 of 1 byte to 100 MiB')
        with video.open('rb') as stream:
            if b'ftyp' not in stream.read(32):
                parser.error('Video does not have an MP4 file header')
    if sum(p.stat().st_size for p in videos) > 200 * 1024 * 1024:
        parser.error('Total playlist video size must not exceed 200 MiB')
    for poster in posters:
        if not poster.is_file() or not poster.read_bytes().startswith(b'\xff\xd8\xff'):
            parser.error('Each poster must be a JPEG file')
    if args.css:
        for css in args.css:
            if not css.is_file():
                parser.error('Missing per-video CSS file')
    output = args.output.resolve()
    if output.exists():
        parser.error('Output already exists; use a new directory')
    template = Path(__file__).resolve().parent.parent / 'assets' / 'template'
    output.mkdir(parents=True)
    for name in ('theme.css', 'inject.js'):
        shutil.copy2(template / name, output / name)
    items = []
    multiple = len(videos) > 1
    for index, (video, poster) in enumerate(zip(videos, posters), 1):
        video_name = f'background-{index:03d}.mp4' if multiple else 'background.mp4'
        poster_name = f'poster-{index:03d}.jpg' if multiple else 'poster.jpg'
        shutil.copy2(video, output / video_name)
        shutil.copy2(poster, output / poster_name)
        item = {'title': video.stem, 'video': video_name, 'poster': poster_name}
        if args.css:
            css_name = f'theme-{index:03d}.css' if multiple else 'theme.css'
            shutil.copy2(args.css[index-1], output / css_name)
            item['css'] = css_name
        items.append(item)
    config = {'name': output.name, 'muted': True, 'scope': 'current renderer session', 'playback': {'mode': args.mode, 'intervalSeconds': args.interval}}
    if multiple:
        config['playlist'] = items
    else:
        config.update(video=items[0]['video'], poster=items[0]['poster'], loop=True)
    (output / 'theme.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'themeDir': str(output), 'count': len(videos), 'videoBytes': sum(p.stat().st_size for p in videos)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
