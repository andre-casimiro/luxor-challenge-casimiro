.PHONY: up down seed run test lint logs psql clean

up:            ## Start TimescaleDB
	docker-compose up -d

down:          ## Stop TimescaleDB (keeps data volume)
	docker-compose down

seed:          ## Apply schema + seed the assets maestro table
	uv run python -m crypto_feed.bootstrap

run:           ## Run the feed: poll -> Postgres + alerts (Ctrl-C to stop)
	uv run python -m bytewax.run crypto_feed.dataflow:flow

test:          ## Unit tests
	uv run pytest

lint:          ## Ruff lint
	uv run ruff check

psql:          ## Open a psql shell in the container
	docker exec -it crypto-feed-db psql -U crypto -d crypto

logs:          ## Tail the alert stream
	tail -f alerts.txt

clean:         ## Stop and remove the data volume
	docker-compose down -v
