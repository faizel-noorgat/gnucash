"""Development overrides. Not used in production or CI."""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# In development, surface a clearer traceback for misconfigured secrets.
import os

if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set. Copy .env.example to .env and "
        "fill in a value; do NOT paste a real secret into this file."
    )
