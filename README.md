# Starch Lite Project

Starch Lite, a personal Linux made to  serve you the endless horizons of Arch/Artix,
without roleplaying as a systems engineer. 

If you'd like to contribute to this project, understand your contribution matters
more than you likely think. I'm currently one dude spending many hours out of my 
day to make this thing happen. I really wish I could understand everything in an entire 
Linux distro, but just as Linus Torvalds stated no single person can understand the whole 
Linux Kernel, the same applies to a whole operating system. I'm not a professional developer
and I'm not some prodigy programmer. This is exactly why this project needs experts. Maybe not a 
Linux Systems Engineer, but rather someone who loves one specific part. If you love
diving into a couple niche parts of Linux, these are the kind of contributors that change
things. A jack of all trades is a master of none, a master of one will get their job done. 
I have done the best I can covering all bases, and I've learned so much from this project. 
This project has allowed me to learn so much, but at the end of the day I can't become an expert
on everything. Look through the configs, the choices I've made or anything else here, and propose
a fix to anything you think could be improved. 5 niche experts > one dude. 



# Starch Lite

Starch Lite is an x86_64 Linux distribution with a dedicated live ISO and a
graphical online installer. The live session uses Xfce on X11 with LightDM,
systemd, and the Arch `linux` kernel. Calamares installs Starch Lite directly
with Xfce, LightDM, Linux Zen, OpenRC, and Artix repositories plus Arch `extra`.

Calamares downloads fresh packages with pacstrap and erases the selected disk.
The installed system uses ext4, Limine (UEFI or BIOS), zram, NetworkManager,
PipeWire, Flatpak, and Linux Update Utility.

An optional Additional Software page accepts pacman packages and Flathub app IDs
for installation after the essential OS succeeds, with safe skipping and warnings
for optional failures. Nothing is deferred to first boot.

See [installation](starch-linux/docs/installation-profiles.md),
[supported scope](starch-linux/docs/decisions.md), and [licensing](starch-linux/docs/licensing.md).

Source: `archiso/profile/` holds the live image; `calamares/` the installer;
`manifests/` the base package list; `scripts/installer/` profile configuration;
`packages/` integrations; and `tests/` automated checks.

## Build the ISO

Place the Linux Update Utility AppImage and SVG icon in `luu-input/` at the
repository root. From that root, run:

```bash
./starch-linux/build.sh --check && ./starch-linux/build.sh --build
```

The ISO and build reports are written to `starch-out/run-*/` at the repository root.
