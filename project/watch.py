from project.monitor import get_mac_table_entries
import time
while True:
    entries = get_mac_table_entries("g0_s1")

    print("\033c")

    print("RL MAC TABLE VIEW")
    print("-" * 70)

    print(f"Entries : {len(entries)}")

    oldest = max(entries, key=lambda x: x["age"]) if entries else None

    for e in entries:
        marker = ""

        if oldest and e["mac"] == oldest["mac"]:
            marker = " <-- WILL BE EVICTED"

        print(
            f"Port {e['port']} | "
            f"{e['mac']} | "
            f"Age {e['age']}s"
            f"{marker}"
        )

    time.sleep(1)