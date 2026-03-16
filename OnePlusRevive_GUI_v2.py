#!/usr/bin/env python3
"""
OnePlus 11 (CPH2451) Recovery Tool - GUI v2 with Auto Firehose Detection
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
import hashlib
import serial.tools.list_ports

class OnePlusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnePlus 11 (CPH2451) Recovery Tool v2")
        self.root.geometry("1000x800")
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
        self.firehose_file = tk.StringVar(value="Not found")
        self.firehose_info = tk.StringVar(value="")

        self.firehose_path = None
        self.prog_files = []
        self.patch_files = []

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
        style.configure('Firehose.TLabel', background="#1e1e1e", foreground="#ff6b35",
                       font=("Arial", 10, "bold"))

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=10)

        header_label = ttk.Label(header_frame, text="OnePlus 11 (CPH2451) Recovery Tool v2",
                                style='Header.TLabel')
        header_label.pack()

        firmware_label = ttk.Label(header_frame, text="Firmware: 15.0.0.600 NA EX01 | Auto Firehose Detection",
                                  foreground="#888888")
        firmware_label.pack()

        # Device Status
        status_frame = ttk.LabelFrame(main_frame, text="Device Status", padding=10)
        status_frame.pack(fill=tk.X, pady=10)

        status_label = ttk.Label(status_frame, textvariable=self.device_status,
                                style='Status.TLabel')
        status_label.pack()

        detect_btn = ttk.Button(status_frame, text="Detect Device",
                               command=self.detect_device)
        detect_btn.pack(pady=5)

        # Firehose Detection
        firehose_frame = ttk.LabelFrame(main_frame, text="Firehose Programmer (Auto-Detected)", padding=10)
        firehose_frame.pack(fill=tk.X, pady=10)

        fh_label = ttk.Label(firehose_frame, text="Status:")
        fh_label.pack(side=tk.LEFT, padx=5)

        fh_value = ttk.Label(firehose_frame, textvariable=self.firehose_file,
                            style='Firehose.TLabel')
        fh_value.pack(side=tk.LEFT, padx=5)

        fh_info = ttk.Label(firehose_frame, textvariable=self.firehose_info,
                           foreground="#aaaaaa")
        fh_info.pack(side=tk.LEFT, padx=5)

        # Loader Path
        loader_frame = ttk.LabelFrame(main_frame, text="Loader Files", padding=10)
        loader_frame.pack(fill=tk.X, pady=10)

        loader_entry = ttk.Entry(loader_frame, textvariable=self.loader_path, width=70)
        loader_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        loader_btn = ttk.Button(loader_frame, text="Browse...", command=self.browse_loaders)
        loader_btn.pack(side=tk.LEFT, padx=5)

        # Firmware Path
        firmware_frame = ttk.LabelFrame(main_frame, text="Firmware Files", padding=10)
        firmware_frame.pack(fill=tk.X, pady=10)

        firmware_entry = ttk.Entry(firmware_frame, textvariable=self.firmware_path, width=70)
        firmware_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        firmware_btn = ttk.Button(firmware_frame, text="Browse...", command=self.browse_firmware)
        firmware_btn.pack(side=tk.LEFT, padx=5)

        # Recovery Button
        recovery_btn = ttk.Button(main_frame, text="START RECOVERY",
                                 command=self.start_recovery)
        recovery_btn.pack(fill=tk.X, pady=20)

        # Output Log
        log_frame = ttk.LabelFrame(main_frame, text="Operation Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.output_text = scrolledtext.ScrolledText(log_frame, height=18,
                                                     bg="#0a0a0a", fg="#00ff88",
                                                     font=("Courier", 9),
                                                     state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        self.output_text.tag_config("success", foreground="#00ff88")
        self.output_text.tag_config("error", foreground="#ff4444")
        self.output_text.tag_config("warning", foreground="#ffaa00")
        self.output_text.tag_config("info", foreground="#00d9ff")

        self.log("OnePlus 11 Recovery Tool v2 initialized")
        self.log(f"Target: {self.device_info['model']} - {self.device_info['firmware']} {self.device_info['region']}")
        self.log("Ready for auto-detection of firehose and loader files")

    def _find_edl_port(self):
        """Auto-detect Qualcomm EDL device (VID=05C6, PID=9008), fallback COM5."""
        for port in serial.tools.list_ports.comports():
            if port.vid == 0x05C6 and port.pid == 0x9008:
                return port.device.replace("\\\\.\\", "")
        return "COM5"

    def find_firehose(self, loader_dir):
        """Find and validate firehose file"""
        self.log("Searching for firehose programmer...", "info")

        try:
            loader_path = Path(loader_dir)
            if not loader_path.exists():
                self.log("Loader directory not found!", "error")
                return False

            # Search for fhprg.bin (firehose)
            firehose_files = list(loader_path.glob("**/fhprg.bin")) + \
                            list(loader_path.glob("**/fhprg*.bin")) + \
                            list(loader_path.glob("*fhprg*"))

            if not firehose_files:
                self.log("Firehose file not found (fhprg.bin)", "error")
                self.firehose_file.set("NOT FOUND")
                return False

            # Use first found firehose
            self.firehose_path = firehose_files[0]
            filename = self.firehose_path.name
            filesize = self.firehose_path.stat().st_size / (1024 * 1024)  # MB

            # Calculate MD5 hash
            md5_hash = self.calculate_md5(str(self.firehose_path))
            short_hash = md5_hash[:8].upper()

            self.log(f"✓ Firehose found: {filename}", "success")
            self.log(f"  Size: {filesize:.2f} MB", "info")
            self.log(f"  Hash: {short_hash}...", "info")

            self.firehose_file.set(f"✓ {filename}")
            self.firehose_info.set(f"({filesize:.1f}MB | {short_hash}...)")

            return True

        except Exception as e:
            self.log(f"Error searching for firehose: {str(e)}", "error")
            return False

    def find_loader_files(self, loader_dir):
        """Find prog and patch files"""
        self.log("Searching for loader files...", "info")

        try:
            loader_path = Path(loader_dir)

            # Find prog files
            self.prog_files = list(loader_path.glob("**/rawprogram*.xml")) + \
                             list(loader_path.glob("**/prog*.xml"))

            # Find patch files
            self.patch_files = list(loader_path.glob("**/patch*.xml"))

            self.log(f"Found {len(self.prog_files)} prog file(s)", "success")
            self.log(f"Found {len(self.patch_files)} patch file(s)", "success")

            if self.prog_files:
                for prog in self.prog_files:
                    self.log(f"  • {prog.name}", "info")

            if self.patch_files:
                for patch in self.patch_files:
                    self.log(f"  • {patch.name}", "info")

            return len(self.prog_files) > 0

        except Exception as e:
            self.log(f"Error searching for loader files: {str(e)}", "error")
            return False

    def calculate_md5(self, filepath):
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def detect_device(self):
        self.log("Detecting device in EDL mode...", "info")

        def detect():
            try:
                edl_script = r"C:\Users\Andrew Price\edl\edl.py"
                com_port = self._find_edl_port()
                result = subprocess.run([sys.executable, edl_script, "--serial", f"--portname=\\\\.\\{com_port}"], capture_output=True, text=True, timeout=5)
                if "Mode detected" in result.stdout.lower() or "sahara" in result.stdout.lower() or result.returncode == 0:
                    self.device_status.set("✓ DETECTED")
                    self.log(f"Device found on {com_port}!", "success")
                else:
                    self.device_status.set("✗ NOT DETECTED")
                    self.log(f"Device not found on {com_port}. Check connection.", "warning")
            except FileNotFoundError:
                self.device_status.set("✗ EDL NOT INSTALLED")
                self.log("edl tool not found. Install with: pip install edl", "error")
            except subprocess.TimeoutExpired:
                self.device_status.set("✗ TIMEOUT")
                self.log("Device detection timed out.", "error")

        thread = threading.Thread(target=detect, daemon=True)
        thread.start()

    def browse_loaders(self):
        path = filedialog.askdirectory(title="Select Loader Files Directory")
        if path:
            self.loader_path.set(path)
            self.log(f"Loader directory: {path}", "info")

            # Auto-detect firehose and loader files
            thread = threading.Thread(target=lambda: [
                self.find_firehose(path),
                self.find_loader_files(path)
            ], daemon=True)
            thread.start()

    def browse_firmware(self):
        path = filedialog.askdirectory(title="Select Firmware Files Directory")
        if path:
            self.firmware_path.set(path)
            self.log(f"Firmware directory: {path}", "info")

    def start_recovery(self):
        if self.device_status.get() != "✓ DETECTED":
            messagebox.showerror("Error", "Device not detected. Click 'Detect Device' first.")
            return

        if not self.firehose_path:
            messagebox.showerror("Error", "Firehose file not found. Select a valid loader directory.")
            return

        if not self.loader_path.get():
            messagebox.showerror("Error", "Please select a loader directory")
            return

        if not self.firmware_path.get():
            messagebox.showerror("Error", "Please select a firmware directory")
            return

        response = messagebox.askyesno("Confirm Recovery",
            "WARNING\n\n"
            f"Firehose: {self.firehose_path.name}\n"
            f"Prog files: {len(self.prog_files)}\n"
            f"Patch files: {len(self.patch_files)}\n\n"
            "This will erase device data and flash firmware.\n"
            "Do NOT disconnect device during flashing.\n\nContinue?")

        if not response:
            return

        self.log("", "info")
        self.log("="*70, "info")
        self.log("STARTING RECOVERY PROCESS", "success")
        self.log("="*70, "info")

        def recovery():
            try:
                self.log(f"Firehose: {self.firehose_path.name}", "info")
                self.log(f"Prog files: {len(self.prog_files)}", "info")
                self.log(f"Patch files: {len(self.patch_files)}", "info")
                self.log("", "info")
                self.log("[FLASHING] Starting REAL firmware flash...", "info")
                self.log("[PROGRESS] This will take 5-15 minutes", "warning")
                self.log("[CRITICAL] DO NOT DISCONNECT DEVICE", "warning")

                # Construct the real EDL command
                edl_script = r"C:\Users\Andrew Price\edl\edl.py"
                com_port = self._find_edl_port()

                # Get paths
                raw_xml = self.prog_files[0] # Usually rawprogram0.xml
                patch_xml = self.patch_files[0] # Usually patch0.xml
                firmware_dir = self.firmware_path.get()
                loader_file = self.firehose_path

                cmd = [
                    sys.executable,
                    edl_script,
                    "qfil",
                    str(raw_xml),
                    str(patch_xml),
                    str(firmware_dir),
                    f"--loader={str(loader_file)}",
                    "--memory=ufs",
                    "--serial",
                    f"--portname=\\\\.\\{com_port}",
                    "--debugmode"
                ]
                
                self.log(f"Running command: {' '.join(cmd)}", "info")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                for line in process.stdout:
                    self.log(line.strip(), "info")
                    
                process.wait()

                if process.returncode == 0:
                    self.log("", "info")
                    self.log("🎉 FIRMWARE FLASHING COMPLETE", "success")
                    messagebox.showinfo("Success", "Resurrection complete! Device will reboot.")
                else:
                    self.log(f"✗ FLASHING FAILED (Code: {process.returncode})", "error")
                    messagebox.showerror("Error", "Flashing failed. Check logs.")

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
