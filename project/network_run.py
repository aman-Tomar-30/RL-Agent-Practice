from mininet.log import setLogLevel
import json
import os
setLogLevel('info')

from dragonfly import topology, discover_switch_ports

# from mininet.cli import CLI #import during CLI testing
from auto_traffic import keepalive, fdb_refresh_loop, generate_traffic, keepalive
import time
import threading

net = None

try:
    net = topology()
    net.start()

    # get info about all, blockable, uplink ports of a switch
    info = discover_switch_ports(net, "g0_s1")

    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SAVE_PATH = os.path.join(BASE_DIR, "rl", "topology_info.json")

    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)

    with open(SAVE_PATH, "w") as f:
        json.dump(info, f, indent=4)
    






    # info = discover_switch_ports(net, "g0_s1")
    # blockable_ports = info["blockable_ports"]
    # uplink_ports = info["uplink_ports"]
    # all_ports = info["all_ports"]
    # print("\n===== PORT DISCOVERY =====")
    # print(f"Blockable Ports : {blockable_ports}")
    # print(f"Uplink Ports    : {uplink_ports}")
    # print(f"All Ports       : {all_ports}")

    print("\n[!] Configuring switches...")

    for sw in net.switches:
        sw.cmd(f'ovs-vsctl set-fail-mode {sw.name} standalone')
        sw.cmd(f'ovs-vsctl set Bridge {sw.name} stp_enable=true')

    print("\n[!] Waiting 30s for STP to converge...")
    time.sleep(30)

    print("\nNetwork Established ! Go ahead.\n")

    #CLI(net) #testing purpose

    # ── Start fdb refresh thread for g0_s1 ──
    fbd_refresh_thread = threading.Thread(target=fdb_refresh_loop, 
                                          args=('g0_s1', 1), 
                                          daemon=True)
    fbd_refresh_thread.start()

    # ── Generate traffic ──
    generate_traffic(net, 'g0_s1')

    ka_thread = threading.Thread(target=keepalive, 
                                 args=(net,), 
                                 daemon=True)
    ka_thread.start()

    running = True
    try:
        while running:  # main thread program stops (even if other threads are running)
            time.sleep(5)
            # Show live fdb state every 30s
    except KeyboardInterrupt:
        running = False
        print("\n[STOP] Shutting down...")
        net.stop()

except Exception as e:
    print(f"Error: {e}")