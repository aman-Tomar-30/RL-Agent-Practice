from mininet.net import Mininet
        
def topology():
    net = Mininet(controller=None)

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
    g0_s0_h2 = net.addHost('g0_s0_h2')
    g0_s0_h3 = net.addHost('g0_s0_h3')

    g0_s1_h1 = net.addHost('g0_s1_h1', mac='00:00:00:00:00:02')
    g0_s1_h2 = net.addHost('g0_s1_h2')
    g0_s1_h3 = net.addHost('g0_s1_h3')

    # Group 1
    g1_s0_h1 = net.addHost('g1_s0_h1', mac='00:00:00:00:00:03')
    g1_s0_h2 = net.addHost('g1_s0_h2')
    g1_s0_h3 = net.addHost('g1_s0_h3')

    g1_s1_h1 = net.addHost('g1_s1_h1', mac='00:00:00:00:00:04')
    g1_s1_h2 = net.addHost('g1_s1_h2')
    g1_s1_h3 = net.addHost('g1_s1_h3')

    # Group 2
    g2_s0_h1 = net.addHost('g2_s0_h1', mac='00:00:00:00:00:05')
    g2_s0_h2 = net.addHost('g2_s0_h2')
    g2_s0_h3 = net.addHost('g2_s0_h3')

    g2_s1_h1 = net.addHost('g2_s1_h1', mac='00:00:00:00:00:06')
    g2_s1_h2 = net.addHost('g2_s1_h2')
    g2_s1_h3 = net.addHost('g2_s1_h3')

    # g0_s0
    net.addLink(g0_s0_h1, g0_s0)
    net.addLink(g0_s0_h2, g0_s0)
    net.addLink(g0_s0_h3, g0_s0)

    # g0_s1
    net.addLink(g0_s1_h1, g0_s1)
    net.addLink(g0_s1_h2, g0_s1)
    net.addLink(g0_s1_h3, g0_s1)

    # g1_s0
    net.addLink(g1_s0_h1, g1_s0)
    net.addLink(g1_s0_h2, g1_s0)
    net.addLink(g1_s0_h3, g1_s0)

    # g1_s1
    net.addLink(g1_s1_h1, g1_s1)
    net.addLink(g1_s1_h2, g1_s1)
    net.addLink(g1_s1_h3, g1_s1)

    # g2_s0
    net.addLink(g2_s0_h1, g2_s0)
    net.addLink(g2_s0_h2, g2_s0)
    net.addLink(g2_s0_h3, g2_s0)

    # g2_s1
    net.addLink(g2_s1_h1, g2_s1)
    net.addLink(g2_s1_h2, g2_s1)
    net.addLink(g2_s1_h3, g2_s1)

    return net

def discover_switch_ports(net, switch_name):
    """
    Returns:
    {
        'blockable_ports': [...],  # host-facing
        'uplink_ports': [...],     # switch-facing
        'all_ports': [...]
    }
    """

    sw = net.get(switch_name)

    blockable_ports = []
    uplink_ports = []
    all_ports = []

    for intf in sw.intfList():

        if intf.name == "lo":
            continue

        link = intf.link
        if link is None:
            continue

        if link.intf1 == intf:
            peer_intf = link.intf2
        else:
            peer_intf = link.intf1

        peer_node = peer_intf.node

        port_no = sw.ports[intf]

        all_ports.append(port_no)

        if peer_node.name.startswith("g") and "_h" in peer_node.name:
            blockable_ports.append(port_no)

        elif peer_node.name.startswith("g") and "_s" in peer_node.name:
            uplink_ports.append(port_no)

    return {
        "blockable_ports": sorted(blockable_ports),
        "uplink_ports": sorted(uplink_ports),
        "all_ports": sorted(all_ports)
    }