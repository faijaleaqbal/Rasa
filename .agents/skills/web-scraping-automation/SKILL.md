---
name: web-scraping-automation
description: Browser automation with Playwright and Puppeteer, headless web scraping, dynamic page rendering, and anti-bot mitigation.
---

# Web Scraping & Browser Automation Skill

Automates web interactions, data extraction from Javascript-heavy websites, form submissions, and screenshot capture.

## Automation Engines

### 1. Playwright / Puppeteer Headless Runner
```javascript
const { chromium } = require('playwright');

async function scrapePage(url) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const content = await page.content();
  await browser.close();
  return content;
}
```

### 2. Beautiful Soup & Requests Fast Parser
For static HTML pages without dynamic JS requirements:
```python
import requests
from bs4 import BeautifulSoup

def extract_article_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    return " ".join([p.get_text() for p in soup.find_all("p")])
```

## Best Practices
* Always respect `robots.txt` and rate limits.
* Use randomized delays between requests to prevent IP throttling.
