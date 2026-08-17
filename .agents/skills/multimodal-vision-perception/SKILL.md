---
name: multimodal-vision-perception
description: Multimodal visual understanding, image and video scene analysis, diagram inspection, and visual question answering (VQA).
---

# Multimodal Vision & Perception Skill

Processes visual inputs (screenshots, photos, diagrams, UI mockups, video frames) to extract deep semantic context.

## Vision Processing Pipelines
1. **Scene & UI Analysis**: Detect layout hierarchy, color palettes, UI components, typography, and visual bugs in screenshots.
2. **Visual Question Answering (VQA)**: Extract specific details from charts, architecture diagrams, receipts, and whiteboard sketches.
3. **Video Frame Sampling**: Extract representative keyframes at regular intervals (e.g. 1 frame/sec) for sequential action recognition and summarization.

## Python Integration
```python
import base64

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
```
