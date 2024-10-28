import fitz  # PyMuPDF
import io
from typing import List, Dict
from PIL import Image, ImageEnhance

class PDFHandler:
    @staticmethod
    def preprocess_image(image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR results."""
        try:
            # Convert to RGB if needed
            if image.mode not in ['RGB']:
                image = image.convert('RGB')
                
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Increase contrast
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)  # Increase sharpness
            
            return image
            
        except Exception as e:
            print(f"Warning: Image preprocessing failed: {str(e)}")
            return image
    
    @staticmethod
    def extract_images_from_pdf(pdf_file) -> List[bytes]:
        images = []
        try:
            pdf_bytes = pdf_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Get page as image (without optimize parameter)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Using 2x scaling for better quality
                img_data = pix.tobytes()  # Remove optimize parameter
                
                # Convert raw bytes to PIL Image for processing
                img_stream = io.BytesIO(img_data)
                pil_image = Image.open(img_stream)
                
                # Convert to RGB and process
                if pil_image.mode not in ['RGB']:
                    pil_image = pil_image.convert('RGB')
                
                # Save as JPEG
                output = io.BytesIO()
                pil_image.save(output, format='JPEG', quality=95)
                images.append(output.getvalue())
                
                # Also try to extract embedded images
                image_list = page.get_images()
                for img in image_list:
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Add embedded image if it exists
                        if image_bytes:
                            images.append(image_bytes)
                    except Exception as e:
                        print(f"Error extracting embedded image: {str(e)}")
                        continue
            
            doc.close()
            return images
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return []
        finally:
            pdf_file.seek(0)

    @staticmethod
    def validate_pdf(pdf_file) -> tuple[bool, str]:
        """Validate PDF file with detailed error reporting."""
        try:
            pdf_bytes = pdf_file.read()
            pdf_file.seek(0)  # Reset file pointer
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count == 0:
                return False, "PDF file appears to be empty"
                
            doc.close()
            return True, "PDF validation successful"
            
        except Exception as e:
            error_msg = f"PDF validation error: {str(e)}"
            print(error_msg)
            return False, error_msg
