# Rangalipi


# USE JetBrainsMono Nerd Font AND FiraCode Nerd Font Mono (Retina)

Without them every icon renders as tofu boxes. Get both from `scoop`
(`nerd-fonts/JetBrainsMono-NF`, `nerd-fonts/FiraCode-NF`,
`nerd-fonts/FiraCode-NF-Mono`) or nerdfonts.com, then set them as the
four `--*-font` vars at the top of `styles.css` (preset block included).

Original Rangalipi palette: 12 hand-built themes (base + Ember, Mossfern,
Wine, Dune, Matcha, Espresso, Noir, Aubergine, Clay, Olive, Light), each
with its own folk-motif artwork, bar runner, and full hue set. Komorebi
workspaces, system stats, media with full controls, and one suckless
palette picker for all 12 palettes (Light is for bright wallpapers).





## Features

- **Opaque islands**: solid theme-tinted bar and popups, readable on light and dark wallpapers (bar blur stays off)
- **Palette browser**: flexbox switcher for the 12 Rangalipi palettes, live search
- **Komorebi set**: workspaces, layout, control, stack widgets
- **Full media**: thumbnail, controls, bounce titles, progress, volume
- **Monitors**: CPU, GPU, memory, disk, traffic, integer readouts, statuses
- **Zero flash**: launchers run through a hidden runner process
- **RDP-proof**: remote windows ignored by class, exe and title
- **Boot-proof**: ordered login chain plus a verifying one-shot setup script



## Installation

Full guide with fonts, tools, switching, and troubleshooting:
[`docs/INSTALL.md`](docs/INSTALL.md)

1. **Fonts**: install `JetBrainsMono Nerd Font` and
   `FiraCode Nerd Font Mono` (Retina), plus `Segoe Fluent Icons`.
2. Run the replicator â€” it backs up live files, deploys the bar + artwork +
   WM configs, builds the tools and verifies everything:
   `powershell -ExecutionPolicy Bypass -File tools\setup\yasb-setup.ps1`
   Tested on YASB v2.0.7, Komorebi 0.1.41, GlazeWM 3.10.1.
3. Companion tools ship as source only (no binaries) under `tools\`
   (theme CLI, palette picker) and `yasb-theme\` (Rust source).
   Without the built exes the bar still works; only the palette button
   needs rebinding. WM configs live in `configs\` (deployed by the script).



  deploys bar + artwork + WM configs, builds the exes, verifies the chain.
  Idempotent, safe to re-run.
  (`list|current|set|next|prev`) and deploys `silent-run.exe`.
  (palette browser) from the only Python source left.