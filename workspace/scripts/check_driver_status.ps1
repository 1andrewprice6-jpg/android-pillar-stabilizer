# Check Driver Status
# This script helps diagnose driver installation issues
Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  USB Driver Status Checker" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
# Check 1: Test Signing
Write-Host "[1] Checking Test Signing Status..." -ForegroundColor Yellow
$testSigning = bcdedit | Select-String "testsigning"
if ($testSigning -match "Yes") {
    Write-Host "  [OK] Test signing is ENABLED" -ForegroundColor Green
} else {
    Write-Host "  [!!] Test signing is DISABLED" -ForegroundColor Red
    Write-Host "    Run: bcdedit /set testsigning on" -ForegroundColor Yellow
}
Write-Host ""
# Check 2: Certificate Installation
Write-Host "[2] Checking Test Certificate..." -ForegroundColor Yellow
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*LibusbK*" }
if ($cert) {
    Write-Host "  [OK] Test certificate found in Personal store" -ForegroundColor Green
    Write-Host "    Subject: $($cert.Subject)" -ForegroundColor Gray
    Write-Host "    Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
} else {
    Write-Host "  [!!] Test certificate NOT found" -ForegroundColor Red
    Write-Host "    Run sign-driver.ps1 to create certificate" -ForegroundColor Yellow
}
$certRoot = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*LibusbK*" }
if ($certRoot) {
    Write-Host "  [OK] Certificate in Trusted Root store" -ForegroundColor Green
} else {
    Write-Host "  [!!] Certificate NOT in Trusted Root store" -ForegroundColor Red
}
$certPub = Get-ChildItem -Path Cert:\LocalMachine\TrustedPublisher | Where-Object { $_.Subject -like "*LibusbK*" }
if ($certPub) {
    Write-Host "  [OK] Certificate in Trusted Publishers store" -ForegroundColor Green
} else {
    Write-Host "  [!!] Certificate NOT in Trusted Publishers store" -ForegroundColor Red
}
Write-Host ""
# Check 3: Driver Files
Write-Host "[3] Checking Driver Files..." -ForegroundColor Yellow
$files = @(
    "QUSB_BULK_CID0437_SN2B5BCB51.inf",
    "QUSB_BULK_CID0437_SN2B5BCB51_v2.inf",
    "QUSB_BULK_CID0437_SN2B5BCB51.cat",
    "amd64\libusbK.sys",
    "amd64\libusbK.dll",
    "x86\libusbK.sys",
    "x86\libusbK.dll"
)
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [!!] $file" -ForegroundColor Red
    }
}
Write-Host ""
# Check 4: Driver Installation
Write-Host "[4] Checking Driver Installation..." -ForegroundColor Yellow
$drivers = pnputil /enum-drivers | Select-String "libusbk" -Context 0,5
if ($drivers) {
    Write-Host "  [OK] Driver found in Windows driver store:" -ForegroundColor Green
    Write-Host "$drivers" -ForegroundColor Gray
} else {
    Write-Host "  [!!] Driver NOT installed in driver store" -ForegroundColor Red
    Write-Host "    Run setup-driver.bat to install" -ForegroundColor Yellow
}
Write-Host ""
# Check 5: Device Detection
Write-Host "[5] Checking for Qualcomm Devices..." -ForegroundColor Yellow
$devices = Get-PnpDevice | Where-Object {
    $_.InstanceId -like "*VID_05C6&PID_9008*" -or
    $_.FriendlyName -like "*Qualcomm*" -or
    $_.FriendlyName -like "*QUSB*" -or
    $_.FriendlyName -like "*QDLoader*"
}
if ($devices) {
    Write-Host "  [OK] Qualcomm device(s) detected:" -ForegroundColor Green
    foreach ($device in $devices) {
        Write-Host "    Name: $($device.FriendlyName)" -ForegroundColor Gray
        Write-Host "    Status: $($device.Status)" -ForegroundColor Gray
        Write-Host "    Instance: $($device.InstanceId)" -ForegroundColor DarkGray
        Write-Host ""
    }
} else {
    Write-Host "  [-] No Qualcomm devices detected" -ForegroundColor Yellow
    Write-Host "    Connect your device in EDL/9008 mode" -ForegroundColor Gray
}
Write-Host ""
# Check 6: System Information
Write-Host "[6] System Information..." -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "  OS: $($os.Caption)" -ForegroundColor Gray
Write-Host "  Version: $($os.Version)" -ForegroundColor Gray
Write-Host "  Architecture: $($os.OSArchitecture)" -ForegroundColor Gray
Write-Host ""
# Summary
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
$issues = 0
if ($testSigning -notmatch "Yes") { $issues++ }
if (-not $cert) { $issues++ }
if (-not $certRoot) { $issues++ }
if (-not $certPub) { $issues++ }
if (-not $drivers) { $issues++ }
if ($issues -eq 0) {
    Write-Host "[OK] All checks passed! Driver should work correctly." -ForegroundColor Green
} else {
    Write-Host "[!!] Found $issues issue(s) that need attention." -ForegroundColor Red
    Write-Host ""
    Write-Host "Recommended actions:" -ForegroundColor Yellow
    if ($testSigning -notmatch "Yes") {
        Write-Host "  1. Enable test signing: bcdedit /set testsigning on" -ForegroundColor White
    }
    if (-not $cert -or -not $certRoot -or -not $certPub) {
        Write-Host "  2. Create and install certificate: Run sign-driver.ps1" -ForegroundColor White
    }
    if (-not $drivers) {
        Write-Host "  3. Install driver: Run setup-driver.bat" -ForegroundColor White
    }
}
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
