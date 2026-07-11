# Claude Usage Tray

**English** | [ไทย](README.th.md)

![Claude Usage Tray](docs/hero.png)

A lightweight Windows system-tray application that monitors your **Claude Code**
token usage in real time. The tray icon changes colour as your quota runs down,
and a single click opens an elegant dashboard with a circular usage gauge — so you
always know how much of your 5-hour and weekly quota you have left without opening
a terminal.

Free and open source (MIT). Works with any Claude subscription (Pro, Max, Team)
that you have logged into through Claude Code.

---

## Table of contents

- [Features](#features)
- [How the colours work](#how-the-colours-work)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [First run — connecting your Claude account](#first-run--connecting-your-claude-account)
- [Using the app](#using-the-app)
- [Configuration](#configuration)
- [Building from source](#building-from-source)
- [Troubleshooting](#troubleshooting)
- [Privacy and Terms of Service](#privacy-and-terms-of-service)
- [License](#license)

---

## Features

- **Live quota in your tray** — reads the same 5-hour session and weekly limits
  that Claude Code's own `/usage` command uses, so the numbers match exactly.
- **Colour-coded icon** — green, orange, or red depending on how much quota
  remains. You can read your status at a glance without opening anything.
- **Big, legible percentage** — the remaining percentage is drawn large in the
  centre of the icon and stays readable even at 16–32 px.
- **Graphical dashboard** — a dark-themed window with a glowing circular gauge,
  selectable quota cards, reset countdowns, and a refresh button.
- **Threshold alerts** — an on-screen popup and a tray notification appear the
  moment your remaining quota crosses below 50% and below 20%.
- **Runs quietly** — polls every 3 minutes (safe against rate limits), sits in the
  tray, and can start automatically with Windows.
- **Two ways to ship** — a single portable `.exe`, or a one-click installer.

---

## How the colours work

The icon is coloured by how much quota you have **left** (not how much you have used).

![Status colours](docs/states.png)

| Colour | Remaining quota | Meaning |
|--------|-----------------|---------|
| Green  | more than 50%   | Healthy — work freely |
| Orange | 50% or less     | Low — start pacing yourself |
| Red    | 20% or less     | Critical — the icon blinks and a popup warns you |

When more than one quota is active (for example the 5-hour window and the weekly
cap), the icon always reflects **whichever one is lowest**, so you are never caught
out by the limit you were not watching. All thresholds are configurable.

---

## How it works

![How it works](docs/how-it-works.png)

1. You log in to Claude through **Claude Code** (the official CLI) one time.
2. Claude Code stores your access token locally in `~/.claude/.credentials.json`.
3. Claude Usage Tray reads that token and calls
   `https://api.anthropic.com/api/oauth/usage` — read-only — to fetch your current
   quota percentages and reset times.
4. The tray icon colour and the dashboard gauge update.

Your token never leaves your PC. The app only reads it locally to display your own
usage, and it communicates with `api.anthropic.com` only.

---

## Requirements

- Windows 10 or Windows 11.
- **Claude Code** installed and logged in with a Claude subscription
  (Pro, Max, or Team). The app reads the account you are logged into.
  - Install Claude Code: `npm install -g @anthropic-ai/claude-code`

You do **not** need Python installed to run the released `.exe`.

---

## Installation

Pick either option.

### Option 1 — Installer (recommended)

1. Download `ClaudeUsageTray-Setup.exe` from the
   [Releases](https://github.com/ksmaster03/claude-usage-tray/releases) page.
2. Run it. The wizard lets you choose:
   - create a desktop shortcut,
   - start automatically with Windows.
3. The app installs per-user (no administrator rights required) and can launch
   immediately after install.

To remove it later: **Settings > Apps > Claude Usage Tray > Uninstall**, or use the
"Uninstall" shortcut in the Start menu.

### Option 2 — Portable

1. Download `ClaudeUsageTray.exe` from the Releases page.
2. Put it anywhere and double-click to run. Nothing is installed.

> Note: the executable is not code-signed, so Windows SmartScreen may show an
> "unknown publisher" warning the first time you run it. Choose **More info >
> Run anyway**.

---

## First run — connecting your Claude account

The app reads the Claude account that is logged into Claude Code on this PC. Each
person who runs the app sees their own usage; there is nothing to share or paste in.

If no login is found the first time you open the app, a **Connect** window appears
and walks you through it:

1. Install Claude Code if you have not already:
   `npm install -g @anthropic-ai/claude-code`
2. Click **Open login via Claude Code** (or open a terminal, type `claude`, then
   run `/login`).
3. Sign in with your Claude account in the browser.
4. Click **Check again**. The icon turns green and starts showing your usage.

You can reopen this window any time from the tray menu:
**Connect Claude account**.

---

## Using the app

Find the icon in the system tray (bottom-right of the taskbar; click the `^` arrow
if it is hidden).

**Open the dashboard** — double-click the icon, or right-click and choose
**Details**. The dashboard shows:

- a circular gauge with the remaining percentage of the selected quota,
- a card for each quota (for example "5 hours" and "Weekly") — click a card to make
  the gauge show that quota,
- the reset countdown for each quota,
- a round refresh button to fetch the latest numbers immediately.

Drag anywhere on the window to move it; press **Esc** or the back arrow to close it.

**Right-click menu:**

| Item | What it does |
|------|--------------|
| Refresh now | Fetch the latest usage immediately |
| Details | Open the dashboard |
| Connect Claude account | Open the login / onboarding window |
| Start with Windows | Toggle automatic startup |
| Notification (balloon) | Toggle the tray notification on threshold crossings |
| Popup alert below 50% / 20% | Toggle the on-screen warning window |
| Quit | Exit the app |

**Alerts** — when your remaining quota first drops to 50% or below, and again at 20%
or below, the app shows a popup warning and (optionally) a tray notification. Each
alert fires once per crossing, so it never spams you.

---

## Configuration

Settings are stored in `~/.claude-usage-tray.json` (created automatically on first
run). Edit it with any text editor, then restart the app.

| Key | Default | Description |
|-----|---------|-------------|
| `poll_seconds` | `180` | Seconds between updates. Do **not** set below 180 — the usage endpoint rate-limits faster polling. |
| `green_above` | `50` | Remaining % above which the icon is green. |
| `orange_at` | `50` | Remaining % at or below which the icon is orange. |
| `red_at` | `20` | Remaining % at or below which the icon is red (and blinks). |
| `notify` | `true` | Show a tray notification when a threshold is crossed. |
| `popup_alert` | `true` | Show an on-screen popup when remaining drops below 50% / 20%. |
| `blink_when_red` | `true` | Blink the icon while in the red state. |
| `show_percent_text` | `true` | Draw the remaining percentage on the icon. |
| `watch` | `["five_hour", "seven_day"]` | Which quotas drive the icon colour (the lowest wins). |

---

## Building from source

Requires Python 3.10+ on Windows.

```bash
git clone https://github.com/ksmaster03/claude-usage-tray.git
cd claude-usage-tray
pip install -r requirements.txt
```

Run in development mode:

```bash
python -m claude_usage_tray
```

Build the standalone executable:

```bash
pip install pyinstaller
python build.py
# output: dist/ClaudeUsageTray.exe
```

Build the executable **and** the installer in one step:

```bat
build_all.bat
```

`build_all.bat` runs PyInstaller, then compiles `installer.iss` with
[Inno Setup](https://jrsoftware.org/isdl.php) (install it first). Outputs:

- `dist/ClaudeUsageTray.exe` — portable executable
- `dist_installer/ClaudeUsageTray-Setup.exe` — installer

Regenerate the documentation images:

```bash
python scripts/make_docs.py   # writes docs/*.png
```

### Project layout

```
claude-usage-tray/
  claude_usage_tray/
    api.py         Read the token, call the usage endpoint
    status.py      Turn the response into a status + colour
    icon.py        Draw the coloured tray icon
    dashboard.py   Render the graphical dashboard (Pillow)
    ui.py          tkinter windows: dashboard, alert, onboarding
    tray.py        Tray loop, menu, polling, alerts
    config.py      Load and save settings
    autostart.py   Start-with-Windows toggle
  app.py           Entry point used by the build
  build.py         PyInstaller build
  build_all.bat    Build exe + installer
  installer.iss    Inno Setup script
  scripts/make_docs.py  Documentation image generator
```

---

## Troubleshooting

**The icon is grey.** The app cannot find or read your token. Open Claude Code and
run `/login`, then choose **Refresh now** from the tray menu.

**"token expired" message.** Access tokens are rotated by Claude Code. Open Claude
Code (or run `/login` again) and the app will pick up the new token automatically.

**"rate limited" message.** You are polling too fast. Keep `poll_seconds` at 180 or
higher.

**SmartScreen warning on first launch.** The build is not code-signed. Choose
**More info > Run anyway**. If you prefer, build it yourself from source.

**Thai or other text looks wrong in the dashboard.** The dashboard uses fonts that
ship with Windows (Leelawadee UI, Tahoma, Segoe UI). Make sure your Windows
installation has its standard font set.

---

## Privacy and Terms of Service

This app is a read-only monitor. It reads the token that Claude Code has already
stored on your machine and uses it to fetch **your own** usage from Anthropic. It
does not store, copy, or transmit your token anywhere else.

Anthropic's terms state that OAuth tokens from consumer plans (Free, Pro, Max) are
intended for use with Claude Code and Claude.ai only. This app therefore does **not**
implement its own login — it relies entirely on the official Claude Code login and
simply reads the resulting local credentials to show you your usage. Use it with the
account you are already signed into.

---

## Credits

Inspired by [jens-duttke/usage-monitor-for-claude](https://github.com/jens-duttke/usage-monitor-for-claude)
and the wider Claude Code usage-tooling community
([ccusage](https://ccusage.com), Claude-Code-Usage-Monitor, and others).

## License

[MIT](LICENSE). Free to use, modify, and distribute.
