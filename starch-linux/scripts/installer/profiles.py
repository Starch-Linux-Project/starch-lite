"""Installed-system identity and Lite bundle verification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess


LITE_PACKAGES = ('starch-lite',)
LITE_BUNDLE_PACKAGES = ('starch-lite', 'artix-keyring')
PROFILE = 'lite-xfce'
DESKTOP = 'xfce'
KERNEL = 'linux-zen'


def validate_selection(gs):
    if gs.value('starchProfile') != PROFILE:
        raise RuntimeError('The Starch Lite installation profile changed after preflight.')


def verified_bundle(directory):
    """Reject obsolete custom runtimes as well as modified bundle inputs."""
    directory = Path(directory)
    manifest = directory / 'bundle.json'
    if directory.is_symlink() or manifest.is_symlink() or not manifest.is_file():
        raise RuntimeError('The Starch Lite bundle is missing from this ISO. Rebuild the ISO.')
    try:
        bundle = json.loads(manifest.read_text())
        entries = bundle['packages']
        if (bundle['format'] != 3 or bundle['repositories'] != 'artix-arch-extra'
                or [e['name'] for e in entries] != list(LITE_BUNDLE_PACKAGES)):
            raise ValueError('unexpected bundle format or package set')
        result = []
        for entry in entries:
            name, filename, digest = entry['name'], entry['filename'], entry['sha256']
            if (not re.fullmatch(re.escape(name) + r'-[0-9][A-Za-z0-9.+_:-]*-(?:x86_64|any)\.pkg\.tar\.zst', filename)
                    or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                raise ValueError('invalid package filename or checksum')
            path = directory / filename
            if path.is_symlink() or not path.is_file():
                raise ValueError('package must be a regular file')
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f'checksum mismatch: {filename}')
            if name == "starch-lite":
                verify_lite_archive(path)
            result.append(path)
        return result
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f'Invalid Starch Lite bundle: {error}') from error


def verify_lite_archive(path):
    """Inspect the archive, not just its filename or self-reported bundle hash."""
    try:
        info = subprocess.check_output(['bsdtar', '-xOf', str(path), '.PKGINFO'], text=True, timeout=30)
        names = subprocess.check_output(['bsdtar', '-tf', str(path)], text=True, timeout=30).splitlines()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f'Cannot inspect Lite archive: {path}') from error
    if 'pkgname = starch-lite\n' not in info or 'pkgver = 0.2.2-19\n' not in info:
        raise RuntimeError('Obsolete or unreviewed Lite package; rebuild the bundle (expected 0.2.2-19).')
    forbidden = {'audio-session', 'starch-audio.desktop', 'configure-pam', '95-starch-lite-pam.hook'}
    if any(Path(name.rstrip('/')).name in forbidden for name in names):
        raise RuntimeError('Lite archive contains retired audio/PAM integration.')
    retired_profiles = {'legacy-desktop-config', 'legacy-wayland-sessions',
                        'plasma-session', 'plasma-session-inner', 'startkderc'}
    if any(retired_profiles.intersection(Path(name).parts) for name in names):
        raise RuntimeError('Lite archive contains retired desktop integration.')
