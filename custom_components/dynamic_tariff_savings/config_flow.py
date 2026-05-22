"""Config flow for Dynamic Tariff Savings Suite — minimal, defensive version."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
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

_LOGGER = logging.getLogger(__name__)


class DynamicTariffSavingsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            cleaned = {k: v for k, v in user_input.items() if v not in ("", None)}
            return self.async_create_entry(title="DTS Suite", data=cleaned)

        sensor_picker = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_GRID_IMPORT_SENSOR): sensor_picker,
                vol.Optional(CONF_GRID_EXPORT_SENSOR): sensor_picker,
                vol.Required(CONF_DYNAMIC_PRICE_SENSOR): sensor_picker,
                vol.Optional(CONF_DYNAMIC_EXPORT_PRICE_SENSOR): sensor_picker,
                vol.Required(
                    CONF_BASELINE_IMPORT_PRICE, default=0.30
                ): vol.Coerce(float),
                vol.Required(
                    CONF_BASELINE_EXPORT_PRICE, default=DEFAULT_BASELINE_EXPORT_PRICE
                ): vol.Coerce(float),
                vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
