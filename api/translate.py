"""
PDF Catalogue Translator API
Translates Chinese text to English while preserving layout, images, and English text.
"""

import io
import re
import os
import tempfile
from http.server import BaseHTTPRequestHandler
import cgi

# We'll use a simplified approach for Vercel's serverless environment
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


def is_chinese_text(text: str) -> bool:
    """Check if text contains Chinese characters"""
    if not text or not text.strip():
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars == 0:
        return False
    return (chinese_chars / total_chars) > 0.3


def translate_chinese(text: str, translator) -> str:
    """Translate Chinese text to English"""
    if not text or not text.strip():
        return text
    try:
        return translator.translate(text)
    except Exception:
        return text


def get_text_font_info(page, span):
    """Extract font information from a text span"""
    return {
        'size': span.get('size', 12),
        'font': span.get('font', 'helv'),
        'color': span.get('color', 0),
        'flags': span.get('flags', 0),
    }


def process_pdf(input_bytes: bytes) -> bytes:
    """
    Process PDF: translate Chinese text to English while preserving layout.
    Uses PyMuPDF's native text handling for quality preservation.
    """
    if not fitz:
        raise ImportError("PyMuPDF (fitz) not available")
    if not GoogleTranslator:
        raise ImportError("deep_translator not available")
    
    # Initialize translator
    translator = GoogleTranslator(source='zh-CN', target='en')
    translation_cache = {}
    
    # Open PDF from bytes
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get all text blocks with their positions
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        
        # Collect Chinese text regions to redact
        redact_regions = []
        translations_to_add = []
        
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks (images)
                continue
                
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    # Check if Chinese
                    if is_chinese_text(text):
                        bbox = span.get("bbox")
                        if bbox:
                            # Get translation
                            if text in translation_cache:
                                translated = translation_cache[text]
                            else:
                                translated = translate_chinese(text, translator)
                                translation_cache[text] = translated
                            
                            if translated and translated != text:
                                # Store region for redaction and translation
                                font_info = get_text_font_info(page, span)
                                redact_regions.append(bbox)
                                translations_to_add.append({
                                    'bbox': bbox,
                                    'text': translated,
                                    'font_size': font_info['size'],
                                    'font': font_info['font'],
                                    'color': font_info['color'],
                                })
        
        # Apply redactions (remove Chinese text)
        for bbox in redact_regions:
            # Add redaction annotation
            rect = fitz.Rect(bbox)
            annot = page.add_redact_annot(rect)
            annot.set_colors(stroke=None, fill=None)  # Transparent fill
        
        # Apply all redactions at once
        if redact_regions:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        
        # Add translated text
        for item in translations_to_add:
            bbox = item['bbox']
            text = item['text']
            font_size = item['font_size']
            
            # Calculate text position (left-aligned in original box)
            rect = fitz.Rect(bbox)
            
            # Adjust font size if text is too long
            # Use a standard font that's available
            fontname = "helv"  # Helvetica
            
            # Measure text width and adjust size if needed
            test_size = font_size
            while test_size > 6:
                text_length = fitz.get_text_length(text, fontname=fontname, fontsize=test_size)
                if text_length <= rect.width * 1.1:  # Allow 10% overflow
                    break
                test_size -= 0.5
            
            # Insert text
            # Position at vertical center of original bbox
            insert_point = fitz.Point(rect.x0, rect.y0 + (rect.height + test_size) / 2)
            
            # Convert color from int to RGB tuple
            color_int = item['color']
            if isinstance(color_int, int):
                r = ((color_int >> 16) & 255) / 255
                g = ((color_int >> 8) & 255) / 255
                b = (color_int & 255) / 255
                color = (r, g, b)
            else:
                color = (0, 0, 0)  # Default black
            
            try:
                page.insert_text(
                    insert_point,
                    text,
                    fontname=fontname,
                    fontsize=test_size,
                    color=color,
                )
            except Exception:
                # Fallback: try with default settings
                try:
                    page.insert_text(
                        insert_point,
                        text,
                        fontsize=test_size,
                    )
                except Exception:
                    pass  # Skip if text insertion fails
    
    # Save to bytes with maximum quality
    output_buffer = io.BytesIO()
    doc.save(
        output_buffer,
        garbage=4,  # Maximum garbage collection
        deflate=True,  # Compress
        clean=True,  # Clean up redundant objects
        linear=True,  # Optimize for web viewing
    )
    doc.close()
    
    return output_buffer.getvalue()


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler"""
    
    def do_POST(self):
        """Handle POST request with PDF file"""
        try:
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' not in content_type:
                self.send_error_response(400, "Content-Type must be multipart/form-data")
                return
            
            # Parse the multipart data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type,
                }
            )
            
            # Get the file
            if 'file' not in form:
                self.send_error_response(400, "No file provided")
                return
            
            file_item = form['file']
            if not file_item.file:
                self.send_error_response(400, "Invalid file")
                return
            
            # Read file content
            file_content = file_item.file.read()
            
            if not file_content:
                self.send_error_response(400, "Empty file")
                return
            
            # Process the PDF
            try:
                output_pdf = process_pdf(file_content)
            except ImportError as e:
                self.send_error_response(500, f"Missing dependency: {str(e)}")
                return
            except Exception as e:
                self.send_error_response(500, f"Processing error: {str(e)}")
                return
            
            # Send successful response
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', 'attachment; filename="translated.pdf"')
            self.send_header('Content-Length', str(len(output_pdf)))
            self.end_headers()
            self.wfile.write(output_pdf)
            
        except Exception as e:
            self.send_error_response(500, f"Server error: {str(e)}")
    
    def send_error_response(self, code: int, message: str):
        """Send JSON error response"""
        import json
        response = json.dumps({"error": message})
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode())
    
    def do_GET(self):
        """Handle GET request - return API info"""
        import json
        response = json.dumps({
            "name": "PDF Translator API",
            "version": "1.0.0",
            "status": "ready",
            "usage": "POST a PDF file to translate Chinese text to English"
        })
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode())

