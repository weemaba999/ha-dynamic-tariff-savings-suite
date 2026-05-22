"""Config flow for Dynamic Tariff Savings."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BASELINE_EXPORT_PRICE,
    CONF_BASELINE_IMPORT_PRICE,
    CONF_CURRENCY,
    CONF_DYNAMIC_EXPORT_PRICE_SENSOR,
    CONF_DYNAMIC_PRICE_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_GRID_IMPORT_SENSOR,
    DEFAULT_BASELINE_EXPORT_PRICE,
    DEFAULT_CURRENCY,
    DOMAIN,
)

ENERGY_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="energy")
)

NUMERIC_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

PRICE_NUMBER_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.0,
        max=2.0,
        step=0.0001,
        mode=selector.NumberSelectorMode.BOX,
    )
)


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_GRID_IMPORT_SENSOR,
                default=defaults.get(CONF_GRID_IMPORT_SENSOR),
            ): ENERGY_SENSOR_SELECTOR,
            vol.Optional(
                CONF_GRID_EXPORT_SENSOR,
                default=defaults.get(CONF_GRID_EXPORT_SENSOR),
            ): ENERGY_SENSOR_SELECTOR,
            vol.Required(
                CONF_DYNAMIC_PRICE_SENSOR,
                default=defaults.get(CONF_DYNAMIC_PRICE_SENSOR),
            ): NUMERIC_SENSOR_SELECTOR,
            vol.Optional(
                CONF_DYNAMIC_EXPORT_PRICE_SENSOR,
                default=defaults.get(CONF_DYNAMIC_EXPORT_PRICE_SENSOR),
            ): NUMERIC_SENSOR_SELECTOR,
            vol.Required(
                CONF_BASELINE_IMPORT_PRICE,
                default=defaults.get(CONF_BASELINE_IMPORT_PRICE, 0.30),
            ): PRICE_NUMBER_SELECTOR,
            vol.Required(
                CONF_BASELINE_EXPORT_PRICE,
                default=defaults.get(
                    CONF_BASELINE_EXPORT_PRICE, DEFAULT_BASELINE_EXPORT_PRICE
                ),
            ): PRICE_NUMBER_SELECTOR,
            vol.Required(
                CONF_CURRENCY,
                default=defaults.get(CONF_CURRENCY, DEFAULT_CURRENCY),
            ): selector.TextSelector(),
        }
    )


class DynamicTariffSavingsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # One Dynamic Tariff Savings instance per HA install is plenty for v0.1.
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Strip empty optional fields
            cleaned = {k: v for k, v in user_input.items() if v not in ("", None)}
            return self.async_create_entry(title="DTS Suite", data=cleaned)

        return self.async_show_form(
            step_id="user", data_schema=_build_schema(), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return DynamicTariffSavingsOptionsFlow(config_entry)


class DynamicTariffSavingsOptionsFlow(OptionsFlow):
    """Allow editing baseline prices and sensor wiring."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {k: v for k, v in user_input.items() if v not in ("", None)}
            return self.async_create_entry(title="", data=cleaned)

        merged = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_build_schema(merged)
        )
