import time
import json
import redis
from prometheus_client import start_http_server, Gauge

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

HASH_KEY = "mac_table"

mac_age = Gauge(
    "mac_table_age",
    "MAC age",
    ["mac", "port", "vlan"]
)

mac_seen = Gauge(
    "mac_table_seen_count",
    "MAC seen count",
    ["mac", "port", "vlan"]
)

mac_table_size = Gauge("mac_table_size", "MAC count")


def collect():
    try:
        entries = r.hgetall(HASH_KEY)

        # reset metrics every cycle
        mac_age.clear()
        mac_seen.clear()

        mac_table_size.set(len(entries))

        for mac, raw in entries.items():
            try:
                data = json.loads(raw)

                labels = {
                    "mac": mac,
                    "port": data.get("port", "0"),
                    "vlan": str(data.get("vlan", 0))
                }

                mac_age.labels(**labels).set(data.get("age", 0))
                mac_seen.labels(**labels).set(data.get("seen_count", 0))

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"[WARN] Error parsing MAC {mac}: {e}")
                continue

    except redis.RedisError as e:
        print(f"[REDIS ERROR] {e}")
    except Exception as e:
        print(f"[COLLECT ERROR] {e}")


if __name__ == "__main__":
    try:
        start_http_server(8003)
        print("[INFO] Prometheus exporter running on :8003")

        while True:
            collect()
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down exporter (KeyboardInterrupt)...")