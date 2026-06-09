#from mininet.topo import Topo
#from mininet.net import Mininet
#from mininet.node import Controller
#import threading
#import os
#from mininet.log import setLogLevel

import time
import subprocess
import random

def fdb_refresh_loop(switch_name, interval=1):
    """Continuously dump fdb to file so RL agent can read it."""
    fdb_file = f"/tmp/fdb_{switch_name}.txt"
    print(f"[FDB] Refreshing {fdb_file} every {interval}s")
    while True:
        try:
            result = subprocess.run(
                ["ovs-appctl", "fdb/show", switch_name],
                capture_output=True, text=True
            )

            entries = len(result.stdout.splitlines()) - 1 #first row contains column headers
            print(f"[FDB REFRESH] Entries={entries}")

            with open(fdb_file, "w") as f:
                f.write(result.stdout)
        except Exception as e:
            print(f"[FDB ERROR] {e}")
        time.sleep(interval)


def generate_traffic(net, switch_name):
    """
    Find all hosts connected to the target switch and ping between them.
    Also sends arping to force MAC learning.
    """
    # Find hosts directly connected to our switch
    target_hosts = []
    for host in net.hosts:
        for intf in host.intfList():
            if intf.link:
                node1 = intf.link.intf1.node
                node2 = intf.link.intf2.node
                other = node2 if node1 == host else node1
                if other.name == switch_name:
                    target_hosts.append(host)
                    break

    # Also grab all hosts for cross-traffic
    all_hosts = net.hosts

    print(f"\n[TRAFFIC] Hosts on {switch_name}: {[h.name for h in target_hosts]}")
    print(f"[TRAFFIC] All hosts: {[h.name for h in all_hosts]}\n")

    if len(all_hosts) < 2:
        print("[WARN] Need at least 2 hosts for traffic generation")
        return

    # Force ARP/MAC learning — send arping from each host
    print("[TRAFFIC] Forcing MAC learning via arping...")
    for host in all_hosts:
        for other in all_hosts:
            if host == other:
                continue
            other_ip = other.IP()
            if other_ip:
                host.cmd(f"arping -c 3 -I {host.defaultIntf()} {other_ip} &")

    time.sleep(2)

    # Start continuous pings between all host pairs
    print("[TRAFFIC] Starting continuous pings...")
    for i, src in enumerate(all_hosts):
        for j, dst in enumerate(all_hosts):
            if i >= j:
                continue
            dst_ip = dst.IP()
            if dst_ip:
                src.cmd(f"ping -i 0.5 {dst_ip} > /dev/null 2>&1 &")
                print(f"  {src.name} → {dst.name} ({dst_ip})")

    print("\n[TRAFFIC] All streams started.\n")

    # ── Force all remote hosts to ping g0_s1_h1 aggressively ──
    # so g0_s1 learns all MACs and mac_fill reaches higher states
    g0_s1_host = net.get('g0_s1_h1')
    g0_s1_ip   = g0_s1_host.IP()
    print(f"[TRAFFIC] Forcing all hosts to ping g0_s1_h1 ({g0_s1_ip}) aggressively...")
    for host in all_hosts:
        if host.name != 'g0_s1_h1':
            host.cmd(f"ping -i 0.2 {g0_s1_ip} > /dev/null 2>&1 &")
            print(f"  {host.name} → g0_s1_h1 ({g0_s1_ip})")
    print("[TRAFFIC] Aggressive pings started.\n")


def mac_learning_storm(hosts):
    print("[ATTACK] MAC learning storm")
    for _ in range(100):
        src = random.choice(hosts)
        dst = random.choice(hosts)
        if src == dst:
            continue
        if not dst.intfs: # it has no active interface
            continue
        src.cmd(
            f"arping -c 1 -I {src.defaultIntf()} {dst.IP()} > /dev/null 2>&1 &"
        )

# ── Keep traffic alive — re-ping every 20s so MACs don't age out ──
def keepalive(net):
    all_hosts  = net.hosts
    g0_s1_host = net.get('g0_s1_h1')
    g0_s1_ip   = g0_s1_host.IP()
    #print(all_hosts)
    cycle = 0

    while True:
        cycle += 1

        # ── 3s: minimal keepalive (light ping refresh) ──
        for host in random.sample(all_hosts, 1): #one random host ping g0_s1_h1
            if host.name != 'g0_s1_h1':
                host.cmd(f"ping -i 0.5 {g0_s1_ip} > /dev/null 2>&1 &")

        # ── 20s: full traffic reshuffle ──
        if cycle % 7 == 0:   # ~21s if sleep=3
            print("[KEEPALIVE] Reshuffling traffic...")

            host = random.choice(all_hosts)
            host.cmd("pkill -f ping 2>/dev/null") #Stop one host's current ping traffic so a different traffic flow can be started

            pairs = [(s, d) for i, s in enumerate(all_hosts)
                             for j, d in enumerate(all_hosts) if i < j] #handle self-pairing and duplicates

            k = random.randint(max(1, len(pairs)//5), len(pairs)) #20% pairs will be activate
            active = random.sample(pairs, k) #create list of that random 20% pairs
            #print(active)

            for src, dst in active:
                interval = random.choice([0.1, 0.2, 0.5, 1.0])
                if not dst.intfs:
                        continue
                src.cmd(f"ping -i {interval} {dst.IP()} > /dev/null 2>&1 &") #supress errors
            
            print(f"[KEEPALIVE] {k}/{len(pairs)} pairs active + all hosts pinging g0_s1_h1")

        # ── optional ARP storm (less frequent) ──
        if cycle % 20 == 0:
            mac_learning_storm(all_hosts)

        time.sleep(3)


       
