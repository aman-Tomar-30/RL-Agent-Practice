"""
Run this AS the Mininet script, replacing dragonfly.py's CLI call.
It starts the network, generates traffic, and keeps fdb fresh.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller
from mininet.log import setLogLevel
import time
import subprocess
import threading
import os
import random

def fdb_refresh_loop(switch_name, interval=2):
    """Continuously dump fdb to file so RL agent can read it."""
    fdb_file = f"/tmp/fdb_{switch_name}.txt"
    print(f"[FDB] Refreshing {fdb_file} every {interval}s")
    while True:
        try:
            result = subprocess.run(
                ["ovs-appctl", "fdb/show", switch_name],
                capture_output=True, text=True
            )

            entries = len(result.stdout.splitlines())
            print(f"[FDB] Entries={entries}")

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


def topology():
    net = Mininet(controller=None)

    # ── Build topology (same as your dragonfly.py) ──
    g0_s0 = net.addSwitch('g0_s0')
    g0_s1 = net.addSwitch('g0_s1')
    g1_s0 = net.addSwitch('g1_s0')
    g1_s1 = net.addSwitch('g1_s1')
    g2_s0 = net.addSwitch('g2_s0')
    g2_s1 = net.addSwitch('g2_s1')

    #Switch connection
    net.addLink(g0_s0, g0_s1) 
    net.addLink(g1_s0, g1_s1) 
    net.addLink(g2_s0, g2_s1) 
    net.addLink(g0_s0, g1_s0) 
    net.addLink(g1_s0, g2_s0) 
    net.addLink(g0_s0, g2_s0)

    # Group 0
    g0_s0_h1 = net.addHost('g0_s0_h1', mac='00:00:00:00:00:01')
    #g0_s0_h2 = net.addHost('g0_s0_h2')
    #g0_s0_h3 = net.addHost('g0_s0_h3')

    g0_s1_h1 = net.addHost('g0_s1_h1', mac='00:00:00:00:00:02')
    #g0_s1_h2 = net.addHost('g0_s1_h2')
    #g0_s1_h3 = net.addHost('g0_s1_h3')

    # Group 1
    g1_s0_h1 = net.addHost('g1_s0_h1', mac='00:00:00:00:00:03')
    #g1_s0_h2 = net.addHost('g1_s0_h2')
    #g1_s0_h3 = net.addHost('g1_s0_h3')

    g1_s1_h1 = net.addHost('g1_s1_h1', mac='00:00:00:00:00:04')
    #g1_s1_h2 = net.addHost('g1_s1_h2')
    #g1_s1_h3 = net.addHost('g1_s1_h3')

    # Group 2
    g2_s0_h1 = net.addHost('g2_s0_h1', mac='00:00:00:00:00:05')
    #g2_s0_h2 = net.addHost('g2_s0_h2')
    #g2_s0_h3 = net.addHost('g2_s0_h3')

    g2_s1_h1 = net.addHost('g2_s1_h1', mac='00:00:00:00:00:06')
    #g2_s1_h2 = net.addHost('g2_s1_h2')
    #g2_s1_h3 = net.addHost('g2_s1_h3')

    # g0_s0
    net.addLink(g0_s0_h1, g0_s0)
    #net.addLink(g0_s0_h2, g0_s0)
    #net.addLink(g0_s0_h3, g0_s0)

    # g0_s1
    net.addLink(g0_s1_h1, g0_s1)
    #net.addLink(g0_s1_h2, g0_s1)
    #net.addLink(g0_s1_h3, g0_s1)

    # g1_s0
    net.addLink(g1_s0_h1, g1_s0)
    #net.addLink(g1_s0_h2, g1_s0)
    #net.addLink(g1_s0_h3, g1_s0)

    # g1_s1
    net.addLink(g1_s1_h1, g1_s1)
    #net.addLink(g1_s1_h2, g1_s1)
    #net.addLink(g1_s1_h3, g1_s1)

    # g2_s0
    net.addLink(g2_s0_h1, g2_s0)
    #net.addLink(g2_s0_h2, g2_s0)
    #net.addLink(g2_s0_h3, g2_s0)

    # g2_s1
    net.addLink(g2_s1_h1, g2_s1)
    #net.addLink(g2_s1_h2, g2_s1)
    #net.addLink(g2_s1_h3, g2_s1)

    net.start()

    print("\n[!] Configuring switches...")
    for sw in [g0_s0, g0_s1, g1_s0, g1_s1, g2_s0, g2_s1]:
        sw.cmd(f'ovs-vsctl set-fail-mode {sw.name} standalone')
        sw.cmd(f'ovs-vsctl set Bridge {sw.name} stp_enable=true')

    print("\n[!] Waiting 30s for STP to converge...")
    time.sleep(30)
    print("[OK] Network ready.\n")

    # ── Start fdb refresh thread for g0_s1 ──
    t = threading.Thread(target=fdb_refresh_loop, args=('g0_s1', 1), daemon=True)
    t.start()

    # ── Generate traffic ──
    generate_traffic(net, 'g0_s1')

    def mac_learning_storm(hosts):
        print("[ATTACK] MAC learning storm")

        for _ in range(300):

            src = random.choice(hosts)
            dst = random.choice(hosts)

            if src == dst:
                continue

            src.cmd(
                f"arping -c 1 -I {src.defaultIntf()} {dst.IP()} > /dev/null 2>&1 &"
            )

    # ── Keep traffic alive — re-ping every 20s so MACs don't age out ──
    def keepalive(net):
        import random
        all_hosts  = net.hosts
        g0_s1_host = net.get('g0_s1_h1')
        g0_s1_ip   = g0_s1_host.IP()

        while True:
            if random.random() < 0.2:
                 mac_learning_storm(all_hosts)
            
            #if random.random() < 0.05:
            #    print("[CHAOS] Traffic blackout")

            #   for host in all_hosts:
            #        host.cmd("pkill -f ping 2>/dev/null")

            #   time.sleep(random.randint(2,4))

            time.sleep(3)

            print("[KEEPALIVE] Reshuffling traffic...")

            victims = random.sample(
                    all_hosts,
                    1
                )

            for host in victims:
                host.cmd("pkill -f ping 2>/dev/null")
            time.sleep(1)

            pairs = [(s, d) for i, s in enumerate(all_hosts)
                             for j, d in enumerate(all_hosts) if i < j]
            k      = random.randint(max(1, len(pairs) // 3), len(pairs))
            active = random.sample(pairs, k)

            for src, dst in active:
                interval = random.choice([
                    0.01,
                    0.05,
                    0.1,
                    0.2,
                    0.5,
                    1.0,
                    2.0
                ])
                src.cmd(f"ping -i {interval} {dst.IP()} > /dev/null 2>&1 &")

            # Force re-learning and broadcast traffic
            for src in all_hosts:
                for dst in random.sample(all_hosts, min(3, len(all_hosts))):

                    if src == dst:
                        continue

                    src.cmd(
                        f"arping -c 2 -I {src.defaultIntf()} {dst.IP()} > /dev/null 2>&1 &"
                    )

            # Always keep aggressive pings to g0_s1_h1 alive regardless of reshuffle
            for host in all_hosts:
                if host.name != 'g0_s1_h1':
                    interval = random.choice([
                        0.01,
                        0.02,
                        0.05,
                        0.1,
                        0.2
                    ])

                    host.cmd(f"ping -i {interval} {g0_s1_ip} > /dev/null 2>&1 &")

            print(f"[KEEPALIVE] {k}/{len(pairs)} pairs active + all hosts pinging g0_s1_h1")


    ka = threading.Thread(target=keepalive, args=(net,), daemon=True)
    ka.start()
    
    print("=" * 50)
    print("  Network + traffic running.")
    print("  Now run RL agent in another terminal:")
    print("  sudo ./venv/bin/python rl/main.py")
    print("=" * 50 + "\n")

    def show_fdb(net):

        while True:
            try:
                result = subprocess.run(
                    ["ovs-appctl", "fdb/show", "g0_s1"],
                    capture_output=True,
                    text=True
                )

                lines = result.stdout.splitlines()

                entries = []

                for line in lines:
                    parts = line.split()

                    if len(parts) >= 3:
                        entries.append(parts)

                print(
                    f"\n[FDB STATUS] "
                    f"Entries={len(entries)}"
                )

            except Exception as e:
                print(e)

            time.sleep(5)


    fdb_thread = threading.Thread(
            target=show_fdb,
            args=(net,),
            daemon=True
        )
    
    fdb_thread.start()

    # Keep alive until Ctrl+C
    try:
        while True:
            time.sleep(5)
            # Show live fdb state every 30s
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()