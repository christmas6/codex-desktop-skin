import base64
import hashlib
import json
import os
import socket
import struct
import time
import urllib.parse
import urllib.request


def targets(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=5) as r:
        return json.load(r)


class CDP:
    def __init__(self, url):
        u = urllib.parse.urlsplit(url)
        if u.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('Only local CDP is supported')
        self.sock = socket.create_connection((u.hostname, u.port), timeout=20)
        self.buffer = b''
        self.counter = 0
        key = base64.b64encode(os.urandom(16)).decode()
        request = f'GET {u.path} HTTP/1.1\r\nHost: {u.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
        self.sock.sendall(request.encode())
        while b'\r\n\r\n' not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                self.close()
                raise ConnectionError('CDP closed during handshake')
            self.buffer += chunk
        header, self.buffer = self.buffer.split(b'\r\n\r\n', 1)
        expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        fields = dict(line.split(b':', 1) for line in header.split(b'\r\n')[1:] if b':' in line)
        accept = next((v.strip() for k, v in fields.items() if k.lower() == b'sec-websocket-accept'), None)
        if not header.startswith(b'HTTP/1.1 101 ') or accept != expected:
            self.close()
            raise RuntimeError('CDP WebSocket handshake failed')

    def close(self):
        self.sock.close()

    def read(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(max(4096, count - len(self.buffer)))
            if not chunk:
                raise ConnectionError('CDP closed')
            self.buffer += chunk
        result, self.buffer = self.buffer[:count], self.buffer[count:]
        return result

    def send_frame(self, payload, opcode=1):
        mask = os.urandom(4)
        n = len(payload)
        header = bytes([0x80 | opcode])
        header += bytes([0x80 | n]) if n < 126 else (bytes([0xfe]) + struct.pack('!H', n) if n < 65536 else bytes([0xff]) + struct.pack('!Q', n))
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def receive(self):
        fragments = []
        while True:
            first, second = self.read(2)
            n = second & 127
            if n == 126:
                n = struct.unpack('!H', self.read(2))[0]
            elif n == 127:
                n = struct.unpack('!Q', self.read(8))[0]
            mask = self.read(4) if second & 128 else None
            payload = self.read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            opcode = first & 15
            if opcode == 8:
                raise ConnectionError('CDP WebSocket closed')
            if opcode == 9:
                self.send_frame(payload, 10)
                continue
            if opcode == 10:
                continue
            fragments.append(payload)
            if first & 128:
                return json.loads(b''.join(fragments))

    def call(self, method, params=None):
        self.counter += 1
        identifier = self.counter
        self.send_frame(json.dumps({'id': identifier, 'method': method, 'params': params or {}}).encode())
        while True:
            message = self.receive()
            if message.get('id') == identifier:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True, 'returnByValue': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result', {}).get('value')
