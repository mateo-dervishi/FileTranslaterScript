"""
PDF Catalogue Translator API
Translates Chinese text to English while preserving layout, images, and English text.
Handles files via URL (from Vercel Blob storage).
"""

from http.server import BaseHTTPRequestHandler
import json
import io
import urllib.request
import urllib.parse
import os

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
        result = translator.translate(text)
        return result if result else text
    except Exception:
        return text


def process_pdf(input_bytes: bytes) -> bytes:
    """
    Process PDF: translate Chinese text to English while preserving layout.
    """
    if not fitz:
        raise ImportError("PyMuPDF not available")
    if not GoogleTranslator:
        raise ImportError("deep_translator not available")
    
    translator = GoogleTranslator(source='zh-CN', target='en')
    translation_cache = {}
    
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        
        redact_regions = []
        translations_to_add = []
        
        for block in blocks:
            if block.get("type") != 0:
                continue
                
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    if is_chinese_text(text):
                        bbox = span.get("bbox")
                        if bbox:
                            if text in translation_cache:
                                translated = translation_cache[text]
                            else:
                                translated = translate_chinese(text, translator)
                                translation_cache[text] = translated
                            
                            if translated and translated != text:
                                font_size = span.get('size', 12)
                                color = span.get('color', 0)
                                redact_regions.append(bbox)
                                translations_to_add.append({
                                    'bbox': bbox,
                                    'text': translated,
                                    'font_size': font_size,
                                    'color': color,
                                })
        
        # Apply redactions
        for bbox in redact_regions:
            rect = fitz.Rect(bbox)
            annot = page.add_redact_annot(rect)
            annot.set_colors(stroke=None, fill=None)
        
        if redact_regions:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        
        # Add translated text
        for item in translations_to_add:
            bbox = item['bbox']
            text = item['text']
            font_size = item['font_size']
            rect = fitz.Rect(bbox)
            fontname = "helv"
            
            test_size = font_size
            while test_size > 6:
                text_length = fitz.get_text_length(text, fontname=fontname, fontsize=test_size)
                if text_length <= rect.width * 1.1:
                    break
                test_size -= 0.5
            
            insert_point = fitz.Point(rect.x0, rect.y0 + (rect.height + test_size) / 2)
            
            color_int = item['color']
            if isinstance(color_int, int):
                r = ((color_int >> 16) & 255) / 255
                g = ((color_int >> 8) & 255) / 255
                b = (color_int & 255) / 255
                color = (r, g, b)
            else:
                color = (0, 0, 0)
            
            try:
                page.insert_text(insert_point, text, fontname=fontname, fontsize=test_size, color=color)
            except Exception:
                try:
                    page.insert_text(insert_point, text, fontsize=test_size)
                except Exception:
                    pass
    
    output_buffer = io.BytesIO()
    doc.save(output_buffer, garbage=4, deflate=True, clean=True)
    doc.close()
    
    return output_buffer.getvalue()


def download_file(url: str) -> bytes:
    """Download file from URL"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length == 0:
                self._send_json_error(400, "No content received")
                return
            
            # Read JSON body with file URL
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_json_error(400, "Invalid JSON")
                return
            
            file_url = data.get('url')
            if not file_url:
                self._send_json_error(400, "No file URL provided")
                return
            
            # Download file from blob storage
            try:
                file_content = download_file(file_url)
            except Exception as e:
                self._send_json_error(500, f"Failed to download file: {str(e)}")
                return
            
            if not file_content:
                self._send_json_error(400, "Empty file")
                return
            
            # Check PDF magic bytes
            if not file_content[:4] == b'%PDF':
                self._send_json_error(400, "Invalid PDF file")
                return
            
            # Process PDF
            try:
                output_pdf = process_pdf(file_content)
            except ImportError as e:
                self._send_json_error(500, f"Server configuration error: {str(e)}")
                return
            except Exception as e:
                self._send_json_error(500, f"Translation failed: {str(e)}")
                return
            
            # Return the PDF directly (base64 encoded for JSON response)
            import base64
            output_base64 = base64.b64encode(output_pdf).decode('utf-8')
            
            response = json.dumps({
                "success": True,
                "pdf": output_base64,
                "size": len(output_pdf)
            })
            response_bytes = response.encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
            
        except Exception as e:
            self._send_json_error(500, f"Unexpected error: {str(e)}")
    
    def _send_json_error(self, code: int, message: str):
        response = json.dumps({"error": message})
        response_bytes = response.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_bytes)
    
    def do_GET(self):
        response = json.dumps({
            "name": "PDF Translator API",
            "version": "2.0.0",
            "status": "ready",
            "dependencies": {
                "pymupdf": fitz is not None,
                "deep_translator": GoogleTranslator is not None
            }
        })
        response_bytes = response.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_bytes)
    
    def log_message(self, format, *args):
        pass
