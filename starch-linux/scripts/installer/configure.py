import re

from runtime import chroot, put, target
from profiles import KERNEL
import lite


def run(gs):
    root = target(gs)
    kernel = KERNEL
    put(root, 'etc/os-release', 'NAME="Starch Lite"\nPRETTY_NAME="Starch Lite 1.2"\nID=starch\nID_LIKE=arch\nVERSION="1.2"\nVERSION_ID="1.2"\nVERSION_CODENAME=evergreen\nBUILD_ID=rolling\nANSI_COLOR="38;2;23;147;209"\n')
    put(root, 'etc/issue', 'Starch Lite \\r (\\l)\n\n')
    put(root, 'etc/issue.net', 'Starch Lite\n')
    put(root, 'etc/mkinitcpio.conf.d/10-starch.conf',
        'HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont block filesystems fsck)\n')
    if gs.value('firmwareType') == 'efi':
        fstab = (root / 'etc/fstab').read_text()
        match = re.search(r'^UUID=(\S+)\s+/\s+ext4\s', fstab, re.M)
        if not match:
            raise RuntimeError('Could not find the installed ext4 root UUID.')
        put(root, 'etc/kernel/cmdline', f'root=UUID={match.group(1)} rw rootfstype=ext4 init=/usr/bin/openrc-init\n')
        (root / 'boot/efi/EFI/Linux').mkdir(parents=True, exist_ok=True)
        stub = lite.efi_stub(root)
        put(root, 'etc/kernel/starch-lite-uki.conf', f'[UKI]\nStub={stub}\n')
        uki_options = ' --ukiconfig /etc/kernel/starch-lite-uki.conf'
        put(root, f'etc/mkinitcpio.d/{kernel}.preset',
            f'ALL_kver="/boot/vmlinuz-{kernel}"\n'
            'PRESETS=(\'default\')\n'
            f'default_uki="/boot/efi/EFI/Linux/starch-{kernel}.efi"\n'
            f'default_options="--splash /usr/share/starch/splash-starch.bmp{uki_options}"\n')
    chroot(root, 'usermod', '--shell', '/usr/bin/bash', 'root')
    chroot(root, 'passwd', '--lock', 'root')
    chroot(root, 'nft', '--check', '--file', '/etc/nftables.conf')
    lite.configure(root)
    chroot(root, 'mkinitcpio', '-P')
