"""Dynamic Tariff Savings sensors.

Exposes the savings-vs-baseline numbers for today / month / total, plus
the absolute actual and baseline costs so users can build their own cards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CURRENCY, DEFAULT_CURRENCY, DOMAIN
from .coordinator import DynamicTariffSavingsCoordinator
from .counterfactual import CounterfactualEngine, PeriodAccumulator


@dataclass(frozen=True)
class DynamicTariffSavingsSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    period: str = "today"
    value_fn: Callable[[PeriodAccumulator], float | None] = lambda acc: None


def _money(name: str, key: str, period: str, fn) -> DynamicTariffSavingsSensorDescription:
    return DynamicTariffSavingsSensorDescription(
        key=key,
        name=name,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        period=period,
        value_fn=fn,
    )


SENSOR_DESCRIPTIONS: tuple[DynamicTariffSavingsSensorDescription, ...] = (
    # Today
    _money("Actual cost today", "actual_cost_today", "today",
           lambda a: a.actual_net_cost),
    _money("Baseline cost today", "baseline_cost_today", "today",
           lambda a: a.baseline_net_cost),
    _money("Savings today", "savings_today", "today",
           lambda a: a.savings),
    # Month
    _money("Actual cost this month", "actual_cost_month", "month",
           lambda a: a.actual_net_cost),
    _money("Baseline cost this month", "baseline_cost_month", "month",
           lambda a: a.baseline_net_cost),
    _money("Savings this month", "savings_month", "month",
           lambda a: a.savings),
    # Total
    _money("Actual cost total", "actual_cost_total", "total",
           lambda a: a.actual_net_cost),
    _money("Baseline cost total", "baseline_cost_total", "total",
           lambda a: a.baseline_net_cost),
    _money("Savings total", "savings_total", "total",
           lambda a: a.savings),
    # Percentage (today)
    DynamicTariffSavingsSensorDescription(
        key="savings_pct_today",
        name="Savings percentage today",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        period="today",
        value_fn=lambda a: a.savings_pct,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DynamicTariffSavingsCoordinator = hass.data[DOMAIN][entry.entry_id]
    currency = entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
    async_add_entities(
        DynamicTariffSavingsSensor(coordinator, entry, desc, currency)
        for desc in SENSOR_DESCRIPTIONS
    )


class DynamicTariffSavingsSensor(CoordinatorEntity[DynamicTariffSavingsCoordinator], SensorEntity):
    """A single Dynamic Tariff Savings sensor."""

    _attr_has_entity_name = True
    entity_description: DynamicTariffSavingsSensorDescription

    def __init__(
        self,
        coordinator: DynamicTariffSavingsCoordinator,
        entry: ConfigEntry,
        description: DynamicTariffSavingsSensorDescription,
        currency: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        if description.device_class == SensorDeviceClass.MONETARY:
            self._attr_native_unit_of_measurement = currency
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="DTS Suite",
            manufacturer="weemaba999",
            model="Counterfactual Savings Engine",
            sw_version="0.1.0",
        )

    @callback
    def _period_accumulator(self) -> PeriodAccumulator:
        engine: CounterfactualEngine = self.coordinator.engine
        return {
            "today": engine.today,
            "month": engine.month,
            "total": engine.total,
        }[self.entity_description.period]

    @property
    def native_value(self) -> float | None:
        acc = self._period_accumulator()
        val = self.entity_description.value_fn(acc)
        if val is None:
            return None
        return round(val, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        acc = self._period_accumulator()
        return {
            "imported_kwh": round(acc.imported_kwh, 3),
            "exported_kwh": round(acc.exported_kwh, 3),
        }
