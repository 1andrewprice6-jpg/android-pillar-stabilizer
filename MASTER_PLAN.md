# Master Plan: OP11-VIP-BYPASS-RECOVERY

## 1. Project Discovery & Alignment

**Goals & Objectives:**
- Successfully unbrick the OnePlus 11 (CPH2451) currently stuck in EDL mode.
- Bypass the VIP security that prevents unauthorized flashing.
- Establish a repeatable and robust recovery workflow for SM8550 (Gen 2) devices.

**Scope & Constraints:**
- **In-Scope:** EDL communication, Sahara handshake, Firehose loader upload, VIP bypass, GPT reading, Partition flashing.
- **Out-of-Scope:** Rooting, custom ROM development (at this stage).
- **Constraints:** Must use the `edl_repo` at `C:\Users\Andrew Price\Lazarus_11\edl_repo`. Device is on `COM5`.

## 2. Strategy & Architecture

**Core Philosophy:** "The Midnight Watch" – Continuous readiness and precision in execution.
**Technical Stack:**
- **Language:** Python 3.x
- **Core Library:** `edlclient` (customized `edl` repo)
- **Protocols:** Sahara (v2), Firehose (QFIL/XML)

**Structural Design:**
- **Workspace:** All recovery scripts and payloads reside in `workspace/`.
- **Scripts:** Modularized Python scripts for specific tasks (e.g., GPT backup, full flash).
- **Config:** Centralized configuration at `workspace/config.py` for paths and COM ports.

## 3. Tactical Breakdown (The Work)

### Phase 1: Environment Setup & Validation (Completed)
- [x] Scaffold the workspace structure.
- [x] Locate and move the `ULTIMATE_UNBRICK_REAL.py` script.
- [x] Create `workspace/config.py` for centralized path management.
- [x] Create `check_connection.py` for quick connectivity tests.
- [x] Create `requirements.txt` and `README.md` for the workspace.
- [x] Create `run_unbrick.bat` for easy execution.
- [x] Verify firmware files (`rawprogram0.xml`, `patch0.xml`) exist and copy to `payloads/`.
- [x] Create `reset_connection.bat` and `test_edl_hello.bat` for troubleshooting.
- [x] Create `workspace/loaders/` directory for firehose loader staging.

### Phase 2: Connection & Sahara Verification
- [ ] Verify device connection on `COM5`.
- [ ] Run a Sahara hello test to confirm basic handshake.
- [ ] Attempt loader upload using `prog_firehose_ddr.elf`.

### Phase 3: Firehose & VIP Bypass
- [ ] Connect to Firehose loader.
- [ ] Confirm VIP bypass status (Oppo/OnePlus specific checks).
- [ ] Successfully read the GPT (Partition Table).

### Phase 4: Recovery & Unbrick
- [ ] Perform a full flash using `rawprogram0.xml` and `patch0.xml`.
- [ ] Verify critical partitions (A/B slots).
- [ ] Reboot device to bootloader/system.

## 4. Resource & Risk Mapping

**Resources:**
- **EDL Repo:** `C:\Users\Andrew Price\Lazarus_11\edl_repo`
- **Firmware:** `C:\Users\Andrew Price\Desktop\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip`
- **Script:** `workspace/scripts/ULTIMATE_UNBRICK_REAL.py`
- **Config:** `workspace/config.py`

**Risks:**
- **EDL Timing:** Sahara mode can be unstable or time-out.
- **VIP Security:** The bypass might fail if the loader is not correctly signed or if the protocol has changed.
- **Driver Issues:** Qualcomm HS-USB QDLoader 9008 drivers on Windows can be finicky.

## 5. Execution Roadmap

1. **Step 1:** Establish a solid configuration layer.
2. **Step 2:** Test Sahara connectivity.
3. **Step 3:** Run the full unbrick script with logging enabled.
4. **Step 4:** Document results and refine the script for future use.

**Verification:**
- Each phase is verified by successful command output (e.g., "Sahara connected," "✓ Connected to Firehose!").
- Final verification is the device successfully booting OxygenOS.
