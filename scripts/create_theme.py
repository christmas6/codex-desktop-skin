"""Stage a prepared MP4 and JPEG poster with the tested theme templates."""
import argparse
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--poster', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    video, poster, output = args.video.resolve(), args.poster.resolve(), args.output.resolve()
    if not video.is_file() or not 0 < video.stat().st_size <= 100 * 1024 * 1024:
        parser.error('Video must be a prepared MP4 of 1 byte to 100 MiB')
    with video.open('rb') as stream:
        if b'ftyp' not in stream.read(32):
            parser.error('Video does not have an MP4 file header')
    if not poster.is_file() or not poster.read_bytes().startswith(b'\xff\xd8\xff'):
        parser.error('Poster must be a JPEG file')
    if output.exists():
        parser.error('Output already exists; use a new directory')
    template = Path(__file__).resolve().parent.parent / 'assets' / 'template'
    output.mkdir(parents=True)
    for name in ('theme.css', 'inject.js'):
        shutil.copy2(template / name, output / name)
    shutil.copy2(video, output / 'background.mp4')
    shutil.copy2(poster, output / 'poster.jpg')
    (output / 'theme.json').write_text(json.dumps({'name': output.name, 'video': 'background.mp4', 'poster': 'poster.jpg', 'muted': True, 'loop': True, 'scope': 'current renderer session'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'themeDir': str(output), 'videoBytes': video.stat().st_size}, ensure_ascii=False))


if __name__ == '__main__':
    main()
