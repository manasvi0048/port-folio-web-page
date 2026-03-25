import importlib
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "5000"))

DESIGNER_PROFILE = {
    "name": "Manasvi M",
    "title": "Creative Developer & Designer",
    "location": "India",
    "bio": "I create portfolio websites and visual experiences that balance clarity, personality, and modern styling.",
    "expertise": ["HTML5", "CSS3", "JavaScript", "UI Design"],
    "works": [
        {
            "title": "Portfolio Website",
            "category": "Personal Branding",
            "description": "A clean one-page website designed to introduce a creator, highlight skills, and drive inquiries.",
        },
        {
            "title": "Startup Landing Page",
            "category": "Web Design",
            "description": "A bold launch page concept built to explain a product quickly and create a strong visual identity.",
        },
        {
            "title": "Design Concept",
            "category": "Creative Direction",
            "description": "An interface exploration focused on layout, hierarchy, and a memorable first-screen experience.",
        },
    ],
}


def load_psycopg():
    try:
        return importlib.import_module("psycopg")
    except ModuleNotFoundError:
        return None


def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("PGHOST")
    database = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    port = os.getenv("PGPORT", "5432")

    if host and database and user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    return None


def get_db_connection():
    psycopg = load_psycopg()
    database_url = get_database_url()

    if psycopg is None:
        raise RuntimeError("psycopg is not installed")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(database_url)


def init_database():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inquiries (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        connection.commit()


def get_health_snapshot():
    database_url = get_database_url()
    driver_installed = load_psycopg() is not None
    health = {
        "status": "ok",
        "service": "portfolio-app",
        "time": datetime.now(timezone.utc).isoformat(),
        "database": {
            "configured": bool(database_url),
            "driver_installed": driver_installed,
            "connected": False,
            "error": None,
            "url_source": "DATABASE_URL" if os.getenv("DATABASE_URL") else "PG* environment variables" if database_url else None,
        },
    }

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        health["database"]["connected"] = True
    except Exception as exc:
        health["status"] = "degraded"
        health["database"]["error"] = str(exc)

    return health


def get_readiness_snapshot():
    health = get_health_snapshot()
    health["ready"] = health["database"]["connected"]
    return health


class PortfolioHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self.serve_file("index.html", "text/html; charset=utf-8")
            return

        if path == "/style.css":
            self.serve_file("style.css", "text/css; charset=utf-8")
            return

        if path == "/zenitsu-background-web.mp4":
            self.serve_file("zenitsu-background-web.mp4", "video/mp4")
            return

        if path == "/zenitsu-background-safe.mp4":
            self.serve_file("zenitsu-background-safe.mp4", "video/mp4")
            return

        if path == "/zenitsu-background.webm":
            self.serve_file("zenitsu-background.webm", "video/webm")
            return

        if path == "/zenitsu-poster.jpg":
            self.serve_file("zenitsu-poster.jpg", "image/jpeg")
            return

        if path == "/api/profile":
            self.send_json(200, DESIGNER_PROFILE)
            return

        if path in ("/health", "/api/health"):
            health = get_health_snapshot()
            self.send_json(200, health)
            return

        if path in ("/ready", "/api/ready"):
            readiness = get_readiness_snapshot()
            status_code = 200 if readiness["ready"] else 503
            self.send_json(status_code, readiness)
            return

        self.send_error(404, "File not found")

    def do_HEAD(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self.serve_file("index.html", "text/html; charset=utf-8", send_body=False)
            return

        if path == "/style.css":
            self.serve_file("style.css", "text/css; charset=utf-8", send_body=False)
            return

        if path == "/zenitsu-background-web.mp4":
            self.serve_file("zenitsu-background-web.mp4", "video/mp4", send_body=False)
            return

        if path == "/zenitsu-background-safe.mp4":
            self.serve_file("zenitsu-background-safe.mp4", "video/mp4", send_body=False)
            return

        if path == "/zenitsu-background.webm":
            self.serve_file("zenitsu-background.webm", "video/webm", send_body=False)
            return

        if path == "/zenitsu-poster.jpg":
            self.serve_file("zenitsu-poster.jpg", "image/jpeg", send_body=False)
            return

        if path == "/api/profile":
            self.send_json(200, DESIGNER_PROFILE, send_body=False)
            return

        if path in ("/health", "/api/health"):
            health = get_health_snapshot()
            self.send_json(200, health, send_body=False)
            return

        if path in ("/ready", "/api/ready"):
            readiness = get_readiness_snapshot()
            status_code = 200 if readiness["ready"] else 503
            self.send_json(status_code, readiness, send_body=False)
            return

        self.send_error(404, "File not found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/inquiries":
            self.send_error(404, "File not found")
            return

        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
            return

        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip()
        message = payload.get("message", "").strip()

        if not name or not email or not message:
            self.send_json(400, {"ok": False, "error": "Name, email, and message are required."})
            return

        try:
            inquiry_id = self.save_inquiry(name, email, message)
        except Exception as exc:
            self.send_json(
                503,
                {
                    "ok": False,
                    "error": "Unable to save inquiry. Check PostgreSQL configuration.",
                    "details": str(exc),
                    "hint": "Install psycopg and set DATABASE_URL before submitting inquiries.",
                },
            )
            return

        self.send_json(
            201,
            {
                "ok": True,
                "message": "Inquiry submitted successfully.",
                "id": inquiry_id,
            },
        )

    def log_message(self, format, *args):
        return

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        if not raw_body:
            raise ValueError("Request body is empty.")

        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def save_inquiry(self, name, email, message):
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO inquiries (name, email, message)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, message),
                )
                inquiry_id = cursor.fetchone()[0]
            connection.commit()

        return inquiry_id

    def serve_file(self, filename, content_type, send_body=True):
        file_path = BASE_DIR / filename
        if not file_path.exists():
            self.send_error(404, "File not found")
            return

        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header:
            match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                end = min(end, file_size - 1)

                if start >= file_size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return

                chunk_size = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(chunk_size))
                self.end_headers()

                if send_body:
                    with file_path.open("rb") as file_handle:
                        file_handle.seek(start)
                        self.wfile.write(file_handle.read(chunk_size))
                return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size))
        self.end_headers()

        if send_body:
            with file_path.open("rb") as file_handle:
                self.wfile.write(file_handle.read())

    def send_json(self, status_code, payload, send_body=True):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if send_body:
            self.wfile.write(content)


if __name__ == "__main__":
    try:
        init_database()
        print("PostgreSQL database ready.")
    except Exception as exc:
        print(f"Database setup skipped: {exc}")

    server = HTTPServer((HOST, PORT), PortfolioHandler)
    print(f"Portfolio server running at http://{HOST}:{PORT}")
    server.serve_forever()
