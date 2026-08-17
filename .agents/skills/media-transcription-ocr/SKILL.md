---
name: media-transcription-ocr
description: Audio/video speech-to-text transcription (Whisper), Optical Character Recognition (OCR) from screenshots and receipts, and document summarization.
---

# Media Transcription & OCR Skill

Converts unstructured multimedia (voice notes, videos, screenshots, PDF receipts) into clean text, actionable data, and summaries.

## Audio / Speech-to-Text Pipeline (Whisper)
```python
import whisper

def transcribe_audio(audio_path: str) -> str:
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]
```

## OCR & Image Text Extraction (Tesseract / EasyOCR)
```python
import pytesseract
from PIL import Image

def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()
```

## Post-Processing & Summarization
1. Clean OCR artifacts (fix misread digits, remove stray punctuation).
2. For receipts: Extract line items, subtotal, taxes, and final total into JSON.
3. For meetings/voice notes: Generate TL;DR summary and extract action items with assigned owners.
