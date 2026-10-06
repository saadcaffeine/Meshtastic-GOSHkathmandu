---
title: Meshtastic links, documentation and related projects
description: Official Meshtastic documentation, GitHub repositories, tools, hardware pages, maps and related open-source projects used in this Nepal LoRa mesh guide.
---

# Links and related projects

**Everything this project builds on, with the official sources for each topic.**

## Meshtastic

| What | Link |
|---|---|
| Website and documentation | [meshtastic.org](https://meshtastic.org/) · [Introduction](https://meshtastic.org/docs/introduction/) · [Getting started](https://meshtastic.org/docs/getting-started/) · [FAQ](https://meshtastic.org/docs/faq/) |
| Flashing | [Web Flasher](https://flasher.meshtastic.org/) · [Flashing guide](https://meshtastic.org/docs/getting-started/flashing-firmware/) |
| Web client | [client.meshtastic.org](https://client.meshtastic.org/) |
| Radio settings | [LoRa config](https://meshtastic.org/docs/configuration/radio/lora/) · [Radio settings overview](https://meshtastic.org/docs/overview/radio-settings/) · [Region by country](https://meshtastic.org/docs/configuration/region-by-country/) · [Channels](https://meshtastic.org/docs/configuration/radio/channels/) · [Position](https://meshtastic.org/docs/configuration/radio/position/) |
| Modules | [Paxcounter](https://meshtastic.org/docs/configuration/module/paxcounter/) · [MQTT module](https://meshtastic.org/docs/configuration/module/mqtt/) · [MQTT integration](https://meshtastic.org/docs/software/integrations/mqtt/) |
| How it works | [Mesh algorithm](https://meshtastic.org/docs/overview/mesh-algo/) · [Encryption](https://meshtastic.org/docs/overview/encryption/) |
| Python CLI | [CLI guide](https://meshtastic.org/docs/software/python/cli/) · [Installation](https://meshtastic.org/docs/software/python/cli/installation/) · [PyPI](https://pypi.org/project/meshtastic/) |
| Hardware | [Supported devices](https://meshtastic.org/docs/hardware/devices/) · [Heltec LoRa 32](https://meshtastic.org/docs/hardware/devices/heltec-automation/lora32/) · [Seeed Wio-SX1262 + XIAO ESP32S3](https://meshtastic.org/docs/hardware/devices/seeed-studio/wio-series/wio-sx1262s/?wio-sx1262=esp32-s3) |
| GitHub | [meshtastic](https://github.com/meshtastic) · [firmware](https://github.com/meshtastic/firmware) ([releases](https://github.com/meshtastic/firmware/releases)) · [python](https://github.com/meshtastic/python) · [web](https://github.com/meshtastic/web) · [web-flasher](https://github.com/meshtastic/web-flasher) · [protobufs](https://github.com/meshtastic/protobufs) |

## Maps

- [meshmap.net](https://meshmap.net/), the public node map ([source and requirements](https://github.com/brianshea2/meshmap.net))

## Hardware makers

- Heltec: [WiFi LoRa 32 V3](https://heltec.org/project/wifi-lora-32-v3/)
- Seeed Studio: [XIAO ESP32S3 & Wio-SX1262 kit wiki](https://wiki.seeedstudio.com/xiao_esp32s3_&_wio_SX1262_kit_for_meshtastic/) · [kit in the shop](https://www.seeedstudio.com/Wio-SX1262-with-XIAO-ESP32S3-p-5982.html) · [kit with a 3D-printed case](https://www.seeedstudio.com/XIAO-ESP32S3-for-Meshtastic-LoRa-with-3D-Printed-Enclosure-p-6314.html)
- Semtech: [SX1262 LoRa transceiver](https://www.semtech.com/products/wireless-rf/lora-connect/sx1262)

## Related open-source projects

- [RadioLib](https://github.com/jgromes/RadioLib), the radio driver library Meshtastic uses
- [ESP32-Paxcounter](https://github.com/cyberman54/ESP32-Paxcounter), the original standalone Paxcounter
- [Flask](https://flask.palletsprojects.com/) and [paho-mqtt](https://github.com/eclipse-paho/paho.mqtt.python) ([PyPI](https://pypi.org/project/paho-mqtt/)), used by the control panel

## Background

- [LoRaWAN, from the LoRa Alliance](https://lora-alliance.org/about-lorawan/), to see how it differs from Meshtastic
- [Nepal Telecommunications Authority](https://nta.gov.np/) · [Radio Frequency Policy 2080 (PDF)](https://www.nta.gov.np/uploads/contents/Radio-Frequency-Policy-2080-English.pdf)
- [GOSH: Gathering for Open Science Hardware](https://openhardware.science/)
- [GitHub Pages documentation](https://docs.github.com/en/pages) · [llms.txt](https://llmstxt.org/)
