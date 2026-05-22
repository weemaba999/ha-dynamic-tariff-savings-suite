# Dynamic Tariff Savings Suite

> **See in euros what your dynamic electricity contract is actually worth.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/weemaba999/ha-dynamic-tariff-savings-suite?include_prereleases)](https://github.com/weemaba999/ha-dynamic-tariff-savings-suite/releases)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/weemaba999)

Dynamic Tariff Savings Suite (DTS Suite) continuously compares your **dynamic** electricity contract (Nordpool, ENTSO-e, Tibber, EnergyZero, Engie Dynamic, Octopus Agile, …) against a **fixed reference contract** you define, so you can see — in real euros, on your Energy Dashboard — whether the dynamic contract is actually saving you money.

No more "I think it’s saving me something" — DTS Suite tells you exactly how much.

---

## Why this exists

Home Assistant’s Energy Dashboard tracks how much energy you consumed and what it cost on your current tariff. What it does **not** tell you:

- What you *would have paid* on a fixed contract for the same consumption pattern.
- Whether your timed loads (EV charging, dishwasher, heat pump) actually hit the cheap hours.
- Whether your battery’s arbitrage is paying off in monetary terms (*coming in v0.2*).

This is the gap [Discussion #1065](https://github.com/orgs/home-assistant/discussions/1065) and the long-running [Energy: Cost for the individual devices](https://community.home-assistant.io/t/energy-cost-for-the-individual-devices/334932) feature request describe. DTS Suite closes it.

---

## What you get in v0.1

A new **DTS Suite** device with these sensors:

| Sensor | Description |
| --- | --- |
| `sensor.dts_suite_actual_cost_today` | What you really paid (net of any export income) today. |
| `sensor.dts_suite_baseline_cost_today` | What the fixed reference contract would have cost. |
| `sensor.dts_suite_savings_today` | Difference. Positive = dynamic wins. |
| `sensor.dts_suite_savings_percentage_today` | Same, as a percentage of baseline. |
| `sensor.dts_suite_actual_cost_this_month` / `…_baseline_cost_this_month` / `…_savings_this_month` | Monthly versions, reset on the 1st. |
| `sensor.dts_suite_actual_cost_total` / `…_baseline_cost_total` / `…_savings_total` | Cumulative since install. |

All money sensors use `device_class: monetary`, so they integrate cleanly with the Energy Dashboard and statistics.

---

## How the math works

For every kWh increment imported during a moment with dynamic price `p_dyn` and reference price `p_base`:

```
actual_cost   += kwh * p_dyn
baseline_cost += kwh * p_base
savings        = baseline_cost - actual_cost
```

Exports are handled symmetrically. The full derivation is in [`engine/counterfactual.py`](custom_components/dynamic_tariff_savings/engine/counterfactual.py), which is pure Python and unit-tested in [`tests/test_counterfactual.py`](tests/test_counterfactual.py).

---

## Installation

### HACS (recommended)

1. In HACS → **Integrations** → top-right menu → **Custom repositories**.
2. Add `https://github.com/weemaba999/ha-dynamic-tariff-savings-suite` as an **Integration**.
3. Install **Dynamic Tariff Savings Suite**.
4. Restart Home Assistant.
5. **Settings → Devices & Services → Add Integration → Dynamic Tariff Savings Suite**.

### Manual

Copy `custom_components/dynamic_tariff_savings` to your HA config’s `custom_components/` directory and restart.

---

## Configuration

In the integration setup you pick:

- **Grid import (kWh totalizer)** — your `sensor.grid_import_energy` or equivalent. Must be a cumulative `device_class: energy` sensor.
- **Grid export (kWh totalizer)** — optional; needed if you have solar/battery export.
- **Dynamic import price (€/kWh)** — your Nordpool / ENTSO-e / Tibber / etc. current-price sensor.
- **Dynamic export price (€/kWh)** — optional; defaults to the import price (symmetric tariffs).
- **Baseline fixed import price** — what you’d pay on a vanilla fixed contract. Include taxes and distribution fees that wouldn’t change.
- **Baseline fixed export price** — what a fixed contract would pay you for injection. Often `0.00`.
- **Currency** — defaults to `EUR`.

Re-open the integration’s options anytime to update the baseline as fixed-contract market rates shift.

---

## Example Lovelace card

```yaml
type: custom:mushroom-template-card
primary: "DTS Suite"
secondary: "{{ states('sensor.dts_suite_savings_this_month') | round(2) }} € saved this month"
icon: mdi:transmission-tower
icon_color: |
  {% set s = states('sensor.dts_suite_savings_this_month') | float(0) %}
  {{ 'green' if s >= 0 else 'red' }}
```

A polished native card is on the v0.4 roadmap.

---

## Roadmap

- **v0.2** — Battery module: arbitrage tracking, solar self-consumption value, payback prognosis.
- **v0.3** — Per-device cost allocation with dynamic prices (closing the 6-year-old [#334932](https://community.home-assistant.io/t/energy-cost-for-the-individual-devices/334932) request).
- **v0.4** — Native dashboard cards: Savings Summary, Battery ROI, Tomorrow Plan.
- **v0.5** — Cheapest-hours advisor and load-shifting hints ("you could have saved €X by running the dishwasher at 14:00").
- **v1.0** — Regional presets (BE/NL/DE/Nordics/UK) with sane defaults per common dynamic-tariff provider.

---

## Support the project

If DTS Suite is saving you money, consider [buying me a coffee ☕](https://buymeacoffee.com/weemaba999) — it directly funds development of the battery module and the native dashboards.

---

## License

MIT — see [LICENSE](LICENSE).
