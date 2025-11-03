# backend/errors.py
from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def on_validation(err):
        return jsonify({"error": "validation_error", "details": err.messages}), 422

    @app.errorhandler(HTTPException)
    def on_http(err):
        return jsonify({"error": err.name, "message": err.description}), err.code

    @app.errorhandler(Exception)
    def on_uncaught(err):
        app.logger.exception("uncaught")
        return jsonify({"error": "internal_server_error"}), 500
