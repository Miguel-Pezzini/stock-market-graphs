# Stock Desktop

Track B3 stocks on Ubuntu/GNOME — price, change, and chart. Works as a window or desktop widget.

## Install (.deb)

Download the `.deb` from [Releases](https://github.com/Miguel-Pezzini/stock-market-graphs/releases) and install:

```bash
sudo apt install ./stock-desktop_*.deb
stock-desktop
```

On first run, set your [brapi.dev](https://brapi.dev) token in the app settings (or in `~/.config/stock-desktop/token`).

## Install from source (dev)

```bash
git clone https://github.com/Miguel-Pezzini/stock-market-graphs.git
cd stock-market-graphs

sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m src.main
```

## Build the .deb

```bash
./scripts/build-deb.sh
# output: dist/stock-desktop_0.1.0_*.deb
```

## Config

Tickers, theme, and mode (`normal` or `desktop_widget`) live in `~/.config/stock-desktop/config.json`.
