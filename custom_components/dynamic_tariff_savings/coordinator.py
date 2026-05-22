"""Dynamic Tariff Savings data coordinator.

Listens to state changes on the configured grid import/export kWh sensors,
samples the dynamic price sensor at the moment the delta is observed, and
feeds the counterfactual engine.

Sensor entities subscribe to this coordinator and read the accumulators.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BASELINE_EXPORT_PRICE,
    CONF_BASELINE_IMPORT_PRICE,
    CONF_DYNAMIC_EXPORT_PRICE_SENSOR,
    CONF_DYNAMIC_PRICE_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_GRID_IMPORT_SENSOR,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL_SECONDS,
)
from .counterfactual import CounterfactualEngine

_LOGGER = logging.getLogger(__name__)


def _safe_float(state: State | None) -> float | None:
    """Best-effort float conversion of a state value."""
    if state is None:
        return None
    val = state.state
    if val in (None, "unknown", "unavailable", ""):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class DynamicTariffSavingsCoordinator(DataUpdateCoordinator):
    """Coordinates state listeners and the savings engine."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry

        cfg = {**entry.data, **entry.options}
        self.grid_import_sensor: str = cfg[CONF_GRID_IMPORT_SENSOR]
        self.grid_export_sensor: str | None = cfg.get(CONF_GRID_EXPORT_SENSOR)
        self.dynamic_price_sensor: str = cfg[CONF_DYNAMIC_PRICE_SENSOR]
        self.dynamic_export_price_sensor: str | None = cfg.get(
            CONF_DYNAMIC_EXPORT_PRICE_SENSOR
        )
        self.baseline_import_price: float = float(cfg[CONF_BASELINE_IMPORT_PRICE])
        self.baseline_export_price: float = float(
            cfg.get(CONF_BASELINE_EXPORT_PRICE, 0.0)
        )

        self.engine = CounterfactualEngine()

        # Last seen kWh values for delta calculation
        self._last_import_kwh: float | None = None
        self._last_export_kwh: float | None = None
        # Track current month for rollover detection
        self._current_month: int | None = None

        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}"
        )
        self._unsub_callbacks: list = []

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def async_initialize(self) -> None:
        """Load persisted state, set up listeners and time triggers."""
        stored: dict[str, Any] | None = await self._store.async_load()
        if stored:
            self.engine = CounterfactualEngine.from_dict(stored.get("engine"))
            self._last_import_kwh = stored.get("last_import_kwh")
            self._last_export_kwh = stored.get("last_export_kwh")
            self._current_month = stored.get("current_month")

        if self._current_month is None:
            self._current_month = dt_util.now().month

        # State change listeners
        sensors = [self.grid_import_sensor]
        if self.grid_export_sensor:
            sensors.append(self.grid_export_sensor)
        self._unsub_callbacks.append(
            async_track_state_change_event(
                self.hass, sensors, self._async_meter_changed
            )
        )

        # Daily reset at midnight
        self._unsub_callbacks.append(
            async_track_time_change(
                self.hass, self._async_daily_tick, hour=0, minute=0, second=5
            )
        )

        # Persist on HA stop
        self._unsub_callbacks.append(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self._async_on_stop
            )
        )

        await self.async_config_entry_first_refresh()

    async def async_shutdown(self) -> None:
        for unsub in self._unsub_callbacks:
            try:
                unsub()
            except TypeError:
                # async_listen_once returns a callable too, but be defensive
                pass
        await self._async_persist()

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    @callback
    def _async_meter_changed(self, event: Event) -> None:
        entity_id: str = event.data.get("entity_id")
        new_state: State | None = event.data.get("new_state")
        new_val = _safe_float(new_state)
        if new_val is None:
            return

        if entity_id == self.grid_import_sensor:
            self._handle_import(new_val)
        elif entity_id == self.grid_export_sensor:
            self._handle_export(new_val)

        # Tell sensors to refresh
        self.async_set_updated_data(self._snapshot())

    def _handle_import(self, new_kwh: float) -> None:
        if self._last_import_kwh is None:
            self._last_import_kwh = new_kwh
            return
        delta = new_kwh - self._last_import_kwh
        if delta < 0:
            # Meter reset; just rebase
            _LOGGER.debug("Import meter reset detected, rebasing")
            self._last_import_kwh = new_kwh
            return
        if delta == 0:
            return

        dyn_price = _safe_float(self.hass.states.get(self.dynamic_price_sensor))
        if dyn_price is None:
            _LOGGER.debug("Dynamic price unavailable, skipping import delta")
            self._last_import_kwh = new_kwh
            return

        self.engine.record_import(delta, dyn_price, self.baseline_import_price)
        self._last_import_kwh = new_kwh

    def _handle_export(self, new_kwh: float) -> None:
        if self._last_export_kwh is None:
            self._last_export_kwh = new_kwh
            return
        delta = new_kwh - self._last_export_kwh
        if delta < 0:
            _LOGGER.debug("Export meter reset detected, rebasing")
            self._last_export_kwh = new_kwh
            return
        if delta == 0:
            return

        # Default to import price if no separate export price sensor (common case
        # for symmetric dynamic tariffs).
        if self.dynamic_export_price_sensor:
            dyn_export_price = _safe_float(
                self.hass.states.get(self.dynamic_export_price_sensor)
            )
        else:
            dyn_export_price = _safe_float(
                self.hass.states.get(self.dynamic_price_sensor)
            )
        if dyn_export_price is None:
            self._last_export_kwh = new_kwh
            return

        self.engine.record_export(
            delta, dyn_export_price, self.baseline_export_price
        )
        self._last_export_kwh = new_kwh

    @callback
    def _async_daily_tick(self, now: datetime) -> None:
        """Runs at 00:00:05 local time."""
        self.engine.reset_today()
        if now.month != self._current_month:
            self.engine.reset_month()
            self._current_month = now.month
        self.async_set_updated_data(self._snapshot())
        self.hass.async_create_task(self._async_persist())

    async def _async_on_stop(self, _event: Event) -> None:
        await self._async_persist()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _async_update_data(self) -> dict[str, Any]:
        """Periodic safety tick: persist and refresh snapshot."""
        await self._async_persist()
        return self._snapshot()

    def _snapshot(self) -> dict[str, Any]:
        return self.engine.as_dict()

    async def _async_persist(self) -> None:
        await self._store.async_save(
            {
                "engine": self.engine.as_dict(),
                "last_import_kwh": self._last_import_kwh,
                "last_export_kwh": self._last_export_kwh,
                "current_month": self._current_month,
            }
        )
