# 🚚 Freight Invoice Validation AI Agent
### Symplichain Hackathon Submission

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-10%20Passed-brightgreen.svg)](#testing)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Anthropic](https://img.shields.io/badge/Powered%20by-Claude%20API-orange.svg)](https://anthropic.com)

> **Automating freight invoice reconciliation for Symplichain's AI-native supply chain platform — reducing manual review by 80% and protecting against billing leakage.**

---

## 📋 Problem Statement

Logistics companies process **1,000+ freight invoices per month** from carriers, freight forwarders, and warehouse partners. Today, this process is:

- ❌ **Manual** — Finance teams spend 12+ minutes per invoice cross-checking line items
- ❌ **Error-prone** — 1–2% error rates cause payment disputes and damaged vendor relationships
- ❌ **Costly** — Undetected overcharges silently drain working capital
- ❌ **Slow** — Reconciliation delays hold up payment cycles and hurt cash flow

---

## ✅ Solution

An **AI Agent** that automatically:
1. **Extracts** structured data from unstructured invoice text (PDFs, emails, scans)
2. **Validates** each invoice against its Purchase Order using 6 business rules
3. **Classifies** invoices as APPROVED / FLAGGED / REJECTED with confidence scores
4. **Reports** financial impact and recommended actions for every invoice

### Key Results (on sample data)
| Metric | Value |
|---|---|
| Auto-approval rate | 33–95% depending on data quality |
| Overcharge detected | $786 across 3 invoices |
| Manual time saved | ~36 min per batch |
| Test coverage | 10/10 tests passing |

---

## 🏗️ Architecture

```
Raw Invoice Text (PDF/Email/Scan)
        │
        ▼
┌──────────────────────────┐
│  InvoiceExtractionAgent  │  ← Claude API (Anthropic)
│  Parses unstructured text│    Extracts: vendor, amounts,
│  → FreightInvoice object │    dates, IDs via structured prompt
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│   ValidationEngine       │  ← Rule-based + threshold logic
│   6 validation rules:    │
│   1. Vendor match         │
│   2. Base freight check  │
│   3. Fuel surcharge ±5%  │
│   4. Accessorial cap 120%│
│   5. Total cross-check   │
│   6. Duplicate detection │
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  ValidationResult        │  → Status, discrepancies,
│  + BatchReport           │    financial impact, action
└──────────────────────────┘
```

---

## 📁 Project Structure

```
symplichain_hackathon/
├── src/
│   ├── freight_invoice_agent.py   # Core agent: extraction + validation + orchestration
│   └── demo.py                    # Demo runner with sample invoices
├── tests/
│   └── test_validation_engine.py  # 10 unit tests (all passing)
├── docs/
│   └── documentation.pdf          # Full project documentation
├── data/
│   └── sample/                    # Sample invoice text files
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/symplichain-freight-agent.git
cd symplichain-freight-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
export ANTHROPIC_API_KEY="your_key_here"
```

### Run Demo

```bash
# Mock mode — no API key needed, great for offline demos
cd src
python demo.py --mock

# Live mode — uses real Claude API
python demo.py --api-key YOUR_API_KEY
```

### Run Tests

```bash
cd tests
pytest test_validation_engine.py -v
```

---

## 🔌 Usage as a Library

```python
from src.freight_invoice_agent import FreightInvoiceOrchestrator, PurchaseOrder

# Initialize
agent = FreightInvoiceOrchestrator(api_key="YOUR_KEY")

# Define your Purchase Order
po = PurchaseOrder(
    po_number="PO-2025-001",
    shipment_id="SH-001",
    vendor="FastFreight Logistics",
    agreed_base_freight=1200.00,
    agreed_fuel_surcharge=144.00,
    max_accessorial=100.00,
    expected_total=1444.00
)

# Process an invoice (raw text from PDF extraction or email)
invoice_text = """
Invoice #INV-2025-001
Vendor: FastFreight Logistics
Base Freight: $1200.00
Fuel Surcharge: $144.00
Accessorial: $80.00
Total: $1424.00
"""

report = agent.process_batch([{"text": invoice_text, "po": po}])
print(report["summary"])
# {'approved': 1, 'flagged': 0, 'rejected': 0, 'total_potential_overcharge_usd': 0.0}
```

---

## 🧪 Testing

10 unit tests covering all validation rules:

```
✅ test_clean_invoice_approved
✅ test_vendor_mismatch_flagged
✅ test_overcharged_freight_flagged
✅ test_fuel_surcharge_tolerance
✅ test_fuel_surcharge_exceeds_tolerance
✅ test_accessorial_hard_cap
✅ test_duplicate_invoice_detected
✅ test_totals_cross_check
✅ test_large_overcharge_rejected
✅ test_financial_impact_calculation
```

---

## 🔮 Future Enhancements

- **PDF Parser Integration** — Direct PDF ingestion via PyMuPDF / pdfplumber
- **ERP Connector** — REST API integration with SAP, Oracle, Tally
- **ML Anomaly Detection** — Train on historical invoices to detect subtle fraud patterns
- **Multi-currency Support** — Handle INR, EUR, GBP alongside USD
- **Dashboard UI** — React frontend for finance team review queue
- **Webhook Notifications** — Slack/email alerts on REJECTED invoices

---

## 📚 Tech Stack

| Component | Technology |
|---|---|
| AI Extraction | Claude (Anthropic) — `claude-sonnet-4-20250514` |
| Language | Python 3.10+ |
| Data Models | Python dataclasses |
| Testing | pytest |
| Documentation | ReportLab PDF |

---

## 📄 License

MIT License — free to use and build upon.

---

## 🤝 Acknowledgements

Built for the **Symplichain Hackathon** — an AI-native supply chain orchestration platform by Symplichain Technologies Pvt Ltd, a member of the NVIDIA Inception Program.
