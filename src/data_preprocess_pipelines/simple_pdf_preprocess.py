"""Simple PDF text extraction for evaluation purposes."""
from typing import Dict, Any
import PyPDF2
from pathlib import Path
from .base import DataPreprocessBase


class SimplePDFPreprocess(DataPreprocessBase):
    """Simple PDF text extraction using PyPDF2."""
    
    def run_single_doc(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from a single PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
                - success: bool
                - text: str (extracted text)
                - page_count: int
                - error: str (if failed)
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "text": "",
                    "page_count": 0
                }
            
            if path.suffix.lower() != '.pdf':
                return {
                    "success": False,
                    "error": f"Not a PDF file: {file_path}",
                    "text": "",
                    "page_count": 0
                }
            
            # Extract text from PDF
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                extracted_text = "\n".join(text_parts)
                
                if not extracted_text.strip():
                    return {
                        "success": False,
                        "error": "No text could be extracted from PDF",
                        "text": "",
                        "page_count": page_count
                    }
                
                return {
                    "success": True,
                    "text": extracted_text,
                    "page_count": page_count,
                    "character_count": len(extracted_text)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process PDF: {str(e)}",
                "text": "",
                "page_count": 0
            }

