# Catppuccin-Glass

> A sleek, glassy YASB status bar theme built on Catppuccin Mocha — featuring Komorebi workspace integration, live media controls, CPU temperature, while keeping it minimal with a pill based design.

![Preview](https://i.imgur.com/KRRoCua.png)

---

## ⚠️ IMPORTANT — CPU Temp Widget Setup

This widget requires **LibreHardwareMonitor** running in the background. If you don't want it, skip to the [Removing CPU Temp](#removing-cpu-temp) section below.

**First time setup:**

1. Download [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) from the official GitHub releases page
2. Extract and run `LibreHardwareMonitor.exe` as **Administrator**
3. Go to **Options → Web Server → Run**
4. Verify it works by opening `http://localhost:8085` in your browser
5. To make it start minimized to tray on every boot:
   - **Options → Start Minimized** ✓
   - **Options → Minimize To Tray** ✓
   - **Options → Run On Windows Startup** ✓

**Finding your sensor ID:**

Open `http://localhost:8085` in your browser and find your CPU temperature sensor path. Common examples:

Intel: /intelcpu/0/temperature/12
AMD:   /amdcpu/0/temperature/0

Update it in `config.yaml`:

cpu_temp:
  options:
    sensor_id: "/intelcpu/0/temperature/12"  # replace with your sensor path

### Removing CPU Temp

If you don't want the CPU temp widget, remove `"cpu_temp"` from the right widgets list in `config.yaml`:

right: ["memory", "wifi", "volume", "battery", "notifications"]

Then delete the entire `cpu_temp:` widget block from the widgets section.

---

## Bar Layout

[ ⊞  ○ ━━━ ○ ○ ○  App Name ]   [ Date · Media Controls · Apps ]   [  RAM ·  Temp  ·  WiFi  · Vol · Bat · 🔔 ]
  ↑        ↑          ↑             ↑          ↑            ↑         ↑        ↑       ↑
Power   Workspaces  Active         Clock      Media        Center     Memory  CPU     WiFi
Menu               Window                     Player       Grouper    Widget  Temp    Menu

---

## Widgets — What Each Does

### ⊞ Power Menu (Left)
Click the Windows icon on the far left to open the power menu.

<img width="1919" height="1069" alt="Power Menu" src="https://github.com/user-attachments/assets/cbdec2d2-c0d8-4392-bc8d-33cbfe9d4007" />

<br><br>
Options: Shut Down · Restart · Lock · Sign Out · Hibernate · Sleep · Cancel

Uptime is shown at the bottom of the power menu.

---

### ○ ━━━ ○ ○ ○ Komorebi Workspaces (Left)
Shows your active Komorebi tiling window manager workspaces. The active workspace appears as a wider filled pill. Populated workspaces show a small dot.

**Don't use Komorebi?** Remove it from your config:

In `config.yaml`, find this line under `widgets > left`:

left: ["power_menu", "komorebi_workspaces", "active_window"]

Change it to:

left: ["power_menu", "active_window"]

Then remove the `komorebi_workspaces` widget block entirely from the widgets section. It will look something like this:

<img width="1920" height="58" alt="No Komorebi" src="https://github.com/user-attachments/assets/e9d69533-ccaf-43c1-9351-c6908720e35d" />

---

### Media Controls (Center)
Shows currently playing track from Spotify, Apple Music, or any media source. Note: Apple Music does not support playback progress — everything else works fine.

- **Left click** — opens media popup with album art, progress bar and volume
- **Right click** — toggles between `Song - Artist` and `Artist - Song` display
<br><br>
<img width="1919" height="1021" alt="Media Player" src="https://github.com/user-attachments/assets/d7448717-df06-46ef-8f88-15e5079ae647" />

---

### Center Grouper — App Shortcuts (Center)
The pill-shaped group in the center contains quick launch icons:

| Icon | Action |
|------|--------|
| 🔔 | Opens Windows Notification Center |
| 🔍 | Opens Windows Settings search — I personally use [Flow Launcher](https://www.flowlauncher.com/) instead of Windows Search, which is why this opens Settings search rather than the default |
| ⋮⋮⋮ | Opens Komorebi Control menu — start, stop, or reload Komorebi |
| 🏞️ | Opens Wallpaper Gallery — browse and set wallpapers from your folder |
| 📊 | Opens Task Manager 
| `>_` | Opens Windows Terminal as **Administrator** — use with caution |
| 🎚️ | Opens Windows Quick Settings |

**Komorebi Control popup:**

<img width="1919" height="1010" alt="Komorebi Control" src="https://github.com/user-attachments/assets/31220426-895a-401a-9cc8-1c0773dca3a3" />
<br><br>
Komorebi starts automatically on boot via `komorebic start --whkd`. Use this menu if you need to manually restart or stop it or pause it.

---

### Wallpaper Gallery
Click the wallpaper icon in the center grouper to browse your wallpaper collection in a glassy gallery popup.

**Setting your wallpaper folder:**

In `config.yaml`, find the wallpapers widget and update the path:

wallpapers:
  options:
    image_path: "C:\\Users\\YourName\\YourWallpaperFolder"

Replace `YourName` with your Windows username and `YourWallpaperFolder` with the name of your wallpaper folder.

---

### WiFi Widget (Right)
Shows WiFi signal strength percentage. **Left click** opens the WiFi network menu.
<br><br>
<img width="1919" height="1011" alt="WiFi Menu" src="https://github.com/user-attachments/assets/73648a9c-183e-4223-a6d4-575c01b6e92c" />
<br><br>
**Right click** toggles between signal percentage and network name.

---

## Final Note

You can use this however you like, but I personally use it without a Windows taskbar. Everything you need like app switching, system stats, media, workspaces  is right here at the top. For launching apps, [Flow Launcher](https://www.flowlauncher.com/) is recommended as a fast keyboard-driven launcher.

<img width="1919" height="1077" alt="Full Setup" src="https://github.com/user-attachments/assets/282259d8-5af2-4d63-b54c-0b5330446c04" />  
<br><br>

For a complete setup, I personally use [Windhawk](https://windhawk.net/) with the Squircle taskbar mod for a minimal-style taskbar at the bottom, keeping the YASB bar clean and distraction-free at the top.

<br><br>
<img width="1919" height="1079" alt="Screenshot 2026-04-25 152203" src="https://github.com/user-attachments/assets/504c0bd0-b6ef-4bcc-bc9b-a5833a0b6718" />

---

## Requirements

| Tool | Purpose | Link |
|------|---------|------|
| YASB | Status bar | [github.com/amnweb/yasb](https://github.com/amnweb/yasb) |
| Komorebi | Tiling window manager | [github.com/LGUG2Z/komorebi](https://github.com/LGUG2Z/komorebi) |
| whkd | Hotkey daemon for Komorebi | [github.com/LGUG2Z/whkd](https://github.com/LGUG2Z/whkd) |
| JetBrainsMono NFP | Nerd Font for icons | [nerdfonts.com](https://www.nerdfonts.com/font-downloads) |
| Segoe UI Variable | System UI font | Included with Windows 11 |
| LibreHardwareMonitor | CPU temp readings | [GitHub Releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) |

**Liked the theme? Dont forget to give me a ⭐ on this github repo | [Repository link](https://github.com/PraBuDDha1x1/Catppucin-Glass) |**

**Thanks for reading this much Here's a Cookie for the road: 🍪**

---

## Credits

Built with [YASB](https://github.com/amnweb/yasb) by amnweb. Inspired by the design of yasb-004.
Catppuccin color palette by [catppuccin](https://github.com/catppuccin/catppuccin).
Theme by [PRABUDDHA1x1](https://github.com/PRABUDDHA1x1).
