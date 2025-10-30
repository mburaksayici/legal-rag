import os
from urllib.parse import urlparse
from typing import Optional

SUPPORTED_TYPES = {"json", "pdf"}


def detect_media_type(path_or_url: str, hint: Optional[str] = None) -> Optional[str]:
	"""
	Very simple media type detector. Prefers explicit hint, then file extension.
	Returns 'json' or 'pdf' if detected, else None.
	"""
	if hint and hint.lower() in SUPPORTED_TYPES:
		return hint.lower()
	parsed = urlparse(path_or_url)
	candidate = parsed.path if parsed.scheme else path_or_url
	ext = os.path.splitext(candidate)[1].lower().lstrip(".")
	if ext in SUPPORTED_TYPES:  # type: ignore[name-defined]
		return ext
	return None
