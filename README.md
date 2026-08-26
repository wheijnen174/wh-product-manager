# WH Product Manager

> **Work in progress:** this project is unfinished and not production-ready. APIs, integrations, and packaging are still evolving.

WH Product Manager is a FastAPI service for managing supplier product data and synchronising it with Shopify through the GraphQL API. It focuses on integrations, data processing, and backend architecture.

## Highlights

- FastAPI API with bearer-token authentication and OpenAPI documentation
- Async SQLAlchemy with MySQL for products, properties, collections, and Shopify state
- Supplier abstractions for importing and normalising XML product data
- Shopify product upsert and batch-processing workflows
- Service container, repository layer, Pydantic schemas, and structured logging
- Experimental Windows packaging with Nuitka

## Structure

```text
src/wh_product_manager/
├── api/         FastAPI routes and authentication
├── db/          SQLAlchemy models and repositories
├── products/    Product workflows and schemas
├── shopify/     Shopify GraphQL integration
├── suppliers/   Supplier providers and normalisation
└── utils/       Shared data and validation helpers
```

## Local development

The project targets Python 3.12.12 and uses `uv` for dependency management:

```powershell
uv sync
uv run python -m wh_product_manager.main
```

The application expects database and API-key settings in a local `.env` file. See [`settings.py`](src/wh_product_manager/settings.py) for the available configuration.

## Status

This repository is not intended to be a turnkey reproduction guide. Some Shopify routes, integrations, tests, and packaging scripts remain incomplete or experimental.
