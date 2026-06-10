# BI & Operational Data Architecture

## Overview

This document describes a **Data Lakehouse** architecture that serves two goals:

1. **Business Intelligence** — batch-oriented analytics, dashboards, and reporting powered by a medallion storage model.
2. **Operational systems** — real-time data products (alerts, live feeds, ML inference) running off the same platform.

Both goals share a single ingestion spine (a message bus) and a single storage layer (the lakehouse), avoiding duplicate pipelines.

> **Note on tool choices** — The tools and providers listed throughout this document are illustrative and also my personal preferences. Actual choices depend on many factors, including:
> - **Team expertise** — familiarity with a tool reduces onboarding cost and operational risk
> - **Cloud provider** — existing AWS/GCP/Azure contracts favour managed services from that ecosystem
> - **Budget** — OSS tools lower licensing cost but shift burden to operational overhead; managed services invert that trade-off
> - **Scale** — data volume and query concurrency determine whether a lightweight tool suffices or a distributed engine is needed
> - **Latency requirements** — sub-second SLAs push toward stream-first designs; hourly batch windows allow simpler stacks
> - **Compliance and data residency** — regulatory constraints (GDPR, HIPAA, SOC 2) can disqualify certain vendors or cloud regions
> - **Existing infrastructure** — integrating with incumbent databases, identity providers, or BI tools often outweighs the ideal-stack choice
> - **Ecosystem integration** — how well tools interoperate (connectors, metadata standards, auth) affects total complexity

---

## Architecture Diagram

The diagram is presented below and it uses the following conventions:
- it is organized into six zones represented by colored rectangles
- each zone contains a set of services/tools represented by squared boxes
- each zone also contains a set of logical data stores represented by cylinders
- the arrows represent the flow of data, and the main ones are numbered for further description
- I've only presented tools I've used before or I know how they work
- the same architecture is rendered against two concrete stacks — an **OSS / self-hosted** stack and a **modern managed-SaaS** stack — so the design is decoupled from any single vendor
- diagram sources: [`architecture-oss.d2`](./architecture-oss.d2) and [`architecture-modern.d2`](./architecture-modern.d2). Render with `d2 --layout elk <file>.d2 <file>.png`

### Diagram — OSS / self-hosted stack
![architecture-oss.png](architecture-oss.png)

### Diagram — Modern managed-SaaS stack
![architecture-modern.png](architecture-modern.png)

### Layers

The stack is organised into six zones. The two tables below consolidate every tool and logical data store across all of them.

- **⚫ Operational Data Sources** — source systems: external APIs, internal apps, and the operational databases that are the system of record.
- **🟡 Ingestion Layer** — moves data from sources into the lakehouse, via batch pulls or real-time event streaming.
- **🔴 Transformation Layer** — hosts the medallion storage layers (Bronze/Silver/Gold), persisted as open-format **Apache Iceberg** tables on object storage (or Snowflake-managed tables), plus the tools that refine raw data into trusted, analytics-ready assets.
- **🔵 Systems Serving Layer** — materialises and exposes analytics-ready data through specialized engines and query federation.
- **🟣 User Serving Layer** — surfaces data to end users through interactive dashboards, scheduled reports, and cached query results.
- **🟢 Governance Layer** — cross-cutting layer ensuring data is discoverable, trustworthy, and access-controlled across every zone.

### Numbered data flows
1. Batch pull of operational databases into the ingestion layer
2. Applications emit events directly onto the message bus
3. Batch pull of external APIs into the ingestion layer
4. Batch-ingested records are published to the bus (single ingestion spine)
5. Stream ingestion consumes bus topics
6. Stream processing reads from and writes back to the bus (enrichment in motion)
7. Raw events land in the Bronze layer
8. Refined medallion data is served to the systems serving layer
9. Serving layer powers user-facing dashboards and reports
10. Specialized stores feed real-time data products back into operational apps


### Data Stores

Here's an explanation of what types of data sits on each logical data store represented on the diagrams as cylinders. The concrete storage engines that back each store are named in the diagrams.

| Zone | Logical Data Store | Description                                                                                                                                                                                 |
|---|---|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ⚫ Sources | Operational Databases | Transactional stores that are the system of record for business operations                                                           |
| 🟡 Ingestion | Topics | Message bus partitioned by domain/entity, carrying raw change events and application events in real time                                                                                    |
| 🔴 Transformation | Bronze Layer | Landing zone — raw, unmodified data ingested from sources, partitioned by ingestion date. Preserves full history for reprocessing                                                           |
| 🔴 Transformation | Silver Layer | Cleaned and conformed data — deduplication, schema normalization, type casting, and light business rules applied                                                                            |
| 🔴 Transformation | Gold Layer | Aggregated, business-ready datasets modelled around domains (facts & dimensions). Directly consumed by downstream serving and analytics                                                     |
| 🔴 Transformation | User Space | Sandbox area for analysts to create ad-hoc tables and exploratory datasets without polluting governed layers                                                                                |
| 🔵 Systems Serving | Aggregations & Views | Pre-computed rollups (hourly, daily, weekly) and reusable views stored for instant retrieval, avoiding repeated full-table scans                                                            |
| 🔵 Systems Serving | Metrics & KPIs | Operational and product metrics alongside named, versioned key business indicators with agreed calculation logic and ownership — consumed by dashboards, alerting systems, and ML pipelines |
| 🟣 User Serving | Cache Engines | Query results caches that accelerate repeated dashboard queries and reduce pressure on query engines                                                                                        |
