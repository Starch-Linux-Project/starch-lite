#!/usr/bin/env python3
"""Validate installed live-image artifacts without executing code from the image."""
import configparser
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
users = {row.split(":")[0]: row.split(":") for row in (root / "etc/passwd").read_text().splitlines()}
assert users["liveuser"][6] == "/usr/bin/fish", "Live user missing or wrong shell"
assert users["root"][6] == "/usr/bin/bash", "Root shell must be Bash"
home = root / users["liveuser"][5].lstrip("/")
assert home.is_dir() and home.stat().st_uid == int(users["liveuser"][2]), "Live home ownership incorrect"
for path in ("usr/share/xsessions/xfce.desktop", "usr/bin/fish", "usr/bin/fastfetch",
             "usr/bin/cosmic-term", "usr/bin/kdialog", "usr/bin/firefox", "usr/bin/thunar",
             "usr/lib/qt6/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so",
             "usr/lib/systemd/system/lightdm.service", "usr/lib/starch-lite/xfce-defaults",
             "etc/xdg/autostart/starch-xfce-defaults.desktop",
             "usr/share/xfce4/helpers/starch-cosmic-terminal.desktop"):
    assert (root / path).is_file(), f"Missing {path}"
luu_modes = {
    "usr/local/bin/linux-update-utility.AppImage": 0o755,
    "usr/share/icons/hicolor/scalable/apps/linux-update-utility.svg": 0o644,
    "usr/share/applications/linux-update-utility.desktop": 0o644,
}
for path, mode in luu_modes.items():
    artifact = root / path
    assert artifact.is_file(), f"Missing Linux Update Utility artifact: {path}"
    assert artifact.stat().st_mode & 0o777 == mode, f"Wrong mode for {path}"
lightdm_service = root / "etc/systemd/system/display-manager.service"
assert lightdm_service.readlink().as_posix() == "/usr/lib/systemd/system/lightdm.service"
lightdm = configparser.ConfigParser()
lightdm.read(root / "etc/lightdm/lightdm.conf.d/10-starch-live.conf")
assert lightdm["Seat:*"]["autologin-session"] == "xfce"
assert lightdm["Seat:*"]["autologin-user"] == "liveuser"
groups = (root / "etc/group").read_text().splitlines()
assert any(row.split(":")[0] == "autologin" and "liveuser" in row.split(":")[3].split(",")
           for row in groups), "Live user is missing LightDM autologin membership"
panel = home / ".config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
for launcher in ("firefox.desktop", "thunar.desktop", "com.system76.CosmicTerm.desktop",
                 "linux-update-utility.desktop"):
    assert f"/usr/share/applications/{launcher}" in panel.read_text(), f"Missing launcher: {launcher}"
sudoers = root / "etc/sudoers.d/10-starch-live"
assert sudoers.stat().st_uid == 0 and sudoers.stat().st_mode & 0o777 == 0o440, "Unsafe sudoers permissions"
assert not (root / "etc/pacman.d/hooks/90-starch-live-user.hook").exists(), "Build-only hook left in image"
firewall = root / "etc/nftables.conf"
assert firewall.is_file() and "table inet starch_filter" in firewall.read_text(), "Missing nftables ruleset"
nftables_service = root / "etc/systemd/system/multi-user.target.wants/nftables.service"
assert nftables_service.is_symlink() and nftables_service.readlink().as_posix() == "/usr/lib/systemd/system/nftables.service", "nftables service is not enabled"
print("Built live filesystem validation passed")
for path in ["usr/bin/calamares", "usr/local/bin/starch-install", "etc/calamares/settings.conf",
             "usr/share/applications/starch-install.desktop", "usr/share/starch-installer/minimal-packages.txt",
             "usr/lib/starch-installer/runtime.py", "usr/lib/starch-installer/additional.py"]:
    assert (root / path).is_file(), f"Missing installer artifact: {path}"
for module in ["welcome", "locale", "keyboard", "partition", "users", "summary", "finished",
               "starchsoftware", "mount", "umount", "machineid", "fstab", "localecfg", "bootloader",
               "starch-preflight", "starch-bootstrap", "starch-configure", "starch-validate"]:
    assert (root / "usr/lib/calamares/modules" / module / "module.desc").is_file(), f"Missing module: {module}"
assert not (root / "usr/lib/calamares/modules/starchadvanced").exists(), "Profile module shipped in Lite installer"
assert "starchadvanced" not in (root / "etc/calamares/settings.conf").read_text()
assert "preflight.run" in (root / "usr/lib/calamares/modules/starch-preflight/main.py").read_text()
assert (root / "usr/share/starch-installer/lite/bundle.json").is_file(), "Missing verified Lite bundle"
assert (root / "usr/local/bin/starch-install").stat().st_mode & 0o111, "Installer launcher is not executable"
launcher = (root / "usr/local/bin/starch-install").read_text()
assert "kdialog --title" in launcher and 'standard "Standard keyboard" on' in launcher and "unset QT_IM_MODULE" in launcher, "Installer has no standard-keyboard chooser default"
assert "--on-screen-keyboard" in launcher and "export QT_IM_MODULE=qtvirtualkeyboard" in launcher, "Installer has no optional Qt Virtual Keyboard mode"
shortcut = home / "Desktop/starch-install.desktop"
assert shortcut.is_file() and not shortcut.is_symlink(), "Live desktop installer shortcut is missing"
assert shortcut.stat().st_mode & 0o111, "Live desktop installer shortcut is not executable"
assert shortcut.read_bytes() == (root / "usr/share/applications/starch-install.desktop").read_bytes(), "Live desktop shortcut differs from shipped launcher"
trust_helper = "/usr/local/lib/starch/trust-installer-launcher"
assert (root / trust_helper.lstrip("/")).stat().st_mode & 0o111, "Missing executable launcher trust helper"
autostart = configparser.ConfigParser()
autostart.read(root / "etc/xdg/autostart/starch-trust-installer.desktop")
assert autostart["Desktop Entry"]["Exec"] == trust_helper, "Launcher trust helper is not started at login"
partition_modules = list((root / "usr/lib/calamares/modules/partition").glob("*.so"))
assert len(partition_modules) == 1 and b"Starch erase target:" in partition_modules[0].read_bytes(), "Calamares partition safety patch is missing"
print("Built installer filesystem validation passed")
