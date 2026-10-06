---
title: Hardware for Meshtastic in Nepal - Heltec V3 and Seeed XIAO ESP32S3
description: Choosing and preparing Meshtastic boards for the NP_865 band - Heltec WiFi LoRa 32 V3 and the Seeed XIAO ESP32S3 with Wio-SX1262 kit, antennas, frequency variants and power.
---

# Hardware

**This project uses two inexpensive ESP32-S3 boards with a Semtech SX1262 LoRa radio: the Heltec WiFi LoRa 32 V3 and the Seeed XIAO ESP32S3 + Wio-SX1262 kit.** Both are officially supported by Meshtastic. Browse every supported board on the [Meshtastic devices page](https://meshtastic.org/docs/hardware/devices/).

## The boards

| | Heltec WiFi LoRa 32 V3 | Seeed XIAO ESP32S3 + Wio-SX1262 kit |
|---|---|---|
| Chip | ESP32-S3 + SX1262 | ESP32-S3 (8 MB flash, 8 MB PSRAM) + SX1262 |
| Screen | 0.96″ OLED | none |
| Size | about a matchbox | about a thumbnail (21 × 18 mm core) |
| Antenna connector | U.FL / IPEX | U.FL / IPEX |
| Paxcounter capable | yes (ESP32) | yes (ESP32) |
| Meshtastic docs | [Heltec LoRa 32](https://meshtastic.org/docs/hardware/devices/heltec-automation/lora32/) | [Wio-SX1262 + XIAO ESP32S3](https://meshtastic.org/docs/hardware/devices/seeed-studio/wio-series/wio-sx1262s/?wio-sx1262=esp32-s3) |
| Maker page | [heltec.org](https://heltec.org/project/wifi-lora-32-v3/) | [Seeed wiki](https://wiki.seeedstudio.com/xiao_esp32s3_&_wio_SX1262_kit_for_meshtastic/) · [shop](https://www.seeedstudio.com/Wio-SX1262-with-XIAO-ESP32S3-p-5982.html) |

## Buy the right frequency version

Many LoRa boards come in a **low-band** (433 / 470–510 MHz) and a **high-band** (863–928 MHz) version that look almost identical. **Nepal's `NP_865` needs the high-band version.**

- **Heltec V3:** on our board the band wasn't printed on the box. Instead there are two solder pads marked **HF** and **LF** near the radio, with a small resistor bridging one of them. Ours had the resistor on **HF** (high band). Check the listing or the board before you buy.
- **Seeed Wio-SX1262:** covers 862–930 MHz.

## Antennas

- **Always attach the antenna before powering on.** Transmitting without an antenna can damage the radio.
- Use an antenna made for **868/915 MHz**. A 433 MHz antenna is noticeably longer and works badly at 865 MHz.
- The U.FL / IPEX connector is tiny: press it straight down until it clicks. A half-seated connector can cost most of your range.
- Height beats power: a node on a rooftop or a window ledge hears far more than one on a desk.

## Power

- Both boards run from USB-C. The Heltec has a JST connector for a single-cell LiPo battery.
- In the [control panel](control-panel.md), a battery level above 100% means "powered over USB, no battery reading".

## Which firmware?

Flash with the [Meshtastic Web Flasher](https://flasher.meshtastic.org/) and choose the exact board (for example **Heltec V3**, not V2). Keep **every board on the same firmware version**. In this project, a Heltec on a newer firmware than the XIAOs could not hear them at all until it was reflashed (see [Troubleshooting](troubleshooting.md)). Release notes are on [GitHub](https://github.com/meshtastic/firmware/releases).

Next: **[Getting started](getting-started.md)** →
