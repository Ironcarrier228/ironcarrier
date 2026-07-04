#!/usr/bin/env python3
"""
Ironcarrier CLI Entry Point
"""

import os
import sys

def list_vectors(args):
    """List available attack vectors"""
    vectors = {
        'Layer 4': [
            'tcp_flood',
            'udp_flood',
            'syn_flood',
            'ack_flood',
            'udp_lag',
            'blacknurse',
        ],
        'Layer 7': [
            'http_flood',
            'http_bypass',
            'slowloris',
            'slowpost',
            'rage',
            'hammer',
        ],
        'Amplification': [
            'dns_amp',
            'ntp_amp',
            'memcached_amp',
            'ssdp_amp',
            'cldap_amp',
            'chargen_amp',
            'misc_amp',
        ]
    }
    
    for category, items in vectors.items():
        print(f"\n  [{category}]")
        for name in items:
            print(f"    {name}")
    print()
    return 0

def run_attack(args):
    """Run attack with specified vector"""
    print(f"[*] Starting {args.method} attack on {args.target}:{args.port}")
    print(f"[*] Duration: {args.duration}s, Threads: {args.threads}")
    # TODO: Implement actual attack logic
    return 0

def run_utils(args):
    """Run utility modules"""
    print(f"[*] Running utility: {' '.join(args.utils)}")
    # TODO: Implement utility logic
    return 0

def run_c2_server(args):
    """Start C2 server"""
    print(f"[*] Starting C2 server on {args.bind}:{args.port}")
    # TODO: Implement C2 server
    return 0

def run_c2_client(args):
    """Start C2 client agent"""
    print(f"[*] Connecting to C2 server...")
    # TODO: Implement C2 client
    return 0

def run_gui(args):
    """Start web GUI"""
    print(f"[*] Starting web GUI on {args.host}:{args.port}")
    # TODO: Implement GUI
    return 0

def run_tui(args):
    """Start terminal UI"""
    print("[*] Starting terminal UI...")
    # TODO: Implement TUI
    return 0

def main():
    """Main CLI entry point"""
    if os.geteuid() != 0:
        print("[-] Root privileges required for raw socket operations")
        sys.exit(1)
    
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='ironcarrier',
        description='IronCarrier - Multi-Vector Stress Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available vectors
  ironcarrier --list-vectors
  
  # TCP flood
  ironcarrier -m tcp_flood -t 1.2.3.4 -p 80 -d 120 -T 200
  
  # UDP flood with custom size
  ironcarrier -m udp_flood -t 1.2.3.4 -p 53 -d 300 --size 4096
  
  # SYN flood high thread count
  ironcarrier -m syn_flood -t 1.2.3.4 -p 443 -d 60 -T 1000
  
  # HTTP flood with SSL
  ironcarrier -m http_flood -t example.com -p 443 -d 60 --ssl --path /api/v1/
  
  # Slowloris with max connections
  ironcarrier -m slowloris -t example.com -p 80 -d 300 -T 500 --max-conn 1000
  
  # DNS amplification with reflector list
  ironcarrier -m dns_amp -t 1.2.3.4 -p 80 -d 60 -r reflectors/dns/global.txt
  
  # Use custom config
  ironcarrier -c configs/stealth.yaml -m syn_flood -t 1.2.3.4 -p 443 -d 60
  
  # Run as C2 server
  ironcarrier --c2-server --bind 0.0.0.0 --port 8443
  
  # Run as C2 agent
  ironcarrier --c2-client --server 1.2.3.4 --port 8443
  
  # Start web GUI
  ironcarrier --gui --host 0.0.0.0 --port 5000
  
  # Start TUI
  ironcarrier --tui
  
  # Run utility modules
  ironcarrier.utils scan -t 192.168.1.1 --ports 1-1000
  ironcarrier.utils brute -t example.com
  ironcarrier.utils geo -t 8.8.8.8
  ironcarrier.utils proxy -f proxies.txt -o working.txt
""")
    
    # Core options
    parser.add_argument('--list-vectors', action='store_true', help='List available attack vectors')
    parser.add_argument('-c', '--config', help='Path to config file')
    
    # Attack arguments
    parser.add_argument('-m', '--method', help='Attack vector name')
    parser.add_argument('-t', '--target', help='Target IP or hostname')
    parser.add_argument('-p', '--port', type=int, help='Target port')
    parser.add_argument('-d', '--duration', type=int, default=60, help='Duration in seconds')
    parser.add_argument('-T', '--threads', type=int, default=100, help='Thread count')
    
    # Vector-specific arguments
    parser.add_argument('--size', type=int, default=1024, help='Packet size (UDP)')
    parser.add_argument('--ssl', action='store_true', help='Use SSL/TLS')
    parser.add_argument('--path', default='/', help='URL path (HTTP)')
    parser.add_argument('--max-conn', type=int, default=500, help='Max connections (Slowloris)')
    parser.add_argument('--cache-bust', action='store_true', default=True, help='Add cache buster')
    parser.add_argument('--reflector', help='Reflector list file')
    parser.add_argument('--query-type', default='ANY', choices=['ANY', 'TXT', 'DNSKEY'], help='DNS query type')
    parser.add_argument('--amp-port', type=int, default=53, help='Amplification reflector port')
    parser.add_argument('--amp-type', default='dns', choices=['dns', 'ntp', 'memcached', 'ssdp', 'cldap', 'chargen', 'misc'], help='Amplification type')
    parser.add_argument('--http-method', default='GET', choices=['GET', 'POST', 'HEAD', 'OPTIONS'], help='HTTP method')
    parser.add_argument('--min-delay', type=float, default=0.01, help='Min delay (UDP Lag)')
    parser.add_argument('--max-delay', type=float, default=0.1, help='Max delay (UDP Lag)')
    parser.add_argument('--headers-per-interval', type=int, default=5, help='Headers per interval (Slowloris)')
    parser.add_argument('--interval', type=int, default=15, help='Interval between sends (Slowloris)')
    parser.add_argument('--ttl', type=int, default=64, help='TTL value')
    parser.add_argument('--payload-size', type=int, default=0, help='Payload size (TCP)')
    parser.add_argument('--flags', nargs='+', default=['SYN', 'ACK', 'PSH+ACK'], help='TCP flags')
    
    # Utility module
    parser.add_argument('--utils', nargs='+', help='Run utility module: module.function [args]')
    
    # C2 server options
    parser.add_argument('--c2-server', action='store_true', help='Start C2 server')
    parser.add_argument('--c2-client', action='store_true', help='Run C2 agent')
    parser.add_argument('--bind', default='0.0.0.0', help='C2 bind address')
    parser.add_argument('--server', help='C2 server address (for client)')
    parser.add_argument('--ssl-cert', help='SSL certificate path (C2 server)')
    parser.add_argument('--ssl-key', help='SSL key path (C2 server)')
    parser.add_argument('--password', help='C2 auth password')
    
    # C2 client options
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL for C2 client')
    parser.add_argument('--reconnect', type=float, default=30.0, help='Reconnect interval (C2 client)')
    parser.add_argument('--heartbeat', type=float, default=60.0, help='Heartbeat interval')
    parser.add_argument('--jitter', type=float, default=10.0, help='Max jitter (C2 client)')
    parser.add_argument('--kill-date', type=int, default=0, help='Self-destruct after N days (C2 client)')
    
    # GUI options
    parser.add_argument('--gui', action='store_true', help='Start web GUI')
    parser.add_argument('--host', default='0.0.0.0', help='GUI bind address')
    parser.add_argument('--debug', action='store_true', help='Debug mode (Flask)')
    
    # TUI options
    parser.add_argument('--tui', action='store_true', help='Start terminal UI')
    
    args = parser.parse_args()
    
    # Route to appropriate handler
    if args.list_vectors:
        return list_vectors(args)
    elif args.utils:
        return run_utils(args)
    elif args.c2_server:
        return run_c2_server(args)
    elif args.c2_client:
        return run_c2_client(args)
    elif args.gui:
        return run_gui(args)
    elif args.tui:
        return run_tui(args)
    elif args.method and args.target:
        return run_attack(args)
    else:
        parser.print_help()
        return 0

if __name__ == '__main__':
    sys.exit(main())
