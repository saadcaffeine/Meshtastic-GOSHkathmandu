# Contributing

Thanks for helping! This project is meant to be friendly to first-time contributors and to people new to LoRa.

## Ways to help

- **Report what worked or didn't** on your boards: open an [issue](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu/issues) with the board, firmware version and what you saw.
- **Improve the guide** in `docs/`: fix mistakes, add photos of your setup, or translate a page (Nepali translations especially welcome).
- **Improve the panel or tools:** keep `python server.py --mock` working, because it's how everyone tests without hardware.

## Before you open a pull request

1. Try the panel with `--mock`, and with a real board if you have one.
2. **Never commit secrets or private data**: no `meshtastic --info` output, WiFi passwords, private or channel keys, or exact home positions. `.gitignore` already excludes `panel/data/` and `tools/report_*.json`.
3. Keep the guide's tone plain and practical; link to the official [Meshtastic docs](https://meshtastic.org/docs/introduction/) rather than copying them.

## Preview the guide locally (optional)

GitHub Pages builds `docs/` automatically. To preview it on your computer, install Ruby and the [github-pages gem](https://github.com/github/pages-gem), then run `bundle exec jekyll serve` inside `docs/`.

## License

Code contributions are accepted under GPL-3.0, and guide contributions under CC BY-SA 4.0.
