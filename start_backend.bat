@echo off
echo ============================================================
echo E-COMMERCE BACKEND STARTUP
echo ============================================================
echo.

echo [1/4] Checking database schema...
python check_schema.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Schema mismatch detected!
    echo.
    echo Applying migration...
    python -m alembic upgrade head
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ❌ Migration failed! Try manual fix:
        echo    python fix_schema.py --apply
        pause
        exit /b 1
    )
    echo.
    echo ✅ Migration applied successfully!
)

echo.
echo [2/4] Running health check...
python test_backend.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Health check failed! Fix errors before starting.
    pause
    exit /b 1
)

echo.
echo [3/4] Backend is healthy!
echo.
echo [4/4] Starting FastAPI server...
echo.
echo ============================================================
echo Backend will be available at:
echo   - API: http://localhost:8000
echo   - Swagger UI: http://localhost:8000/docs
echo   - ReDoc: http://localhost:8000/redoc
echo ============================================================
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
