import json
import hashlib
from pathlib import Path
import tempfile
from graphics import select_packages
from profiles import DESKTOP, PROFILE, verified_bundle
from repositories import prepare_lite_keyring
from runtime import DATA, STATE, check_disk_tree, command, deactivate_disk, microcode, output, read_manifest, selected_disk


def run(gs):
    gs.insert('starchProfile', PROFILE)
    lite_archives = verified_bundle(DATA / 'lite')
    if gs.value('partitionChoices') != {'install': 'erase', 'swap': 'none'}:
        raise RuntimeError('Only erase-disk installation without disk swap is supported.')
    disk = selected_disk(gs)
    command(['udevadm', 'settle'], timeout=30)
    tree = json.loads(output(['lsblk', '--json', '--tree', '--bytes', '--paths', '--output',
                              'PATH,TYPE,SIZE,RO,MOUNTPOINTS', '--', disk]))
    deactivate_disk(tree, disk)
    command(['udevadm', 'settle'], timeout=30)
    tree = json.loads(output(['lsblk', '--json', '--tree', '--bytes', '--paths', '--output',
                              'PATH,TYPE,SIZE,RO,MOUNTPOINTS', '--', disk]))
    check_disk_tree(tree, disk)
    STATE.mkdir(mode=0o700, exist_ok=True)
    (STATE / 'selection.json').unlink(missing_ok=True)
    packages = read_manifest(DATA / 'minimal-packages.txt') + microcode(Path('/proc/cpuinfo').read_text())
    db = Path(tempfile.mkdtemp(prefix='sync-', dir=STATE))
    (db / 'local').mkdir()
    config_path = DATA / 'pacman-lite.conf'
    keyring_args = ['--gpgdir', prepare_lite_keyring(lite_archives, STATE)]
    args = ['pacman', '--config', config_path, *keyring_args, '--dbpath', db,
            '--logfile', STATE / 'pacman-preflight.log']
    command([*args, '-Sy', '--noconfirm'], timeout=300)
    gpu_packages = select_packages(args, STATE)
    packages = list(dict.fromkeys(packages + gpu_packages))
    command([*args, '-Sp', '--print-format', '%n %v', '--', *packages], timeout=120)
    # Resolve the local integration package against Artix and Arch extra.
    # The bundle has already been authenticated against its ISO manifest.
    config = STATE / 'lite-preflight.conf'
    config.write_text(config_path.read_text().replace(
        'LocalFileSigLevel = Required', 'LocalFileSigLevel = Optional'))
    command(['pacman', '--config', config, *keyring_args, '--dbpath', db, '-Up',
             '--print-format', '%n %v', '--', *lite_archives], timeout=120)
    # Recheck after network operations, immediately before partition jobs run.
    check_disk_tree(json.loads(output(['lsblk', '--json', '--tree', '--bytes', '--paths', '--output',
                                     'PATH,TYPE,SIZE,RO,MOUNTPOINTS', '--', disk])), disk)
    # Record only the resolved selection; no credentials or full global storage.
    (STATE / 'selection.json').write_text(json.dumps({
        'disk': disk, 'packages': packages, 'profile': PROFILE,
        'desktop': DESKTOP,
        'repositories_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
        'lite_bundle_sha256': hashlib.sha256((DATA / 'lite/bundle.json').read_bytes()).hexdigest()}))
