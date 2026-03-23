#!/usr/bin/env python3
"""
OnePlus 11 (CPH2451) Recovery Tool - GUI Version
Firmware: 15.0.0.600 NA EX01
"""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import logging
from pathlib import Path
import time

try:
    import serial.tools.list_ports
except ImportError:
    serial = None

EDL_SCRIPT = Path.home() / "edl" / "edl.py"
PLATFORM_TOOLS = Path.home() / "platform-tools"

class OnePlusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnePlus 11 (CPH2451) Recovery Tool")
        self.root.geometry("900x700")
        self.root.configure(bg="#1e1e1e")

        self.device_info = {
            "model": "CPH2451",
            "chipset": "SM8550",
            "firmware": "15.0.0.600",
            "region": "NA",
            "variant": "EX01"
        }

        self.loader_path = tk.StringVar()
        self.firmware_path = tk.StringVar()
        self.device_status = tk.StringVar(value="NOT DETECTED")

        self.setup_ui()
        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def log(self, message, level="info"):
        self.output_text.config(state=tk.NORMAL)

        if level == "success":
            self.output_text.insert(tk.END, f"[SUCCESS] {message}\n", "success")
        elif level == "error":
            self.output_text.insert(tk.END, f"[ERROR] {message}\n", "error")
        elif level == "warning":
            self.output_text.insert(tk.END, f"[WARNING] {message}\n", "warning")
        else:
            self.output_text.insert(tk.END, f"[INFO] {message}\n", "info")

        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.root.update()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background="#1e1e1e")
        style.configure('TLabel', background="#1e1e1e", foreground="#ffffff")
        style.configure('TButton', background="#0d47a1")
        style.configure('Header.TLabel', background="#1e1e1e", foreground="#00d9ff",
                       font=("Arial", 14, "bold"))
        style.configure('Status.TLabel', background="#1e1e1e", foreground="#00ff88",
                       font=("Arial", 10, "bold"))

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=10)

        header_label = ttk.Label(header_frame, text="OnePlus 11 (CPH2451) Recovery Tool",
                                style='Header.TLabel')
        header_label.pack()

        firmware_label = ttk.Label(header_frame, text="Firmware: 15.0.0.600 NA EX01",
                                  foreground="#888888")
        firmware_label.pack()

        status_frame = ttk.LabelFrame(main_frame, text="Device Status", padding=10)
        status_frame.pack(fill=tk.X, pady=10)

        status_label = ttk.Label(status_frame, textvariable=self.device_status,
                                style='Status.TLabel')
        status_label.pack()

        detect_btn = ttk.Button(status_frame, text="Detect Device",
                               command=self.detect_device)
        detect_btn.pack(pady=5)

        loader_frame = ttk.LabelFrame(main_frame, text="Loader Files", padding=10)
        loader_frame.pack(fill=tk.X, pady=10)

        loader_entry = ttk.Entry(loader_frame, textvariable=self.loader_path, width=60)
        loader_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        loader_btn = ttk.Button(loader_frame, text="Browse...", command=self.browse_loaders)
        loader_btn.pack(side=tk.LEFT, padx=5)

        list_btn = ttk.Button(loader_frame, text="List Loaders", command=self.list_loaders)
        list_btn.pack(side=tk.LEFT, padx=5)

        firmware_frame = ttk.LabelFrame(main_frame, text="Firmware Files", padding=10)
        firmware_frame.pack(fill=tk.X, pady=10)

        firmware_entry = ttk.Entry(firmware_frame, textvariable=self.firmware_path, width=60)
        firmware_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        firmware_btn = ttk.Button(firmware_frame, text="Browse...", command=self.browse_firmware)
        firmware_btn.pack(side=tk.LEFT, padx=5)

        recovery_btn = ttk.Button(main_frame, text="START RECOVERY", command=self.start_recovery)
        recovery_btn.pack(fill=tk.X, pady=20)

        log_frame = ttk.LabelFrame(main_frame, text="Operation Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.output_text = scrolledtext.ScrolledText(log_frame, height=15,
                                                     bg="#0a0a0a", fg="#00ff88",
                                                     font=("Courier", 9),
                                                     state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        self.output_text.tag_config("success", foreground="#00ff88")
        self.output_text.tag_config("error", foreground="#ff4444")
        self.output_text.tag_config("warning", foreground="#ffaa00")
        self.output_text.tag_config("info", foreground="#00d9ff")

        instructions = ("INSTRUCTIONS:\n"
                       "1. Put device in EDL mode: Power OFF > Hold Volume Down > Connect USB\n"
                       "2. Click 'Detect Device' to verify connection\n"
                       "3. Select Loader files directory (contains .bin and .xml files)\n"
                       "4. Select Firmware directory\n"
                       "5. Click 'START RECOVERY' and wait for completion\n"
                       "WARNING: DO NOT DISCONNECT DEVICE DURING FLASHING")

        instr_frame = ttk.LabelFrame(main_frame, text="Instructions", padding=10)
        instr_frame.pack(fill=tk.X, pady=10)

        instr_label = ttk.Label(instr_frame, text=instructions,
                               justify=tk.LEFT, foreground="#888888")
        instr_label.pack()

        self.log("OnePlus 11 Recovery Tool initialized")
        self.log(f"Target: {self.device_info['model']} - {self.device_info['firmware']} {self.device_info['region']}")

    def _find_edl_port(self):
        """Auto-detect EDL device via COM port"""
        if serial is None:
            return None
        for port in serial.tools.list_ports.comports():
            if port.vid == 0x05C6 and port.pid == 0x9008:
                return port.device
        return None

    def detect_device(self):
        self.log("Detecting device in EDL mode...", "info")

        def detect():
            # Check COM port first
            com_port = self._find_edl_port()
            if com_port:
                self.log(f"EDL device found on {com_port}", "info")

            try:
                if not EDL_SCRIPT.exists():
                    self.device_status.set("✗ EDL NOT FOUND")
                    self.log(f"EDL tool not found at {EDL_SCRIPT}", "error")
                    return

                result = subprocess.run(
                    [sys.executable, str(EDL_SCRIPT), "printgpt", "--memory=ufs"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    self.device_status.set("✓ DETECTED")
                    self.log("Device found in EDL mode!", "success")
                else:
                    self.device_status.set("✗ NOT DETECTED")
                    self.log("Device not found. Put device in EDL mode and try again.", "warning")
            except subprocess.TimeoutExpired:
                self.device_status.set("✗ TIMEOUT")
                self.log("Device detection timed out.", "error")
            except Exception as e:
                self.device_status.set("✗ ERROR")
                self.log(f"Detection error: {e}", "error")

        thread = threading.Thread(target=detect, daemon=True)
        thread.start()

    def browse_loaders(self):
        path = filedialog.askdirectory(title="Select Loader Files Directory")
        if path:
            self.loader_path.set(path)
            self.log(f"Loader path set to: {path}", "info")

    def browse_firmware(self):
        path = filedialog.askdirectory(title="Select Firmware Files Directory")
        if path:
            self.firmware_path.set(path)
            self.log(f"Firmware path set to: {path}", "info")

    def list_loaders(self):
        if not self.loader_path.get():
            messagebox.showwarning("Warning", "Please select a loader directory first")
            return

        self.log("Searching for SM8550 loaders...", "info")

        def search():
            try:
                loader_dir = Path(self.loader_path.get())
                if not loader_dir.exists():
                    self.log("Loader directory not found!", "error")
                    return

                extensions = ["*.bin", "*.elf", "*.mbn", "*.xml"]
                loaders = []

                for ext in extensions:
                    matches = list(loader_dir.glob(f"**/{ext}"))
                    for match in matches:
                        if "8550" in str(match) or "CPH2451" in str(match):
                            loaders.append(str(match))

                if loaders:
                    self.log(f"Found {len(loaders)} loader files:", "success")
                    for loader in loaders:
                        self.log(f"  • {Path(loader).name}", "info")
                else:
                    self.log("No SM8550 loaders found in directory", "warning")
            except Exception as e:
                self.log(f"Error searching loaders: {str(e)}", "error")

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def start_recovery(self):
        if self.device_status.get() != "✓ DETECTED":
            messagebox.showerror("Error", "Device not detected. Click Detect Device first.")
            return

        if not self.loader_path.get():
            messagebox.showerror("Error", "Please select a loader directory")
            return

        if not self.firmware_path.get():
            messagebox.showerror("Error", "Please select a firmware directory")
            return

        response = messagebox.askyesno("Confirm Recovery",
            "WARNING\n\nThis will erase device data and flash firmware.\n"
            "Do NOT disconnect device during flashing.\n\nContinue?")

        if not response:
            return

        self.log("", "info")
        self.log("="*60, "info")
        self.log("STARTING RECOVERY PROCESS", "success")
        self.log("="*60, "info")

        def recovery():
            try:
                self.log("Validating loaders...", "info")
                loader_dir = Path(self.loader_path.get())
                firmware_dir = Path(self.firmware_path.get())

                # Find firehose loader
                loader_file = None
                for name in ["prog_firehose_ddr.elf", "prog_emmc_firehose.elf"]:
                    candidate = loader_dir / name
                    if candidate.exists():
                        loader_file = candidate
                        break
                if not loader_file:
                    elfs = list(loader_dir.glob("*.elf")) + list(loader_dir.glob("*.mbn"))
                    if elfs:
                        loader_file = elfs[0]

                if not loader_file:
                    self.log("No firehose loader (.elf/.mbn) found!", "error")
                    return

                # Find rawprogram XML
                rawprogram = firmware_dir / "rawprogram0.xml"
                if not rawprogram.exists():
                    xmls = list(firmware_dir.glob("rawprogram*.xml"))
                    if xmls:
                        rawprogram = xmls[0]
                    else:
                        self.log("No rawprogram XML found in firmware dir!", "error")
                        return

                self.log(f"Loader: {loader_file.name}", "success")
                self.log(f"XML: {rawprogram.name}", "success")
                self.log("", "info")
                self.log("[FLASHING] Starting firmware flash via EDL...", "info")
                self.log("[CRITICAL] DO NOT DISCONNECT DEVICE", "warning")

                cmd = [
                    sys.executable, str(EDL_SCRIPT),
                    "xml", str(rawprogram),
                    "--loader", str(loader_file),
                    "--memory=ufs"
                ]
                self.log(f"CMD: {' '.join(cmd)}", "info")

                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )

                for line in process.stdout:
                    self.log(line.strip(), "info")

                process.wait()

                self.log("", "info")
                if process.returncode == 0:
                    self.log("✓ FIRMWARE FLASHING COMPLETE", "success")
                    self.log("Device will reboot automatically", "info")
                    self.log("Recovery complete!", "success")
                    self.log("=" * 60, "success")
                    messagebox.showinfo("Success", "Recovery complete!\nDevice will reboot shortly.")
                else:
                    self.log(f"✗ Flash failed with exit code {process.returncode}", "error")
                    messagebox.showerror("Error", "Flash failed. Check the log for details.")

            except Exception as e:
                self.log(f"Recovery failed: {str(e)}", "error")
                messagebox.showerror("Error", f"Recovery failed: {str(e)}")

        thread = threading.Thread(target=recovery, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    gui = OnePlusGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
