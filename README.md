# Stock Desktop

Acompanhe ações da B3 no Ubuntu/GNOME — preço, variação e gráfico. Funciona como janela ou widget no desktop.

## Instalar (.deb)

Baixe o `.deb` na [página de Releases](https://github.com/Miguel-Pezzini/stock-market-graphs/releases) e instale:

```bash
sudo apt install ./stock-desktop_*.deb
stock-desktop
```

Na primeira vez, configure o token da [brapi.dev](https://brapi.dev) nas configurações do app (ou em `~/.config/stock-desktop/token`).

## Instalar do código (dev)

```bash
git clone https://github.com/Miguel-Pezzini/stock-market-graphs.git
cd stock-market-graphs

sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m src.main
```

## Gerar o .deb

```bash
./scripts/build-deb.sh
# saída: dist/stock-desktop_0.1.0_*.deb
```

## Config

Tickers, tema e modo (`normal` ou `desktop_widget`) em `~/.config/stock-desktop/config.json`.
