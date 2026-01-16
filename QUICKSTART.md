# Quick Start Guide

## One-Command Setup

```bash
# 1. Install dependencies
pip install google-genai PyPDF2 Pillow python-dotenv requests

# 2. Add API key to .env
echo "GOOGLE_API_KEY=your-key-here" > .env

# 3. Run the generator
python3 generate_podcast.py
```

## What Gets Generated

```
outputs/scripts/
├── podcast_script.txt   ← Human-readable script
└── podcast_script.ssml  ← Ready for Google Cloud TTS
```

## Customize Your PDF

Edit `generate_podcast.py` line 17:
```python
PDF_FILE = "your-paper-name.pdf"
```

## Using Different Models

See available models:
```bash
python3 list_models.py
```

Change model in `generate_podcast.py` line 19:
```python
MODEL = "models/gemini-2.5-pro"  # More powerful
MODEL = "models/gemini-2.0-flash"  # Faster
```

## Common Issues

**No API key?**
Get one here: https://aistudio.google.com/apikey

**Quota exceeded?**
Wait 24 hours or enable billing on Google Cloud.

**Model not found?**
Always use `models/` prefix (e.g., `models/gemini-2.5-flash`)

## Next Steps

Use the SSML file with:
- Google Cloud Text-to-Speech API
- Amazon Polly
- Microsoft Azure Speech
- Any SSML-compatible TTS service
