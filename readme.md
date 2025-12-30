# NinjaMediaManager

A Docker-based web tool for managing MKV subtitles. Extract subtitle tracks, OCR PGS (image-based) subtitles to SRT, spell-check results, and add creator stamps.

**Warning:** This project was vibe-coded with AI assistance. Use at your own risk.

## To-Do:

* Add / to I character replacement.

## Quick Start

```bash
docker-compose up --build
```

Then open `http://localhost:8080`

## Configuration

Mount your media folder read-only and an output folder for extracted subtitles:

```yaml
volumes:
  - /path/to/media:/media:ro
  - ./output:/output
```

## Credits

- [pgs-to-srt](https://github.com/Tentacule/PgsToSrt) - PGS subtitle OCR (Deno/Tesseract)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Text recognition
- [FFmpeg](https://ffmpeg.org/) - Media processing
- [MKVToolNix](https://mkvtoolnix.download/) - MKV container tools
