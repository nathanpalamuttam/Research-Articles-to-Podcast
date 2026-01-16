# Research Article Podcast Generator

Automatically convert arXiv research papers into podcast MP3 files and publish them to your podcast feed on your phone.

## Features

- **Automated arXiv Processing**: Batch process multiple arXiv papers from a simple text file
- **AI Script Generation**: Uses Google Gemini to create engaging 8-10 minute podcast scripts
- **High-Quality TTS**: Google Cloud Text-to-Speech with professional voices
- **Auto-Publishing**: Automatically uploads to Cloudflare R2 and updates RSS feed
- **Duplicate Prevention**: Tracks processed papers to avoid regeneration

## Setup

### 1. Install Dependencies

```bash
pip install google-genai google-cloud-texttospeech PyPDF2 python-dotenv requests feedparser boto3
```

### 2. Configure API Keys

Create a `.env` file with:

```bash
# Google AI API Key (for Gemini script generation)
GOOGLE_API_KEY=your-google-api-key

# Cloudflare R2 Storage (for podcast hosting)
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET=your-bucket-name
R2_PUBLIC_BASE=https://your-podcast-domain.com
```

### 3. Set up Google Cloud TTS

```bash
# Set up Google Cloud credentials for Text-to-Speech
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

## Usage

### Automated Workflow (Recommended)

1. **Add arXiv links** to `arxiv_links.txt`:

```text
https://arxiv.org/abs/2412.14689
https://arxiv.org/abs/2512.10858
```

2. **Run the generator**:

```bash
python3 src/new_tts_generator.py
```

This will automatically:
1. ✅ Download PDFs for new arXiv papers
2. ✅ Extract and clean text content
3. ✅ Generate podcast scripts using Gemini
4. ✅ Synthesize audio with Google Cloud TTS
5. ✅ Upload MP3 to Cloudflare R2 storage
6. ✅ Update podcast RSS feed
7. ✅ Mark papers as processed

### Manual Publishing (if auto-publish fails)

If a podcast was generated but publishing failed, you can manually publish:

```bash
python3 src/publish_episode.py --arxiv 2512.10858
```

## File Structure

```
Spotify_Playlist_Research_Articles/
├── src/
│   ├── new_tts_generator.py   # Main pipeline (generate + publish)
│   ├── publish_episode.py     # Publish to R2 and update feed
│   └── arxiv_utils.py         # arXiv metadata utilities
├── arxiv_links.txt            # Input: arXiv URLs to process
├── processed_links.txt        # Tracks completed papers
├── .env                       # API keys and R2 config
├── data/
│   └── episodes.json          # Podcast episode metadata
├── downloads/pdfs/            # Downloaded arXiv PDFs
└── outputs/audio/             # Generated MP3 files
```

## Configuration

### Podcast Settings

Edit `src/new_tts_generator.py`:

```python
MODEL = "models/gemini-2.5-flash"  # Gemini model for scripts
VOICE_NAME = "en-US-Studio-O"      # TTS voice
SPEAKING_RATE = 1.0                # Playback speed
MAX_TEXT_LENGTH = 30000            # Max chars from PDF
```

### Publishing Settings

Edit `src/publish_episode.py`:

```python
PODCAST_TITLE = "Research Articles (Private)"
PODCAST_DESCRIPTION = "Automatically generated audio narrations..."
ITUNES_CATEGORY = "Science"
KEEP_N_DEFAULT = 30  # Keep last N episodes in feed
```

## How It Works

### 1. Paper Processing
- Checks `arxiv_links.txt` for new URLs not in `processed_links.txt`
- Downloads PDFs and extracts text (removes references, limits to 30k chars)
- Uses Gemini to generate engaging 8-10 minute podcast scripts

### 2. Audio Generation
- Cleans script (removes stage directions, formatting)
- Chunks text to handle long content (max 4500 chars per chunk)
- Synthesizes with Google Cloud TTS using high-quality voices
- Saves MP3 to `outputs/audio/`

### 3. Publishing
- Tags MP3 with metadata using ffmpeg
- Uploads to Cloudflare R2 storage
- Updates `data/episodes.json` with episode metadata
- Regenerates RSS feed (`feed.xml`) with latest episodes
- Maintains last N episodes (configurable, default 30)

## Troubleshooting

### "GOOGLE_API_KEY not found"
Add your API key to `.env` file.

### "Expected MP3 not found"
The filename cleaning logic has changed. Check `outputs/audio/` for the actual filename.

### "Failed to publish episode"
- Verify R2 credentials in `.env`
- Check R2 bucket permissions
- Run manually: `python3 src/publish_episode.py --arxiv <arxiv-id>`

### "429 RESOURCE_EXHAUSTED" (Gemini quota)
You've hit API limits. Wait or enable billing at https://aistudio.google.com/

### Google Cloud TTS authentication error
Set `GOOGLE_APPLICATION_CREDENTIALS`:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## License

MIT
