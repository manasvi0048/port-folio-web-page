import importlib
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.getenv("PORT", "5000"))
STREAMABLE_FILES = {
    "zenitsu-background-web.mp4",
    "zenitsu-background-safe.mp4",
    "zenitsu-background.webm",
}

app = Flask(__name__, static_folder=None)

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


def save_inquiry(name, email, message):
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


def build_file_response(filename):
    file_path = BASE_DIR / filename
    if not file_path.exists():
        abort(404)

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")

    if range_header:
        try:
            range_value = range_header.replace("bytes=", "", 1)
            start_text, end_text = range_value.split("-", 1)
            start = int(start_text)
            end = int(end_text) if end_text else file_size - 1
        except (ValueError, AttributeError):
            return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

        end = min(end, file_size - 1)
        if start >= file_size or start > end:
            return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

        length = end - start + 1
        with file_path.open("rb") as file_handle:
            file_handle.seek(start)
            data = file_handle.read(length)

        response = Response(data, 206, mimetype=content_type, direct_passthrough=True)
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response.headers["Content-Length"] = str(length)
        return response

    response = send_from_directory(BASE_DIR, filename, mimetype=content_type)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(file_size)
    return response


@app.get("/")
@app.get("/index.html")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/style.css")
def styles():
    return send_from_directory(BASE_DIR, "style.css", mimetype="text/css")


@app.get("/server.js")
def server_js():
    return send_from_directory(BASE_DIR, "server.js", mimetype="application/javascript")


@app.get("/zenitsu-poster.jpg")
def zenitsu_poster():
    return send_from_directory(BASE_DIR, "zenitsu-poster.jpg", mimetype="image/jpeg")


@app.get("/zenitsu-background-web.mp4")
def zenitsu_background_web():
    return build_file_response("zenitsu-background-web.mp4")


@app.get("/zenitsu-background-safe.mp4")
def zenitsu_background_safe():
    return build_file_response("zenitsu-background-safe.mp4")


@app.get("/zenitsu-background.webm")
def zenitsu_background_webm():
    return build_file_response("zenitsu-background.webm")


@app.get("/api/profile")
def profile():
    return jsonify(DESIGNER_PROFILE)


@app.get("/health")
@app.get("/api/health")
def health():
    return jsonify(get_health_snapshot())


@app.get("/ready")
@app.get("/api/ready")
def ready():
    readiness = get_readiness_snapshot()
    status_code = 200 if readiness["ready"] else 503
    return jsonify(readiness), status_code


@app.post("/api/inquiries")
def create_inquiry():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"ok": False, "error": "Request body must be valid JSON."}), 400

    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip()
    message = str(payload.get("message", "")).strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email, and message are required."}), 400

    try:
        inquiry_id = save_inquiry(name, email, message)
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Unable to save inquiry. Check PostgreSQL configuration.",
                    "details": str(exc),
                    "hint": "Install psycopg and set DATABASE_URL before submitting inquiries.",
                }
            ),
            503,
        )

    return jsonify({"ok": True, "message": "Inquiry submitted successfully.", "id": inquiry_id}), 201


@app.get("/<path:filename>")
def static_files(filename):
    safe_name = Path(filename).name
    file_path = BASE_DIR / safe_name
    if not file_path.exists():
        abort(404)

    if safe_name in STREAMABLE_FILES:
        return build_file_response(safe_name)

    return send_from_directory(BASE_DIR, safe_name)


if __name__ == "__main__":
    try:
        init_database()
        print("PostgreSQL database ready.")
    except Exception as exc:
        print(f"Database setup skipped: {exc}")

    app.run(host="127.0.0.1", port=PORT, debug=True)
