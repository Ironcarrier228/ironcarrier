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
.
├─ core/                 # Core engine
│   ├─ config.py         # Configuration handling
│   ├─ engine.py         # Main execution logic
│   ├─ init.py           # Entry point for the CLI
│   ├─ logger.py         # Structured logging utilities
│   └─ stats.py          # Statistics collection/reporting
├─ utils/                # Utility modules
│   ├─ __init__.py
│   └─ recon/            # Reconnaissance helpers
│       ├─ __init__.py
│       ├─ port_scanner.py
│       ├─ service_detect.py
│       ├─ subnet_scanner.py
│       └─ vuln_scan.py
├─ vectors/              # Attack vector implementations
│   ├─ amplification/    # Amplification vectors
│   │   ├─ chargen_amp.py
│   │   ├─ cldap_amp.py
│   │   ├─ dns_amp.py
│   │   ├─ __init__.py
│   │   ├─ memcached_amp.py
│   │   ├─ misc_amp.py
│   │   ├─ ntp_amp.py
│   │   └─ ssdp_amp.py
│   └─ layer7/          # Layer‑7 (HTTP) vectors
│       ├─ hammer.py
│       ├─ http_bypass.py
│       ├─ http_flood.py
│       ├─ rage.py
│       ├─ slowloris.py
│       └─ slowpost.py
├─ LICENSE
└─ README.md            # (this file)
```

---

## Getting Started

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
