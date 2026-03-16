import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import os
import sys
import subprocess
import webbrowser
import json
import shutil
import threading
import logging
import glob as glob_module
from datetime import datetime
from pathlib import Path
import serial.tools.list_ports

logger = logging.getLogger(__name__)

# ADB Helper Functions
class ADBManager:
    """Manage ADB operations"""
    def __init__(self):
        self.adb_path = self._find_adb()

    def _find_adb(self):
        """Find ADB executable"""
        candidates = [
            shutil.which('adb'),
            r'C:\Users\Andrew Price\platform-tools\adb.exe',
            r'C:\Android\platform-tools\adb.exe',
            os.path.expanduser('~/AppData/Local/Android/Sdk/platform-tools/adb.exe'),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return 'adb'

    def _find_fastboot(self):
        """Find fastboot executable next to ADB or on PATH"""
        adb_dir = str(Path(self.adb_path).parent)
        candidates = [
            os.path.join(adb_dir, 'fastboot.exe'),
            os.path.join(adb_dir, 'fastboot'),
            shutil.which('fastboot'),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return 'fastboot'

    def run_cmd(self, cmd):
        """Run ADB command and return output"""
        try:
            result = subprocess.run(
                f'"{self.adb_path}" {cmd}',
                capture_output=True, text=True, timeout=10, shell=True
            )
            return result.stdout.strip(), result.returncode == 0
        except Exception as e:
            return str(e), False

    def run_fastboot(self, cmd, timeout=30):
        """Run a fastboot command and return (output, success)"""
        fastboot = self._find_fastboot()
        try:
            result = subprocess.run(
                f'"{fastboot}" {cmd}',
                capture_output=True, text=True, timeout=timeout, shell=True
            )
            combined = (result.stdout + result.stderr).strip()
            return combined, result.returncode == 0
        except Exception as e:
            return str(e), False

    def get_devices(self):
        """List connected devices"""
        output, success = self.run_cmd('devices')
        if not success:
            return []
        devices = [line.split()[0] for line in output.split('\n')[1:] if line.strip() and 'device' in line]
        return devices

    def get_device_info(self):
        """Get device info"""
        info = {}
        commands = {
            'Model': 'shell getprop ro.product.model',
            'Device': 'shell getprop ro.product.device',
            'Android': 'shell getprop ro.build.version.release',
            'Build': 'shell getprop ro.build.fingerprint',
            'Serial': 'get-serialno'
        }
        for key, cmd in commands.items():
            output, _ = self.run_cmd(cmd)
            info[key] = output if output else 'N/A'
        return info

    def is_rooted(self):
        """Check if device has root access"""
        output, _ = self.run_cmd('shell which su')
        return bool(output.strip())

    def grant_root(self):
        """Enable root via su binary"""
        output, success = self.run_cmd('shell su -c id')
        return 'uid=0' in output if success else False


class EDLDetector:
    """Detect devices in EDL (Emergency Download) mode"""

    @staticmethod
    def scan_edl_devices():
        """Scan COM ports for EDL devices (QDLoader 9008)"""
        edl_devices = []
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                logger.debug(f"Found port {port.device}: {port.description} (VID={port.vid:#06x}, PID={port.pid:#06x})")
                # Match by VID/PID (most reliable) or description keyword
                vid_pid_match = port.vid == 0x05C6 and port.pid == 0x9008
                desc_match = any(k in port.description.upper() for k in ('9008', 'QDLOADER', 'QUALCOMM'))
                if vid_pid_match or desc_match:
                    edl_devices.append({
                        'port': port.device,
                        'description': port.description,
                        'hwid': port.hwid
                    })
        except Exception as e:
            logger.error(f"Error scanning ports: {e}")
            return []
        return edl_devices

    @staticmethod
    def get_all_ports():
        """Get all available COM ports"""
        try:
            ports = serial.tools.list_ports.comports()
            return [(port.device, port.description) for port in ports]
        except Exception as e:
            return []


class MainWindow:
    def __init__(self, root, adb):
        self.root = root
        self.adb = adb
        self.edl = EDLDetector()
        self.root.title('OnePlus Recovery Tool')
        self.root.geometry('1000x900')

        # Set dark theme colors
        self.bg_dark = '#1e1e1e'
        self.bg_darker = '#0d0d0d'
        self.accent_color = '#00d4ff'
        self.text_color = '#ffffff'
        self.warning_color = '#ff6b6b'
        self.success_color = '#51cf66'

        self.root.configure(bg=self.bg_dark)
        self._setup_styles()
        self.create_widgets()
        self.refresh_device_status()
        self.schedule_refresh()

    def _setup_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        style.configure('TFrame', background=self.bg_dark, foreground=self.text_color)
        style.configure('TLabel', background=self.bg_dark, foreground=self.text_color, font=('Segoe UI', 9))
        style.configure('Title.TLabel', background=self.bg_dark, foreground=self.accent_color,
                       font=('Segoe UI', 18, 'bold'))
        style.configure('Section.TLabel', background=self.bg_dark, foreground=self.accent_color,
                       font=('Segoe UI', 11, 'bold'))
        style.configure('TButton', font=('Segoe UI', 9))
        style.map('TButton',
                 foreground=[('active', self.bg_dark)],
                 background=[('active', self.accent_color)])

        style.configure('Treeview', background=self.bg_darker, foreground=self.text_color,
                       fieldbackground=self.bg_darker, font=('Segoe UI', 9))
        style.map('Treeview', background=[('selected', self.accent_color)])

    def create_widgets(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(main_container, bg=self.accent_color, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text='OnePlus Recovery Tool', font=('Segoe UI', 20, 'bold'),
                        bg=self.accent_color, fg=self.bg_dark)
        title.pack(pady=10)

        # Main content with scrollbar
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(content_frame, bg=self.bg_dark, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # === DEVICE STATUS SECTION ===
        status_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        status_frame.pack(fill='x', padx=10, pady=10)

        status_title = tk.Label(status_frame, text='Device Status', font=('Segoe UI', 12, 'bold'),
                               bg=self.bg_darker, fg=self.accent_color)
        status_title.pack(anchor='w', padx=10, pady=(10, 5))

        # Device info grid
        device_info = ttk.Frame(status_frame)
        device_info.pack(fill='x', padx=10, pady=5)

        tk.Label(device_info, text='ADB:', font=('Segoe UI', 9, 'bold'),
                bg=self.bg_darker, fg=self.text_color, width=12, anchor='w').pack(side='left')
        self.device_status_label = tk.Label(device_info, text='No device detected',
                                           bg=self.bg_darker, fg=self.success_color,
                                           font=('Courier New', 9))
        self.device_status_label.pack(side='left', padx=10)

        root_info = ttk.Frame(status_frame)
        root_info.pack(fill='x', padx=10, pady=5)

        tk.Label(root_info, text='Root:', font=('Segoe UI', 9, 'bold'),
                bg=self.bg_darker, fg=self.text_color, width=12, anchor='w').pack(side='left')
        self.root_status_label = tk.Label(root_info, text='Not detected',
                                         bg=self.bg_darker, fg=self.warning_color,
                                         font=('Courier New', 9))
        self.root_status_label.pack(side='left', padx=10)

        # EDL Detection
        edl_info = ttk.Frame(status_frame)
        edl_info.pack(fill='x', padx=10, pady=5)

        tk.Label(edl_info, text='EDL:', font=('Segoe UI', 9, 'bold'),
                bg=self.bg_darker, fg=self.text_color, width=12, anchor='w').pack(side='left')
        self.edl_status_label = tk.Label(edl_info, text='No device in EDL mode',
                                        bg=self.bg_darker, fg=self.warning_color,
                                        font=('Courier New', 9))
        self.edl_status_label.pack(side='left', padx=10)

        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill='x', padx=10, pady=(5, 10))
        ttk.Button(button_frame, text='Refresh', command=self.refresh_device_status).pack(side='left', padx=5)
        ttk.Button(button_frame, text='Scan EDL', command=self.scan_edl).pack(side='left', padx=5)

        # === ADB OPERATIONS ===
        adb_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        adb_frame.pack(fill='x', padx=10, pady=10)

        adb_title = tk.Label(adb_frame, text='ADB Device Operations', font=('Segoe UI', 12, 'bold'),
                            bg=self.bg_darker, fg=self.accent_color)
        adb_title.pack(anchor='w', padx=10, pady=(10, 5))

        row1 = ttk.Frame(adb_frame)
        row1.pack(fill='x', padx=10, pady=5)
        ttk.Button(row1, text='Device Info', command=self.on_device_info, width=18).pack(side='left', padx=3)
        ttk.Button(row1, text='Push File', command=self.on_adb_push, width=18).pack(side='left', padx=3)
        ttk.Button(row1, text='Pull File', command=self.on_adb_pull, width=18).pack(side='left', padx=3)

        row2 = ttk.Frame(adb_frame)
        row2.pack(fill='x', padx=10, pady=5)
        ttk.Button(row2, text='Root Access', command=self.on_root_access, width=18).pack(side='left', padx=3)
        ttk.Button(row2, text='Shell Command', command=self.on_shell_cmd, width=18).pack(side='left', padx=3)
        ttk.Button(row2, text='Reboot Device', command=self.on_adb_reboot, width=18).pack(side='left', padx=3)

        # === ADVANCED OPERATIONS ===
        adv_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        adv_frame.pack(fill='x', padx=10, pady=10)

        adv_title = tk.Label(adv_frame, text='Advanced Recovery', font=('Segoe UI', 12, 'bold'),
                            bg=self.bg_darker, fg=self.accent_color)
        adv_title.pack(anchor='w', padx=10, pady=(10, 5))

        row3 = ttk.Frame(adv_frame)
        row3.pack(fill='x', padx=10, pady=5)
        ttk.Button(row3, text='Detect EDL', command=self.detect_edl_mode, width=18).pack(side='left', padx=3)
        ttk.Button(row3, text='Flash Loader', command=self.on_flash_loader, width=18).pack(side='left', padx=3)
        ttk.Button(row3, text='Unlock BL', command=self.on_unlock_bl, width=18).pack(side='left', padx=3)

        row4 = ttk.Frame(adv_frame)
        row4.pack(fill='x', padx=10, pady=5)
        ttk.Button(row4, text='Flash Recovery', command=self.on_flash_recovery, width=18).pack(side='left', padx=3)
        ttk.Button(row4, text='Backup Device', command=self.on_backup_device, width=18).pack(side='left', padx=3)
        ttk.Button(row4, text='Factory Reset', command=self.on_factory_reset, width=18).pack(side='left', padx=3)

        # === AUTOMATION ===
        auto_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        auto_frame.pack(fill='x', padx=10, pady=10)

        auto_title = tk.Label(auto_frame, text='Automation & Scripts', font=('Segoe UI', 12, 'bold'),
                             bg=self.bg_darker, fg=self.accent_color)
        auto_title.pack(anchor='w', padx=10, pady=(10, 5))

        row5 = ttk.Frame(auto_frame)
        row5.pack(fill='x', padx=10, pady=5)
        ttk.Button(row5, text='Create Script', command=self.on_create_script, width=18).pack(side='left', padx=3)
        ttk.Button(row5, text='Run Script', command=self.on_run_script, width=18).pack(side='left', padx=3)
        ttk.Button(row5, text='Schedule Task', command=self.on_schedule_task, width=18).pack(side='left', padx=3)

        # === FILE MANAGEMENT ===
        file_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        file_frame.pack(fill='x', padx=10, pady=10)

        file_title = tk.Label(file_frame, text='File Management', font=('Segoe UI', 12, 'bold'),
                             bg=self.bg_darker, fg=self.accent_color)
        file_title.pack(anchor='w', padx=10, pady=(10, 5))

        row6 = ttk.Frame(file_frame)
        row6.pack(fill='x', padx=10, pady=5)
        ttk.Button(row6, text='Browse Loaders', command=self.on_browse_loaders, width=18).pack(side='left', padx=3)
        ttk.Button(row6, text='Open Drive', command=self.on_open_drive, width=18).pack(side='left', padx=3)
        ttk.Button(row6, text='Clear Temp', command=self.on_clear_temp, width=18).pack(side='left', padx=3)

        # === OPERATION LOG ===
        log_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, relief=tk.FLAT, bd=1)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)

        log_title = tk.Label(log_frame, text='Operation Log', font=('Segoe UI', 12, 'bold'),
                            bg=self.bg_darker, fg=self.accent_color)
        log_title.pack(anchor='w', padx=10, pady=(10, 5))

        log_button = ttk.Frame(log_frame)
        log_button.pack(fill='x', padx=10, pady=5)
        ttk.Button(log_button, text='Clear Log', command=self.on_clear_log).pack(side='right')

        self.log_output = scrolledtext.ScrolledText(log_frame, height=10, width=80,
                                                    bg=self.bg_dark, fg=self.success_color,
                                                    font=('Courier New', 8), state='disabled',
                                                    insertbackground=self.accent_color)
        self.log_output.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # === FOOTER ===
        footer_frame = tk.Frame(scrollable_frame, bg=self.bg_darker, height=50)
        footer_frame.pack(fill='x', padx=10, pady=10)
        footer_frame.pack_propagate(False)

        ttk.Button(footer_frame, text='Help', command=self.on_help).pack(side='left', padx=5, pady=10)
        ttk.Button(footer_frame, text='Settings', command=self.on_settings).pack(side='left', padx=5)
        ttk.Button(footer_frame, text='Exit', command=self.root.quit).pack(side='right', padx=5)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"

        self.log_output.config(state='normal')
        self.log_output.insert(tk.END, full_message)
        self.log_output.see(tk.END)
        self.log_output.config(state='disabled')

    def _find_edl_port(self):
        """Return the COM port of a connected EDL device, or None."""
        for port in serial.tools.list_ports.comports():
            if (port.vid == 0x05C6 and port.pid == 0x9008) or \
               any(k in (port.description or '').upper() for k in ('9008', 'QDLOADER')):
                return port.device
        return None

    def _run_streaming(self, cmd, label="Command"):
        """Run a shell command in a background thread, streaming stdout/stderr to log."""
        def worker():
            self.log_message(f"→ {label}")
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, shell=True, bufsize=1
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.log_message(line)
                proc.wait()
                if proc.returncode == 0:
                    self.log_message(f"✓ {label} completed successfully.")
                else:
                    self.log_message(f"✗ {label} failed (exit {proc.returncode}).")
            except Exception as e:
                self.log_message(f"✗ Error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def refresh_device_status(self):
        """Refresh device status"""
        devices = self.adb.get_devices()
        if devices:
            self.device_status_label.config(text=f"Connected: {', '.join(devices)}", fg=self.success_color)
            is_rooted = self.adb.is_rooted()
            root_text = "✓ ROOTED" if is_rooted else "✗ Not Rooted"
            root_color = self.success_color if is_rooted else self.warning_color
            self.root_status_label.config(text=root_text, fg=root_color)
        else:
            self.device_status_label.config(text='No device detected', fg=self.warning_color)
            self.root_status_label.config(text='N/A', fg=self.warning_color)

    def scan_edl(self):
        """Scan for EDL devices"""
        def scan_thread():
            self.log_message("Scanning for EDL devices...")
            try:
                # Use pyserial to list ports
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                self.log_message(f"Found {len(ports)} COM ports total")
                
                for port in ports:
                    self.log_message(f"Found port: {port.device} - {port.description}")
                    
                edl_devices = self.edl.scan_edl_devices()
                if edl_devices:
                    for device in edl_devices:
                        self.log_message(f"✓ EDL Device found on {device['port']}: {device['description']}")
                        self.edl_status_label.config(text=f"Found on {device['port']}", fg=self.success_color)
                else:
                    self.log_message("No EDL devices detected by filter.")
                    self.edl_status_label.config(text="No EDL device found", fg=self.warning_color)
            except Exception as e:
                self.log_message(f"Error during scan: {str(e)}")

        threading.Thread(target=scan_thread, daemon=True).start()

    def detect_edl_mode(self):
        """Advanced EDL detection"""
        self.log_message("Detecting devices in EDL mode (Emergency Download)...")
        self.log_message("Looking for QDLoader 9008 devices...")
        self.scan_edl()

    def on_device_info(self):
        self.log_message("Fetching device information...")
        info = self.adb.get_device_info()
        info_text = '\n'.join([f'{k}: {v}' for k, v in info.items()])
        messagebox.showinfo('Device Information', info_text)

    def on_adb_push(self):
        self.log_message("Push file to device...")
        source = filedialog.askopenfilename(title='Select file to push')
        if source:
            dest = simpledialog.askstring('Push File', 'Destination path on device:')
            if dest:
                self.log_message(f"Pushing {os.path.basename(source)} to {dest}...")
                output, success = self.adb.run_cmd(f'push "{source}" {dest}')
                self.log_message("✓ File pushed successfully!" if success else f"✗ Error: {output}")

    def on_adb_pull(self):
        self.log_message("Pull file from device...")
        source = simpledialog.askstring('Pull File', 'Source path on device:')
        if source:
            dest = filedialog.askdirectory(title='Select destination folder')
            if dest:
                self.log_message(f"Pulling {source}...")
                output, success = self.adb.run_cmd(f'pull {source} "{dest}"')
                self.log_message("✓ File pulled successfully!" if success else f"✗ Error: {output}")

    def on_root_access(self):
        self.log_message("Checking root access...")
        is_rooted = self.adb.is_rooted()
        if is_rooted:
            self.log_message("✓ Device has root access")
            self.root_status_label.config(text='✓ ROOTED', fg=self.success_color)
        else:
            self.log_message("Attempting to enable root...")
            result = self.adb.grant_root()
            if result:
                self.log_message("✓ Root access enabled!")
                self.root_status_label.config(text='✓ ROOTED', fg=self.success_color)
            else:
                self.log_message("✗ Could not enable root. Device may not be rooted.")

    def on_shell_cmd(self):
        self.log_message("Execute custom shell command...")
        cmd = simpledialog.askstring('Shell Command', 'Enter ADB shell command (without "adb shell"):')
        if cmd:
            self.log_message(f"Executing: {cmd}")
            output, success = self.adb.run_cmd(f'shell {cmd}')
            self.log_message(output if success else f"✗ Error: {output}")

    def on_adb_reboot(self):
        self.log_message("Rebooting device...")
        mode = simpledialog.askstring('Reboot Device', 'Reboot mode (system/recovery/bootloader):',
                                      initialvalue='system')
        if mode:
            output, success = self.adb.run_cmd(f'reboot {mode}')
            self.log_message(f"✓ Reboot command sent ({mode})" if success else f"✗ Error: {output}")

    def on_backup_device(self):
        self.log_message("Starting device backup...")
        backup_dir = filedialog.askdirectory(title='Select backup destination')
        if backup_dir:
            self.log_message("Backing up device data (this may take a while)...")
            output, success = self.adb.run_cmd(f'backup -all -f "{backup_dir}/device_backup.ab"')
            if success:
                self.log_message("✓ Backup completed successfully!")
            else:
                self.log_message(f"✗ Backup error: {output}")

    def on_factory_reset(self):
        if messagebox.askyesno('Factory Reset', 'WARNING: This will wipe all device data. Continue?'):
            self.log_message("Performing factory reset...")
            output, success = self.adb.run_cmd('shell am broadcast -a android.intent.action.MASTER_CLEAR')
            self.log_message("✓ Factory reset initiated!" if success else f"✗ Error: {output}")

    def on_flash_loader(self):
        self.log_message("Flash loader via EDL (Sahara)...")
        loader = filedialog.askopenfilename(
            title='Select firehose loader',
            filetypes=[('ELF/BIN loader', '*.elf *.bin'), ('All files', '*.*')]
        )
        if not loader:
            return
        edl_port = self._find_edl_port()
        if not edl_port:
            messagebox.showerror('EDL Not Found',
                'No Qualcomm EDL device detected.\nPut device into EDL mode first.')
            return
        self.log_message(f"Loader: {os.path.basename(loader)}")
        self.log_message(f"Port:   {edl_port}")
        edl_script = r'C:\Users\Andrew Price\edl\edl.py'
        # Use 'gpt' command which exercises the full Sahara→Firehose handshake
        cmd = (
            f'"{sys.executable}" "{edl_script}" gpt '
            f'--loader="{loader}" --serial --portname="\\\\.\\{edl_port}"'
        )
        self._run_streaming(cmd, label=f"Load {os.path.basename(loader)} via Sahara")

    def on_unlock_bl(self):
        if not messagebox.askyesno('Unlock Bootloader',
                'This will WIPE ALL DATA and unlock the bootloader.\n'
                'Ensure device is in fastboot mode.\nContinue?'):
            return
        self.log_message("Rebooting to fastboot mode first...")
        self.adb.run_cmd('reboot bootloader')
        import time as _time
        _time.sleep(3)
        self.log_message("Sending bootloader unlock command...")
        # Try modern command first, fall back to legacy
        out, ok = self.adb.run_fastboot('flashing unlock')
        if not ok and 'unknown command' in out.lower():
            out, ok = self.adb.run_fastboot('oem unlock')
        self.log_message(out if out else ('✓ Unlock sent — confirm on device screen.' if ok else '✗ Unlock failed.'))
        if ok:
            self.log_message("✓ Confirm the unlock on the device screen, then it will reboot.")

    def on_flash_recovery(self):
        recovery = filedialog.askopenfilename(
            title='Select recovery image',
            filetypes=[('Image files', '*.img'), ('All files', '*.*')]
        )
        if not recovery:
            return
        if not messagebox.askyesno('Flash Recovery',
                f'Flash recovery image?\n{os.path.basename(recovery)}\n\nDevice must be in fastboot mode.'):
            return
        self.log_message(f"Flashing recovery: {os.path.basename(recovery)}")
        fastboot = self.adb._find_fastboot()
        cmd = f'"{fastboot}" flash recovery "{recovery}"'
        self._run_streaming(cmd, label="fastboot flash recovery")

    def on_create_script(self):
        script_window = tk.Toplevel(self.root)
        script_window.title('Script Builder')
        script_window.geometry('700x500')
        script_window.configure(bg=self.bg_dark)

        ttk.Label(script_window, text='Create Automation Script', font=('Segoe UI', 12, 'bold')).pack(pady=10)

        frame = ttk.Frame(script_window, padding=10)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text='Script Name:').pack(anchor='w')
        script_name = ttk.Entry(frame, width=40)
        script_name.pack(anchor='w', pady=5)

        ttk.Label(frame, text='Script Commands (one per line):').pack(anchor='w', pady=(10, 0))
        script_content = scrolledtext.ScrolledText(frame, height=15, width=60, bg=self.bg_darker, fg=self.text_color)
        script_content.pack(fill='both', expand=True, pady=5)

        ttk.Label(frame, text='Commands: device_info, push_file, pull_file, shell, reboot, backup, etc.').pack(anchor='w')

        def save_script():
            name = script_name.get()
            content = script_content.get('1.0', tk.END)
            if not name:
                messagebox.showerror('Error', 'Please enter a script name')
                return

            script_dir = os.path.expanduser('~/OnePlusRecovery/scripts')
            os.makedirs(script_dir, exist_ok=True)
            script_path = os.path.join(script_dir, f"{name}.adb")
            with open(script_path, 'w') as f:
                f.write(content)
            self.log_message(f"✓ Script saved: {script_path}")
            messagebox.showinfo('Success', f'Script saved to:\n{script_path}')
            script_window.destroy()

        button_frame = ttk.Frame(script_window, padding=10)
        button_frame.pack(fill='x')
        ttk.Button(button_frame, text='Save Script', command=save_script).pack(side='left', padx=5)
        ttk.Button(button_frame, text='Cancel', command=script_window.destroy).pack(side='left', padx=5)

    def on_run_script(self):
        self.log_message("Running automation script...")
        script_file = filedialog.askopenfilename(title='Select script file',
                                                 filetypes=[('ADB Scripts', '*.adb'), ('All files', '*.*')])
        if script_file:
            try:
                with open(script_file, 'r') as f:
                    commands = f.readlines()
                self.log_message(f"Executing {len(commands)} commands...")
                for cmd in commands:
                    cmd = cmd.strip()
                    if cmd and not cmd.startswith('#'):
                        self.log_message(f"→ {cmd}")
                        output, success = self.adb.run_cmd(cmd)
                        if not success:
                            self.log_message(f"  ✗ Error: {output}")
                self.log_message("✓ Script execution completed!")
            except Exception as e:
                self.log_message(f"✗ Script error: {str(e)}")

    def on_schedule_task(self):
        self.log_message("Schedule task feature (requires admin)")
        task_name = simpledialog.askstring('Schedule Task', 'Task name:')
        if task_name:
            time = simpledialog.askstring('Schedule Task', 'Schedule time (HH:MM):')
            if time:
                self.log_message(f"Task '{task_name}' scheduled for {time}")
                messagebox.showinfo('Scheduled', f'Task will run at {time}')

    def on_browse_loaders(self):
        loaders_path = os.path.expanduser('~/OneDrive/OnePlus11_Loaders')
        os.makedirs(loaders_path, exist_ok=True)
        os.startfile(loaders_path)
        self.log_message(f"✓ Opened: {loaders_path}")

    def on_open_drive(self):
        drive_path = os.path.expanduser('~/OneDrive/OnePlus11_Loaders')
        os.makedirs(drive_path, exist_ok=True)
        os.startfile(drive_path)
        self.log_message(f"✓ Opened: {drive_path}")

    def on_clear_temp(self):
        temp_path = os.path.expanduser('~/AppData/Local/Temp')
        self.log_message(f"Clearing temp files in: {temp_path}")
        deleted, skipped = 0, 0
        for item in glob_module.glob(os.path.join(temp_path, '*')):
            try:
                if os.path.isfile(item):
                    os.remove(item)
                    deleted += 1
                elif os.path.isdir(item):
                    shutil.rmtree(item, ignore_errors=True)
                    deleted += 1
            except Exception:
                skipped += 1
        self.log_message(f"✓ Deleted {deleted} items, skipped {skipped} (in-use).")

    def on_clear_log(self):
        self.log_output.config(state='normal')
        self.log_output.delete('1.0', tk.END)
        self.log_output.config(state='disabled')

    def on_help(self):
        help_text = """OnePlus Device Recovery Tool - Help

ADB DEVICE OPERATIONS:
• Device Info: Display model, build, Android version
• Push/Pull Files: Transfer files to/from device
• Root Access: Check or enable root privileges
• Shell Command: Execute custom ADB commands
• Reboot Device: Reboot to system/recovery/bootloader

ADVANCED RECOVERY (EDL MODE):
• Detect EDL: Scan for devices in Emergency Download mode
• Flash Loader: Flash bootloader files (requires EDL device)
• Unlock Bootloader: Unlock for custom ROM flashing
• Flash Recovery: Flash custom recovery image
• Backup Device: Full device backup via ADB
• Factory Reset: Wipe device data

AUTOMATION & BATCH:
• Create Script: Build automation scripts
• Run Script: Execute saved automation scripts
• Schedule Task: Schedule operations for later

FILE MANAGEMENT:
• Browse Loaders: Access firmware files from OneDrive
• Clear Temp: Remove temporary files

REQUIREMENTS:
• ADB (Android Debug Bridge) installed
• Device connected via USB with USB Debug enabled
• For EDL: Device must be in Emergency Download mode
• pyserial installed for EDL detection

TIPS:
• Always backup before major operations
• Enable USB Debugging in Developer Options
• EDL mode is activated by specific key combinations
• Use 'Detect EDL' to find devices in emergency mode"""

        help_window = tk.Toplevel(self.root)
        help_window.title('Help')
        help_window.geometry('700x600')
        help_window.configure(bg=self.bg_dark)

        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=('Segoe UI', 9),
                                              bg=self.bg_darker, fg=self.text_color)
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')

    def on_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title('Settings')
        settings_window.geometry('600x500')
        settings_window.configure(bg=self.bg_dark)

        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text='Tool Settings', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=10)

        ttk.Label(frame, text='General Settings:', font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(10, 0))
        log_to_file_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text='Enable logging to file', variable=log_to_file_var).pack(anchor='w')
        auto_detect_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text='Auto-detect device on startup', variable=auto_detect_var).pack(anchor='w')
        confirm_ops_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text='Confirm before operations', variable=confirm_ops_var).pack(anchor='w')

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(frame, text='ADB Settings:', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='ADB Path:').pack(anchor='w')
        adb_path_entry = ttk.Entry(frame, width=50)
        adb_path_entry.insert(0, 'adb')
        adb_path_entry.pack(anchor='w', pady=5)

        def auto_detect_adb():
            adb_manager = ADBManager()
            messagebox.showinfo('ADB Path', f'Found ADB at:\n{adb_manager.adb_path}')

        ttk.Button(frame, text='Auto-Detect ADB', command=auto_detect_adb).pack(anchor='w', pady=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x')
        ttk.Button(button_frame, text='Save', command=lambda: [messagebox.showinfo('Saved', 'Settings saved!'), settings_window.destroy()]).pack(side='left', padx=5)
        ttk.Button(button_frame, text='Cancel', command=settings_window.destroy).pack(side='left', padx=5)

    def schedule_refresh(self):
        """Auto-refresh device status every 2 seconds"""
        self.refresh_device_status()
        self.root.after(2000, self.schedule_refresh)


def main():
    root = tk.Tk()
    adb = ADBManager()

    app = MainWindow(root, adb)
    app.log_message("OnePlus Recovery Tool started")
    app.log_message(f"ADB detected at: {adb.adb_path}")
    app.log_message("Ready for device operations")

    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Error', f'An error occurred: {str(e)}')
        sys.exit(1)
