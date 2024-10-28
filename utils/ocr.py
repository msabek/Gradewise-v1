import fitz  # PyMuPDF
from typing import Dict, Callable

class PDFTextExtractor:
    def __init__(self):
        pass
        
    def process_pdf(self, pdf_bytes: bytes, progress_callback: Callable = None) -> Dict:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_content = []
            
            total_pages = doc.page_count
            for page_num in range(total_pages):
                if progress_callback:
                    progress = (page_num + 1) / total_pages
                    progress_callback(progress, f"Processing page {page_num + 1} of {total_pages}...")
                
                page = doc[page_num]
                text_content.append(page.get_text())
            
            doc.close()
            return {
                "text": "\n\n".join(text_content),
                "status": "success"
            }
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
