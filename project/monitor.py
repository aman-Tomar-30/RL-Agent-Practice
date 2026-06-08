import subprocess
import time
import re
import csv as csv_module
from project.generate_csv import get_output_csv

"""
This script:
1. Collects live state from OVS (MAC entries, flood pressure, entry age)
2. Executes actions on OVS switches (block/unblock port, aging, evict, flood)
"""
#          ┌──────────────┐
#          │   NETWORK    │
#          └──────┬───────┘
#                 ↓
#        OBSERVATION LAYER
#    (MAC, flood, aging, traffic)
#                 ↓
#        STATE REPRESENTATION
#    (normalized RL state vector)
#                 ↓
#       RL AGENT (not shown here)
#                 ↓
#           ACTION EXECUTION
#  (block, flood, evict, aging)
#                 ↓
#          ┌──────┴───────┐
#          │   NETWORK    │
#          └──────────────┘

# =========================
# CONFIGURATION
# =========================

SWITCHES         = subprocess.check_output(["ovs-vsctl", "list-br"], text=True).split()
SWITCH           = "g0_s1"
print(f"Active Switch: {SWITCH}")

INTERVAL         = 3

MAX_MAC_CAPACITY = 24
MAX_FLOOD_RATE   = 15
MAX_ENTRY_AGE    = 300

AGING_HIGH       = 600
AGING_LOW        = 60
AGING_DEFAULT    = 300

# =========================
# HELPER
# =========================

_prev_port_packets = {}

def run_cmd(cmd):
    result = subprocess.check_output(cmd, shell=True, text=True)
    return result.strip()

# =========================================================
# 1. MAC TABLE ENTRIES : all MAC table entries from a switch sw
# =========================================================

def get_mac_table_entries(sw):
    try:
        fdb_file = f"/tmp/fdb_{sw}.txt"
        with open(fdb_file, "r") as f:
            lines = f.read().splitlines()
        # eg
        # lines = [
        #        "1 10 aa:bb:cc:dd:ee:ff 30",
        #       "2 20 ff:ee:dd:cc:bb:aa 12"
        # ]


        entries = []
    #   will store like this      [
    #   {"port": 1, "vlan": 10, "mac": "...", "age": 30},
    #   ...
    # ]
        for line in lines:
            if not line.strip() or "port" in line.lower() or "VLAN" in line:
                continue
            parts = line.split() #eg parts = ["1", "10", "aa:bb:cc:dd:ee:ff", "30"]
            if len(parts) >= 3:
                entries.append({
                    "port": int(parts[0]),
                    "vlan": int(parts[1]),
                    "mac":  parts[2],
                    "age":  int(parts[3]) if len(parts) > 3 else 0
                })
                
        return entries

    except Exception as e:
        print(f"[ERROR] MAC table fetch failed: {e}")
        return []

# =========================================================
# 2. FLOOD PRESSURE  (dump-ports based — measures real traffic)
# normal traffic → uneven ports
# flooding → symmetric spike on ports

# =========================================================

def get_flood_pressure(sw):
    global _prev_port_packets
    try:
        result = subprocess.run(
            ["sudo", "ovs-ofctl", "dump-ports", sw],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()

        current_packets = {}
        current_port    = None

        for line in lines:
            stripped = line.strip()

            # Detect port header line — e.g. "port  1:" or "port LOCAL:"
            port_match = re.match(r"port\s+(\S+):", stripped)
            if port_match:
                current_port = port_match.group(1).replace(":", "")
                continue

            # Parse rx line — handles both "pkts" and "packets"
            if current_port is not None:
                rx_match = re.search(r"rx\s+p(?:kts|ackets)=(\d+)", stripped)
                tx_match = re.search(r"tx\s+p(?:kts|ackets)=(\d+)", stripped)

                if rx_match:
                    rx = int(rx_match.group(1))
                    current_packets[current_port] = current_packets.get(current_port, 0) + rx

                if tx_match:
                    tx = int(tx_match.group(1))
                    current_packets[current_port] = current_packets.get(current_port, 0) + tx

        # First call — just initialise, return 0
        if sw not in _prev_port_packets:
            _prev_port_packets[sw] = current_packets
            return 0.0

        prev_packets = _prev_port_packets[sw]
        _prev_port_packets[sw] = current_packets

        # Only look at operational ports 1 and 2
        deltas = []
        for port in ["1", "2"]:
            if port in current_packets and port in prev_packets:
                deltas.append(max(0, current_packets[port] - prev_packets[port]))

        if not deltas or max(deltas) == 0:
            return 0.0

        # Flood pressure = min/max ratio across ports
        # Unicast (normal): one port high, other low  → ratio near 0
        # Flooding:         both ports spike equally  → ratio near 1
        min_delta = min(deltas)
        max_delta = max(deltas)

        total = sum(deltas)

        balance = (
            float(min_delta) / float(max_delta)
            if max_delta > 0 else 0
        )

        flood_pressure = (
            0.5 * balance +
            0.5 * min(total / 5000.0, 1.0)
        )

        return round(flood_pressure, 4)

    except Exception as e:
        print(f"[ERROR] Failed to calculate live flood pressure: {e}")
        return 0.0

# =========================================================
# 3. ENTRY AGE
# =========================================================

def calculate_entry_age(mac_entries):
    if not mac_entries: # empty mac_entries list
        return 0
    return max(entry["age"] for entry in mac_entries)

# =========================================================
# 4. NORMALIZATION
# =========================================================

def normalize(value, max_value):
    if max_value == 0:
        return 0
    return round(min(value / max_value, 1.0), 4)

# =========================================================
# 5. PORT HELPER
# =========================================================

def get_flood_port(mac_entries):
    """Returns port with most MAC entries — most likely flooding source"""
    port_counts = {}
    for entry in mac_entries:
        p = entry["port"]
        port_counts[p] = port_counts.get(p, 0) + 1
    if not port_counts:
        return None
    return max(port_counts, key=port_counts.get)

def get_all_ports(sw):
    """Returns list of all port names on the switch"""
    try:
        output = run_cmd(f"ovs-vsctl list-ports {sw}")
        return output.splitlines()
    except Exception as e:
        print(f"[ERROR] get_all_ports failed: {e}")
        return []

# =========================================================
# 6. ACTION EXECUTION
# =========================================================

def action_learn_mac(sw):
    run_cmd(f"sudo ovs-ofctl del-flows {sw} cookie=0xDEAD/-1")
    run_cmd(f"ovs-vsctl set-fail-mode {sw} standalone")
    print(f"  [ACTION] LEARN_MAC — Removed flood rule + standalone mode on {sw}")

def action_evict_entry(sw):
    """Evict only the single stalest MAC entry. Does NOT flush the whole table."""
    try:
        mac_entries = get_mac_table_entries(sw)

        if not mac_entries:
            print(f"  [ACTION] EVICT_ENTRY — table already empty, nothing to evict on {sw}")
            return None

        stalest    = max(mac_entries, key=lambda e: e["age"])
        stale_mac  = stalest["mac"]
        stale_port = stalest["port"]
        stale_age  = stalest["age"]

        print(f"  [ACTION] EVICT_ENTRY — evicting MAC {stale_mac} "
              f"(port {stale_port}, age {stale_age}s) on {sw}")

        run_cmd(
            f"ovs-ofctl add-flow {sw} "
            f"priority=100,dl_src={stale_mac},actions=drop"
        )

        time.sleep(2)
        run_cmd(f"ovs-ofctl del-flows {sw} dl_src={stale_mac}")

        print(f"  [ACTION] EVICT_ENTRY — MAC {stale_mac} evicted and rule cleared")
        return stale_mac

    except Exception as e:
        print(f"  [ERROR] EVICT_ENTRY failed: {e}")
        return None

def action_flood(sw):
    # Secure mode so rule takes precedence; idle_timeout=10 auto-expires the rule
    run_cmd(f"ovs-vsctl set-fail-mode {sw} secure")
    run_cmd(f"sudo ovs-ofctl add-flow {sw} cookie=0xDEAD,priority=1,idle_timeout=10,actions=FLOOD")
    print(f"  [ACTION] FLOOD — Temporary flooding rule added (10s idle timeout) on {sw}")

def action_block_port(sw, port):
    """Bring a port administratively down to stop traffic"""
    try:
        run_cmd(f"ovs-ofctl mod-port {sw} {port} down")
        print(f"  [ACTION] BLOCK_PORT — blocked port {port} on {sw}")
    except Exception as e:
        print(f"  [ERROR] BLOCK_PORT failed on port {port}: {e}")

def action_unblock_port(sw, port):
    """Bring a port back up"""
    try:
        run_cmd(f"ovs-ofctl mod-port {sw} {port} up")
        print(f"  [ACTION] UNBLOCK_PORT — unblocked port {port} on {sw}")
    except Exception as e:
        print(f"  [ERROR] UNBLOCK_PORT failed on port {port}: {e}")

def action_increase_aging(sw):
    """Increase MAC aging timer — entries live longer"""
    try:
        run_cmd(f"ovs-vsctl set Bridge {sw} other_config:mac-aging-time={AGING_HIGH}")
        print(f"  [ACTION] INCREASE_AGING — set aging to {AGING_HIGH}s on {sw}")
    except Exception as e:
        print(f"  [ERROR] INCREASE_AGING failed: {e}")

def action_decrease_aging(sw):
    """Decrease MAC aging timer — entries expire faster, table stays fresher"""
    try:
        run_cmd(f"ovs-vsctl set Bridge {sw} other_config:mac-aging-time={AGING_LOW}")
        print(f"  [ACTION] DECREASE_AGING — set aging to {AGING_LOW}s on {sw}")
    except Exception as e:
        print(f"  [ERROR] DECREASE_AGING failed: {e}")

def execute_action(sw, action_idx, port=None):
    evicted_mac = None

    if action_idx == 0:
        action_learn_mac(sw)
    elif action_idx == 1:
        evicted_mac = action_evict_entry(sw)
    elif action_idx == 2:
        action_flood(sw)
    elif action_idx == 3:
        if port:
            action_block_port(sw, port)
        else:
            print(f"  [SKIP] BLOCK_PORT — no flooding port detected on {sw}")
    elif action_idx == 4:
        if port:
            action_unblock_port(sw, port)
        else:
            print(f"  [SKIP] UNBLOCK_PORT — no blocked port to release on {sw}")
    elif action_idx == 5:
        action_increase_aging(sw)
    elif action_idx == 6:
        action_decrease_aging(sw)

    return evicted_mac

# =========================================================
# MAIN MONITOR LOOP
# (used when running monitor.py standalone for data collection)
# =========================================================

def monitor(sw):
    print("\n========== SDN MONITOR STARTED ==========\n")
    data = []

    for n in range(100):

        mac_entries     = get_mac_table_entries(sw)
        current_entries = len(mac_entries)
        mac_fill        = normalize(current_entries, MAX_MAC_CAPACITY)

        flood_rate      = get_flood_pressure(sw)
        flood_pressure  = normalize(flood_rate, MAX_FLOOD_RATE)

        avg_age         = calculate_entry_age(mac_entries)
        age_score       = normalize(avg_age, MAX_ENTRY_AGE)

        state = [mac_fill, flood_pressure, age_score]
        print(f"[{n+1:3d}] State: mac_fill={mac_fill} | "
              f"flood_pressure={flood_pressure} | "
              f"age_score={age_score}")

        data.append(state)
        time.sleep(INTERVAL)

    print(f"\nCollected {len(data)} states")
    print(data)
    get_output_csv(data)

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    monitor(SWITCH)