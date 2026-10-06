---
title: Meshtastic in Nepal - the NP_865 region, 865-868 MHz and LongFast frequency
description: Which frequencies Meshtastic uses in Nepal. The NP_865 region covers 865.0-868.0 MHz with 100% duty cycle and up to 30 dBm; the default LongFast channel sits on 867.875 MHz.
---

# Nepal: the NP_865 region

**In Nepal, Meshtastic uses the `NP_865` region: 865.0–868.0 MHz, with no duty-cycle limit (100%) and a maximum of 30 dBm.** With the default `LONG_FAST` preset and the default channel, every node transmits and listens on **867.875 MHz**.

## Region details

| Property | Value |
|---|---|
| Region code | `NP_865` |
| Frequency range | 865.0 – 868.0 MHz |
| Duty cycle | 100% (no airtime limit) |
| Maximum power | 30 dBm (the board's own maximum is lower: the SX1262 tops out around 22 dBm) |
| Default preset | `LONG_FAST` (250 kHz bandwidth, spreading factor 11) |
| Channel slots with LONG_FAST | 12 × 250 kHz |
| Default LongFast frequency | **867.875 MHz** (slot 11) |

Sources: Meshtastic's [LoRa configuration](https://meshtastic.org/docs/configuration/radio/lora/) and [region by country](https://meshtastic.org/docs/configuration/region-by-country/) pages, and the region table in the [firmware source](https://github.com/meshtastic/firmware). That table cites the Nepal Telecommunications Authority's [Radio Frequency Policy 2080 (2023)](https://www.nta.gov.np/uploads/contents/Radio-Frequency-Policy-2080-English.pdf). Its Schedule 4 sets aside 865–868 MHz for non-cellular IoT on a shared, non-exclusive basis with no frequency fee.

## How is the frequency chosen?

Meshtastic splits the region into slots as wide as the preset's bandwidth. It then hashes the **channel name** (for the default channel, the preset's name, `LongFast`) to pick a slot, unless you set `lora.channel_num` or `lora.override_frequency` yourself:

```
slots     = (868.0 − 865.0) MHz / 0.250 MHz = 12
slot      = djb2("LongFast") mod 12        = 11
frequency = 865.0 + 0.125 + 11 × 0.250   = 867.875 MHz
```

When a Heltec boots, you can see this in its serial log: `Radio freq=867.875 … region=NP_865, name=LongFast … ch=11`. If two of your boards show different frequencies, they will never hear each other. [`tools/radio_check.py`](https://github.com/saadcaffeine/Meshtastic-GOSHkathmandu/tree/main/tools) prints the computed frequency for each board.

## Do nodes in India use the same band?

India's `IN` region is 865–867 MHz, which overlaps but is not identical. A different region gives a different slot layout, so set every node in Nepal to `NP_865`.

## Is it legal?

Meshtastic's `NP_865` settings were made to follow the NTA policy above. Regulations change and depend on your use, so check with the [Nepal Telecommunications Authority](https://nta.gov.np/) for anything beyond hobby and educational experiments. This page is not legal advice.

Next: **[Paxcounter](paxcounter.md)** →
