"""
Symplichain Hackathon — Freight Invoice Validation AI Agent
===========================================================
Problem:  Logistics companies process 1,000+ freight invoices/month manually,
          leading to errors, billing leakage, and slow reconciliation.
Solution: An AI agent that automatically extracts, validates, and reconciles
          freight invoices against purchase orders and shipment records.

Author : Hackathon Submission
Tech   : Python 3.10+, Claude API (Anthropic), pandas, reportlab
"""

import json
import re
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
import anthropic

# ── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class FreightInvoice:
    """Represents a parsed freight invoice."""
    invoice_id: str
    vendor: str
    shipment_id: str
    invoice_date: str
    due_date: str
    base_freight: float
    fuel_surcharge: float
    accessorial_charges: float
    total_amount: float
    currency: str = "USD"
    raw_text: str = ""


@dataclass
class PurchaseOrder:
    """Expected shipment cost from the PO/contract."""
    po_number: str
    shipment_id: str
    vendor: str
    agreed_base_freight: float
    agreed_fuel_surcharge: float
    max_accessorial: float
    expected_total: float


@dataclass
class ValidationResult:
    """Result of invoice vs PO validation."""
    invoice_id: str
    shipment_id: str
    status: str                    # APPROVED | FLAGGED | REJECTED
    discrepancies: list[str]
    financial_impact: float        # Overcharge amount (+ = overcharged)
    confidence_score: float        # 0.0 – 1.0
    recommended_action: str
    validated_at: str


# ── AI Extraction Layer ────────────────────────────────────────────────────────

class InvoiceExtractionAgent:
    """
    Uses Claude API to extract structured data from raw invoice text.
    Handles PDFs, scanned documents, varied formats.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

    def extract(self, raw_invoice_text: str) -> FreightInvoice:
        """
        Extract structured invoice fields from unstructured text.
        Returns a FreightInvoice dataclass.
        """
        prompt = f"""You are a freight invoice parsing expert. Extract ALL fields from the invoice below.

Return ONLY a valid JSON object with EXACTLY these keys:
{{
  "invoice_id": "string",
  "vendor": "string",
  "shipment_id": "string",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "base_freight": <number>,
  "fuel_surcharge": <number>,
  "accessorial_charges": <number>,
  "total_amount": <number>,
  "currency": "USD"
}}

Rules:
- All monetary values must be numbers (not strings)
- If a field is missing, use 0 for numbers and "UNKNOWN" for strings
- Do NOT include markdown, backticks, or explanations — pure JSON only

INVOICE TEXT:
{raw_invoice_text}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_json = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw_json = re.sub(r"^```json\s*|^```\s*|```$", "", raw_json, flags=re.MULTILINE).strip()

        data = json.loads(raw_json)
        return FreightInvoice(raw_text=raw_invoice_text, **data)


# ── Validation Engine ──────────────────────────────────────────────────────────

class ValidationEngine:
    """
    Rule-based + AI-assisted validation of extracted invoices against POs.
    Detects overcharges, missing items, duplicate invoices, and anomalies.
    """

    # Tolerance thresholds
    FUEL_SURCHARGE_TOLERANCE = 0.05   # ±5% tolerance on fuel surcharges
    ACCESSORIAL_HARD_CAP = 1.20       # Never exceed 120% of agreed accessorial
    DUPLICATE_WINDOW_DAYS = 30        # Flag duplicates within 30 days

    def __init__(self):
        self._seen_invoices: dict[str, str] = {}  # invoice_id → date

    def validate(self, invoice: FreightInvoice, po: PurchaseOrder) -> ValidationResult:
        """
        Validate invoice against PO. Returns a ValidationResult with
        status, discrepancies, and recommended action.
        """
        discrepancies = []
        financial_impact = 0.0

        # ── Rule 1: Vendor match ──────────────────────────────────────────────
        if invoice.vendor.lower() != po.vendor.lower():
            discrepancies.append(
                f"Vendor mismatch: Invoice says '{invoice.vendor}', PO says '{po.vendor}'"
            )

        # ── Rule 2: Base freight within tolerance ─────────────────────────────
        freight_diff = invoice.base_freight - po.agreed_base_freight
        if abs(freight_diff) > 0.01:
            discrepancies.append(
                f"Base freight discrepancy: Invoiced ${invoice.base_freight:.2f} "
                f"vs agreed ${po.agreed_base_freight:.2f} (diff: ${freight_diff:+.2f})"
            )
            financial_impact += freight_diff

        # ── Rule 3: Fuel surcharge tolerance check ────────────────────────────
        expected_fuel = po.agreed_fuel_surcharge
        fuel_ratio = (invoice.fuel_surcharge / expected_fuel) if expected_fuel > 0 else 1.0
        if abs(fuel_ratio - 1.0) > self.FUEL_SURCHARGE_TOLERANCE:
            fuel_diff = invoice.fuel_surcharge - expected_fuel
            discrepancies.append(
                f"Fuel surcharge exceeds ±5% tolerance: Invoiced ${invoice.fuel_surcharge:.2f} "
                f"vs expected ${expected_fuel:.2f}"
            )
            financial_impact += fuel_diff

        # ── Rule 4: Accessorial hard cap ─────────────────────────────────────
        if invoice.accessorial_charges > po.max_accessorial * self.ACCESSORIAL_HARD_CAP:
            excess = invoice.accessorial_charges - po.max_accessorial
            discrepancies.append(
                f"Accessorial charges exceed cap: ${invoice.accessorial_charges:.2f} "
                f"vs max allowed ${po.max_accessorial:.2f} (excess: ${excess:.2f})"
            )
            financial_impact += excess

        # ── Rule 5: Total amount cross-check ─────────────────────────────────
        calculated_total = (
            invoice.base_freight + invoice.fuel_surcharge + invoice.accessorial_charges
        )
        if abs(calculated_total - invoice.total_amount) > 0.02:
            discrepancies.append(
                f"Invoice totals don't add up: Line items sum to ${calculated_total:.2f} "
                f"but invoice total shows ${invoice.total_amount:.2f}"
            )

        # ── Rule 6: Duplicate detection ───────────────────────────────────────
        if invoice.invoice_id in self._seen_invoices:
            discrepancies.append(
                f"DUPLICATE INVOICE: {invoice.invoice_id} was already processed on "
                f"{self._seen_invoices[invoice.invoice_id]}"
            )
        else:
            self._seen_invoices[invoice.invoice_id] = invoice.invoice_date

        # ── Determine status ──────────────────────────────────────────────────
        if not discrepancies:
            status = "APPROVED"
            confidence = 0.97
            action = "Auto-approve for payment processing."
        elif financial_impact > 500 or any("DUPLICATE" in d for d in discrepancies):
            status = "REJECTED"
            confidence = 0.92
            action = f"Reject and dispute with vendor. Estimated overcharge: ${financial_impact:.2f}."
        else:
            status = "FLAGGED"
            confidence = 0.85
            action = f"Route to finance team for manual review. Potential overcharge: ${financial_impact:.2f}."

        return ValidationResult(
            invoice_id=invoice.invoice_id,
            shipment_id=invoice.shipment_id,
            status=status,
            discrepancies=discrepancies,
            financial_impact=round(financial_impact, 2),
            confidence_score=confidence,
            recommended_action=action,
            validated_at=datetime.utcnow().isoformat() + "Z"
        )


# ── Orchestrator ───────────────────────────────────────────────────────────────

class FreightInvoiceOrchestrator:
    """
    Main orchestration layer: extract → validate → summarize.
    Processes batches of invoices and returns a structured audit report.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.extractor = InvoiceExtractionAgent(api_key=api_key)
        self.validator = ValidationEngine()

    def process_batch(
        self,
        invoices: list[dict],   # Each dict: {"text": "...", "po": PurchaseOrder}
    ) -> dict:
        """
        Process a batch of raw invoices against their matched POs.
        Returns a full audit report dict.
        """
        results = []
        total_overcharge = 0.0
        approved = flagged = rejected = 0

        for item in invoices:
            try:
                # Step 1: AI extraction
                invoice = self.extractor.extract(item["text"])

                # Step 2: Rule-based validation
                result = self.validator.validate(invoice, item["po"])
                results.append(asdict(result))

                # Step 3: Tally
                if result.status == "APPROVED":
                    approved += 1
                elif result.status == "FLAGGED":
                    flagged += 1
                    total_overcharge += max(result.financial_impact, 0)
                else:
                    rejected += 1
                    total_overcharge += max(result.financial_impact, 0)

            except Exception as e:
                results.append({
                    "invoice_id": "PARSE_ERROR",
                    "error": str(e),
                    "status": "ERROR"
                })

        return {
            "report_generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_processed": len(invoices),
                "approved": approved,
                "flagged": flagged,
                "rejected": rejected,
                "total_potential_overcharge_usd": round(total_overcharge, 2),
                "auto_approval_rate": f"{(approved / len(invoices) * 100):.1f}%" if invoices else "0%"
            },
            "results": results
        }
