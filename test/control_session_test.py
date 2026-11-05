#!/usr/bin/env python3
"""Exercise TCP control close/reset diagnostics against a real Snapserver."""

import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(binary):
    with tempfile.TemporaryDirectory(prefix="snapcast-control-") as directory:
        root = Path(directory)
        port = free_port()
        config = root / "server.conf"
        config.write_text(f"""[server]
threads = 4
datadir = {root}
mdns_enabled = false
[http]
enabled = false
[tcp-control]
bind_to_address = 127.0.0.1
port = {port}
[tcp-streaming]
enabled = false
[stream]
source = tcp://127.0.0.1:{free_port()}?name=base&codec=pcm
""")
        log_path = root / "server.log"
        with log_path.open("w") as log:
            process = subprocess.Popen([str(binary), "--config", str(config)],
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        connection = socket.create_connection(("127.0.0.1", port), 1)
                        break
                    except OSError:
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise
                        time.sleep(0.05)
                with connection:
                    first_peer = connection.getsockname()[1]
                    connection.sendall(b'{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}\r\n')
                    with connection.makefile("rb") as reader:
                        assert "result" in json.loads(reader.readline())
                with socket.create_connection(("127.0.0.1", port), 1) as reset:
                    reset_peer = reset.getsockname()[1]
                    reset.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                    time.sleep(0.05)
                for request_id in range(2, 12):
                    with socket.create_connection(("127.0.0.1", port), 1) as sock:
                        sock.sendall(json.dumps({"id": request_id, "jsonrpc": "2.0",
                                                 "method": "Server.GetStatus"}).encode() + b"\r\n")
                        with sock.makefile("rb") as reader:
                            response = json.loads(reader.readline())
                            assert response["id"] == request_id and "result" in response
                deadline = time.monotonic() + 3
                while True:
                    output = log_path.read_text()
                    if (f"Control peer 127.0.0.1:{first_peer} closed connection to 127.0.0.1:{port}" in output
                            and f"Error reading control peer 127.0.0.1:{reset_peer} on 127.0.0.1:{port}" in output):
                        break
                    if time.monotonic() > deadline:
                        raise AssertionError(output)
                    time.sleep(0.02)
                assert "Error while reading from control socket: End of file" not in output
                assert "Error in socket shutdown" not in output
                assert process.poll() is None
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
            assert process.returncode == 0, log_path.read_text()
        print("PASS: graceful close, reset, peer identification, and 10 reconnects")


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
