import time
import subprocess
import csv
import os

SWITCH = "g0_s1"
MAX_MAC_CAPACITY = 10
DEFAULT_AGE = 300


CSV_FILE = "without_rl_stats.csv"

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "mac_fill",
            "age_score",
            "flood_pressure"
        ])


def write_stats(metrics):
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            metrics["mac_fill"],
            metrics["age_score"],
            metrics["flood_pressure"]
        ])


# Helper Function
def run_cmd(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip()

    except subprocess.CalledProcessError as e:
        print("\n[WARN] Command failed")
        print("CMD:", e.cmd)
        print("Return code:", e.returncode)
        print("STDERR:", e.stderr)

        return None
    


def get_mac_table(sw_name):
    cmd = f"ovs-appctl fdb/show {sw_name}"
    output = run_cmd(cmd)
    #print(output)
    if not output:
        return {}

    entries = {}

    for line in output.splitlines()[1:]:

        parts = line.split()
        #print(parts)
        # skip headers or invalid lines
        if len(parts) < 3:
            continue

        try:
            port = parts[0]
            vlan = int(parts[1])
            mac = parts[2]
            age = int(parts[3])

            entries[mac]={
                "port": port,
                "mac": mac,
                "vlan": vlan,   # OVS FDB usually doesn't expose VLAN here
                "age": age
            }

        except:
            continue
    
    #print(entries)
    return entries


def calculate_metrics(mac_table, max_entries=MAX_MAC_CAPACITY,
                      default_time=DEFAULT_AGE,
                      new_seen_mac=0):
    total_macs = len(mac_table)

    # 1. MAC fill ratio
    mac_fill = round(total_macs / max_entries, 3) if max_entries else 0

    # 2. Age score
    if total_macs > 0:
        ages = [entry["age"] for entry in mac_table.values()]
        age_score = round((sum(ages) / len(ages)) / default_time, 3)
    else:
        age_score = 0

    # 3. Flood pressure
    flood_pressure = round(new_seen_mac / total_macs, 3) if total_macs > 0 else round(0, 3)

    return {
        "mac_fill": mac_fill,
        "age_score": age_score,
        "flood_pressure": flood_pressure
    }



previous_macs = set()
episodes = 200
steps = 30

try:
    for e in range(1, episodes+1):
        for s in range(1, steps+1): 
            mac_table = get_mac_table(SWITCH)

            current_macs = set(mac_table.keys())

            new_seen_mac = len(current_macs - previous_macs)

            metrics = calculate_metrics(
                mac_table,
                new_seen_mac=new_seen_mac
            )

            write_stats(metrics)
            #print(metrics)

            previous_macs = current_macs

            time.sleep(1)

except KeyboardInterrupt:
    print("User INterrupted!!!")