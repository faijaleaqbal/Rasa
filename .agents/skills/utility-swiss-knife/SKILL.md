---
name: utility-swiss-knife
description: Currency and unit conversion, QR code generation/reading, document format conversion (PDF/Word/Image), and weather-based contextual suggestions.
---

# Utility Swiss Knife Skill

Everyday utilitarian operations: conversions, QR codes, document format transforms, and weather-aware lifestyle nudges.

## Utilities

### 1. Currency & Unit Conversions
* Live currency conversion (USD, INR, EUR, GBP, AED, JPY).
* Metric/Imperial length, weight, temperature, data transfer conversions.

### 2. QR Code Generation & Decoding
```python
import qrcode

def generate_qr(data_text: str, output_path: str = "web/public/qr.png"):
    qr = qrcode.make(data_text)
    qr.save(output_path)
```

### 3. File Format Conversions
* Image resizing, compression, WebP conversion.
* Markdown to PDF / HTML generation, CSV to JSON / Excel transformations.

### 4. Weather-Based Contextual Suggestions
* Check precipitation probability and UV index to give contextual advice (e.g. "Carry an umbrella today", "High heat index — stay hydrated").
