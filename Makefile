.PHONY: help install dev-install test lint format run docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  install      Install production dependencies"
	@echo "  dev-install  Install development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  run          Run the application"
	@echo "  docker-up    Start services with docker-compose"
	@echo "  docker-down  Stop docker services"
	@echo "  clean        Clean up generated files"

install:
	pip install -r requirements.txt

dev-install: install
	pip install -e .

test:
	pytest

lint:
	ruff check src tests
	mypy src

format:
	black src tests
	ruff check --fix src tests

run:
	python -m src.main

run-worker:
	python -m src.run_worker

run-all:
	python -m src.main & python -m src.run_worker

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache
	rm -rf chroma_db/ logs/ tmp/