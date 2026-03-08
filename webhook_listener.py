import hashlib
import hmac
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
DEPLOY_SCRIPT = "/opt/errorlens/deploy.sh"
LOG_FILE = "/var/log/errorlens_deploy.log"


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        signature = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            WEBHOOK_SECRET, body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        with open(LOG_FILE, "a") as log:
            subprocess.Popen(
                ["/bin/bash", DEPLOY_SCRIPT],
                stdout=log,
                stderr=log,
            )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # Отключаем стандартный лог http.server


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9090), WebhookHandler)
    print("Webhook listener started on :9090")
    server.serve_forever()
