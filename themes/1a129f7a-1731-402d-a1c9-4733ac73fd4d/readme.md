# YASB Catppuccin Mocha

A clean & minimal YASB theme inspired by the Catppuccin Mocha color palette, focusing on a calm dark aesthetic with subtle accents, simple layouts & a distraction-free desktop experience.

## Requirements

- Windows 10 or Windows 11
- Latest version of [YASB](https://github.com/amnweb/yasb)
- [JetBrainsMono Nerd Font](https://www.nerdfonts.com/font-downloads) or another compatible Nerd Font
- [GlazeWM](https://github.com/glzr-io/glazewm) if you want to use the GlazeWM workspace & binding mode widgets

## Installation

1. Install YASB & make sure it is working correctly.
2. Install JetBrainsMono Nerd Font.
3. Copy `config.yaml` & `styles.css` into your YASB configuration directory.
4. Restart or reload YASB.
5. If you use GlazeWM, make sure it is running for the workspace widgets to work correctly.

## Theme Structure

MochaYASB/
├── config.yaml
├── styles.css

## Features

- Catppuccin Mocha color palette
- Minimal dark bar design
- Subtle colored widget accents
- GlazeWM workspace integration
- CPU, GPU & memory monitoring
- Network traffic monitoring
- Wi-Fi status
- Disk usage
- Battery status
- Volume controls
- Control center
- Calendar & clock
- Power menu
- Interactive system information popups
- JetBrains Mono Nerd Font styling

## Configuration

The theme uses a 34px top bar with widgets divided into three sections:

- Left: Home, GlazeWM workspaces & binding mode
- Center: Clock
- Right: Window controls, control center, network & system information

You can freely modify `config.yaml` to add, remove or rearrange widgets.

## Customization

The main colors are defined at the beginning of `styles.css` using CSS variables. You can change these values to customize the theme while keeping the overall design consistent.

--background: rgba(30, 30, 46, 0.9);
--accent: #94e2d5;
--text: #cdd6f4;
--border: #b4befe;

The theme uses a zero-radius design for the bar widgets while popups use rounded corners for a subtle contrast.

## Notes

Some widgets depend on your system configuration. In particular, the GlazeWM widgets require GlazeWM to be installed & running.

The disk widget is currently configured for the C: drive. If your Windows installation uses a different drive, update `volume_label` in `config.yaml`.

The theme uses Font Awesome/Nerd Font glyphs for many of its icons. If icons appear incorrectly, check that JetBrainsMono Nerd Font is installed & selected correctly.

## Credits

- Theme: Catppuccin Mocha Minimalism
- Built for: YASB
- Color palette: Catppuccin Mocha
- Font: JetBrainsMono Nerd Font
- Window manager integration: GlazeWM