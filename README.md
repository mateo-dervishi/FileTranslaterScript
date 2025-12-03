# 文译 Wényì — PDF Catalogue Translator

A web application that translates Chinese text in PDF catalogues to English while preserving the original layout, images, and design quality.

## Features

- ✅ **Chinese → English Translation**: Accurately translates all Chinese text using Google Translate
- ✅ **English Text Preserved**: All English text remains completely untouched
- ✅ **Layout Preservation**: Maintains original design, positioning, and formatting
- ✅ **High Quality Output**: No quality loss in images or graphics
- ✅ **Simple Interface**: Drag & drop your PDF, download the translated version
- ✅ **Team Access**: Share the URL with your team for easy collaboration

## Live Demo

[Your Vercel URL will be here after deployment]

## How It Works

1. **Upload**: Drag and drop your Chinese PDF catalogue
2. **Process**: The app identifies Chinese text, translates it, and replaces it in-place
3. **Download**: Get your translated PDF with all formatting preserved

## Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS, Framer Motion
- **Backend**: Python serverless functions on Vercel
- **PDF Processing**: PyMuPDF (fitz)
- **Translation**: Google Translate via deep-translator

## Local Development

### Prerequisites

- Node.js 18+
- Python 3.9+

### Setup

```bash
# Install Node dependencies
npm install

# Run development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Testing the API locally

```bash
# Install Python dependencies
pip install pymupdf deep-translator

# The API runs automatically with Next.js dev server
```

## Deployment to Vercel

### Option 1: GitHub Integration (Recommended)

1. Push this repository to GitHub
2. Connect your GitHub repo to Vercel
3. Vercel will automatically deploy on every push

### Option 2: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

## Configuration

The application uses the following Vercel function settings:

- **Max Duration**: 300 seconds (5 minutes) for large catalogues
- **Memory**: 3008 MB for PDF processing

## Limitations

- Maximum file size: 100MB
- Processing time depends on catalogue size and number of pages
- Only translates Chinese characters (Unicode range `\u4e00-\u9fff`)
- Text embedded in images is not translated

## API Reference

### POST /api/translate

Translates a PDF file from Chinese to English.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` - The PDF file to translate

**Response:**
- Success: PDF file (application/pdf)
- Error: JSON with error message

```bash
# Example with curl
curl -X POST -F "file=@catalogue.pdf" https://your-app.vercel.app/api/translate -o translated.pdf
```

## Author

Mateo Dervishi

## License

MIT License - feel free to use and modify.

