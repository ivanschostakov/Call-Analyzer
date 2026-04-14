from __future__ import annotations

import os
import shutil
import subprocess

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse


FRONTEND_DIR = Path(__file__).resolve().parent
DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", FRONTEND_DIR / "dist")).expanduser()
INDEX_FILE = DIST_DIR / "index.html"
HOST = "127.0.0.1"
PORT = 4173


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_frontend_build() -> None:
    if INDEX_FILE.exists():
        return

    build_error_details: str | None = None
    should_auto_build = _env_flag("FRONTEND_AUTO_BUILD", True)
    npm_path = shutil.which("npm")

    if should_auto_build and DIST_DIR == FRONTEND_DIR / "dist" and npm_path and (FRONTEND_DIR / "package.json").exists():
        result = subprocess.run(
            [npm_path, "run", "build"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if INDEX_FILE.exists():
            return
        output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()
        if output:
            build_error_details = output[-2000:]
        else:
            build_error_details = f"`npm run build` exited with status {result.returncode}."

    message = (
        f"Frontend build not found: {INDEX_FILE}\n"
        "Expected a Vite production build before starting the SPA server."
    )

    if DIST_DIR == FRONTEND_DIR / "dist":
        message += "\nRun `npm install` (if needed) and `npm run build` in the frontend directory."
    else:
        message += f"\nCheck FRONTEND_DIST_DIR={DIST_DIR}."

    if build_error_details:
        message += f"\nBuild attempt output:\n{build_error_details}"
    elif should_auto_build and not npm_path:
        message += "\n`npm` is not available on PATH, so the server could not build the frontend automatically."

    raise FileNotFoundError(message)


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
    ensure_frontend_build()

    with ThreadingHTTPServer((HOST, PORT), SPARequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
