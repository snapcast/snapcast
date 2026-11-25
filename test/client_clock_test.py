#!/usr/bin/env python3
"""Exercise the real Snapclient without speakers or changing system clocks.

SNAPCLIENT_BINARY=/path/to/bin/snapclient python test/client_clock_test.py -v

The localhost server implements Snapcast protocol v2 with synthetic PCM and
clock origins. Output is checked for silence, not just successful startup.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import select
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest


HEADER = struct.Struct("<HHHiiiiI")
RATE = 48000
PCM = struct.pack("<hh", 4096, -4096) * 960
WAVE = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36, b"WAVE", b"fmt ",
                   16, 1, 2, RATE, RATE * 4, 4, 16, b"data", 0)
BINARY = os.environ.get("SNAPCLIENT_BINARY")


def timestamp(seconds: float) -> tuple[int, int]:
    return divmod(round(seconds * 1_000_000), 1_000_000)


def blob(data: bytes) -> bytes:
    return struct.pack("<I", len(data)) + data


class FakeServer:
    def __init__(self, offsets: list[float], stall: bool = False, jitter: bool = False):
        self.offsets = offsets
        self.stall = stall
        self.jitter = jitter
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.errors: list[Exception] = []
        self.final_started = 0.0
        self.connections = 0
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.sock.settimeout(0.1)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self) -> None:
        try:
            for index, offset in enumerate(self.offsets):
                conn = None
                while not self.stop.is_set() and conn is None:
                    try:
                        conn, _ = self.sock.accept()
                    except socket.timeout:
                        continue
                if conn is None:
                    return
                self.connections += 1
                with conn:
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.serve(conn, offset, index == len(self.offsets) - 1)
        except (OSError, ValueError, struct.error) as exc:
            if not self.stop.is_set():
                self.errors.append(exc)

    def serve(self, conn: socket.socket, offset: float, final: bool) -> None:
        data = bytearray()
        syncs = 0
        next_chunk = None
        next_jitter = time.monotonic() + 1

        def send(kind: int, payload: bytes, refers: int = 0) -> None:
            now = timestamp(time.monotonic() + offset)
            conn.sendall(HEADER.pack(kind, 0, refers, *now, 0, 0, len(payload)) + payload)

        while not self.stop.is_set():
            if select.select([conn], [], [], 0.002)[0]:
                received = conn.recv(65536)
                if not received:
                    return
                data.extend(received)
            while len(data) >= HEADER.size:
                header = HEADER.unpack_from(data)
                kind, ident, _, sec, usec, _, _, length = header
                if len(data) < HEADER.size + length:
                    break
                del data[:HEADER.size + length]
                if kind == 5:
                    settings = dict(bufferMs=230, latency=0, volume=100, muted=False)
                    send(3, blob(json.dumps(settings).encode()), ident)
                    send(1, blob(b"pcm") + blob(WAVE))
                    next_chunk = time.monotonic()
                    if final:
                        self.final_started = next_chunk
                elif kind == 4:
                    delta = time.monotonic() + offset - (sec + usec / 1_000_000)
                    send(4, struct.pack("<ii", *timestamp(delta)), ident)
                    syncs += 1
                    if syncs == 50:
                        if not final:
                            if self.stall:
                                # Withhold traffic across the two-second sync deadline.
                                self.stop.wait(3.3)
                            return  # Reconnect while previous time samples are still fresh.
                        self.ready.set()
            if next_chunk is not None:
                now = time.monotonic()
                if self.jitter and now >= next_jitter:
                    self.stop.wait(0.08)
                    now = time.monotonic()
                    next_jitter = now + 1
                while next_chunk <= now:
                    send(2, struct.pack("<ii", *timestamp(next_chunk + offset)) + blob(PCM))
                    next_chunk += 0.02

    def close(self) -> None:
        self.stop.set()
        self.thread.join(2)
        self.sock.close()


@unittest.skipUnless(BINARY, "set SNAPCLIENT_BINARY to run real audio integration tests")
class SnapcastClockTests(unittest.TestCase):
    def check_audio(self, offsets: list[float], **options: bool) -> None:
        with tempfile.TemporaryDirectory(prefix="snapcast-clock-") as directory:
            root = Path(directory)
            output = root / "output.pcm"
            server = FakeServer(offsets, **options)
            try:
                with (root / "client.log").open("w+") as log:
                    process = subprocess.Popen([
                        BINARY, "--hostID", "clock-regression", "--logsink", "stdout",
                        "--player", f"file:filename={output},mode=a",
                        f"tcp://127.0.0.1:{server.port}",
                    ], stdout=log, stderr=subprocess.STDOUT)
                    try:
                        self.assertTrue(server.ready.wait(15), "initial time sync did not complete")
                        time.sleep(2)  # Initial buffering and synchronization are not steady playback.
                        start = output.stat().st_size
                        time.sleep(2)
                        end = output.stat().st_size
                        self.assertIsNone(process.poll())
                        self.assertFalse(server.errors, server.errors)
                        self.assertEqual(server.connections, len(offsets))
                        with output.open("rb") as audio:
                            audio.seek(start)
                            samples = audio.read(end - start)
                        self.assertGreater(len(samples), RATE * 4)
                        silent = sum(a == 0 and b == 0 for a, b in struct.iter_unpack("<hh", samples))
                        silence_ratio = silent / (len(samples) / 4)
                        log.flush()
                        log.seek(0)
                        self.assertLess(silence_ratio, 0.01, log.read()[-5000:])
                    finally:
                        process.terminate()
                        try:
                            process.wait(3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
            finally:
                server.close()

    def test_offset_minus_30_days(self) -> None:
        self.check_audio([-30 * 86400])

    def test_offset_plus_one_year(self) -> None:
        self.check_audio([365 * 86400])

    def test_offset_minus_one_year(self) -> None:
        self.check_audio([-365 * 86400])

    def test_reconnect_after_server_clock_reset(self) -> None:
        # Fill the 200-sample filter across connections without waiting 200s.
        self.check_audio([30 * 86400] * 4 + [0])

    def test_reconnect_after_server_clock_jumps_forward(self) -> None:
        self.check_audio([0] * 4 + [365 * 86400])

    def test_transport_timeout_recovers_in_same_process(self) -> None:
        self.check_audio([-30 * 86400, -30 * 86400], stall=True)

    def test_bursty_delivery_within_playback_buffer(self) -> None:
        self.check_audio([365 * 86400], jitter=True)


if __name__ == "__main__":
    unittest.main()
