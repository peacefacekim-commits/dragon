"""표준 라이브러리만 쓰는 로컬 서버.

정적 파일(static/index.html 등)을 서빙하고, POST /api/ocr 로 업로드된
통장 스캔 이미지를 tesseract로 인식해 거래 행 목록(JSON)을 돌려준다.
인터넷 접속이나 pip install 없이, 미리 설치된 tesseract 실행 파일만 있으면 동작한다.
"""
from __future__ import annotations

import json
import mimetypes
import os
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .ocr import recognize_image, rows_from_tsv, page_width_from_tsv

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 스캔 이미지 한 장 기준 넉넉한 상한


def _parse_boundary(content_type: str) -> bytes | None:
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):].strip('"')
            return boundary.encode("utf-8")
    return None


def _extract_file_part(body: bytes, boundary: bytes) -> tuple[bytes, str] | None:
    """multipart/form-data 본문에서 첫 번째 파일 파트를 추출한다 (cgi 모듈 미사용)."""
    marker = b"--" + boundary
    parts = body.split(marker)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        header_blob, content = part.split(b"\r\n\r\n", 1)
        headers = header_blob.decode("utf-8", errors="replace")
        if "Content-Disposition" not in headers or "filename=" not in headers:
            continue
        content = content.rstrip(b"\r\n")
        filename = "upload.png"
        for piece in headers.split(";"):
            piece = piece.strip()
            if piece.startswith("filename="):
                filename = piece[len("filename="):].strip('"') or filename
        return content, filename
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "PassbookLedger/1.0"

    def log_message(self, fmt, *args):  # 콘솔이 너무 시끄럽지 않게
        pass

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"
        safe_rel = os.path.normpath(path).lstrip(os.sep)
        full_path = os.path.join(STATIC_DIR, safe_rel)
        if not os.path.abspath(full_path).startswith(os.path.abspath(STATIC_DIR)):
            self.send_error(403)
            return
        if not os.path.isfile(full_path):
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/ocr":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD_BYTES:
                self._send_json(400, {"error": "업로드 크기가 올바르지 않습니다."})
                return
            body = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "")
            boundary = _parse_boundary(content_type)
            if not boundary:
                self._send_json(400, {"error": "이미지 업로드 형식이 올바르지 않습니다."})
                return
            found = _extract_file_part(body, boundary)
            if not found:
                self._send_json(400, {"error": "업로드된 이미지를 찾을 수 없습니다."})
                return
            image_bytes, filename = found
            suffix = os.path.splitext(filename)[1] or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                tsv = recognize_image(tmp_path)
                rows = rows_from_tsv(tsv, page_width_from_tsv(tsv))
                self._send_json(200, {"rows": rows})
            finally:
                os.unlink(tmp_path)
        except RuntimeError as exc:
            self._send_json(500, {"error": str(exc)})
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "이미지 인식 중 오류가 발생했습니다."})


def run(port: int = 8877):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"통장 정리 도구: http://127.0.0.1:{port}/  (종료: Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
