#!/usr/bin/env python3
"""Stage maintained installer inputs into a fresh archiso profile snapshot."""
from pathlib import Path
import hashlib
import re
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[2]

LUU_FILES = {
    'appimage': Path('usr/local/bin/linux-update-utility.AppImage'),
    'icon': Path('usr/share/icons/hicolor/scalable/apps/linux-update-utility.svg'),
    'desktop': Path('usr/share/applications/linux-update-utility.desktop'),
}

WALLPAPER_SUFFIXES = {'.avif', '.bmp', '.gif', '.jpeg', '.jpg', '.jxl', '.png', '.svg', '.tif', '.tiff', '.webp'}
EVERGREEN_SOURCE = 'wyxina-tree-8559118.jpg'


def stage_wallpapers(fs, input_dir=None):
    """Stage wallpaper images for the live and installed Xfce desktops."""
    input_dir = Path(input_dir) if input_dir is not None else SOURCE / 'wallpapers'
    if not input_dir.exists():
        return
    if input_dir.is_symlink() or not input_dir.is_dir():
        raise RuntimeError('wallpapers must be a real directory')
    images = sorted(path for path in input_dir.rglob('*')
                    if path.suffix.lower() in WALLPAPER_SUFFIXES)
    if any(path.is_symlink() or not path.is_file() for path in images):
        raise RuntimeError('Wallpaper inputs must be regular, non-symlink files')

    overlay = fs / 'usr/share/starch-installer/target-overlay'
    for source in images:
        relative = source.relative_to(input_dir).as_posix()
        slug = re.sub(r'[^a-z0-9]+', '-', source.stem.lower()).strip('-') or 'wallpaper'
        digest = hashlib.sha256(relative.encode()).hexdigest()[:8]
        package_name = f'Starch-{slug}-{digest}'
        if relative == EVERGREEN_SOURCE:
            package_name = 'Starch-Evergreen'
        image_name = f'3840x2160{source.suffix.lower()}'
        for root in (fs, overlay):
            package = root / 'usr/share/wallpapers' / package_name
            destination = package / 'contents/images' / image_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)


def stage_luu(fs, input_dir=None):
    """Install local LUU inputs into the live image and installed-system overlay."""
    input_dir = Path(input_dir) if input_dir is not None else SOURCE.parent / 'luu-input'
    appimages = list(input_dir.glob('*.AppImage'))
    icons = list(input_dir.glob('*.svg'))
    if not appimages and not icons:
        return
    if len(appimages) != 1 or len(icons) != 1:
        raise RuntimeError('luu-input must contain exactly one *.AppImage and one *.svg file')
    if any(path.is_symlink() or not path.is_file() for path in (*appimages, *icons)):
        raise RuntimeError('Linux Update Utility inputs must be regular, non-symlink files')

    desktop = SOURCE / 'packages/linux-update-utility/linux-update-utility.desktop'
    sources = {'appimage': appimages[0], 'icon': icons[0], 'desktop': desktop}
    overlay = fs / 'usr/share/starch-installer/target-overlay'
    for name, relative in LUU_FILES.items():
        mode = 0o755 if name == 'appimage' else 0o644
        for root in (fs, overlay):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sources[name], destination)
            destination.chmod(mode)


def stage_lite(fs, input_dir):
    destination = fs / 'usr/share/starch-installer/lite'
    if input_dir is None:
        return
    sys.path.insert(0, str(SOURCE / 'scripts/installer'))
    from profiles import verified_bundle
    archives = verified_bundle(input_dir)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for archive in archives:
        shutil.copyfile(archive, destination / archive.name)
    shutil.copyfile(Path(input_dir) / 'bundle.json', destination / 'bundle.json')


def stage_live_xfce(fs):
    """Reuse Lite desktop defaults without installing Artix services."""
    integration = SOURCE / 'packages/starch-lite/integration/root'
    defaults = integration / 'usr/share/starch-lite'
    files = {
        'usr/lib/starch-lite/xfce-defaults': integration / 'usr/lib/starch-lite/xfce-defaults',
        'usr/share/starch-lite/xfce-panel.xml': defaults / 'xfce-panel.xml',
        'usr/share/xfce4/helpers/starch-cosmic-terminal.desktop':
            integration / 'usr/share/xfce4/helpers/starch-cosmic-terminal.desktop',
        'etc/xdg/autostart/starch-xfce-defaults.desktop':
            defaults / 'xfce-config/autostart/starch-xfce-defaults.desktop',
        'etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml':
            defaults / 'xfce-panel.xml',
    }
    for relative, source in files.items():
        destination = fs / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copytree(defaults / 'xfce-config/xfce4', fs / 'etc/skel/.config/xfce4', dirs_exist_ok=True)


def stage(profile, luu_input=None, wallpaper_input=None, lite_input=None):
    fs = profile / 'airootfs'
    # Keep live and installed banners sourced from the maintained root artwork.
    artwork = fs / 'usr/share/starch/fastfetch-text'
    artwork.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / 'fastfetch-text', artwork)
    config = fs / 'etc/calamares'
    shutil.copytree(SOURCE / 'calamares', config, dirs_exist_ok=True)
    stage_lite(fs, lite_input)
    data = fs / 'usr/share/starch-installer'
    data.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / 'manifests/minimal-packages.txt', data / 'minimal-packages.txt')
    shutil.copyfile(SOURCE / 'calamares/pacman-lite.conf', data / 'pacman-lite.conf')
    runtime = fs / 'usr/lib/starch-installer'
    shutil.copytree(SOURCE / 'scripts/installer', runtime, ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=True)
    for name in ('preflight', 'bootstrap', 'configure', 'limine', 'validate'):
        (config / 'modules' / f'starch-{name}.conf').write_text('{}\n')
        module = fs / 'usr/lib/calamares/modules' / f'starch-{name}'
        module.mkdir(parents=True, exist_ok=True)
        (module / 'module.desc').write_text(f'type: job\nname: starch-{name}\ninterface: python\nscript: main.py\nweight: {20 if name == "bootstrap" else 1}\n')
        entrypoint = f'{name}.run'
        (module / 'main.py').write_text(
            'import sys\nimport libcalamares\n'
            'sys.path.insert(0, "/usr/lib/starch-installer")\n'
            f'import {name}\nfrom runtime import run_stage\n\n'
            f'def pretty_name():\n    return "Starch Lite: {name}"\n\n'
            f'def run():\n    return run_stage("{name}", libcalamares.globalstorage, {entrypoint})\n')
    overlay = data / 'target-overlay'
    # Copy the target defaults explicitly to keep live credentials and services out.
    for relative in ('etc/nftables.conf', 'etc/fastfetch/config.jsonc',
                     'usr/share/starch/fastfetch-text', 'usr/share/starch/splash-starch.bmp'):
        destination = overlay / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fs / relative, destination)
    fish = overlay / 'etc/fish/conf.d/10-starch.fish'
    fish.parent.mkdir(parents=True, exist_ok=True)
    fish.write_text('if status is-interactive; and test (id -u) -ne 0\n    fastfetch\nend\n')
    stage_live_xfce(fs)
    stage_luu(fs, luu_input)
    stage_wallpapers(fs, wallpaper_input)


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3, 4):
        sys.exit('Usage: stage-installer.py SNAPSHOT_PROFILE [LUU_INPUT [WALLPAPER_INPUT]]')
    profile = Path(sys.argv[1]).resolve()
    if profile == (SOURCE / 'archiso/profile').resolve() or not (profile / 'profiledef.sh').is_file():
        sys.exit('Installer staging requires a generated profile snapshot.')
    stage(profile, sys.argv[2] if len(sys.argv) >= 3 else None,
          sys.argv[3] if len(sys.argv) == 4 else None,
          SOURCE / 'build/starch-lite/artix-repo')
