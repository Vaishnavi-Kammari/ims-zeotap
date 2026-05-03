import requests
import time
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='localhost')
parser.add_argument('--port', default=8000, type=int)
args = parser.parse_args()

BASE_URL = f"http://{args.host}:{args.port}/api/v1"


def send_batch(signals, label):
    chunks = [signals[i:i+100] for i in range(0, len(signals), 100)]
    total_accepted = 0
    for chunk in chunks:
        try:
            res = requests.post(f"{BASE_URL}/signals/batch", json=chunk, timeout=10)
            data = res.json()
            total_accepted += data.get("accepted", 0)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(0.1)
    print(f"  OK {label}: {total_accepted}/{len(signals)} signals accepted")
    return total_accepted


def make_signals(component_id, component_type, error_code, message, count, latency_ms=None):
    return [
        {
            "component_id": component_id,
            "component_type": component_type,
            "error_code": error_code,
            "message": message,
            "latency_ms": latency_ms,
            "metadata": {"simulation": True, "index": i},
        }
        for i in range(count)
    ]


print("\nIMS Failure Simulation Starting...")
print(f"Target: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)

print("\n[Phase 1] RDBMS outage (P0 Critical)...")
signals = make_signals(
    "POSTGRES_MAIN_01", "RDBMS",
    "CONNECTION_TIMEOUT",
    "Primary database connection pool exhausted.",
    150, 5000
)
send_batch(signals, "RDBMS outage")
time.sleep(2)

print("\n[Phase 2] MCP Host failure (P0 Critical)...")
signals = make_signals(
    "MCP_HOST_PROD_01", "MCP_HOST",
    "HOST_UNREACHABLE",
    "MCP host not responding to health checks.",
    80, None
)
send_batch(signals, "MCP failure")
time.sleep(1)

print("\n[Phase 3] API gateway errors (P1 High)...")
signals = make_signals(
    "API_GATEWAY_01", "API",
    "HTTP_503",
    "Service unavailable. Upstream timeout.",
    50, 30000
)
send_batch(signals, "API errors")
time.sleep(1)

print("\n[Phase 4] Cache miss spike (P2 Medium)...")
signals = make_signals(
    "CACHE_CLUSTER_01", "CACHE",
    "CACHE_MISS",
    "Cache miss rate exceeded 80 percent.",
    30, 800
)
send_batch(signals, "Cache degradation")

print("\n" + "=" * 55)
print("Simulation complete!")
print("Expected: 4 incidents on dashboard")
print("Open http://localhost:5173")
