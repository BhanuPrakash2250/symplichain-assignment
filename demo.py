"""
demo.py — Symplichain Hackathon Demo Runner
============================================
Demonstrates the Freight Invoice Validation Agent with realistic sample data.
Run with:  python demo.py
           python demo.py --mock      (no API key needed)
"""

import argparse
import json
from freight_invoice_agent import (
    FreightInvoice, PurchaseOrder, ValidationEngine,
    FreightInvoiceOrchestrator
)

# ── Sample Invoice Texts ───────────────────────────────────────────────────────

SAMPLE_INVOICES = [
    # Invoice 1: Clean — should be APPROVED
    {
        "text": """
FREIGHT INVOICE
Invoice No: INV-2025-0891
Date: 2025-03-10  Due: 2025-04-10
Vendor: FastFreight Logistics Pvt Ltd
Shipment ID: SH-2025-0312

Bill To: Symplichain Technologies

CHARGES:
Base Freight (Mumbai → Chennai, 1,200 km):  $1,200.00
Fuel Surcharge (12%):                         $144.00
Accessorial (Loading/Unloading):               $80.00
                                           ----------
TOTAL DUE:                                 $1,424.00

Payment terms: Net 30
""",
        "po": PurchaseOrder(
            po_number="PO-20250301",
            shipment_id="SH-2025-0312",
            vendor="FastFreight Logistics Pvt Ltd",
            agreed_base_freight=1200.00,
            agreed_fuel_surcharge=144.00,
            max_accessorial=100.00,
            expected_total=1424.00
        )
    },
    # Invoice 2: Fuel surcharge inflated — should be FLAGGED
    {
        "text": """
TAX INVOICE
Invoice #: INV-2025-0892
Billing Date: 10-Mar-2025   Due: 10-Apr-2025
From: FastFreight Logistics Pvt Ltd
Shipment Ref: SH-2025-0313

Base Freight:       $950.00
Fuel Surcharge:     $190.00   ← (20% — above agreed 12%)
Accessorial Fees:    $60.00
---------------------------
Total:            $1,200.00
""",
        "po": PurchaseOrder(
            po_number="PO-20250302",
            shipment_id="SH-2025-0313",
            vendor="FastFreight Logistics Pvt Ltd",
            agreed_base_freight=950.00,
            agreed_fuel_surcharge=114.00,
            max_accessorial=80.00,
            expected_total=1144.00
        )
    },
    # Invoice 3: Significant overcharge + totals don't add up — REJECTED
    {
        "text": """
COMMERCIAL INVOICE
INV NO: 2025-894
DATE: March 10, 2025
Vendor: FastFreight Logistics Pvt Ltd
SHIP ID: SH-2025-0315

Freight charges Mumbai to Delhi:   $2,400.00
Fuel adjustment:                     $300.00
Extra handling + demurrage:          $450.00
INVOICE TOTAL:                     $3,500.00
""",
        "po": PurchaseOrder(
            po_number="PO-20250304",
            shipment_id="SH-2025-0315",
            vendor="FastFreight Logistics Pvt Ltd",
            agreed_base_freight=2000.00,
            agreed_fuel_surcharge=240.00,
            max_accessorial=200.00,
            expected_total=2440.00
        )
    }
]


# ── Mock Extraction (no API key needed) ───────────────────────────────────────

def mock_extract(invoice_text: str, index: int) -> FreightInvoice:
    """Returns hardcoded extracted invoices for demo without API."""
    mock_data = [
        FreightInvoice(
            invoice_id="INV-2025-0891", vendor="FastFreight Logistics Pvt Ltd",
            shipment_id="SH-2025-0312", invoice_date="2025-03-10", due_date="2025-04-10",
            base_freight=1200.00, fuel_surcharge=144.00, accessorial_charges=80.00,
            total_amount=1424.00, raw_text=invoice_text
        ),
        FreightInvoice(
            invoice_id="INV-2025-0892", vendor="FastFreight Logistics Pvt Ltd",
            shipment_id="SH-2025-0313", invoice_date="2025-03-10", due_date="2025-04-10",
            base_freight=950.00, fuel_surcharge=190.00, accessorial_charges=60.00,
            total_amount=1200.00, raw_text=invoice_text
        ),
        FreightInvoice(
            invoice_id="2025-894", vendor="FastFreight Logistics Pvt Ltd",
            shipment_id="SH-2025-0315", invoice_date="2025-03-10", due_date="2025-03-25",
            base_freight=2400.00, fuel_surcharge=300.00, accessorial_charges=450.00,
            total_amount=3500.00, raw_text=invoice_text
        ),
    ]
    return mock_data[index % len(mock_data)]


def run_mock_demo():
    """Full demo run without calling the Claude API."""
    print("\n" + "="*65)
    print("  SYMPLICHAIN HACKATHON — Freight Invoice Validation Agent")
    print("  [MOCK MODE — No API Key Required]")
    print("="*65)

    validator = ValidationEngine()
    results = []
    total_overcharge = 0.0
    counters = {"APPROVED": 0, "FLAGGED": 0, "REJECTED": 0}

    for i, item in enumerate(SAMPLE_INVOICES):
        invoice = mock_extract(item["text"], i)
        result = validator.validate(invoice, item["po"])

        # Pretty print per invoice
        print(f"\n📄 Invoice: {invoice.invoice_id}")
        print(f"   Shipment : {invoice.shipment_id}")
        print(f"   Total    : ${invoice.total_amount:,.2f}")
        print(f"   Status   : {'✅' if result.status=='APPROVED' else '⚠️' if result.status=='FLAGGED' else '❌'} {result.status}")

        if result.discrepancies:
            print("   Issues:")
            for d in result.discrepancies:
                print(f"     → {d}")

        print(f"   Financial Impact  : ${result.financial_impact:+.2f}")
        print(f"   Confidence Score  : {result.confidence_score:.0%}")
        print(f"   Action            : {result.recommended_action}")

        counters[result.status] = counters.get(result.status, 0) + 1
        total_overcharge += max(result.financial_impact, 0)
        results.append(result)

    print("\n" + "="*65)
    print("  BATCH SUMMARY")
    print("="*65)
    print(f"  Total Processed       : {len(SAMPLE_INVOICES)}")
    print(f"  ✅ Approved            : {counters['APPROVED']}")
    print(f"  ⚠️  Flagged             : {counters['FLAGGED']}")
    print(f"  ❌ Rejected            : {counters['REJECTED']}")
    print(f"  💰 Potential Overcharge: ${total_overcharge:,.2f}")
    auto_rate = counters['APPROVED'] / len(SAMPLE_INVOICES) * 100
    print(f"  🤖 Auto-Approval Rate  : {auto_rate:.0f}%")
    print(f"  ⏱️  Est. Time Saved     : ~{len(SAMPLE_INVOICES) * 12} minutes of manual review")
    print("="*65 + "\n")

    return results


def run_live_demo(api_key: str):
    """Full demo run using the actual Claude API."""
    print("\n" + "="*65)
    print("  SYMPLICHAIN HACKATHON — Freight Invoice Validation Agent")
    print("  [LIVE MODE — Claude API Active]")
    print("="*65)

    orchestrator = FreightInvoiceOrchestrator(api_key=api_key)
    report = orchestrator.process_batch(SAMPLE_INVOICES)

    print(f"\n📊 Report Generated: {report['report_generated_at']}")
    print(f"\nSUMMARY:")
    for k, v in report["summary"].items():
        print(f"  {k:35s}: {v}")

    print(f"\nDETAILED RESULTS:")
    for r in report["results"]:
        status_icon = {"APPROVED": "✅", "FLAGGED": "⚠️", "REJECTED": "❌"}.get(r.get("status"), "❓")
        print(f"\n  {status_icon} {r.get('invoice_id')} → {r.get('status')}")
        if r.get("discrepancies"):
            for d in r["discrepancies"]:
                print(f"     → {d}")
        print(f"     Action: {r.get('recommended_action', 'N/A')}")

    # Save report to JSON
    with open("validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n✅ Full report saved to validation_report.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Symplichain Freight Invoice Validator")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no API key needed)")
    parser.add_argument("--api-key", type=str, help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()

    if args.mock:
        run_mock_demo()
    else:
        api_key = args.api_key or __import__("os").environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️  No API key found. Running in mock mode instead.")
            print("    To use live mode: python demo.py --api-key YOUR_KEY\n")
            run_mock_demo()
        else:
            run_live_demo(api_key)
