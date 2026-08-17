---
name: invoice-billing-mgmt
description: PDF invoice generation, client payment tracking, tax calculation (GST/VAT), and automated billing reminder dispatch.
---

# Invoice & Freelance Billing Management Skill

Generates professional PDF invoices, computes tax subtotals (GST, TDS, VAT), tracks receivables, and automates overdue payment reminders.

## Core Capabilities
1. **PDF Generation**: Use ReportLab / Weasyprint to render pixel-perfect, branded client invoices with payment links (UPI QR / Stripe).
2. **Itemization & Tax Calculations**: Compute base amount, discounts, applicable taxes (CGST+SGST / IGST), and total payable amount.
3. **Accounts Receivable Ledger**: Track invoice states (`draft`, `issued`, `paid`, `overdue`) inside SQLite.
