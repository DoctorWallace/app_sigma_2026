import json
from pathlib import Path

from django.conf import settings


QUALITY_TEMPLATES_ROOT = Path(settings.BASE_DIR) / "quality_templates"


def load_quality_json(relative_path, fallback=None):
    """Load a quality template JSON file, returning fallback on failure."""
    path = QUALITY_TEMPLATES_ROOT.joinpath(*relative_path)
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return fallback if fallback is not None else {}
