# Luxor Data Engineer Challenge — André Casimiro

My submission for the [Luxor Data Engineer Challenge](luxor-challenge.md), in two parts:

| Part | What | Details |
|------|------|---------|
| **1 · BI Architecture** | A data architecture for Business Intelligence, extended to support real-time, operational data products. Diagram + rationale for each stage (sources, ingestion/transformation, storage, processing, output), with notes on testing and security. | [`1-bi-architecture/`](1-bi-architecture/README.md) |
| **2 · Coding** | A real-time crypto feed that polls CoinGecko (BTC, ETH, ZEC) once per second and, in one push-based [Bytewax](https://bytewax.io/) dataflow, **persists** ticks to TimescaleDB and **emits an alert stream** on >2% moves vs. the trailing 5-min average. Includes schema rationale, scalability strategy, and tests. | [`2-coding/`](2-coding/README.md) |

See each part's README for the design, trade-offs, and run instructions.
