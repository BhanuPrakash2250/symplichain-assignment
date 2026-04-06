"""
tests/test_validation_engine.py
================================
Unit tests for the Freight Invoice Validation Engine.
Run with: pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from freight_invoice_agent import FreightInvoice, PurchaseOrder, ValidationEngine


@pytest.fixture
def engine():
    return ValidationEngine()


@pytest.fixture
def clean_invoice():
    return FreightInvoice(
        invoice_id="INV-001",
        vendor="FastFreight Logistics",
        shipment_id="SH-001",
        invoice_date="2025-03-10",
        due_date="2025-04-10",
        base_freight=1000.00,
        fuel_surcharge=120.00,
        accessorial_charges=80.00,
        total_amount=1200.00
    )


@pytest.fixture
def matching_po():
    return PurchaseOrder(
        po_number="PO-001",
        shipment_id="SH-001",
        vendor="FastFreight Logistics",
        agreed_base_freight=1000.00,
        agreed_fuel_surcharge=120.00,
        max_accessorial=100.00,
        expected_total=1200.00
    )


class TestValidationEngine:

    def test_clean_invoice_approved(self, engine, clean_invoice, matching_po):
        """A perfectly matching invoice should be APPROVED."""
        result = engine.validate(clean_invoice, matching_po)
        assert result.status == "APPROVED"
        assert result.discrepancies == []
        assert result.financial_impact == 0.0
        assert result.confidence_score >= 0.90

    def test_vendor_mismatch_flagged(self, engine, clean_invoice, matching_po):
        """Vendor name mismatch should produce a discrepancy."""
        clean_invoice.vendor = "WrongVendor Ltd"
        result = engine.validate(clean_invoice, matching_po)
        assert any("Vendor mismatch" in d for d in result.discrepancies)

    def test_overcharged_freight_flagged(self, engine, clean_invoice, matching_po):
        """Base freight overcharge should be detected and flagged."""
        clean_invoice.base_freight = 1300.00  # $300 over
        clean_invoice.total_amount = 1500.00
        result = engine.validate(clean_invoice, matching_po)
        assert result.financial_impact == pytest.approx(300.00, abs=0.01)
        assert any("Base freight" in d for d in result.discrepancies)

    def test_fuel_surcharge_tolerance(self, engine, clean_invoice, matching_po):
        """Fuel surcharge within ±5% tolerance should pass."""
        clean_invoice.fuel_surcharge = 124.00  # 3.3% over — within tolerance
        result = engine.validate(clean_invoice, matching_po)
        assert not any("Fuel surcharge" in d for d in result.discrepancies)

    def test_fuel_surcharge_exceeds_tolerance(self, engine, clean_invoice, matching_po):
        """Fuel surcharge >5% above expected should be flagged."""
        clean_invoice.fuel_surcharge = 135.00  # 12.5% over
        result = engine.validate(clean_invoice, matching_po)
        assert any("Fuel surcharge" in d for d in result.discrepancies)

    def test_accessorial_hard_cap(self, engine, clean_invoice, matching_po):
        """Accessorial charges > 120% of max should be flagged."""
        clean_invoice.accessorial_charges = 150.00  # 150% of 100
        result = engine.validate(clean_invoice, matching_po)
        assert any("Accessorial" in d for d in result.discrepancies)

    def test_duplicate_invoice_detected(self, engine, clean_invoice, matching_po):
        """Same invoice ID submitted twice should be flagged as duplicate."""
        engine.validate(clean_invoice, matching_po)   # First submission
        second = FreightInvoice(
            invoice_id="INV-001",   # Same ID
            vendor="FastFreight Logistics",
            shipment_id="SH-002",
            invoice_date="2025-03-15",
            due_date="2025-04-15",
            base_freight=1000.00,
            fuel_surcharge=120.00,
            accessorial_charges=80.00,
            total_amount=1200.00
        )
        po2 = PurchaseOrder(
            po_number="PO-002",
            shipment_id="SH-002",
            vendor="FastFreight Logistics",
            agreed_base_freight=1000.00,
            agreed_fuel_surcharge=120.00,
            max_accessorial=100.00,
            expected_total=1200.00
        )
        result = engine.validate(second, po2)
        assert any("DUPLICATE" in d for d in result.discrepancies)

    def test_totals_cross_check(self, engine, clean_invoice, matching_po):
        """Invoice total that doesn't match line items sum should be flagged."""
        clean_invoice.total_amount = 9999.99  # Clearly wrong total
        result = engine.validate(clean_invoice, matching_po)
        assert any("totals don't add up" in d for d in result.discrepancies)

    def test_large_overcharge_rejected(self, engine, clean_invoice, matching_po):
        """Financial impact > $500 should result in REJECTED status."""
        clean_invoice.base_freight = 1700.00  # $700 overcharge
        clean_invoice.total_amount = 1900.00
        result = engine.validate(clean_invoice, matching_po)
        assert result.status == "REJECTED"
        assert result.financial_impact >= 500.0

    def test_financial_impact_calculation(self, engine, clean_invoice, matching_po):
        """Verify precise financial impact calculation."""
        clean_invoice.base_freight = 1200.00  # $200 over
        result = engine.validate(clean_invoice, matching_po)
        assert result.financial_impact == pytest.approx(200.00, abs=0.01)
