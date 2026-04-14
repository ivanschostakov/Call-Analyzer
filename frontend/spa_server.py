from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse


FRONTEND_DIR = Path(__file__).resolve().parent
DIST_DIR = FRONTEND_DIR / "dist"
INDEX_FILE = DIST_DIR / "index.html"
HOST = "127.0.0.1"
PORT = 4173


class SPARequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def _request_path(self) -> str:
        return unquote(urlparse(self.path).path)

    def _is_asset_request(self, path: str) -> bool:
        return "." in PurePosixPath(path).name

    def send_head(self):
        request_path = self._request_path()
        candidate = DIST_DIR / request_path.lstrip("/")

        if request_path != "/" and not candidate.exists() and not self._is_asset_request(request_path):
            self.path = "/index.html"

        return super().send_head()


def main() -> None:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"Frontend build not found: {INDEX_FILE}")

    with ThreadingHTTPServer((HOST, PORT), SPARequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
