"""API package: FastAPI application exposing the platform's HTTP interface."""

from app.api.server import create_app

__all__ = ["create_app"]
