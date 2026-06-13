import subprocess
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project.monitor import (
    get_mac_table_entries,
    get_flood_pressure,
    calculate_entry_age,
    normalize,
    execute_action,
    get_flood_port,
    MAX_MAC_CAPACITY,
    MAX_FLOOD_RATE,
    MAX_ENTRY_AGE
)
from project.rl.reward import get_reward
from project.rl.actions import ActionSpace

"""
    Reads live network state
    Applies RL actions safely (with guards)
    omputes reward + next state transition
"""

class LiveEnv:
    def __init__(self, switch=None):

        try:
            bridges = subprocess.check_output(
                ["ovs-vsctl", "list-br"], text=True
            ).split()
            if not bridges:
                raise RuntimeError(
                    "\n[ERROR] No OVS switches found.\n"
                    "Start Mininet first: sudo python3 dragonfly.py\n"
                    "Then run the RL agent in a separate terminal."
                )
            self.switch = switch or "g0_s1"
            print(f"[OK] Connected to switch: {self.switch}")

        except FileNotFoundError:
            raise RuntimeError(
                "\n[ERROR] ovs-vsctl not found.\n"
                "Are you running inside WSL with OVS installed?"
            )

        self.port_blocked = {}

        # load topology info
        import os
        import json

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        file_path = os.path.join(BASE_DIR, "topology_info.json")

        with open(file_path, "r") as f:
            topology = json.load(f)

        self.blockable_ports = topology["blockable_ports"]
        

    def get_live_state(self):
        mac_entries    = get_mac_table_entries(self.switch)
        mac_fill       = normalize(len(mac_entries),          MAX_MAC_CAPACITY)
        flood_packets  = get_flood_pressure(self.switch)
        flood_pressure = normalize(flood_packets,             MAX_FLOOD_RATE)
        avg_age        = calculate_entry_age(mac_entries)
        age_score      = normalize(avg_age,                   MAX_ENTRY_AGE)

        return {
            "mac_fill"       : mac_fill,
            "flood_pressure" : flood_pressure,
            "age_score"      : age_score,
            "mac_entries"    : mac_entries
        }

    def step(self, action):
        state_info  = self.get_live_state()
        mac_entries = state_info["mac_entries"]
        port_acted  = None
        original_action = action          # pre-guard action


        # EVICT_ENTRY guard (Problem 2: Prevent loop when table nearly empty)
        if action == 1:
            if state_info["mac_fill"] < 0.3:
                print("  [GUARD] EVICT skipped — mac_fill too low, switching to LEARN_MAC")
                action = 0

        # BLOCK_PORT guard
        elif action == 3:
            port = get_flood_port(self.switch, self.blockable_ports)

            if not port:
                print("[GUARD] No flood port found")
                action = 0
                port = None

            elif port not in self.blockable_ports:
                print(f"[GUARD] Port {port} is not blockable")
                action = 0

            elif self.port_blocked.get(port, False):
                print(f"[GUARD] Port {port} already blocked")
                action = 0

            else:
                

                ports_that_would_remain = [
                    p for p in self.blockable_ports
                    if not self.port_blocked.get(p, False) 
                    and p != port
                ]

                if len(ports_that_would_remain) == 0:
                    print(
                        "[GUARD] BLOCK_PORT skipped — "
                        "would isolate switch completely"
                    )
                    action = 0

                else:
                    self.port_blocked[port] = True
                    port_acted = port
                    print(
                        f"[BLOCK] Port {port} marked as blocked "
                        f"on {self.switch}"
                    )

        # UNBLOCK_PORT guard
        elif action == 4:
            blocked_ports = [p for p, v in self.port_blocked.items() if v]
            if not blocked_ports:
                print("  [GUARD] UNBLOCK_PORT skipped — no ports are blocked, switching to LEARN_MAC")
                action = 0
            else:
                port = blocked_ports[0]
                self.port_blocked[port] = False
                port_acted = port
                print(f"  [UNBLOCK] Port {port} marked as unblocked on {self.switch}")

        executed_action = action          # post-guard actual action

        evicted_mac = execute_action(self.switch, executed_action, port=port_acted)

        if executed_action == 1: # evict
            time.sleep(4)
        else:
            time.sleep(1)

        next_state_info = self.get_live_state()
        fill_change = next_state_info["mac_fill"] - state_info["mac_fill"]

        flood_change = (
            next_state_info["flood_pressure"]
            - state_info["flood_pressure"]
        )
        print(
            f"[STATE] "
            f"MAC {len(mac_entries)}->{len(next_state_info['mac_entries'])} | "
            f"Fill {state_info['mac_fill']:.3f}->{next_state_info['mac_fill']:.3f} | "
            f"Flood {state_info['flood_pressure']:.3f}->{next_state_info['flood_pressure']:.3f} | "
            f"Age {state_info['age_score']:.3f}->{next_state_info['age_score']:.3f}"
        )

        all_ports = list(set(entry['port'] for entry in state_info["mac_entries"] if 'port' in entry))
        is_isolated = len(all_ports) > 0 and all(self.port_blocked.get(p, False) for p in all_ports)

        reward, outcome, situation = get_reward(
            action=executed_action,

            old_fill=state_info["mac_fill"],
            new_fill=next_state_info["mac_fill"],

            old_flood=state_info["flood_pressure"],
            new_flood=next_state_info["flood_pressure"],

            old_age=state_info["age_score"],
            new_age=next_state_info["age_score"],

            all_ports_blocked=is_isolated
        )

        # Problem 2 (Fix 1): Harder penalty for evicting empty table (-3.0 penalty override)
        if evicted_mac is None and executed_action == 1:
            reward = -1.0
            outcome = "unnecessary_flood"

        info = {
            "mac_fill"          : state_info["mac_fill"],
            "mac_count"         : len(mac_entries),
            "fill_change": round(fill_change,4),
            "flood_change": round(flood_change,4),
            "flood_pressure"    : state_info["flood_pressure"],
            "age_score"         : state_info["age_score"],
            "situation"         : situation,
            "outcome"           : outcome,
            "action_name"       : ActionSpace.get_action_name(executed_action),
            "original_action"   : original_action,
            "executed_action"   : executed_action,
            "port_acted"        : port_acted if port_acted else "N/A",
            "currently_blocked" : str([p for p, v in self.port_blocked.items() if v]),
            "evicted_mac"       : evicted_mac if evicted_mac else "N/A"
        }

        return next_state_info, reward, info
    

