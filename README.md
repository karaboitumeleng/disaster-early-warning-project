# SA Natural Disaster Early Warning System (prototype)

## Run locally
    make setup            # then edit .env: set JWT_SECRET (openssl rand -hex 32) and DEMO_PASSWORD
    make run              # API on :8000  (docs at /docs)
    make frontend         # dashboard on :5173
    make demo             # ingests a flood reading and prints measured alert latency
    make test

Or: `docker compose up --build`.

## Demo users
`admin`, `analyst`, `viewer`, all with the password you set as `DEMO_PASSWORD`.
Only admin/analyst can ingest data and acknowledge or resolve alerts.