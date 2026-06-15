import time
import subprocess
import random
import threading


# =========================
# GLOBAL CONTROL
# =========================

stop_event = threading.Event()

current_profile = None
profile_start_time = 0


# =========================
# FDB MONITOR
# =========================

def fdb_refresh_loop(switch_name, interval=1):

    fdb_file = f"/tmp/fdb_{switch_name}.txt"

    while True:

        try:

            result = subprocess.run(
                ["ovs-appctl", "fdb/show", switch_name],
                capture_output=True,
                text=True
            )

            lines = result.stdout.splitlines()
            entries = max(0, len(lines) - 1)

            print(f"[FDB] Entries={entries}")

            with open(fdb_file, "w") as f:
                f.write(result.stdout)

        except Exception as e:
            print(f"[FDB ERROR] {e}")

        time.sleep(interval)


# =========================
# GROUP DETECTION (FROM TOPOLOGY)
# =========================

def get_groups(net):

    groups = {0: [], 1: [], 2: []}

    for h in net.hosts:

        if h.name.startswith("g0_"):
            groups[0].append(h)

        elif h.name.startswith("g1_"):
            groups[1].append(h)

        elif h.name.startswith("g2_"):
            groups[2].append(h)

    return groups


# =========================
# TRAFFIC PROFILES
# =========================

TRAFFIC_PROFILES = [

    {
        "name": "90_10",
        "local_prob": 0.9,
        "active_range": (4, 8),
        "flow_type": "short"
    },

    {
        "name": "70_30",
        "local_prob": 0.7,
        "active_range": (8, 12),
        "flow_type": "short"
    },

    {
        "name": "50_50",
        "local_prob": 0.5,
        "active_range": (12, 18),
        "flow_type": "mixed"
    },

    {
        "name": "uniform",
        "local_prob": None,
        "active_range": (4, 18),
        "flow_type": "mixed"
    },

    {
        "name": "heavy_tail",
        "local_prob": 0.7,
        "active_range": (8, 18),
        "flow_type": "heavy"
    }
]


# =========================
# DESTINATION SELECTION
# =========================

def choose_destination(src, groups, local_prob):

    src_group = None

    for gid, hosts in groups.items():
        if src in hosts:
            src_group = gid
            break

    if src_group is None:
        return random.choice(list(groups.values())[0])

    # uniform case
    if local_prob is None:

        candidates = []

        for gid, hosts in groups.items():
            if gid != src_group:
                candidates.extend(hosts)

        return random.choice(candidates)

    # local vs remote
    if random.random() < local_prob:

        candidates = [
            h for h in groups[src_group]
            if h != src
        ]

    else:

        candidates = []

        for gid, hosts in groups.items():
            if gid != src_group:
                candidates.extend(hosts)

    return random.choice(candidates)


# =========================
# FLOW DURATION MODEL
# =========================

def get_duration(flow_type):

    if flow_type == "short":
        return random.randint(3, 15)

    elif flow_type == "long":
        return random.randint(300, 1800)

    elif flow_type == "heavy":

        return int(
            min(
                3600,
                random.paretovariate(1.4) * 10
            )
        )

    else:
        return random.randint(10, 120)


# =========================
# ACTIVE HOST SELECTION
# =========================

def get_active_hosts(all_hosts, profile):

    amin, amax = profile["active_range"]

    count = random.randint(
        amin,
        min(amax, len(all_hosts))
    )

    return random.sample(all_hosts, count)


# =========================
# BOOTSTRAP TRAFFIC
# =========================

def bootstrap_learning(net):

    all_hosts = net.hosts

    print("[BOOTSTRAP] Initial MAC learning")

    for host in all_hosts:

        dst = random.choice([h for h in all_hosts if h != host])

        host.cmd(f"ping -c 1 {dst.IP()} > /dev/null 2>&1")

    time.sleep(2)

    print("[BOOTSTRAP] Done")


# =========================
# KEEPALIVE TRAFFIC
# =========================

def random_keepalive(net):

    all_hosts = net.hosts

    count = random.randint(1, max(1, len(all_hosts) // 5))

    hosts = random.sample(all_hosts, count)

    for src in hosts:

        dst = random.choice([h for h in all_hosts if h != src])

        src.cmd(f"ping -c 1 {dst.IP()} > /dev/null 2>&1 &")

    print(f"[KEEPALIVE] Refreshed {len(hosts)} hosts")


# =========================
# USER SESSION FLOW
# =========================

def start_user_session(net, groups, profile):

    src = random.choice(net.hosts)

    dst = choose_destination(
        src,
        groups,
        profile["local_prob"]
    )

    duration = get_duration(profile["flow_type"])

    interval = random.choice([0.5, 1.0, 2.0])

    src.cmd(
        f"timeout {duration} "
        f"ping -i {interval} {dst.IP()} "
        f"> /dev/null 2>&1 &"
    )

    print(f"[SESSION] {src.name} -> {dst.name} ({duration}s)")


# =========================
# BURST TRAFFIC
# =========================

def start_burst(net, groups, profile):

    print("[BURST] Starting burst")

    all_hosts = net.hosts

    num_flows = random.randint(
        max(2, len(all_hosts) // 4),
        max(3, len(all_hosts) // 2)
    )

    for _ in range(num_flows):

        src = random.choice(all_hosts)

        dst = choose_destination(
            src,
            groups,
            profile["local_prob"]
        )

        duration = get_duration(profile["flow_type"])

        src.cmd(
            f"timeout {duration} "
            f"ping -i 0.5 {dst.IP()} "
            f"> /dev/null 2>&1 &"
        )

    print(f"[BURST] {num_flows} flows started")


# =========================
# MAIN TRAFFIC ENGINE
# =========================

def keepalive(net):

    global current_profile, profile_start_time

    print("[TRAFFIC] Engine started")

    groups = get_groups(net)

    current_profile = random.choice(TRAFFIC_PROFILES)
    profile_start_time = time.time()

    last_burst = time.time()

    while not stop_event.is_set():

        try:

            # rotate scenario every 5 minutes
            if time.time() - profile_start_time > 300:

                current_profile = random.choice(TRAFFIC_PROFILES)
                profile_start_time = time.time()

                print(f"[PROFILE] Switched to {current_profile['name']}")

            profile = current_profile

            # active host subset
            active_hosts = get_active_hosts(net.hosts, profile)

            # keepalive traffic
            if random.random() < 0.4:

                for src in random.sample(
                    active_hosts,
                    max(1, len(active_hosts) // 3)
                ):

                    dst = choose_destination(
                        src,
                        groups,
                        profile["local_prob"]
                    )

                    src.cmd(f"ping -c 1 {dst.IP()} > /dev/null 2>&1 &")

            # user sessions
            if random.random() < 0.3:
                start_user_session(net, groups, profile)

            # periodic burst
            burst_interval = random.randint(300, 600)

            if time.time() - last_burst > burst_interval:
                start_burst(net, groups, profile)
                last_burst = time.time()

        except Exception as e:

            if stop_event.is_set():
                break

            print(f"[WARN] {e}")

        time.sleep(10)

    print("[TRAFFIC] Stopped cleanly")