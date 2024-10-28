from typing import Dict
from .ocr import PDFTextExtractor
from .grading import GradingSystem

class BatchProcessor:
    def __init__(self, text_extractor: PDFTextExtractor, grading_system: GradingSystem):
        self.text_extractor = text_extractor
        self.grading_system = grading_system
