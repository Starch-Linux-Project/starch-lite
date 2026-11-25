# Installing Starch Lite

Starch Lite runs Xfce on X11 with the `linux-zen` kernel, OpenRC, LightDM for
login, and elogind for session management.

Thunar handles files, Ristretto handles images, and Xfce supplies screenshot and
task-manager applications. Compositing and session restoration are disabled by
default. The bundled Lite integration supplies low-memory settings, zram
configuration, and Xfce defaults. Starch's automatic screen-rotation integration
is not included in Lite.

Repository priority is Artix `system`, `world`, and `galaxy`, followed by Arch
`extra`; Arch `core` is disabled. System services use OpenRC. Audio runs through
Artix's OpenRC user services for PipeWire and WirePlumber. A recovery text login
is available with **Ctrl+Alt+F2**.

The ISO build requires a verified Starch Lite package bundle. The installer
verifies the bundle again before preparing the selected disk.
The [Starch Lite reference](starch-lite.md) covers service integration.

New Lite installations use a full-width top taskbar and a centered bottom dock
with Thunar, COSMIC Terminal, and Firefox launchers. The native Xfce dock hides
when the focused window overlaps it. Existing user panel settings are preserved.

## Shared components

- An x86_64 installation with Limine boot support for UEFI or legacy BIOS.
- An ext4 root filesystem and compressed RAM swap through zram, rather than a
  disk swap partition.
- NetworkManager, PipeWire/WirePlumber audio, and nftables.
- Fish as the standard user's default shell, with authenticated desktop login
  and installed-system autologin disabled.
- Shared applications including Firefox, VLC, nano, and btop.
- Flatpak with Flathub configured; no Flatpak applications are selected by default.
- [Linux Update Utility](linux-update-utility.md), supplied as a bundled AppImage.

The [base package manifest](../manifests/minimal-packages.txt) is the starting
point, not the complete package list for installation. The installer transforms the baseline into the Xfce/OpenRC
package set, resolves dependencies, and
selects graphics packages for the detected hardware and target kernel.

## Installation model and supported scope

Installation requires an internet connection: Calamares downloads fresh target
packages with `pacstrap`. It does not copy the running live desktop into the
installed system. The live ISO runs Xfce with LightDM, systemd, and the regular Arch `linux` kernel.

Starch Lite uses an erase-disk installation that replaces the contents
of the entire selected disk. Manual partitioning,
install-alongside/dual boot, offline installation, full-disk encryption, Secure
Boot, hibernation, and snapshot rollback are outside the supported scope.
There are no ARM or 32-bit images. Installation and hardware boundaries are
documented in [supported scope](decisions.md).

## Additional Software

On the Additional Software page, optionally enter **Pacman package names** and
**Flathub app IDs** in separate fields. Separate entries with spaces, commas,
or newlines. Both fields start empty; there are no presets or AUR support.
Entries survive backward navigation and appear in Summary. Duplicate entries
are installed once per field.

Optional installs run in the mounted target only after essential OS installation
and validation succeed, immediately before unmounting. Pacman uses the target's
configured repositories (including Lite's Artix-first configuration). Flathub
apps install system-wide; the Flathub remote is added if missing. No installation
is deferred to first boot or login.

A separate progress window shows each requested install, its elapsed time, and
live package-manager output. Each request is checked in the installed package
database before being reported as installed. **Skip remaining
optional installs** waits for the current transaction to finish, then skips the
rest without interrupting package writes. Failed or invalid requests appear as
warnings; other requests continue, and the completed OS installation is neither
failed nor rolled back. Results remain visible until you choose **Continue**,
including when all requests succeeded. Failure output stays in the results when the next request
starts. Per-request outcomes and package command logs are retained under
`/var/log/starch-installer/` in the target.

## Updates and existing installations

Starch does not stage upstream Arch updates or provide automatic rollback.
Starch-owned utilities and configuration are bundled with ISO releases and have
no dedicated update channel for existing installations. Rebuilding an ISO
changes future installations. Existing installations keep their desktop and
user settings.

## Implementation reference

The Calamares preflight job sets the `lite-xfce` identity before validating the
target package set and repositories. See
[`scripts/installer/profiles.py`](../scripts/installer/profiles.py).
