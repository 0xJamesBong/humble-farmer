# FreqTrade (core stack)

Binance, majors **BTC/USDT**, **ETH/USDT**, **SOL/USDT**, **4h** timeframe, spot dry-run by default.

## Quickstart

From this directory:

```bash
docker compose pull
docker compose run --rm freqtrade create-userdir --userdir user_data
# If user_data already exists, skip create-userdir.

docker compose run --rm freqtrade download-data \
  --pairs BTC/USDT ETH/USDT SOL/USDT \
  --exchange binance \
  --timeframes 4h \
  --days 800

docker compose run --rm freqtrade backtesting \
  --config user_data/config.json \
  --strategy MajorsTrend4h \
  --timerange 20240101-
```

Try other strategies: `MajorsRsiMeanRev4h`, `MajorsBreakout4h` (change `--strategy`).

Strategies live in [user_data/strategies/](user_data/strategies/): trend / momentum (`MajorsTrend4h`), mean reversion (`MajorsRsiMeanRev4h`), Donchian-style breakout (`MajorsBreakout4h`). Tune thresholds and ROI after you have data; then use FreqTrade hyperopt on parameters you expose with `DecimalParameter` / `IntParameter` in the strategy class.

## Live / dry-run bot + FreqUI

```bash
docker compose up -d
```

Open `http://localhost:8081` (host port maps to API in container). Set `api_server.username` / `password` in `user_data/config.json` before exposing the network.

## Futures / margin

Config is **spot** today. For long/short and margin, switch to Binance futures in FreqTrade docs (`trading_mode`, pair names, leverage) once you are ready—do not mix spot and futures assumptions in the same config without reading the official migration notes.
