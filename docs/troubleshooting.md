---
title: Meshtastic troubleshooting - board can't hear other nodes, serial port busy, wrong frequency
description: Fixes for common Meshtastic problems found while building a Nepal LoRa mesh - a Heltec V3 that heard no other nodes (a firmware mismatch), matching region, preset and key, busy USB ports, last-heard times and paused map reporting.
---

# Troubleshooting

**Most "my node can't see the others" problems come down to one of four things: the region, preset or channel don't match; the antenna; the firmware; or the radio band of the board.** Work through them in that order.

## My board can't hear any other nodes

This happened to us: a Heltec V3 sat next to two working XIAO boards and never heard them, and they never heard it.

**1. Compare the radio settings.** All nodes need the same region, preset, channel name and key, and so the same frequency. Run [`tools/radio_check.py`](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu/tree/main/tools) on each board; it lists them side by side and stars any difference. In our case everything matched: `NP_865`, `LONG_FAST`, the default key, and 867.875 MHz on both.

**2. Check the radio chip starts.** Open the serial monitor in the [web flasher](https://flasher.meshtastic.org/), press reset and look for `SX1262 init success` and `Frequency set to 867.875`. Ours started fine.

**3. Swap antennas.** Put a known-good antenna from a working board on the deaf one. It made no difference for us.

**4. Match the firmware.** The Heltec was on **2.7.26** and the XIAOs on **2.5.2**. After reflashing the Heltec to match, it immediately heard both XIAOs at −21 to −56 dBm, and they heard it. **Keep every board on the same firmware version**, and read the [release notes](https://github.com/meshtastic/firmware/releases) before upgrading only one node.

**5. Check the band.** Low-band (433/470 MHz) and high-band (868/915 MHz) versions of many boards look the same; Nepal needs high band. See [Hardware](hardware.md).

### Picked the wrong firmware?

Our first reflash accidentally installed a very old **2.0.x** build. It talked to the others on the default channel, but `meshtastic --device-metadata` showed `hw_model: UNSET` and `hasPKC: False`, which means no encrypted direct messages. Reflash with the exact board name (for example **Heltec V3**) and a current version, and check:

```bash
meshtastic --device-metadata    # expect your firmware version, the right hw_model, hasPKC: True
```

## "Resource busy" or "could not open port"

Only one program can use a board's USB serial port at a time. Close the browser web client, the web-flasher serial monitor, the control panel, `paxwatch.py` and any other `meshtastic` command, then try again.

## The region is set but nothing transmits

After a full erase the region is **unset** and the radio stays silent. Run `meshtastic --set lora.region NP_865` and wait for the reboot.

## "Last heard" times look wrong (for example, hours ago for a node that just sent a packet)

Boards without GPS or an internet connection don't know the time, so the "last heard" stored on the board can be wrong. The [control panel](control-panel.md) times each packet with the computer's clock instead.

## My node isn't on meshmap.net

Go through the [map checklist](map-reporting-mqtt.md#checklist-for-meshmapnet). The usual misses are *OK to MQTT* being off, precise location left on, a 5 GHz-only WiFi network, or a custom channel key.

## Paxcounter shows nothing

WiFi **and** Bluetooth must be off on the Paxcounter node, and it must be an ESP32 board. Reports arrive only once per interval (for example every 60 s). See [Paxcounter](paxcounter.md).

## I shared `meshtastic --info` output publicly

That output contains the node's **private key** and possibly your **WiFi password**. Regenerate the keys (the security settings in the [web client](https://client.meshtastic.org/)) and change the WiFi password.

Still stuck? Try the [Meshtastic FAQ](https://meshtastic.org/docs/faq/) or [open an issue](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu/issues).
