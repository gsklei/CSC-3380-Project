# app_images.py
import os
import imghdr
import uuid
from pathlib import Path
from typing import Optional, Dict

from flask import Flask, request, jsonify, send_from_directory, url_for, abort
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
# Directory where image assets will be saved. Override with env var ASSET_DIR.
ASSET_DIR = Path(os.getenv("ASSET_DIR", "./images")).resolve()

# Max upload size in MiB (can override via ASSET_MAX_MB environment variable)
MAX_MB = float(os.getenv("ASSET_MAX_MB", "10"))  # default 10 MiB
MAX_CONTENT_LENGTH = int(MAX_MB * 1024 * 1024)   # Flask expects bytes

# Allowed extensions (basic validation). We also validate with imghdr.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Ensure the asset directory exists
ASSET_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# In-memory "DB" for demo purposes
# -----------------------------------------------------------------------------
# item_id -> filename (string). Replace with real DB integration later.
ITEM_IMAGE_MAP: Dict[int, str] = {}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def allowed_extension(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_image_type(path: Path) -> Optional[str]:
    """
    Minimal file-type sniffing for safety. Uses Python stdlib imghdr.
    Returns a type like 'png', 'jpeg', 'gif', 'webp', or None if unknown.
    """
    try:
        kind = imghdr.what(path)
    except Exception:
        kind = None
    return kind

def safe_unique_filename(original_name: str, detected_ext: Optional[str]) -> str:
    """
    Generate a collision-resistant filename using UUID4 while preserving extension.
    If the original extension is untrusted, prefer the detected image extension.
    """
    base = secure_filename(Path(original_name).stem) or "image"
    # Prefer detected extension if available, else fall back to original
    orig_ext = Path(original_name).suffix.lower().lstrip(".")
    ext = (detected_ext or orig_ext or "png").lower()
    # Normalize jpeg extension
    if ext == "jpg":
        ext = "jpeg"
    if ext not in {"png", "jpeg", "gif", "webp"}:
        # Fallback to png if we got something odd
        ext = "png"
    return f"{base}-{uuid.uuid4().hex}.{ext}"

def build_asset_url(filename: str) -> str:
    return url_for("serve_asset", filename=filename, _external=True)

def extract_dominant_color(path: Path) -> str:
    """
    Stub for future color analysis (no real CV required now).
    Return a hex color string as a placeholder.
    """
    # TODO: Implement real color extraction later.
    return "#808080"

def associate_image_with_item(item_id: int, filename: str) -> None:
    """
    Helper to associate an image with an item after your /api/items flow.
    Replace with your real persistence layer (DAO/ORM) later.
    """
    ITEM_IMAGE_MAP[item_id] = filename

# -----------------------------------------------------------------------------
# Error handlers
# -----------------------------------------------------------------------------
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify(error="File too large", max_bytes=app.config["MAX_CONTENT_LENGTH"]), 413

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/api/images", methods=["POST"])
def upload_image():
    """
    Accepts multipart/form-data with field 'image'.
    Optional: include 'item_id' to associate immediately.
    Returns: { image_url, filename, size_bytes, dominant_color, item_id? }
    """
    if "image" not in request.files:
        return jsonify(error="Missing file field 'image'"), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify(error="Empty filename"), 400

    if not allowed_extension(file.filename):
        return jsonify(error="Unsupported file extension"), 400

    # Save to a temp path first to allow type sniffing safely
    tmp_name = secure_filename(file.filename) or "upload"
    tmp_path = ASSET_DIR / f"__tmp__{uuid.uuid4().hex}_{tmp_name}"
    file.save(tmp_path)

    # Basic sniffing: ensure it's actually an image
    detected_type = detect_image_type(tmp_path)
    if detected_type is None:
        tmp_path.unlink(missing_ok=True)
        return jsonify(error="Uploaded file is not a recognized image"), 400

    # Final safe unique filename (prefer detected type)
    final_name = safe_unique_filename(file.filename, detected_type)
    final_path = ASSET_DIR / final_name
    tmp_path.replace(final_path)  # atomic move within same filesystem

    # Optional: associate with item_id if provided
    item_id = request.form.get("item_id", type=int)
    if item_id is not None:
        associate_image_with_item(item_id, final_name)

    # Minimal metadata
    dominant_color = extract_dominant_color(final_path)
    size_bytes = final_path.stat().st_size

    return jsonify(
        image_url=build_asset_url(final_name),
        filename=final_name,
        size_bytes=size_bytes,
        dominant_color=dominant_color,
        item_id=item_id,
    ), 201

@app.route("/api/items/<int:item_id>/image", methods=["POST"])
def link_item_image(item_id: int):
    """
    Helper endpoint to associate an already-uploaded image with an item.
    Body (JSON or form): filename=<stored filename>
    """
    filename = request.form.get("filename") or (request.json or {}).get("filename")
    if not filename:
        return jsonify(error="Missing 'filename'"), 400

    path = ASSET_DIR / filename
    if not path.exists():
        return jsonify(error="File not found"), 404

    associate_image_with_item(item_id, filename)
    return jsonify(
        item_id=item_id,
        filename=filename,
        image_url=build_asset_url(filename),
        message="Image associated with item."
    ), 200

@app.route("/assets/<path:filename>", methods=["GET"])
def serve_asset(filename: str):
    """
    Static file serving route. Reverse proxy/real static hosting is recommended
    in production, but this satisfies the DoD for local dev and simple deploys.
    """
    # Normalize to prevent path traversal; send_from_directory handles safety, too.
    return send_from_directory(ASSET_DIR, filename, as_attachment=False, etag=True, cache_timeout=31536000)

@app.route("/api/items/<int:item_id>/image", methods=["GET"])
def get_item_image(item_id: int):
    """
    Convenience: fetch the image URL for an item_id (from our in-memory map).
    """
    filename = ITEM_IMAGE_MAP.get(item_id)
    if not filename:
        return jsonify(error="No image associated with this item"), 404
    return jsonify(
        item_id=item_id,
        filename=filename,
        image_url=build_asset_url(filename)
    )

# -----------------------------------------------------------------------------
# Health check / root
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify(status="ok", asset_dir=str(ASSET_DIR), max_bytes=app.config["MAX_CONTENT_LENGTH"])

# -----------------------------------------------------------------------------
# App entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # 0.0.0.0 to be reachable in Docker/WSL; threaded for basic concurrency.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), threaded=True)
