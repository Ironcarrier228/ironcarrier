# ironcarrier

## Overview

`ironcarrier` is a lightweight, modular framework for building network attack vectors and a core engine to run them. The repository is organized as a **monorepo** containing two main components:

1. **core** – The engine, configuration, logging, and statistics modules that drive vector execution.
2. **vectors** – A collection of ready‑to‑use attack vector implementations, split into two categories:
   - **amplification** – Protocol‑level amplification attacks (e.g., DNS, NTP, SSDP, Memcached, CHARGEN, CLDAP, etc.).
   - **layer7** – Application‑layer (HTTP) attacks such as slowloris, slow‑post, HTTP flood, bypass, hammer, and rage.

The project is intentionally minimal with no external build system; each Python module can be imported and used directly or executed via the `core/init.py` entry point.

---

## Project Structure

```
ironcarrier/
├── README.md
├── requirements.txt
├── ironcarrier/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── stats.py
│   ├── vectors/
│   │   ├── __init__.py
│   │   ├── layer4/
│   │   │   ├── __init__.py
│   │   │   ├── tcp_flood.py
│   │   │   ├── udp_flood.py
│   │   │   ├── syn_flood.py
│   │   │   ├── ack_flood.py
│   │   │   ├── udp_lag.py
│   │   │   └── blacknurse.py
│   │   ├── layer7/
│   │   │   ├── __init__.py
│   │   │   ├── http_flood.py
│   │   │   ├── http_bypass.py
│   │   │   ├── slowloris.py
│   │   │   ├── slowpost.py
│   │   │   ├── rage.py
│   │   │   └── hammer.py
│   │   └── amplification/
│   │       ├── __init__.py
│   │       ├── dns_amp.py
│   │       ├── ntp_amp.py
│   │       ├── memcached_amp.py
│   │       ├── ssdp_amp.py
│   │       ├── cldap_amp.py
│ │       ├── chargen_amp.py
│   │       └── misc_amp.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── recon/
│   │   │   ├── __init__.py
│   │   │   ├── port_scanner.py
│   │   │   ├── subnet_scanner.py
│   │   │   ├── service_detect.py
│   │   │   └── vuln_scan.py
│   │   ├── osint/
│   │   │   ├── __init__.py
│   │   │   ├── geolocator.py
│   │   │   ├── whois.py
│   │   ├── dns_enum.py
│   │   ├── subdomain.py
│   │   ├── shodan.py
│   │   └── hunter.py
│   │   ├── proxy/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   ├── rotator.py
│   │   │   ├── scraper.py
│   │   │   ├── socks.py
│   │   └── validator.py
│   │   ├── payload/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py
│   │   │   ├── obfuscator.py
│   │   │   ├── fragmentation.py
│   │   │   └── templates.py
│   │   └── opsec/
│   │       ├── __init__.py
│   │       ├── log_cleaner.py
│   │       ├── process_hide.py
│   │       ├── artifact_hide.py
│   │       └── traffic_noise.py
│   ├── net/
│   │   ├── __init__.py
│   │   ├── raw_socket.py
│   │   ├── tcp_stack.py
│   │   └── tunnel.py
│   ├── c2/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── protocol.py
│   │   ├── client.py
│   │   └── server.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── web/
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── api.py
│   │   │   ├── websocket.py
│   │   │   ├── templates/
|   │   │   └── index.html
│   │   │   └── static/
│   │   └── tui/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── panels.py
│   │       └── widgets.py
│   └── plugins/
│       ├── __init__.py
│       ├── api.py
│       ├── loader.py
│       └── examples/
│           ├── __init__.py
│           ├── telegram_notify.py
│           ├── discord_webhook.py
│           └── auto_schedule.py
├── configs/
│   └── default.yaml
├── reflectors/
├── wordlists/
├── logs/
└── tests/

---

## Getting Started

## Security Notice

This repository contains **offensive network‑attack vectors** (e.g., DNS amplification, HTTP slow‑loris, TCP/UDP flood scripts). These tools are provided **solely for research, education, and authorized penetration‑testing**.

- Do **not** run any vector against systems you do not have explicit permission to test.
- Misuse may be illegal in many jurisdictions and can cause service disruption.
- The authors assume no liability for any damage caused by misuse of these scripts.

By using this code you agree to comply with all applicable laws and obtain proper authorization before any testing.



### Prerequisites

- Python 3.9+ (the code uses type hints and f‑strings).
- No additional third‑party dependencies; the core modules rely only on the Python standard library.

### Installation

Clone the repository and install the package in editable mode if you want to develop against it:

```bash
git clone https://github.com/ironcarrier/ironcarrier.git
cd ironcarrier
pip install -e .  # optional – creates an editable install
```

> **Note**: The repository does not contain a `setup.py` or `pyproject.toml`. For simple usage you can add the repository root to `PYTHONPATH`:
>
> ```bash
> export PYTHONPATH=$(pwd):$PYTHONPATH
> ```

### Running a Vector

Each vector can be imported and executed via the core engine. Below is an example of running the DNS amplification vector:

```python
from core.engine import Engine
from vectors.amplification.dns_amp import DNSAmplificationVector

engine = Engine()
engine.add_vector(DNSAmplificationVector())
engine.run()
```

Replace `DNSAmplificationVector` with any other vector class from `vectors/amplification` or `vectors/layer7`.

---

## Core Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Loads and validates configuration files (JSON/YAML). |
| `engine.py` | Orchestrates vector execution, concurrency, and result collection. |
| `init.py` | Provides a simple CLI (`python -m core.init`) for quick tests. |
| `logger.py` | Centralised, JSON‑line logging with timestamps and severity levels. |
| `stats.py` | Aggregates packet/response statistics for reporting.

---

## Adding New Vectors

1. Create a new Python file under the appropriate sub‑directory (`amplification` or `layer7`).
2. Subclass `core.engine.BaseVector` (or follow the pattern of existing vectors) and implement the required `run(self, target)` method.
3. Register the vector in `vectors/<category>/__init__.py` if you want it automatically discoverable.
4. Update any documentation and optionally add unit tests under a `tests/` folder.

---

## License

This project is licensed under the terms of the **GNU AGPL v3 License** – see the `LICENSE` file for details.

---

## Contributing

Contributions are not welcome! Please do not open an issue or pull request with a clear description of the change. Follow for any new public changes  or functions.
