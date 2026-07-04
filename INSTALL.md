# Ironcarrier Installation Guide

## Prerequisites

- Python 3.9+
- Virtual environment (`venv`)

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate          # Linux/macOS
# or
venv\Scripts\activate             # Windows
```

### 2. Install Dependencies

#### Linux
```bash
pip install -r requirements.txt
```

#### Windows
```bash
pip install -r requirements.txt -r requirements-windows.txt
```

#### macOS
```bash
pip install -r requirements.txt -r requirements-macos.txt
```

## Notes

- `requirements.txt` contains universal dependencies (all platforms)
- `requirements-windows.txt` adds Windows-specific packages (`pywin32`)
- `requirements-macos.txt` adds macOS-specific packages (`py2app`)
- Linux users only need the main `requirements.txt`
- The `ipaddress` module is built-in to Python 3.3+, not needed as a package

## Troubleshooting

### "externally-managed-environment"
This is normal on systems like Arch Linux. Use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Package compilation failures
Some packages (like `cryptography`) may require build tools:
- Linux: `sudo pacman -S base-devel` (Arch) or `apt-get install build-essential` (Debian)
- macOS: `xcode-select --install`
- Windows: Install Visual Studio Build Tools

### pywin32 on non-Windows
Safely ignored if installing on Linux/macOS using separate requirements files.
