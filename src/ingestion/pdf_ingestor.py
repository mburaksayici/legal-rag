from .base import BaseIngestor
from .schemas import IngestRequest, IngestResponse, IngestedItem

class PDFIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(name="pdf")

	def ingest(self, request: IngestRequest) -> IngestResponse:
		"""
		Uses Docling to parse PDFs conceptually. If Docling is unavailable, leaves placeholder.
		- For local paths: convert to text via Docling's DocumentConverter
		- For URLs: not implemented here (placeholder for future HTTP fetch + temp file)
		"""
		path_or_url = request.path_or_url
		text = ""
		try:
			# Lazy import to avoid hard dependency at import-time
			from docling.document_converter import DocumentConverter  # type: ignore
			# NOTE: URL handling can be added by downloading to a temp file first
			converter = DocumentConverter()
			result = converter.convert(path_or_url)  # expects local file path
			# Depending on Docling version, export APIs differ; using generic text export
			# text = result.document.export_to_text()  # placeholder API
			# If export_to_text isn't available in your version, use markdown/plain export
			text = getattr(getattr(result, "document", object()), "export_to_text", lambda: "")()
		except Exception:
			# Leave empty or add TODO for implementation specifics
			text = ""  # implement PDF parsing

		item = IngestedItem(source=path_or_url, len_characters=len(text), text=text)
		return IngestResponse(items=[item])
