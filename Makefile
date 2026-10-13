.PHONY: setup lint test run frontend demo

setup:
	cd backend && python -m venv .venv && . .venv/bin/activate && \
	  pip install -r requirements-dev.txt
	cd frontend && npm install
	@test -f .env || (cp .env.example .env && echo "Created .env - set JWT_SECRET and DEMO_PASSWORD")

lint:
	cd backend && . .venv/bin/activate && ruff check . && black --check . && mypy app

test:
	cd backend && . .venv/bin/activate && pytest --cov=app --cov-report=term-missing

run:
	cd backend && . .venv/bin/activate && uvicorn app.main:create_app --factory --reload --port 8000

frontend:
	cd frontend && npm run dev

demo:
	cd backend && . .venv/bin/activate && python ../scripts/measure_latency.py