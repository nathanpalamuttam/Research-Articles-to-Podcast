# Research Article Podcast Generator

Automatically convert research papers (PDFs) into podcast scripts and SSML audio files.

## Features

- 📄 **PDF Text Extraction**: Intelligently extracts text from research papers, removing references and keeping only relevant diagrams
- 🤖 **AI Script Generation**: Uses Google Gemini to create engaging podcast scripts
- 🔊 **SSML Conversion**: Converts scripts to SSML format for text-to-speech synthesis
- 🎯 **Smart Image Filtering**: Only extracts diagrams from methodology/architecture sections

## Setup

### 1. Install Dependencies

```bash
pip install google-genai PyPDF2 Pillow python-dotenv requests
```

### 2. Get Google AI API Key

1. Visit https://aistudio.google.com/apikey
2. Create an API key
3. Add it to `.env` file:

```bash
GOOGLE_API_KEY=your-api-key-here
```

## Usage

### Quick Start

Generate a podcast from a PDF:

```bash
python3 generate_podcast.py
```

This will:
1. Extract text from the PDF
2. Generate a podcast script using Gemini
3. Convert the script to SSML format
4. Save both files to `outputs/scripts/`

### Individual Components

#### Extract PDF Content

```python
from extract_pdf_text import extract_content_from_pdf

content = extract_content_from_pdf(
    pdf_path="paper.pdf",
    remove_references=True,
    keep_images=True,
    image_quality=70
)

text = content['text']
images = content['images']  # Base64 encoded
```

#### Convert Script to SSML

```python
from script_to_ssml import convert_script_file
from pathlib import Path

ssml_path = convert_script_file(
    input_path=Path("script.txt"),
    output_path=Path("script.ssml")
)
```

## File Structure

```
Spotify_Playlist_Research_Articles/
├── generate_podcast.py       # Main script (recommended)
├── extract_pdf_text.py        # PDF extraction utilities
├── script_to_ssml.py          # SSML conversion utilities
├── list_models.py             # List available Gemini models
├── .env                       # API keys (create this)
└── outputs/
    └── scripts/
        ├── podcast_script.txt
        └── podcast_script.ssml
```

## Configuration

Edit `generate_podcast.py` to customize:

```python
PDF_FILE = "your-paper.pdf"           # Input PDF
MODEL = "models/gemini-2.5-flash"     # Gemini model
MAX_TEXT_LENGTH = 30000               # Max chars to send to AI
OUTPUT_DIR = Path("outputs/scripts")  # Output directory
```

## Available Gemini Models

Run `python3 list_models.py` to see all available models.

**Recommended models:**
- `models/gemini-2.5-flash` - Best balance (default)
- `models/gemini-2.5-pro` - Most capable
- `models/gemini-flash-latest` - Always latest version

## Output Files

### podcast_script.txt
Plain text podcast script ready for human review or editing.

### podcast_script.ssml
SSML-formatted version ready for Google Cloud Text-to-Speech:

```xml
<?xml version="1.0"?>
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <p>Welcome to the podcast...</p>
  <break time="1s"/>
  <p><emphasis level="strong">Section Header</emphasis></p>
</speak>
```

## Tips

- **Quota Limits**: Free tier has daily limits. Enable billing for higher quotas.
- **Text Length**: Papers longer than 30,000 chars will be truncated. Adjust `MAX_TEXT_LENGTH` as needed.
- **Image Quality**: Lower `image_quality` (default: 70) to reduce API payload size.
- **SSML Voice**: Edit `script_to_ssml.py` to change TTS voice (default: `en-US-Neural2-J`).

## Troubleshooting

### "GOOGLE_API_KEY not found"
Add your API key to `.env` file.

### "404 NOT_FOUND" model error
Use the full model path with `models/` prefix (e.g., `models/gemini-2.5-flash`).

### "429 RESOURCE_EXHAUSTED" quota error
You've hit your free tier limit. Wait 24 hours or enable billing.

### PDF extraction too large
- Set `remove_references=True` (default)
- Set `keep_images=False` to skip images
- Lower `image_quality` parameter

## License

MIT
