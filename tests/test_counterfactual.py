"""Unit tests for the counterfactual savings engine."""
from __future__ import annotations

import math

import pytest

from engine.counterfactual import CounterfactualEngine, PeriodAccumulator


def test_empty_engine_has_zero_savings():
    e = CounterfactualEngine()
    assert e.today.savings == 0.0
    assert e.month.savings == 0.0
    assert e.total.savings == 0.0
    assert e.today.savings_pct is None


def test_import_at_dynamic_below_baseline_yields_positive_savings():
    e = CounterfactualEngine()
    # Imported 2 kWh at 0.15 €/kWh dynamic vs 0.30 €/kWh baseline
    e.record_import(2.0, dynamic_price=0.15, baseline_price=0.30)
    assert e.today.actual_import_cost == pytest.approx(0.30)
    assert e.today.baseline_import_cost == pytest.approx(0.60)
    assert e.today.savings == pytest.approx(0.30)
    assert e.today.savings_pct == pytest.approx(50.0)


def test_import_at_dynamic_above_baseline_yields_negative_savings():
    e = CounterfactualEngine()
    e.record_import(1.0, dynamic_price=0.50, baseline_price=0.30)
    # Dynamic is more expensive here, baseline net cost is 0.30
    # Savings = 0.30 - 0.50 = -0.20
    assert e.today.savings == pytest.approx(-0.20)


def test_export_increases_savings_when_dynamic_pays_more():
    e = CounterfactualEngine()
    # Exporting 5 kWh, baseline pays 0.05/kWh, dynamic pays 0.20/kWh
    e.record_export(5.0, dynamic_export_price=0.20, baseline_export_price=0.05)
    # baseline_net_cost = -0.25, actual_net_cost = -1.00
    # savings = -0.25 - (-1.00) = 0.75
    assert e.today.savings == pytest.approx(0.75)


def test_combined_import_and_export_balances():
    e = CounterfactualEngine()
    # Import 10 kWh @ peak (0.40 dynamic, 0.30 baseline) → -1.00 savings
    e.record_import(10.0, 0.40, 0.30)
    # Export 5 kWh @ noon (0.10 dynamic, 0.05 baseline) → +0.25 savings
    e.record_export(5.0, 0.10, 0.05)
    assert e.today.savings == pytest.approx(-1.00 + 0.25)


def test_negative_or_zero_kwh_delta_is_ignored():
    e = CounterfactualEngine()
    e.record_import(-1.0, 0.20, 0.30)
    e.record_import(0.0, 0.20, 0.30)
    e.record_export(-2.0, 0.10, 0.05)
    assert e.today.imported_kwh == 0
    assert e.today.exported_kwh == 0
    assert e.today.savings == 0.0


def test_missing_prices_are_ignored_not_zero():
    """A None price must not be treated as 0 €/kWh."""
    e = CounterfactualEngine()
    e.record_import(1.0, None, 0.30)
    e.record_import(1.0, 0.20, None)
    assert e.today.imported_kwh == 0
    assert e.today.actual_import_cost == 0
    assert e.today.baseline_import_cost == 0


def test_daily_reset_clears_today_but_keeps_month_and_total():
    e = CounterfactualEngine()
    e.record_import(2.0, 0.15, 0.30)  # +0.30 savings everywhere

    e.reset_today()
    assert e.today.savings == 0.0
    assert e.month.savings == pytest.approx(0.30)
    assert e.total.savings == pytest.approx(0.30)


def test_monthly_reset_clears_month_but_keeps_total():
    e = CounterfactualEngine()
    e.record_import(2.0, 0.15, 0.30)
    e.reset_today()
    e.reset_month()
    assert e.today.savings == 0.0
    assert e.month.savings == 0.0
    assert e.total.savings == pytest.approx(0.30)


def test_serialization_roundtrip():
    e1 = CounterfactualEngine()
    e1.record_import(7.5, 0.18, 0.32)
    e1.record_export(3.0, 0.09, 0.05)
    data = e1.as_dict()

    e2 = CounterfactualEngine.from_dict(data)
    assert e2.today.savings == pytest.approx(e1.today.savings)
    assert e2.month.savings == pytest.approx(e1.month.savings)
    assert e2.total.savings == pytest.approx(e1.total.savings)
    assert e2.today.imported_kwh == pytest.approx(7.5)


def test_from_dict_handles_none_and_empty():
    assert isinstance(CounterfactualEngine.from_dict(None), CounterfactualEngine)
    assert isinstance(CounterfactualEngine.from_dict({}), CounterfactualEngine)


def test_savings_pct_handles_near_zero_baseline():
    e = CounterfactualEngine()
    # Tiny import that produces a near-zero baseline cost
    e.record_import(1e-12, 0.20, 0.30)
    # Baseline net cost is ~3e-13, below the 1e-9 cutoff → percent must be None
    assert e.today.savings_pct is None


def test_realistic_day_scenario():
    """A plausible day: cheap night imports, solar export at noon, peak imports."""
    e = CounterfactualEngine()
    # Night: 3 kWh import at €0.08 dynamic vs €0.30 baseline
    e.record_import(3.0, 0.08, 0.30)
    # Noon export: 8 kWh at €0.05 dynamic vs €0.05 baseline (no diff)
    e.record_export(8.0, 0.05, 0.05)
    # Evening peak: 4 kWh import at €0.45 dynamic vs €0.30 baseline
    e.record_import(4.0, 0.45, 0.30)

    # Hand calc:
    # actual_import = 3*0.08 + 4*0.45 = 0.24 + 1.80 = 2.04
    # baseline_import = 3*0.30 + 4*0.30 = 2.10
    # export income equal → no contribution
    # savings = 2.10 - 2.04 = 0.06
    assert e.today.savings == pytest.approx(0.06)
    assert e.today.imported_kwh == pytest.approx(7.0)
    assert e.today.exported_kwh == pytest.approx(8.0)
