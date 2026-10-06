---
title: LoRa explained for WiFi and Bluetooth users
description: How LoRa and Meshtastic differ from WiFi and Bluetooth in range, speed, frequency, power and networking, explained for people who already know WiFi and Bluetooth.
---

# LoRa explained for WiFi and Bluetooth users

**LoRa is a radio technology that trades speed for range: it sends small amounts of data, slowly, over kilometres, using very little power.** If you know WiFi and Bluetooth, the easiest way to understand LoRa is to see what it gives up and what it gains.

## How is LoRa different from WiFi and Bluetooth?

| | WiFi | Bluetooth (BLE) | LoRa with Meshtastic |
|---|---|---|---|
| Range | tens of metres | metres to tens of metres | typically 1–10+ km with a clear line of sight; hundreds of metres to a few km in a dense city |
| Data rate | Mbit/s to Gbit/s | about 1–2 Mbit/s | about 1 kbit/s on the default `LONG_FAST` preset |
| What you send | anything: video, web pages | audio, files, sensor data | short text messages, positions, sensor readings |
| Frequency | 2.4 / 5 / 6 GHz | 2.4 GHz | sub-GHz; in Nepal **865–868 MHz** |
| Network shape | star (devices ↔ router) | point-to-point or star | **mesh**: every node can relay for others |
| Internet needed? | usually | no | **no** (optional bridge via MQTT) |
| Power use | high | low | very low |

## Why is it so slow but so far-reaching?

LoRa uses **chirp spread spectrum**: each bit is spread over a wide sweep of frequencies and sent slowly. A receiver can pick the signal out even when it is weaker than the background noise. That's why the signal-to-noise ratio (**SNR**) you see in Meshtastic is often *negative* and still works; on `LONG_FAST`, packets still decode at roughly −15 to −17 dB SNR.

Lower frequencies (865 MHz versus 2.4 GHz) also travel further and pass through walls and trees better.

## What is a "mesh" and why does it matter?

With WiFi, your phone talks to a router. With Meshtastic, there is no router: when a node hears a message, it re-broadcasts it so nodes further away can hear it too. Each message carries a **hop limit** (3 by default) so it doesn't bounce around forever. In the [control panel](control-panel.md) the "hops" figure shows how many other nodes relayed a packet before it reached you.

## Is LoRa the same as LoRaWAN?

**No.** [LoRaWAN](https://lora-alliance.org/about-lorawan/) is a network protocol built on LoRa radios where sensors talk to gateways run by a network operator. Meshtastic uses the same LoRa radios but its own peer-to-peer mesh protocol, with no gateways or operators. A Meshtastic node won't join a LoRaWAN network, and the other way round.

## What do the radio settings mean?

| Setting | WiFi/Bluetooth analogy | Meshtastic meaning |
|---|---|---|
| **Region** (e.g. `NP_865`) | the country setting on a router | which frequencies and power the radio may legally use |
| **Modem preset** (e.g. `LONG_FAST`) | 802.11n vs 802.11ac | trade-off between range and speed (spreading factor and bandwidth) |
| **Channel** and **key (PSK)** | network name (SSID) and password | which messages your node can decrypt; the default channel uses a well-known public key |
| **Frequency slot** | the WiFi channel number | worked out automatically from the region, preset and channel name |

All nodes that want to talk must share the **same region, preset, channel name and key**. See the official [radio settings overview](https://meshtastic.org/docs/overview/radio-settings/) and [LoRa configuration](https://meshtastic.org/docs/configuration/radio/lora/).

## Where do WiFi and Bluetooth still fit in?

Most Meshtastic boards also have WiFi and Bluetooth, but they are used *around* the LoRa link:

- **Bluetooth** connects your phone's Meshtastic app to the board.
- **WiFi** can connect a node to the internet to publish to an [MQTT](map-reporting-mqtt.md) server or the public map.
- The **[Paxcounter](paxcounter.md)** uses the WiFi and Bluetooth radios as *scanners* to count nearby devices, then sends the count over LoRa.

## Is it private?

Messages on a channel are encrypted with that channel's key (AES-256), but the **default channel's key is public**, so treat it like a public chat room. Since firmware 2.5, direct messages use public-key encryption. Read Meshtastic's [encryption overview](https://meshtastic.org/docs/overview/encryption/) for the limits.

Next: **[Hardware](hardware.md)** →
