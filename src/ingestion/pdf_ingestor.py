from .base import BaseIngestor
from .schemas import IngestRequest, IngestResponse, IngestedItem
import PyPDF2
from pathlib import Path


class PDFIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(name="pdf")

	def ingest(self, request: IngestRequest) -> IngestResponse:
		"""
		Uses PyPDF2 to parse PDFs quickly.
		- For local paths: convert to text via PyPDF2's PdfReader
		- For URLs: not implemented here (placeholder for future HTTP fetch + temp file)
		"""
		path_or_url = request.path_or_url
		text = ""
		
		try:
			path = Path(path_or_url)
			
			# Check if file exists
			if not path.exists():
				# Return empty response for missing file
				item = IngestedItem(source=path_or_url, len_characters=0, text="")
				return IngestResponse(items=[item])
			
			# Check if it's a PDF file
			if path.suffix.lower() != '.pdf':
				# Return empty response for non-PDF files
				item = IngestedItem(source=path_or_url, len_characters=0, text="")
				return IngestResponse(items=[item])
			
			# Extract text from PDF using PyPDF2
			with open(path_or_url, 'rb') as file:
				pdf_reader = PyPDF2.PdfReader(file)
				
				text_parts = []
				for page in pdf_reader.pages:
					page_text = page.extract_text()
					if page_text:
						text_parts.append(page_text)
				
				text = "\n".join(text_parts)
		
		except Exception as e:
			# On any error, return empty text
			text = ""
		
		item = IngestedItem(source=path_or_url, len_characters=len(text), text=text)
		return IngestResponse(items=[item])
