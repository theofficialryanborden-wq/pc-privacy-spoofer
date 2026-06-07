# PC Privacy Spoofer

A Windows tool that rotates common hardware and software identifiers used to fingerprint your PC. Every change is backed up so you can restore your original values.

**Use this for legitimate privacy on your own machine.** Do not use it to evade access controls, impersonate other devices, or violate network policies.

## Download (no install required)

1. Open **[Releases](https://github.com/theofficialryanborden-wq/pc-privacy-spoofer/releases)** on GitHub.
2. Download **`PC-Privacy-Spoofer.exe`** from the latest release.
3. Right-click the file → **Run as administrator** (required for spoof/restore).
4. Use the GUI to view identifiers, spoof selected items, or restore from backup.

No Python install is needed when using the `.exe`. Windows 10/11 only.

## What it changes

| Identifier | Location | Reboot needed |
|---|---|---|
| MAC address | Network adapter registry + adapter restart | No |
| MachineGuid | `HKLM\SOFTWARE\Microsoft\Cryptography` | No |
| HwProfileGuid | Hardware profile registry | No |
| ProductId | Windows NT CurrentVersion | No |
| SusClientId | Windows Update registry (if present) | No |
| Computer name | Multiple registry keys + Rename-Computer | **Yes** |

## Requirements

- Windows 10/11
- Python 3.10+
- **Administrator privileges** (for spoof/restore)

## Quick start

Open **PowerShell as Administrator**, then:

```powershell
cd C:\Users\theof\Projects\pc-privacy-spoofer

# View current identifiers (no admin needed for read-only status)
$env:PYTHONPATH = ".\src"
python -m privacy_spoofer status

# Spoof everything (backs up originals first)
.\run.ps1 spoof --all

# Spoof only MAC addresses
.\run.ps1 spoof --mac

# Spoof only registry IDs
.\run.ps1 spoof --registry

# Restore from backup
.\run.ps1 restore
```

Or use the helper script without setting `PYTHONPATH`:

```powershell
.\run.ps1 list-adapters
.\run.ps1 spoof --mac --adapter "Intel"
.\run.ps1 restore
```

## Backup location

Original values are saved to:

```
%USERPROFILE%\.pc-privacy-spoofer\backups\latest.json
```

Run `restore` to revert. Keep this file safe if you plan to undo changes later.

## Limitations

- **SMBIOS/UEFI UUID**, motherboard serial, and CPU ID are firmware-level and not changed by this tool.
- **Volume serial numbers** are shown in `status` but not modified (changing them requires low-level disk tools and carries data risk).
- Some apps cache identifiers; you may need to restart them or reboot after spoofing.
- Virtual adapters are skipped when physical adapters are available.
- Changing identifiers may affect licensed software, domain membership, or Windows Update behavior.

## Install as a command (optional)

```powershell
pip install -e .
privacy-spoofer status
```

## Legal and ethical use

Only run this on systems you own or are authorized to modify. Spoofing identifiers on networks you do not control may violate terms of service or local policy.
