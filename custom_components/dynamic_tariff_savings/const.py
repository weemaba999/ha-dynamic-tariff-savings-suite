"""Constants for Dynamic Tariff Savings."""
from __future__ import annotations

DOMAIN = "dynamic_tariff_savings"
PLATFORMS = ["sensor"]

# Config flow keys
CONF_GRID_IMPORT_SENSOR = "grid_import_sensor"
CONF_GRID_EXPORT_SENSOR = "grid_export_sensor"
CONF_DYNAMIC_PRICE_SENSOR = "dynamic_price_sensor"
CONF_DYNAMIC_EXPORT_PRICE_SENSOR = "dynamic_export_price_sensor"
CONF_BASELINE_IMPORT_PRICE = "baseline_import_price"
CONF_BASELINE_EXPORT_PRICE = "baseline_export_price"
CONF_CURRENCY = "currency"

# Defaults
DEFAULT_CURRENCY = "EUR"
DEFAULT_BASELINE_EXPORT_PRICE = 0.0

# Periods used internally
PERIOD_TODAY = "today"
PERIOD_MONTH = "month"
PERIOD_TOTAL = "total"
PERIODS = (PERIOD_TODAY, PERIOD_MONTH, PERIOD_TOTAL)

# Sensor metric keys (used to derive entity ids)
METRIC_ACTUAL_COST = "actual_cost"
METRIC_BASELINE_COST = "baseline_cost"
METRIC_SAVINGS = "savings"
METRIC_SAVINGS_PCT = "savings_pct"

# Coordinator update interval (state listeners do the real work; this is a safety tick)
UPDATE_INTERVAL_SECONDS = 60

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = "dynamic_tariff_savings_state"
