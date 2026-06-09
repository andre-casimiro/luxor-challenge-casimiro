# Luxor Data Engineer Coding Challenge

Welcome to Luxor's Data Engineer Coding Challenge.

Elegant, well-written, and commented code is preferred over over-engineered models. You should be able to explain all of the steps and decisions you've made.

For the coding part of this challenge, you can use any programming language.

---

## Design & Architecture

Expect a diagram with the stages in a typical data architecture that shows the tools used in each step and how the data flows from one system to another.

### Tasks

1. Design an architecture for Business Intelligence.
2. Extend the previous design to incorporate operational systems, meaning real-time data-powered products.

Detail the tools that you would use for each stage of the stack:

- Sources
- Ingestion and transformation
- Storage
- Processing
- Output and analysis

Additional points if you describe how and where the data could be tested and secured.

Only use technologies you have either used in the past or understand how they work. A comprehensive design that you're able to explain is preferred over an over-engineered architecture.

---

## Coding

Write a tool that retrieves data once per second from [CoinGecko's API](https://www.coingecko.com/api/documentations/v3) for three different tickers:

- BTC
- ETH
- ZEC

The tool should perform two main operations.

### 1. Store the data feed in PostgresDB

Based on the API response structure, create the database schema.

Recommended tables:

- Maestro of digital assets
- Historical OHLCV data

### 2. Create an alert system

Create an alert system that outputs an alert stream when an event occurs.

The alert stream can be logged to one of the following, or a similar output:

- `.txt` file
- Message queue
- Pub/Sub

Example alert condition:

> Trigger an alert when price or volume changes by more than 2% from the previous 5-minute average.

You should use a push-based approach, as opposed to asynchronously retrieving data from the database.

---

## Extension Question

Describe how this app can be extended to different metrics, assets, or purposes.

---

## Guidelines

- Be biased for production-ready over features, and quality over quantity.
- Document trade-offs, rationale behind your implementation, or things you would do differently with more time and resources.
- Bonus points for unit tests.
- Provide documentation on how to run the app.

---

## Scalability

Each new asset adds to the app **2,592,000 records per month**.

The table containing the historical data of digital assets will get large fast and eventually slow down database retrieval.

Address the following questions:

1. How would you address scalability without losing information?
2. How can you optimize for retrieval speed?

---

## Submission

Submit the assignment files through the provided submission form.

