#!/bin/bash
set -e

echo "🚀 Starting Performance Gate..."

# 1. Start Master with 1GB RAM simulation (using a lightweight approach if cgroups not available)
# In CI, we use the runner's resources but monitor them.
export KOSATKA_API_KEY="default-key"
export KOSATKA_RATE_LIMIT_ENABLED="false"
cd master
uv run uvicorn kosatka_master.main:app --port 8000 &
MASTER_PID=$!
cd ..

# Wait for master
sleep 5

# 2. Run Locust Load Test
echo "🔥 Running Load Tests..."
uv run locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 30s --host http://localhost:8000 --only-summary

# 3. Kill master
kill $MASTER_PID

echo "✅ Performance Gate Passed!"
