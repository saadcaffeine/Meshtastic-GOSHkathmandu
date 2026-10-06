---
title: Getting started with Meshtastic in Nepal - flash, set NP_865, send a message
description: Step-by-step Meshtastic setup for Nepal - flash firmware with the web flasher, install the Python CLI, set region NP_865 and LONG_FAST, check the default channel and send a first message.
---

# Getting started

**To get two Meshtastic boards talking in Nepal: flash the same firmware on both, set the region to `NP_865`, leave the preset and channel at their defaults, and send a message.** This page shows each step, with the command-line equivalents.

## 1. Flash the firmware

1. Plug the board into your computer with a **data** USB-C cable (some cables only carry power).
2. Open the [Meshtastic Web Flasher](https://flasher.meshtastic.org/) in **Chrome or Edge**, because it needs Web Serial.
3. Pick your exact board and a firmware version. Use the **same version on every board**.
4. Tick **Full erase** when changing between major versions, then **Flash**.

Official guide: [Flashing firmware](https://meshtastic.org/docs/getting-started/flashing-firmware/).

## 2. Install the command-line tool

```bash
pip3 install --upgrade "meshtastic[cli]"   # Linux / Windows
pipx install "meshtastic[cli]"             # macOS
```

See the [CLI installation guide](https://meshtastic.org/docs/software/python/cli/installation/). Only one program can use the USB port at a time, so close the web client, the panel and any serial monitor before running CLI commands.

## 3. Set the region (required)

After flashing, the region is unset and **the radio will not transmit until you set it**.

```bash
meshtastic --set lora.region NP_865
```

The board reboots; wait about 20 seconds before the next command.

## 4. Match the radio settings

These are the defaults, so a fresh board already has them. Run this if a board was changed before:

```bash
meshtastic --set lora.modem_preset LONG_FAST --set lora.use_preset true \
  --set lora.channel_num 0 --set lora.override_frequency 0 --set lora.frequency_offset 0 \
  --set lora.tx_enabled true --set lora.sx126x_rx_boosted_gain true
meshtastic --ch-index 0 --ch-set psk default
```

## 5. Name the node and set the time zone (optional)

```bash
meshtastic --set-owner "Kathmandu desk node" --set-owner-short KTM1
meshtastic --set device.tzdef "<+0545>-5:45"
```

## 6. Send a message and listen

```bash
meshtastic --sendtext "namaste from Kathmandu"
meshtastic --listen          # shows packets as they arrive (Ctrl+C to stop)
```

Or connect in a browser with the [Meshtastic web client](https://client.meshtastic.org/), or the phone app over Bluetooth.

## 7. Confirm two boards hear each other

Use [`tools/radio_check.py`](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu/tree/main/tools) on each board. It prints the radio settings, listens for a few minutes and compares the two boards side by side.

> **Careful when sharing output:** `meshtastic --info` prints the node's **private key** and your **WiFi password** if one is set. Don't paste it publicly. `radio_check.py` and the control panel hide these.

## Using the control panel instead

Once the region is set, the [control panel](control-panel.md) can switch a board between the modes used in this project with one click.

Next: **[Nepal: NP_865](nepal-np865.md)** →
