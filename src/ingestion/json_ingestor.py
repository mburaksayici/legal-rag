import json
import os
from typing import Any, List, Tuple

from .base import BaseIngestor
from .schemas import IngestRequest, IngestResponse, IngestedItem

class JSONIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(name="json")

	def ingest(self, request: IngestRequest) -> IngestResponse:
		"""
		Reads a local JSON file and emits text where every line is formatted as
		"key: value" and lines are separated by three newlines ("\n\n\n").
		Nested structures are flattened with dot-separated keys.
		URLs are not handled in this conceptual version.
		"""
		path_or_url = request.path_or_url
		if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
			# Placeholder for URL fetch + parsing
			text = ""  # implement remote fetch if needed later
		else:
			text = self._read_local_json_as_text(path_or_url)

		item = IngestedItem(source=path_or_url, len_characters=len(text), text=text)
		return IngestResponse(items=[item])

	def _read_local_json_as_text(self, path: str) -> str:
		if not os.path.exists(path):
			return ""
		try:
			with open(path, "r", encoding="utf-8") as f:
				data = json.load(f)
		except Exception:
			return ""
		lines = self._flatten_kv_lines(data)
		# Join with triple newlines as requested
		return "\n\n\n".join(lines)

	def _flatten_kv_lines(self, data: Any, prefix: str = "") -> List[str]:
		lines: List[str] = []
		for key, value in self._iter_items(data):
			flat_key = f"{prefix}.{key}" if prefix else str(key)
			if isinstance(value, (dict, list)):
				lines.extend(self._flatten_kv_lines(value, prefix=flat_key))
			else:
				lines.append(f"{flat_key}: {value}")
		return lines

	def _iter_items(self, data: Any) -> List[Tuple[str, Any]]:
		if isinstance(data, dict):
			return list(data.items())
		if isinstance(data, list):
			return [(str(i), v) for i, v in enumerate(data)]
		# Scalar root
		return [("value", data)]
