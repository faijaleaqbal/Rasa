---
name: expense-tracker-finance
description: Bank SMS and transaction parsing, auto-categorization of expenses, budget monitoring, and financial report generation.
---

# Expense & Personal Finance Tracker Skill

Automates parsing of transactional notifications (UPI, Credit Cards, Net Banking) and computes real-time spending insights.

## SMS / Notification Regex Parsing
Extract amount, vendor/merchant, transaction type (`debited`/`credited`), and account reference:
```python
import re

PATTERNS = [
    # UPI / Card Debited pattern
    r"(?i)(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)\s*(?:debited|spent|paid).*?(?:to|at|vpa)\s+([A-Za-z0-9\s\.\@]+)",
    # Credit pattern
    r"(?i)(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)\s*(?:credited|received).*?(?:from)\s+([A-Za-z0-9\s\.\@]+)"
]
```

## Expense Categorization Engine
Map merchant keywords to financial buckets:
* **Food & Dining**: Zomato, Swiggy, Blinkit, Zepto, Starbucks.
* **Shopping & Retail**: Amazon, Flipkart, Myntra, Zara.
* **Utilities & Bills**: Electricity, Water, Broadband, Mobile Recharge, Gas.
* **Travel & Commute**: Uber, Ola, Rapido, IRCTC, Fuel/Petrol.
* **Investments**: Zerodha, Groww, INDmoney, Mutual Funds.

## Monthly Summary Generation
Compute total spend, top spending category, remaining monthly budget, and deliver a visual breakdown.
