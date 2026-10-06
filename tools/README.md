# Tools

Small command-line helpers for Meshtastic boards on USB. They need the [Meshtastic Python library](https://meshtastic.org/docs/software/python/cli/installation/) (`pip install "meshtastic[cli]"`); `paxwatch.py --mqtt` also needs `paho-mqtt`.

Close the web client, the control panel and any serial monitor first, because only one program can use the USB port.

## `radio_check.py`: why can't my boards hear each other?

```bash
python radio_check.py                 # report + send a ping + listen 120 s
python radio_check.py --listen 300    # listen longer
python radio_check.py --fix           # reset LoRa and channel settings to NP_865 / LONG_FAST / default key
python radio_check.py --port /dev/cu.usbserial-0001
```

It prints the region, preset, computed frequency, channel and key fingerprint (never the key itself). Then it listens and counts packets heard **by radio** from other nodes, and saves `report_<nodeid>.json`. Run it once on each board; from the second run on it prints a side-by-side comparison with `*` marking differences.

To test a link, run it on board A while board B is powered nearby, and press B's reset button during the listen, because a booting node announces itself. Then swap the boards.

## `paxwatch.py`: Paxcounter and packet counter in the terminal

```bash
python paxwatch.py                               # Paxcounter reports + packet summary every 30 s
python paxwatch.py --mqtt --nodes '!a1f80938'    # also count messages from that node on the public MQTT server
```

Example output:

```
14:02:11  PAX !a1f80460  wifi=3 ble=7 total=10  ##########
14:02:30  SUMMARY  mesh=12 {'TELEMETRY_APP': 6, 'PAXCOUNTER_APP': 4, 'POSITION_APP': 2}  proxy=0  pax={'wifi': 3, 'ble': 7}
```

See the guide: [Paxcounter](../docs/paxcounter.md) · [Troubleshooting](../docs/troubleshooting.md).
