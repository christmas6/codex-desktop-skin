"""Controller/manifest regression tests; no Codex connection is made."""
import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import skin


class TransferClient:
    def __init__(self):
        self.current = []
        self.items = []
        self.config = None

    def evaluate(self, expression):
        if expression.startswith('window.__nightCityChunks=[]; window.'):
            self.items = []
        elif expression == 'window.__nightCityChunks=[]; true':
            self.current = []
        elif expression.startswith('window.__nightCityChunks.push'):
            encoded = expression.split('atob(', 1)[1].split('),c=>', 1)[0]
            self.current.append(base64.b64decode(json.loads(encoded)))
        elif expression.startswith('window.__nightCityPlaylistChunks.push'):
            self.items.append(b''.join(self.current))
        elif expression.startswith('// Independent, local CDP'):
            self.config = json.loads(expression.rsplit('\n})\n(', 1)[1][:-1])
            return {'applied': True}
        return True


class PlaylistTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / 'source.mp4'
        self.video.write_bytes(b'\0\0\0\x18ftypmp42' + b'x' * (512 * 1024 + 17))
        self.poster = self.root / 'source.jpg'
        self.poster.write_bytes(b'\xff\xd8\xfffixture')

    def stage(self, count=2, extra=()):
        target = self.root / 'theme'
        command = [sys.executable, str(ROOT / 'scripts/create_theme.py'), '--video', *([str(self.video)] * count), '--poster', *([str(self.poster)] * count), '--output', str(target), *extra]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return target

    def test_single_video_compatibility(self):
        target = self.stage(1)
        config, _, _, media, _ = skin.load_theme(target)
        self.assertNotIn('playlist', config)
        self.assertEqual(config['video'], 'background.mp4')
        self.assertEqual(len(media), 1)

    def test_playlist_transfer_and_styles(self):
        first, second = self.root/'first.css', self.root/'second.css'
        first.write_text('body {color: pink}', encoding='utf-8')
        second.write_text('body {color: cyan}', encoding='utf-8')
        target = self.stage(extra=['--css',str(first),str(second),'--mode','shuffle','--interval','10'])
        client = TransferClient()
        skin.apply(client,target)
        self.assertEqual(client.items, [self.video.read_bytes()] * 2)
        self.assertEqual(client.config['playlist'][0]['css'], first.read_text())
        self.assertEqual(client.config['playlist'][1]['css'], second.read_text())
        self.assertEqual(client.config['playback'], {'mode':'shuffle','intervalSeconds':10.0})

    def test_invalid_manifest_keeps_live_theme_untouched(self):
        target = self.stage()
        config_path = target/'theme.json'
        config = json.loads(config_path.read_text())
        for value in ([], [{'video':'../source.mp4','poster':'poster-001.jpg'}]):
            config['playlist']=value
            config_path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                skin.load_theme(target)

    def test_invalid_interval_and_existing_output(self):
        target = self.stage()
        base = [sys.executable,str(ROOT/'scripts/create_theme.py'),'--video',str(self.video),'--poster',str(self.poster)]
        for args in (['--output',str(target)], ['--output',str(self.root/'invalid'),'--interval','nan']):
            result=subprocess.run(base+args,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'invalid').exists())


if __name__ == '__main__':
    unittest.main()
