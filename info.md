# Dynamic Tariff Savings Suite

See in euros what your dynamic electricity contract is actually worth.

DTS Suite continuously compares your dynamic tariff (Nordpool, ENTSO-e, Tibber, EnergyZero, Octopus Agile, …) against a fixed reference contract you define, and exposes the **savings in real money** as sensors on the Energy Dashboard.

## v0.1 features

- Counterfactual savings (today / this month / total).
- Works with any energy and price sensor.
- Survives HA restarts (state persisted).
- Pure-Python core engine with full unit tests.

Entity IDs use the short `sensor.dts_suite_*` prefix.

## Roadmap

- **v0.2** — Battery arbitrage + payback prognosis.
- **v0.3** — Per-device dynamic-price cost allocation.
- **v0.4** — Native dashboard cards.

[Full README, screenshots, and configuration guide on GitHub →](https://github.com/weemaba999/ha-dynamic-tariff-savings-suite)
