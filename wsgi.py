"""WSGI entrypoint for Vercel and other production hosts."""

from app import create_app

app = create_app()
