param (
    [Parameter(Mandatory=\$true, Position=0)]
    [ValidateSet("setup", "lint", "test", "run", "frontend", "demo")]
    [string]\$Task
)

# Helper function to run backend commands in the virtual environment
function Invoke-BackendCommand {
    param ([string]\$Command)
    cd backend
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        & .\.venv\Scripts\Activate.ps1
    } else {
        Write-Warning "Virtual environment not found. Run '.\run.ps1 setup' first."
    }
    Invoke-Expression \$Command
    cd ..
}

switch (\$Task) {
    "setup" {
        # Backend setup
        cd backend
        python -m venv .venv
        & .\.venv\Scripts\Activate.ps1
        pip install -r requirements-dev.txt
        cd ..

        # Frontend setup
        if (Test-Path .\frontend) {
            cd frontend; npm install; cd ..
        }

        # Env file safety check
        if (-not (Test-Path .\.env)) {
            Write-Host "⚠️ .env file missing! Creating one..." -ForegroundColor Yellow
            New-Item .env -ItemType File
            Set-Content .env "APP_ENV=dev`nDATABASE_URL=sqlite+aiosqlite:///./ewsa.db`nJWT_SECRET=`nJWT_EXPIRE_MINUTES=60`nCORS_ORIGINS=http://localhost:5173`nALERT_THRESHOLD=0.6`nMAX_PAYLOAD_BYTES=1000000`nDEMO_PASSWORD=`nVITE_API_URL=http://localhost:8000"
            Write-Host "✅ Created empty .env. Please open it and set your JWT_SECRET and DEMO_PASSWORD." -ForegroundColor Green
        }
    }

    "lint" {
        Invoke-BackendCommand "ruff check . && black --check . && mypy app"
    }

    "test" {
        Invoke-BackendCommand "pytest --cov=app --cov-report=term-missing"
    }

    "run" {
        Invoke-BackendCommand "uvicorn app.main:create_app --factory --reload --port 8000"
    }

    "frontend" {
        cd frontend; npm run dev; cd ..
    }

    "demo" {
        Invoke-BackendCommand "python ../scripts/measure_latency.py"
    }
}
