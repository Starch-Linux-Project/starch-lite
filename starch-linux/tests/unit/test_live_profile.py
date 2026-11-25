import configparser
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROFILE = ROOT / "archiso/profile"
FS = PROFILE / "airootfs"

class LiveProfile(unittest.TestCase):
    def test_starch_identity_is_consistent(self):
        profiledef = (PROFILE / "profiledef.sh").read_text()
        self.assertIn('iso_name="starch-lite"', profiledef)
        self.assertIn('iso_label="STARCHLITE_', profiledef)
        os_release = (FS / "etc/os-release").read_text()
        self.assertIn('NAME="Starch Lite"', os_release)
        self.assertIn('PRETTY_NAME="Starch Lite 1.2 Live"', os_release)
        self.assertIn('ID=starch', os_release)
        self.assertEqual((FS / "etc/hostname").read_text().strip(), "starch-live")
        self.assertTrue((FS / "etc/issue").read_text().startswith("Starch Lite Live"))
        self.assertEqual((FS / "etc/issue.net").read_text().strip(), "Starch Lite Live")
        visible_boot_files = [
            PROFILE / "grub/grub.cfg",
            PROFILE / "grub/loopback.cfg",
            PROFILE / "efiboot/loader/entries/01-archiso-linux.conf",
            PROFILE / "efiboot/loader/entries/02-archiso-speech-linux.conf",
            PROFILE / "syslinux/archiso_head.cfg",
            PROFILE / "syslinux/archiso_sys-linux.cfg",
            PROFILE / "syslinux/archiso_pxe-linux.cfg",
        ]
        for path in visible_boot_files:
            text = path.read_text()
            self.assertIn("Starch Lite", text, path)
            self.assertNotIn("Arch Linux", text, path)

    def test_desktop_boot_and_account_hook(self):
        units = FS / "etc/systemd/system"
        self.assertEqual((units / "default.target").readlink().name, "graphical.target")
        self.assertEqual((units / "display-manager.service").readlink().name, "lightdm.service")
        cfg = configparser.ConfigParser()
        cfg.read(FS / "etc/lightdm/lightdm.conf.d/10-starch-live.conf")
        self.assertEqual(cfg["Seat:*"]["autologin-session"], "xfce")
        self.assertEqual(cfg["Seat:*"]["autologin-user"], "liveuser")
        hook = configparser.ConfigParser(strict=False)
        hook.read(FS / "etc/pacman.d/hooks/90-starch-live-user.hook")
        self.assertEqual(hook["Trigger"]["Target"], "lightdm")
        script = hook["Action"]["Exec"].split()[-1]
        setup_script = FS / script.lstrip("/")
        self.assertTrue(setup_script.is_file())
        self.assertIn("'liveuser:password' | chpasswd", setup_script.read_text())
        self.assertIn("--groups autologin", setup_script.read_text())
        self.assertFalse((units / "getty@tty1.service.d/autologin.conf").exists())
        self.assertIn("root:/root:/usr/bin/bash", (FS / "etc/passwd").read_text())

    def test_network_manager_has_no_competing_enabled_backend(self):
        units = FS / "etc/systemd/system"
        self.assertEqual((units / "multi-user.target.wants/NetworkManager.service").readlink().name, "NetworkManager.service")
        for unit in ("systemd-networkd.service", "systemd-networkd.socket", "iwd.service"):
            self.assertEqual(str((units / unit).readlink()), "/dev/null")
        self.assertTrue((units / "multi-user.target.wants/systemd-resolved.service").is_symlink())
        self.assertTrue((FS / "etc/resolv.conf").is_symlink())

    def test_artwork_and_manifest_contract(self):
        config = json.loads((FS / "etc/fastfetch/config.jsonc").read_text())
        artwork = FS / config["logo"]["source"].lstrip("/")
        self.assertEqual(artwork.read_bytes(), (ROOT / "fastfetch-text").read_bytes())
        self.assertEqual(config["logo"]["position"], "top")
        packages = [line.strip() for line in (PROFILE / "packages.x86_64").read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(len(packages), len(set(packages)))
        self.assertTrue({"fish", "fuse2", "fastfetch", "lightdm", "lightdm-gtk-greeter",
                         "xfce4-session", "xfce4-panel", "thunar", "xorg-server",
                         "qt6-virtualkeyboard", "networkmanager", "network-manager-applet",
                         "cosmic-terminal", "kdialog", "firefox", "nftables"}.issubset(packages))
        self.assertFalse({"plasma-desktop", "plasma-workspace", "sddm", "xorg-xwayland"} & set(packages))

    def test_nftables_workstation_firewall(self):
        rules = (FS / "etc/nftables.conf").read_text()
        self.assertIn('table inet starch_filter', rules)
        self.assertIn('ct state { established, related } accept', rules)
        self.assertIn('chain input {', rules)
        self.assertIn('hook input priority filter; policy drop;', rules)
        self.assertIn('hook forward priority filter; policy drop;', rules)
        self.assertIn('hook output priority filter; policy accept;', rules)
        service = FS / "etc/systemd/system/multi-user.target.wants/nftables.service"
        self.assertEqual(str(service.readlink()), "/usr/lib/systemd/system/nftables.service")

    def test_installer_uses_x11_across_sudo(self):
        launcher = (FS / "usr/local/bin/starch-install").read_text()
        self.assertIn("--preserve-env=DISPLAY,XAUTHORITY", launcher)
        self.assertIn("export QT_QPA_PLATFORM=xcb", launcher)
        self.assertIn("kdialog --title", launcher)
        self.assertIn('standard "Standard keyboard" on', launcher)
        self.assertIn("--standard-keyboard", launcher)
        self.assertIn("unset QT_IM_MODULE", launcher)
        self.assertIn("--on-screen-keyboard", launcher)
        self.assertIn("export QT_IM_MODULE=qtvirtualkeyboard", launcher)
        self.assertNotIn("--preserve-env=WAYLAND_DISPLAY,XDG_RUNTIME_DIR", launcher)

    def test_linux_update_utility_archiso_permissions(self):
        profiledef = (PROFILE / "profiledef.sh").read_text()
        expected = {
            "/usr/local/bin/linux-update-utility.AppImage": "0:0:755",
            "/usr/share/starch-installer/target-overlay/usr/local/bin/linux-update-utility.AppImage": "0:0:755",
            "/usr/share/icons/hicolor/scalable/apps/linux-update-utility.svg": "0:0:644",
            "/usr/share/applications/linux-update-utility.desktop": "0:0:644",
        }
        for path, ownership_and_mode in expected.items():
            self.assertIn(f'["{path}"]="{ownership_and_mode}"', profiledef)
