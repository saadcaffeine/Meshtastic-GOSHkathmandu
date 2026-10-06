"""Radio check: find out why a board can't hear the others, and optionally fix it.

Run with the board on USB (close the web client, the panel and any serial monitor first):

    ~/paxenv/bin/python radio_check.py                 # report + listen 120 s
    ~/paxenv/bin/python radio_check.py --listen 300    # listen longer
    ~/paxenv/bin/python radio_check.py --fix           # make LoRa settings match the XIAO boards
    ~/paxenv/bin/python radio_check.py --port /dev/cu.usbserial-0001

It writes report_<nodeid>.json next to this script. Run it once on the
Heltec and once on a working XIAO; the two reports are compared automatically.
Keys and passwords are never written: channel keys are reduced to a short fingerprint.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# region: (start MHz, end MHz, spacing MHz) — from the firmware's region table
REGIONS = {"NP_865": (865.0, 868.0, 0.0), "IN": (865.0, 867.0, 0.0),
           "EU_868": (869.4, 869.65, 0.0), "US": (902.0, 928.0, 0.0)}
PRESET = {"LONG_FAST": ("LongFast", 250), "LONG_SLOW": ("LongSlow", 125),
          "LONG_MODERATE": ("LongMod", 125), "MEDIUM_FAST": ("MediumFast", 250),
          "MEDIUM_SLOW": ("MediumSlow", 250), "SHORT_FAST": ("ShortFast", 250),
          "SHORT_SLOW": ("ShortSlow", 250), "SHORT_TURBO": ("ShortTurbo", 500),
          "VERY_LONG_SLOW": ("VLongSlow", 62.5)}


def djb2(s):
    h = 5381
    for c in s.encode():
        h = ((h << 5) + h + c) & 0xFFFFFFFF
    return h


def frequency(region, preset, ch_name, channel_num, override, offset, use_preset, bw_custom):
    if override:
        return round(override + offset, 4), "override_frequency"
    if region not in REGIONS:
        return None, "unknown region table"
    start, end, spacing = REGIONS[region]
    bw = (PRESET.get(preset, ("", 250))[1] if use_preset else bw_custom) or 250
    n = int((end - start + spacing) / (spacing + bw / 1000.0))
    name = ch_name or PRESET.get(preset, ("?",))[0]
    slot = (channel_num - 1) if channel_num else djb2(name) % n
    return round(start + bw / 2000.0 + slot * bw / 1000.0 + offset, 4), "slot %d of %d" % (slot, n)


def fingerprint(psk):
    if not psk:
        return "none (no encryption)"
    if len(psk) == 1:
        return "default key #%d" % psk[0]
    return "custom key " + hashlib.sha256(psk).hexdigest()[:8]


def collect(iface):
    node = iface.localNode
    lc, mc = node.localConfig, node.moduleConfig
    lora = lc.lora
    E = lambda msg, f: msg.DESCRIPTOR.fields_by_name[f].enum_type.values_by_number[getattr(msg, f)].name
    ch0 = node.channels[0].settings if node.channels else None
    region, preset = E(lora, "region"), E(lora, "modem_preset")
    freq, how = frequency(region, preset, ch0.name if ch0 else "", lora.channel_num,
                          lora.override_frequency, lora.frequency_offset, lora.use_preset,
                          lora.bandwidth)
    me = iface.getMyNodeInfo() or {}
    meta = getattr(iface, "metadata", None)
    user = me.get("user", {})
    others = []
    for n in iface.nodes.values():
        u = n.get("user", {})
        if u.get("id") == user.get("id"):
            continue
        others.append({"id": u.get("id"), "name": u.get("longName"), "hw": u.get("hwModel"),
                       "snr": n.get("snr"), "hops": n.get("hopsAway"),
                       "last_heard_s_ago": int(time.time() - n["lastHeard"]) if n.get("lastHeard") else None})
    return {
        "node": {"id": user.get("id"), "name": user.get("longName"), "hw": user.get("hwModel"),
                 "firmware": getattr(meta, "firmware_version", "") if meta else "",
                 "role": E(lc.device, "role"), "is_licensed": bool(user.get("isLicensed"))},
        "lora": {"region": region, "preset": preset, "use_preset": lora.use_preset,
                 "bandwidth": lora.bandwidth, "spread_factor": lora.spread_factor,
                 "coding_rate": lora.coding_rate, "channel_num": lora.channel_num,
                 "override_frequency": lora.override_frequency,
                 "frequency_offset": lora.frequency_offset, "tx_enabled": lora.tx_enabled,
                 "tx_power": lora.tx_power, "hop_limit": lora.hop_limit,
                 "sx126x_rx_boosted_gain": getattr(lora, "sx126x_rx_boosted_gain", None),
                 "ignore_mqtt": getattr(lora, "ignore_mqtt", None),
                 "ignore_incoming": list(lora.ignore_incoming),
                 "computed_frequency_mhz": freq, "frequency_from": how},
        "channel0": {"name": (ch0.name if ch0 else "") or "(default)",
                     "key": fingerprint(bytes(ch0.psk)) if ch0 else None,
                     "role": E(node.channels[0], "role") if node.channels else None},
        "nodes_in_db": others,
    }


def listen(iface, seconds):
    from pubsub import pub
    seen = []

    def on_rx(packet, interface):
        d = packet.get("decoded") or {}
        seen.append({"from": packet.get("fromId"), "port": d.get("portnum", "ENCRYPTED/undecodable"),
                     "snr": packet.get("rxSnr"), "rssi": packet.get("rxRssi"),
                     "via_mqtt": packet.get("viaMqtt", False)})
        print("  heard %-10s %-22s snr=%s rssi=%s%s" % (
            packet.get("fromId"), seen[-1]["port"], seen[-1]["snr"], seen[-1]["rssi"],
            " (via MQTT, not radio)" if seen[-1]["via_mqtt"] else ""))

    pub.subscribe(on_rx, "meshtastic.receive")
    print("Listening %d s. Send a message from a XIAO now (or wait for its routine broadcasts)..." % seconds)
    try:
        iface.sendText("radio check ping from " + str(iface.getMyNodeInfo()["user"].get("id")))
    except Exception as e:
        print("  could not send ping:", e)
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(1)
    me = iface.getMyNodeInfo()["user"]["id"]
    radio = [s for s in seen if s["from"] != me and not s["via_mqtt"]]
    return {"seconds": seconds, "packets_total": len(seen), "from_other_nodes_by_radio": len(radio),
            "undecodable": sum(1 for s in radio if s["port"].startswith("ENCRYPTED")),
            "packets": seen[-50:]}


def apply_fix(iface, ref):
    """Set the LoRa/channel settings that must match the XIAO boards."""
    node = iface.localNode
    lora = node.localConfig.lora
    try:
        from meshtastic.protobuf import config_pb2
    except ImportError:
        from meshtastic import config_pb2
    lora.region = config_pb2.Config.LoRaConfig.RegionCode.Value(ref["region"])
    lora.modem_preset = config_pb2.Config.LoRaConfig.ModemPreset.Value(ref["preset"])
    lora.use_preset = True
    lora.channel_num = 0
    lora.override_frequency = 0
    lora.frequency_offset = 0
    lora.tx_enabled = True
    lora.sx126x_rx_boosted_gain = True
    del lora.ignore_incoming[:]
    node.writeConfig("lora")
    ch = node.channels[0].settings
    changed_ch = False
    if ch.name:
        ch.name = ""
        changed_ch = True
    if bytes(ch.psk) != b"\x01":
        ch.psk = b"\x01"          # the public default key every stock node uses
        changed_ch = True
    if changed_ch:
        node.writeChannel(0)
    print("Settings written. The board will reboot; run the check again in ~30 s.")


def compare(reports):
    if len(reports) < 2:
        return
    keys = [("lora", "region"), ("lora", "preset"), ("lora", "use_preset"), ("lora", "channel_num"),
            ("lora", "override_frequency"), ("lora", "frequency_offset"),
            ("lora", "computed_frequency_mhz"), ("lora", "tx_enabled"),
            ("channel0", "name"), ("channel0", "key"), ("node", "is_licensed"), ("node", "firmware")]
    print("\nComparison of saved reports (* = differs):")
    names = [r["node"]["name"] or r["node"]["id"] for r in reports]
    print("  %-26s" % "" + "".join("%-24s" % n[:22] for n in names))
    for a, b in keys:
        vals = [str(r[a].get(b)) for r in reports]
        flag = "*" if len(set(vals)) > 1 and b != "firmware" else " "
        print("%s %-26s" % (flag, b) + "".join("%-24s" % v[:22] for v in vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--listen", type=int, default=120)
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()
    import meshtastic.serial_interface as si
    print("Connecting...")
    iface = si.SerialInterface(devPath=args.port)
    try:
        rep = collect(iface)
        print(json.dumps({k: rep[k] for k in ("node", "lora", "channel0")}, indent=2))
        print("Other nodes in its database:", len(rep["nodes_in_db"]))
        if args.fix:
            apply_fix(iface, {"region": "NP_865", "preset": "LONG_FAST"})
            return
        if args.listen:
            rep["listen"] = listen(iface, args.listen)
            l = rep["listen"]
            print("\nHeard %d packets by radio from other nodes (%d could not be decrypted)."
                  % (l["from_other_nodes_by_radio"], l["undecodable"]))
        path = os.path.join(HERE, "report_%s.json" % (rep["node"]["id"] or "unknown").strip("!"))
        with open(path, "w") as f:
            json.dump(rep, f, indent=2)
        print("Saved", path)
    finally:
        iface.close()
    reports = []
    for p in sorted(glob.glob(os.path.join(HERE, "report_*.json"))):
        with open(p) as f:
            reports.append(json.load(f))
    compare(reports)


if __name__ == "__main__":
    sys.exit(main())
