---
title: Meshtastic and LoRa FAQ for Nepal
description: Short answers about Meshtastic and LoRa in Nepal - frequency (NP_865, 867.875 MHz), range, LoRa vs WiFi, Bluetooth and LoRaWAN, nodes that can't hear each other, Paxcounter, meshmap.net and privacy.
---

# FAQ

**Short, direct answers to the questions people ask most about Meshtastic and LoRa in Nepal.** Each links to a longer page.

## What is Meshtastic?

Meshtastic is free, open-source firmware that turns inexpensive LoRa radio boards into an off-grid mesh network for text messages, positions and sensor data, with no phone signal, WiFi or internet needed. See [meshtastic.org](https://meshtastic.org/).

More: [LoRa for WiFi and Bluetooth users](lora-for-wifi-and-bluetooth-users.md)

## Which frequency does Meshtastic use in Nepal?

Nepal uses the NP_865 region: 865.0–868.0 MHz, 100% duty cycle, up to 30 dBm. With the default LongFast preset and channel, nodes use 867.875 MHz.

More: [Nepal: NP_865](nepal-np865.md)

## How far can Meshtastic LoRa reach?

Typically 1–10 km or more with a clear line of sight between elevated nodes, and hundreds of metres to a few kilometres in a dense city like Kathmandu. Height and a good 868 MHz antenna matter more than transmit power.

More: [Hardware](hardware.md)

## How is LoRa different from WiFi and Bluetooth?

LoRa sends very little data (about 1 kbit/s on LongFast) but reaches kilometres using little power, on sub-GHz frequencies (865–868 MHz in Nepal). WiFi and Bluetooth are fast but short-range on 2.4 GHz. Meshtastic nodes relay for each other, so no router is needed.

More: [LoRa for WiFi and Bluetooth users](lora-for-wifi-and-bluetooth-users.md)

## Is Meshtastic the same as LoRaWAN?

No. LoRaWAN is an operator network where sensors talk to gateways. Meshtastic uses the same LoRa radios with its own peer-to-peer mesh protocol and no gateways.

More: [LoRa for WiFi and Bluetooth users](lora-for-wifi-and-bluetooth-users.md)

## Why can't my Meshtastic node see other nodes?

Check that all nodes share the same region (NP_865), preset (LONG_FAST), channel name and key; that the antenna is attached and made for 868 MHz; and that all boards run the same firmware version. In this project a Heltec V3 on firmware 2.7.26 could not hear XIAO boards on 2.5.2 until it was reflashed to match.

More: [Troubleshooting](troubleshooting.md)

## Do I need internet for Meshtastic?

No. Messages travel radio to radio. Internet is only needed for optional extras like MQTT and the public map meshmap.net.

More: [Map reporting and MQTT](map-reporting-mqtt.md)

## What is the Meshtastic Paxcounter?

A module for ESP32 boards that counts nearby WiFi and Bluetooth devices and broadcasts the counts over LoRa. WiFi and Bluetooth must be turned off on that node because the module uses them to scan.

More: [Paxcounter](paxcounter.md)

## How do I get my node on meshmap.net?

Use the default primary channel and key, turn on OK to MQTT, enable the MQTT module with the default server mqtt.meshtastic.org, enable uplink on the primary channel, share a position with precise location off (between about 364 m and 23.3 km), and give the node internet access.

More: [Map reporting and MQTT](map-reporting-mqtt.md)

## Which boards work well for Meshtastic in Nepal?

This project uses the Heltec WiFi LoRa 32 V3 and the Seeed XIAO ESP32S3 with Wio-SX1262 kit, both ESP32-S3 + SX1262 boards. Buy the 863–928 MHz (high-band) versions.

More: [Hardware](hardware.md)

## Are Meshtastic messages private?

Channel messages are encrypted with the channel key, but the default channel's key is public, so treat it as a public room. Since firmware 2.5, direct messages use public-key encryption. Use a private channel with your own key for group privacy.

More: [LoRa for WiFi and Bluetooth users](lora-for-wifi-and-bluetooth-users.md)

## What does SNR mean in Meshtastic?

Signal-to-noise ratio in dB. LoRa can decode signals below the noise floor, so negative SNR is normal; on LongFast packets still decode down to roughly −15 dB.

More: [The control panel](control-panel.md)

<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "FAQPage",
 "mainEntity": [
  {
   "@type": "Question",
   "name": "What is Meshtastic?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Meshtastic is free, open-source firmware that turns inexpensive LoRa radio boards into an off-grid mesh network for text messages, positions and sensor data, with no phone signal, WiFi or internet needed. See https://meshtastic.org/."
   }
  },
  {
   "@type": "Question",
   "name": "Which frequency does Meshtastic use in Nepal?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Nepal uses the NP_865 region: 865.0–868.0 MHz, 100% duty cycle, up to 30 dBm. With the default LongFast preset and channel, nodes use 867.875 MHz."
   }
  },
  {
   "@type": "Question",
   "name": "How far can Meshtastic LoRa reach?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Typically 1–10 km or more with a clear line of sight between elevated nodes, and hundreds of metres to a few kilometres in a dense city like Kathmandu. Height and a good 868 MHz antenna matter more than transmit power."
   }
  },
  {
   "@type": "Question",
   "name": "How is LoRa different from WiFi and Bluetooth?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "LoRa sends very little data (about 1 kbit/s on LongFast) but reaches kilometres using little power, on sub-GHz frequencies (865–868 MHz in Nepal). WiFi and Bluetooth are fast but short-range on 2.4 GHz. Meshtastic nodes relay for each other, so no router is needed."
   }
  },
  {
   "@type": "Question",
   "name": "Is Meshtastic the same as LoRaWAN?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "No. LoRaWAN is an operator network where sensors talk to gateways. Meshtastic uses the same LoRa radios with its own peer-to-peer mesh protocol and no gateways."
   }
  },
  {
   "@type": "Question",
   "name": "Why can't my Meshtastic node see other nodes?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Check that all nodes share the same region (NP_865), preset (LONG_FAST), channel name and key; that the antenna is attached and made for 868 MHz; and that all boards run the same firmware version. In this project a Heltec V3 on firmware 2.7.26 could not hear XIAO boards on 2.5.2 until it was reflashed to match."
   }
  },
  {
   "@type": "Question",
   "name": "Do I need internet for Meshtastic?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "No. Messages travel radio to radio. Internet is only needed for optional extras like MQTT and the public map meshmap.net."
   }
  },
  {
   "@type": "Question",
   "name": "What is the Meshtastic Paxcounter?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "A module for ESP32 boards that counts nearby WiFi and Bluetooth devices and broadcasts the counts over LoRa. WiFi and Bluetooth must be turned off on that node because the module uses them to scan."
   }
  },
  {
   "@type": "Question",
   "name": "How do I get my node on meshmap.net?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Use the default primary channel and key, turn on OK to MQTT, enable the MQTT module with the default server mqtt.meshtastic.org, enable uplink on the primary channel, share a position with precise location off (between about 364 m and 23.3 km), and give the node internet access."
   }
  },
  {
   "@type": "Question",
   "name": "Which boards work well for Meshtastic in Nepal?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "This project uses the Heltec WiFi LoRa 32 V3 and the Seeed XIAO ESP32S3 with Wio-SX1262 kit, both ESP32-S3 + SX1262 boards. Buy the 863–928 MHz (high-band) versions."
   }
  },
  {
   "@type": "Question",
   "name": "Are Meshtastic messages private?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Channel messages are encrypted with the channel key, but the default channel's key is public, so treat it as a public room. Since firmware 2.5, direct messages use public-key encryption. Use a private channel with your own key for group privacy."
   }
  },
  {
   "@type": "Question",
   "name": "What does SNR mean in Meshtastic?",
   "acceptedAnswer": {
    "@type": "Answer",
    "text": "Signal-to-noise ratio in dB. LoRa can decode signals below the noise floor, so negative SNR is normal; on LongFast packets still decode down to roughly −15 dB."
   }
  }
 ]
}
</script>
