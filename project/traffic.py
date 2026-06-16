import random
import time
import threading
random.seed(42) #pseudorandom number generator

stop_event = threading.Event()


# PROFILES
TRAFFIC_PROFILES = [

    {
        "name": "90_10",
        "local_prob": 0.9,
        "active_range": (4, 8)
    },

    {
        "name": "70_30",
        "local_prob": 0.7,
        "active_range": (8, 12)
    },

    {
        "name": "50_50",
        "local_prob": 0.5,
        "active_range": (12, 18)
    },

    {
        "name": "uniform",
        "local_prob": None,
        "active_range": (4, 18)
    },

    {
        "name": "heavy_tail",
        "local_prob": 0.7,
        "active_range": (8, 18)
    }
]



# GROUP DETECTION
def get_groups(net):

    groups = {
        0: [],
        1: [],
        2: []
    }

    for h in net.hosts:

        if h.name.startswith("g0_"):
            groups[0].append(h)

        elif h.name.startswith("g1_"):
            groups[1].append(h)

        elif h.name.startswith("g2_"):
            groups[2].append(h)

    return groups


# ACTIVE HOSTS
def get_active_hosts(net, profile):

    amin, amax = profile["active_range"]

    count = random.randint(
        amin,
        min(amax, len(net.hosts))
    )

    return random.sample(net.hosts, count)


# DESTINATION CHOICE
def choose_destination(src, groups, local_prob):

    src_group = None

    for gid, hosts in groups.items():

        if src in hosts:
            src_group = gid
            break

    # TRUE UNIFORM
    if local_prob is None:

        candidates = [
            h for h in sum(groups.values(), [])
            if h != src
        ]

        return random.choice(candidates)

    # LOCAL
    if random.random() < local_prob:

        candidates = [
            h
            for h in groups[src_group]
            if h != src
        ]

    # REMOTE
    else:

        candidates = []

        for gid, hosts in groups.items():

            if gid != src_group:
                candidates.extend(hosts)

    return random.choice(candidates)


# FLOW DURATION
def get_duration(profile_name):

    if profile_name == "heavy_tail":

        return int(
            min(
                3600,
                random.paretovariate(1.5) * 30
            )
        )

    r = random.random()

    # many short flows
    if r < 0.80:
        return random.randint(3, 15)

    # some medium flows
    elif r < 0.95:
        return random.randint(10, 120)

    # few long flows
    else:
        return random.randint(300, 1800)



# BOOTSTRAP LEARNING

def bootstrap_learning(net):

    print("[BOOTSTRAP] Starting")

    for src in net.hosts:

        dst = random.choice(
            [h for h in net.hosts if h != src]
        )

        src.cmd(
            f"ping -c 1 {dst.IP()} > /dev/null 2>&1"
        )

    time.sleep(2)

    print("[BOOTSTRAP] Done")



# KEEPALIVE

def keepalive_hosts(active_hosts, groups, profile):

    refresh_count = max(
        1,
        len(active_hosts) // 3
    )

    selected = random.sample(
        active_hosts,
        refresh_count
    )

    for src in selected:

        dst = choose_destination(
            src,
            groups,
            profile["local_prob"]
        )

        src.cmd(
            f"ping -c 1 {dst.IP()} "
            f"> /dev/null 2>&1 &"
        )


# SESSION FLOW
def start_session(active_hosts,
                  groups,
                  profile):

    src = random.choice(active_hosts)

    dst = choose_destination(
        src,
        groups,
        profile["local_prob"]
    )

    duration = get_duration(
        profile["name"]
    )

    interval = random.choice(
        [0.5, 1.0, 2.0]
    )

    src.cmd(
        f"timeout {duration} "
        f"ping -i {interval} {dst.IP()} "
        f"> /dev/null 2>&1 &"
    )

    print(
        f"[FLOW] "
        f"{src.name} -> {dst.name} "
        f"({duration}s)"
    )



# BURST

def start_burst(active_hosts,
                groups,
                profile):

    num_flows = random.randint(
        max(2, len(active_hosts)//2),
        len(active_hosts)
    )

    print(
        f"[BURST] "
        f"{num_flows} flows"
    )

    for _ in range(num_flows):

        src = random.choice(active_hosts)

        dst = choose_destination(
            src,
            groups,
            profile["local_prob"]
        )

        duration = get_duration(
            profile["name"]
        )

        src.cmd(
            f"timeout {duration} "
            f"ping -i 0.5 {dst.IP()} "
            f"> /dev/null 2>&1 &"
        )



# MAIN ENGINE

def start_learning_phase(net):

    bootstrap_learning(net)

    groups = get_groups(net)

    burst_interval = random.randint(
        180,
        300
    )

    last_burst = time.time()

    while not stop_event.is_set():

        profile = random.choice(
            TRAFFIC_PROFILES
        )

        print(
            f"\n[PROFILE] "
            f"{profile['name']}"
        )

        profile_start = time.time()

        # Run each profile for 2 minutes
        while (
            time.time() - profile_start < 120
            and not stop_event.is_set()
        ):

            active_hosts = get_active_hosts(
                net,
                profile
            )

            print(
                f"[ACTIVE] "
                f"{len(active_hosts)} hosts"
            )

            keepalive_hosts(
                active_hosts,
                groups,
                profile
            )

            sessions = random.randint(
                1,
                max(2, len(active_hosts)//2)
            )

            for _ in range(sessions):

                start_session(
                    active_hosts,
                    groups,
                    profile
                )

            if (
                time.time() - last_burst
                > burst_interval
            ):

                start_burst(
                    active_hosts,
                    groups,
                    profile
                )

                last_burst = time.time()

                burst_interval = random.randint(
                    180,
                    300
                )

            time.sleep(10)

    print("[TRAFFIC] Stopped")


def stop_learning_phase():
    stop_event.set()