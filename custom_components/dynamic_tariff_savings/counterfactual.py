"""Counterfactual savings engine.

This module is intentionally pure-Python with no Home Assistant imports
so it can be unit-tested in isolation. The HA coordinator wraps it and
feeds it events.

Model
-----
For every increment of imported kWh during a moment with dynamic price
``p_dyn``, the user actually pays ``kwh * p_dyn``. The counterfactual is
what they *would have paid* on a fixed reference tariff ``p_base``:
``kwh * p_base``. The difference is the (signed) savings for that
increment.

Exports are handled symmetrically. The user *receives* ``kwh * p_dyn_export``
in reality and ``kwh * p_base_export`` under the baseline.

Total savings = (baseline_import_cost - actual_import_cost)
              + (actual_export_income - baseline_export_income)

A positive number means the dynamic contract is cheaper than the baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PeriodAccumulator:
    """Running totals for one rollup period (today / month / total)."""

    actual_import_cost: float = 0.0
    baseline_import_cost: float = 0.0
    actual_export_income: float = 0.0
    baseline_export_income: float = 0.0
    imported_kwh: float = 0.0
    exported_kwh: float = 0.0

    @property
    def actual_net_cost(self) -> float:
        """Net cost under the dynamic contract (positive = paid out)."""
        return self.actual_import_cost - self.actual_export_income

    @property
    def baseline_net_cost(self) -> float:
        """Net cost under the fixed baseline contract."""
        return self.baseline_import_cost - self.baseline_export_income

    @property
    def savings(self) -> float:
        """Savings of dynamic vs baseline. Positive = dynamic wins."""
        return self.baseline_net_cost - self.actual_net_cost

    @property
    def savings_pct(self) -> float | None:
        """Savings as percentage of baseline cost. None if baseline is ~0."""
        if abs(self.baseline_net_cost) < 1e-9:
            return None
        return (self.savings / self.baseline_net_cost) * 100.0

    def reset(self) -> None:
        """Zero all counters."""
        self.actual_import_cost = 0.0
        self.baseline_import_cost = 0.0
        self.actual_export_income = 0.0
        self.baseline_export_income = 0.0
        self.imported_kwh = 0.0
        self.exported_kwh = 0.0


@dataclass
class CounterfactualEngine:
    """Holds accumulators for today / month / total."""

    today: PeriodAccumulator = field(default_factory=PeriodAccumulator)
    month: PeriodAccumulator = field(default_factory=PeriodAccumulator)
    total: PeriodAccumulator = field(default_factory=PeriodAccumulator)

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_import(
        self,
        kwh_delta: float,
        dynamic_price: float,
        baseline_price: float,
    ) -> None:
        """Record an imported energy increment.

        ``kwh_delta`` must be non-negative. Negative deltas indicate a meter
        reset or rollover and are ignored.
        """
        if kwh_delta is None or kwh_delta <= 0:
            return
        if dynamic_price is None or baseline_price is None:
            return

        actual = kwh_delta * dynamic_price
        baseline = kwh_delta * baseline_price

        for acc in (self.today, self.month, self.total):
            acc.imported_kwh += kwh_delta
            acc.actual_import_cost += actual
            acc.baseline_import_cost += baseline

    def record_export(
        self,
        kwh_delta: float,
        dynamic_export_price: float,
        baseline_export_price: float,
    ) -> None:
        """Record an exported energy increment."""
        if kwh_delta is None or kwh_delta <= 0:
            return
        if dynamic_export_price is None or baseline_export_price is None:
            return

        actual = kwh_delta * dynamic_export_price
        baseline = kwh_delta * baseline_export_price

        for acc in (self.today, self.month, self.total):
            acc.exported_kwh += kwh_delta
            acc.actual_export_income += actual
            acc.baseline_export_income += baseline

    # ------------------------------------------------------------------ #
    # Period rollovers
    # ------------------------------------------------------------------ #

    def reset_today(self) -> None:
        self.today.reset()

    def reset_month(self) -> None:
        self.month.reset()

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #

    def as_dict(self) -> dict[str, Any]:
        return {
            "today": asdict(self.today),
            "month": asdict(self.month),
            "total": asdict(self.total),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CounterfactualEngine":
        if not data:
            return cls()
        return cls(
            today=PeriodAccumulator(**data.get("today", {})),
            month=PeriodAccumulator(**data.get("month", {})),
            total=PeriodAccumulator(**data.get("total", {})),
        )
