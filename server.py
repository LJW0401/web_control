#!/usr/bin/env python3
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

OUTPUT_ADDR = (CONFIG["output_host"], int(CONFIG["output_port"]))
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(INDEX_PATH, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/config":
            body = json.dumps({
                "output_host": CONFIG["output_host"],
                "output_port": CONFIG["output_port"],
                "send_interval_ms": int(CONFIG.get("send_interval_ms", 50)),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/control":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_error(400, "invalid json")
            return
        payload = json.dumps({
            "vx": float(data.get("speed", 0.0)),
            "yaw": float(data.get("yaw", 0.0)),
            "L0": float(data.get("leg", 0.0)),
            "pitch": float(data.get("pitch", 0.0)),
        }).encode("utf-8")
        try:
            udp_sock.sendto(payload, OUTPUT_ADDR)
        except Exception as e:
            self.send_error(500, f"udp send failed: {e}")
            return
        self.send_response(204)
        self.end_headers()


def main():
    addr = (CONFIG["listen_host"], int(CONFIG["listen_port"]))
    server = ThreadingHTTPServer(addr, Handler)
    print(f"HTTP listening on http://{addr[0]}:{addr[1]}")
    print(f"Forwarding control to UDP {OUTPUT_ADDR[0]}:{OUTPUT_ADDR[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
