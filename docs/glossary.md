---
title: Meshtastic and LoRa glossary
description: Plain-language definitions of Meshtastic and LoRa terms - node, mesh, hop, region, preset, spreading factor, bandwidth, SNR, RSSI, PSK, channel, duty cycle, airtime, MQTT, uplink, Paxcounter, U.FL and more.
---

# Glossary

**Plain-language definitions of the terms you'll meet in Meshtastic, with WiFi and Bluetooth comparisons where they help.**

| Term | Meaning |
|---|---|
| **Airtime (TX utilisation)** | Share of time a node spends transmitting. Shown as "Airtime used to send" in the panel. |
| **Bandwidth (BW)** | How wide a slice of spectrum each transmission uses; 250 kHz on LongFast. Wider is faster but shorter range. |
| **Channel** | A named group with its own encryption key, like a WiFi network name plus password. The default primary channel has an empty name (shown as LongFast) and a public key. |
| **Channel utilisation** | Share of time the radio hears *any* LoRa traffic. Shown as "Channel busy"; above about 25% the mesh is getting crowded. |
| **CLI** | The `meshtastic` command-line tool from the [Python library](https://meshtastic.org/docs/software/python/cli/). |
| **Duty cycle** | A legal limit on how much of the time you may transmit. `NP_865` allows 100%; some EU bands allow only 1–10%. |
| **Firmware** | The software on the board. Flash it with the [web flasher](https://flasher.meshtastic.org/); keep all boards on the same version. |
| **Hop / hop limit** | One relay by another node. The hop limit (default 3) caps how many times a message is relayed. |
| **ISM band** | Licence-exempt radio bands such as 2.4 GHz (WiFi/Bluetooth) and sub-GHz bands like 865–868 MHz, subject to national rules. |
| **LoRa** | "Long Range": a chirp spread-spectrum radio method from Semtech; slow but very long-range and low-power. |
| **LoRaWAN** | A different, operator-run network protocol built on LoRa radios. Meshtastic does not use it. |
| **MAC address** | The hardware address of the board's WiFi or Bluetooth radio. ESP32 nodes derive their node ID from it. |
| **Mesh** | A network where every node can relay messages for others, with no central router. |
| **Modem preset** | A bundle of LoRa settings (bandwidth, spreading factor, coding rate). `LONG_FAST` is the default. |
| **MQTT** | A lightweight publish/subscribe protocol. Nodes can uplink packets to `mqtt.meshtastic.org` for maps and tools. |
| **Node / node ID** | One Meshtastic device; its ID looks like `!a1f80938`. |
| **NodeInfo** | A packet announcing a node's name and hardware model. Until it arrives, other nodes only know the ID. |
| **OK to MQTT** | A setting (`lora.config_ok_to_mqtt`) that lets your packets be published to MQTT by any gateway. meshmap.net requires it. |
| **Paxcounter** | An ESP32 module that counts nearby WiFi and Bluetooth devices and broadcasts the totals. See [Paxcounter](paxcounter.md). |
| **PKC** | Public-key cryptography, used for direct messages since firmware 2.5 (`hasPKC: True`). |
| **Position precision** | How much a shared location is blurred. Lower bit values mean a bigger blur; meshmap.net needs between about 364 m and 23.3 km. |
| **PSK** | Pre-shared key: a channel's encryption key. `default` / `AQ==` is the public default key. |
| **Region** | Which band and power rules the radio follows. Nepal: `NP_865`. |
| **RSSI** | Received signal strength in dBm. Closer to 0 is stronger; about −120 dBm is near the limit. |
| **SNR** | Signal-to-noise ratio in dB. LoRa decodes below the noise floor, so negative values are normal. |
| **Spreading factor (SF)** | How much each bit is spread out in time. Higher SF gives more range and less speed; LongFast uses SF11. |
| **SX1262** | The [Semtech LoRa radio chip](https://www.semtech.com/products/wireless-rf/lora-connect/sx1262) on both boards in this project. |
| **Telemetry** | Packets with battery, voltage, channel use or sensor readings. |
| **U.FL / IPEX** | The tiny snap-on antenna connector on both boards. Press it straight down until it clicks. |
| **Uplink / downlink** | Uplink sends mesh packets to MQTT; downlink brings MQTT packets back onto the mesh. |
