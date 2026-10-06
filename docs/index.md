---
title: Meshtastic LoRa mesh for Kathmandu
description: A beginner-friendly guide to Meshtastic LoRa mesh radios in Nepal (NP_865), with an open-source web control panel for Heltec V3 and Seeed XIAO ESP32S3 boards.
---

# Meshtastic LoRa mesh for Kathmandu

**This guide shows how to build a small off-grid LoRa mesh network with [Meshtastic](https://meshtastic.org/) in Nepal, using inexpensive ESP32 boards on the `NP_865` (865–868 MHz) region.** It is written for makers and hobbyists, and for people who already understand WiFi and Bluetooth but have never used LoRa.

It comes with an open-source **web control panel** that runs on a laptop or Raspberry Pi. The panel switches a board between operating modes (map reporter, Paxcounter sensor, listener) and shows live signal, packets and device counts.

![Control panel overview](assets/img/panel-overview.png)

## Start here

1. **[LoRa for WiFi and Bluetooth users](lora-for-wifi-and-bluetooth-users.md)**: what's different and why it matters.
2. **[Hardware](hardware.md)**: the Heltec V3 and the Seeed XIAO ESP32S3 + Wio-SX1262 kit, plus antennas.
3. **[Getting started](getting-started.md)**: flash, set the region, send your first message.
4. **[Nepal: NP_865](nepal-np865.md)**: the frequencies Meshtastic uses in Nepal and why.

## Do more

- **[Paxcounter](paxcounter.md)**: count nearby phones and laptops (WiFi and Bluetooth) and send the totals over LoRa.
- **[Map reporting](map-reporting-mqtt.md)**: put a node on [meshmap.net](https://meshmap.net/) through MQTT.
- **[The control panel](control-panel.md)**: a live dashboard and mode switcher for a USB-connected board.

## When things go wrong

- **[Troubleshooting](troubleshooting.md)**: real problems we hit, including a board that could not hear anyone, and how we found the cause.
- **[FAQ](faq.md)** · **[Glossary](glossary.md)** · **[Links and related projects](resources.md)**

## About

A community tech demo and educational project for Kathmandu, Nepal. The code is on [GitHub](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu) under GPL-3.0; the guide is CC BY-SA 4.0.
Not affiliated with Meshtastic LLC, Heltec or Seeed Studio.
