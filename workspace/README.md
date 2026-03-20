# OP11-VIP-BYPASS-RECOVERY Workspace

This workspace contains specialized tools for the OnePlus 11 (CPH2451) recovery process.

## Setup
1. Ensure the `edl_repo` at `C:\Users\Andrew Price\Lazarus_11\edl_repo` is up to date.
2. Ensure Python 3 is installed.
3. Install workspace dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Verify the device is connected in **EDL Mode (Qualcomm HS-USB QDLoader 9008)** on `COM7`.

## Usage

### 1. Check Connection
Verify the device is detected and the Sahara handshake is functional.
```bash
python scripts/check_connection.py
```
*If connection fails, try resetting the USB:*
```bash
scripts/reset_connection.bat
```
*If device is not detected by standard tools, try low-level test:*
```bash
scripts/test_edl_hello.bat
```

### 2. Verify Firmware Files
Ensure `rawprogram0.xml` and `patch0.xml` exist and are valid.
```bash
python scripts/check_firmware_files.py
```

### 3. Run Full Unbrick
Executes the Sahara handshake, uploads the Firehose loader, and initializes the flashing process.
```bash
python scripts/ULTIMATE_UNBRICK_REAL.py
```
*Alternatively, use `scripts/run_unbrick.bat`.*

### 4. Auto-Monitor Mode
Continuously scans for the device and auto-runs unbrick when detected.
```bash
scripts/auto_monitor_edl.bat
```

## Structure
```
workspace/
├── config.py           # Central configuration: paths, COM port, Firehose args
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── payloads/           # Partition XMLs: rawprogram0.xml, patch0.xml
├── loaders/            # Place prog_firehose_ddr.elf here (copy from firmware)
└── scripts/            # Python scripts and batch files for recovery
```

## Safety
- Always backup partitions before flashing if possible.
- Ensure the battery is sufficiently charged.
- Do not disconnect the device during the flashing process.
