"""Radio layer for the Meshtastic control panel.

RealRadio talks to a board over USB serial with the meshtastic Python library.
MockRadio simulates a board so the panel can be tried without any hardware.

Both expose the same small interface:

    start() / stop()
    snapshot()                       -> dict describing the node right now
    apply_mode(mode_id, pax_interval) -> blocking, raises on failure

and report what they see through a hooks object with these methods:

    hooks.packet(dict)               every packet seen (own and others)
    hooks.pax(dict)                  every Paxcounter reading
    hooks.proxy(topic, payload, retained)   MQTT messages the node wants forwarded
    hooks.event(str)                 short human-readable log lines

WiFi credentials are never read or written by this module.
"""
import random
import threading
import time

LOCAL_SECTIONS = {"device", "position", "power", "network", "display",
                  "lora", "bluetooth", "security"}

# Every mode is a list of settings forced on the node. "pax" says whether the
# mode runs Paxcounter (so the UI can offer an update interval).
MODES = {
    "map_reporter": {
        "label": "Map reporter",
        "summary": "WiFi and MQTT uplink on, Paxcounter off. The node publishes "
                   "to the public server and can appear on meshmap.net.",
        "note": "Needs a 2.4 GHz WiFi network already saved on the node.",
        "settings": {
            "network.wifi_enabled": True,
            "bluetooth.enabled": False,
            "paxcounter.enabled": False,
            "mqtt.enabled": True,
            "mqtt.proxy_to_client_enabled": False,
            "mqtt.map_reporting_enabled": True,
            "lora.config_ok_to_mqtt": True,      # meshmap.net only shows nodes that allow MQTT
        },
        "uplink": True,
        "pax": False,
    },
    "paxcounter": {
        "label": "Paxcounter sensor",
        "summary": "WiFi and Bluetooth off, Paxcounter on. Counts nearby "
                   "devices and sends the totals over LoRa.",
        "note": "The node leaves the public map after about 8 hours.",
        "settings": {
            "network.wifi_enabled": False,
            "bluetooth.enabled": False,
            "paxcounter.enabled": True,
            "mqtt.enabled": False,
            "mqtt.proxy_to_client_enabled": False,
        },
        "uplink": None,
        "pax": True,
    },
    "listener": {
        "label": "Listener only",
        "summary": "WiFi, MQTT and Paxcounter off. The node just receives "
                   "and shows mesh traffic.",
        "note": "Good for checking radio range and signal.",
        "settings": {
            "network.wifi_enabled": False,
            "paxcounter.enabled": False,
            "mqtt.enabled": False,
            "mqtt.proxy_to_client_enabled": False,
        },
        "uplink": None,
        "pax": False,
    },
    "usb_proxy": {
        "label": "USB proxy (experimental)",
        "summary": "WiFi and Bluetooth off, Paxcounter on, MQTT forwarded "
                   "through this computer's internet connection.",
        "note": "Only works while this panel stays running and connected. "
                "Not confirmed to work on every firmware version.",
        "settings": {
            "network.wifi_enabled": False,
            "bluetooth.enabled": False,
            "paxcounter.enabled": True,
            "mqtt.enabled": True,
            "mqtt.proxy_to_client_enabled": True,
            "mqtt.map_reporting_enabled": True,
            "lora.config_ok_to_mqtt": True,      # meshmap.net only shows nodes that allow MQTT
        },
        "uplink": True,
        "pax": True,
    },
}


def detect_mode(c):
    """Name the mode that matches a config snapshot, or 'custom'."""
    if not c:
        return None
    wifi, pax, mqtt, proxy = c["wifi"], c["paxcounter"], c["mqtt"], c["mqtt_proxy"]
    if mqtt and proxy and pax and not wifi:
        return "usb_proxy"
    if wifi and mqtt and not proxy and not pax:
        return "map_reporter"
    if pax and not wifi and not proxy:
        return "paxcounter"
    if not wifi and not pax and not proxy:
        return "listener"
    return "custom"


def preset_channel_name(preset):
    """LONG_FAST -> LongFast, the default channel name for that preset."""
    return "".join(w.capitalize() for w in (preset or "LONG_FAST").split("_"))


def _enum_name(msg, field):
    fd = msg.DESCRIPTOR.fields_by_name[field]
    return fd.enum_type.values_by_number[getattr(msg, field)].name


def _mac_from(user):
    """User.macaddr arrives base64-encoded from the Python library."""
    import base64
    m = user.get("macaddr")
    if not m:
        return None
    try:
        b = base64.b64decode(m) if isinstance(m, str) else bytes(m)
        return ":".join("%02x" % x for x in b) if len(b) == 6 else None
    except Exception:
        return None


def _usb_details(path):
    """Describe the USB serial device (chip, maker, serial number) if pyserial can see it."""
    try:
        from serial.tools import list_ports
        for p in list_ports.comports():
            if p.device == path:
                vidpid = "%04x:%04x" % (p.vid, p.pid) if p.vid is not None else None
                return {"usb_description": p.description, "usb_manufacturer": p.manufacturer,
                        "usb_serial": p.serial_number, "usb_vid_pid": vidpid}
    except Exception:
        pass
    return {}


def _new_conn():
    return {"connected_at": None, "last_connected": None, "last_lost": None,
            "connects": 0, "device_path": None, "usb": {},
            "last_error": None, "last_error_at": None}


class RealRadio:
    def __init__(self, port, hooks):
        self.port = port
        self.h = hooks
        self.iface = None
        self.error = ""
        self.busy = False
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._apply_lock = threading.Lock()
        self._thread = None
        self.conn = _new_conn()
        self.last_board = None           # what was plugged in last, kept after unplugging
        self._protos()
        from pubsub import pub
        pub.subscribe(self._on_receive, "meshtastic.receive")
        pub.subscribe(self._on_proxy, "meshtastic.mqttclientproxymessage")
        pub.subscribe(self._on_lost, "meshtastic.connection.lost")

    @staticmethod
    def _protos():
        global paxcount_pb2
        try:
            from meshtastic.protobuf import paxcount_pb2
        except ImportError:
            from meshtastic import paxcount_pb2

    # ---------- connection loop ----------
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._close()

    def _close(self):
        iface, self.iface = self.iface, None
        if iface is not None:
            try:
                iface.close()
            except Exception:
                pass

    def _run(self):
        import meshtastic.serial_interface as si
        import meshtastic.util as mu
        while not self._stop.is_set():
            try:
                if not self.port and not mu.findPorts(True):
                    self.error = "No Meshtastic board found on USB"
                else:
                    self.error = ""
                    self._lost.clear()
                    self.h.event("connecting to the board")
                    iface = si.SerialInterface(devPath=self.port)
                    self.iface = iface
                    now = time.time()
                    path = getattr(iface, "devPath", None) or self.port
                    self.conn.update(connected_at=now, last_connected=now, device_path=path,
                                     connects=self.conn["connects"] + 1, usb=_usb_details(path))
                    self.h.event("connected on %s" % path)
                    while not self._stop.is_set() and not self._lost.wait(1.0):
                        pass
                    self.h.event("connection lost")
            except (Exception, SystemExit) as e:
                self.error = str(e)[:200]
                self.conn.update(last_error=self.error, last_error_at=time.time())
                self.h.event("connection error: " + self.error)
            finally:
                if self.conn["connected_at"]:
                    self.conn.update(connected_at=None, last_lost=time.time())
                self._close()
            self._stop.wait(3)

    def _on_lost(self, interface):
        if interface is self.iface:
            self._lost.set()

    # ---------- packets ----------
    def _on_receive(self, packet, interface):
        if interface is not self.iface:
            return
        d = packet.get("decoded", {})
        port = d.get("portnum", "ENCRYPTED")
        try:
            self.h.raw({k: v for k, v in packet.items() if k != "raw"})
        except Exception:
            pass
        frm = packet.get("fromId")
        if not frm and isinstance(packet.get("from"), int):
            frm = "!%08x" % packet["from"]
        hs, hl = packet.get("hopStart"), packet.get("hopLimit")
        self.h.packet({"port": port, "from": frm,
                       "snr": packet.get("rxSnr"), "rssi": packet.get("rxRssi"),
                       "hops": (hs - hl) if isinstance(hs, int) and isinstance(hl, int) else None,
                       "via_mqtt": bool(packet.get("viaMqtt")), "ts": time.time()})
        if port == "PAXCOUNTER_APP" and d.get("payload"):
            try:
                p = paxcount_pb2.Paxcount()
                p.ParseFromString(d["payload"])
                self.h.pax({"ts": time.time(), "from": frm,
                            "wifi": p.wifi, "ble": p.ble})
            except Exception as e:
                self.h.event("bad paxcounter packet: %s" % e)

    def _on_proxy(self, proxymessage, interface):
        if interface is not self.iface:
            return
        which = proxymessage.WhichOneof("payload_variant")
        payload = proxymessage.data if which == "data" else proxymessage.text.encode()
        self.h.proxy(proxymessage.topic, payload, proxymessage.retained)

    # ---------- state ----------
    def snapshot(self):
        base = {"connected": False, "port": self.port or "auto", "error": self.error,
                "busy": self.busy, "node": None, "config": None, "nodes": [],
                "conn": dict(self.conn), "last_board": self.last_board}
        iface = self.iface
        if iface is None:
            return base
        try:
            node = iface.localNode
            lc, mc = node.localConfig, node.moduleConfig
            me = iface.getMyNodeInfo() or {}
            user, dm = me.get("user", {}), me.get("deviceMetrics", {})
            ch0 = node.channels[0].settings if node.channels else None
            meta = getattr(iface, "metadata", None)
            my_id = user.get("id")
            nodes = []
            for n in list(iface.nodes.values()):
                u, m = n.get("user", {}), n.get("deviceMetrics", {})
                nodes.append({
                    "id": u.get("id"), "long": u.get("longName"),
                    "short": u.get("shortName"), "hw": u.get("hwModel"),
                    "snr": n.get("snr"), "last_heard": n.get("lastHeard"),
                    "hops": n.get("hopsAway"), "battery": m.get("batteryLevel"),
                    "is_me": u.get("id") == my_id})
            base.update({
                "connected": True,
                "node": {"id": my_id, "long": user.get("longName"),
                         "short": user.get("shortName"), "hw": user.get("hwModel"),
                         "fw": getattr(meta, "firmware_version", "") if meta else "",
                         "uptime": dm.get("uptimeSeconds"),
                         "battery": dm.get("batteryLevel"),
                         "chan_util": dm.get("channelUtilization"),
                         "air_tx": dm.get("airUtilTx"),
                         "mac": _mac_from(user),
                         "role": _enum_name(lc.device, "role"),
                         "reboots": getattr(getattr(iface, "myInfo", None), "reboot_count", None),
                         "has_wifi": getattr(meta, "hasWifi", None) if meta else None,
                         "has_bluetooth": getattr(meta, "hasBluetooth", None) if meta else None,
                         "has_pkc": getattr(meta, "hasPKC", None) if meta else None},
                "config": {
                    "region": _enum_name(lc.lora, "region"),
                    "preset": _enum_name(lc.lora, "modem_preset"),
                    "wifi": bool(lc.network.wifi_enabled),
                    "bluetooth": bool(lc.bluetooth.enabled),
                    "paxcounter": bool(mc.paxcounter.enabled),
                    "pax_interval": int(mc.paxcounter.paxcounter_update_interval),
                    "mqtt": bool(mc.mqtt.enabled),
                    "mqtt_proxy": bool(mc.mqtt.proxy_to_client_enabled),
                    "map_reporting": bool(mc.mqtt.map_reporting_enabled),
                    "ok_to_mqtt": bool(getattr(lc.lora, "config_ok_to_mqtt", False)),
                    "mqtt_root": mc.mqtt.root,
                    "uplink": bool(ch0.uplink_enabled) if ch0 else None,
                    "channel_name": ch0.name if ch0 else ""},
                "nodes": nodes})
            self.last_board = {k: base["node"].get(k) for k in ("id", "long", "short", "hw", "fw", "mac")}
            base["last_board"] = self.last_board
        except Exception as e:  # board mid-reboot or config not ready
            base["error"] = "reading board: %s" % str(e)[:120]
        return base

    def channels(self):
        """Active channels: [{index, name, role}]. The primary's empty name becomes the preset name."""
        iface = self.iface
        if iface is None:
            return []
        node = iface.localNode
        preset = _enum_name(node.localConfig.lora, "modem_preset")
        out = []
        for c in node.channels or []:
            role = _enum_name(c, "role")
            if role == "DISABLED":
                continue
            out.append({"index": c.index, "role": role,
                        "name": c.settings.name or (preset_channel_name(preset) if role == "PRIMARY" else "Channel %d" % c.index)})
        return out

    def send_text(self, text, dest="^all", channel_index=0, on_ack=None):
        iface = self.iface
        if iface is None:
            raise RuntimeError("board not connected")
        pkt = _send_text(iface, text, dest, channel_index, on_ack)
        return {"id": getattr(pkt, "id", None)}

    def raw_info(self):
        """Everything the board reports, roughly what `meshtastic --info` prints.
        Secrets are removed by the caller."""
        from google.protobuf.json_format import MessageToDict
        iface = self.iface
        if iface is None:
            raise RuntimeError("board not connected")
        md = lambda m: MessageToDict(m, preserving_proto_field_name=True)
        node = iface.localNode
        out = {"myInfo": md(iface.myInfo) if getattr(iface, "myInfo", None) else None,
               "metadata": md(iface.metadata) if getattr(iface, "metadata", None) else None,
               "localConfig": md(node.localConfig), "moduleConfig": md(node.moduleConfig),
               "channels": [md(c) for c in (node.channels or [])],
               "nodes": dict(iface.nodes or {})}
        return out

    # ---------- changing modes ----------
    def apply_mode(self, mode_id, pax_interval=60):
        mode = MODES[mode_id]
        with self._apply_lock:
            iface = self.iface
            if iface is None:
                raise RuntimeError("board not connected")
            self.busy = True
            try:
                node = iface.localNode
                node.waitForConfig()
                settings = dict(mode["settings"])
                if mode["pax"]:
                    settings["paxcounter.paxcounter_update_interval"] = int(pax_interval)
                begin = getattr(node, "beginSettingsTransaction", None)
                if begin:
                    begin()
                touched = []
                for path, value in settings.items():
                    section, field = path.split(".", 1)
                    root = node.localConfig if section in LOCAL_SECTIONS else node.moduleConfig
                    try:
                        setattr(getattr(root, section), field, value)
                    except AttributeError:       # setting doesn't exist on this firmware
                        self.h.event("skipped %s (not in this firmware)" % path)
                        continue
                    if section not in touched:
                        touched.append(section)
                for section in touched:
                    node.writeConfig(section)
                if mode["uplink"] is not None:
                    node.channels[0].settings.uplink_enabled = mode["uplink"]
                    node.writeChannel(0)
                commit = getattr(node, "commitSettingsTransaction", None)
                if commit:
                    commit()
                self.h.event("settings sent for mode: " + mode["label"])
            finally:
                self.busy = False


def _send_text(iface, text, dest, channel_index, on_ack):
    """sendText with an ACK callback, across Python-library versions."""
    import inspect
    def cb(pkt):
        try:
            routing = (pkt.get("decoded") or {}).get("routing") or {}
            on_ack(routing.get("errorReason", "NONE"))
        except Exception:
            pass
    kw = dict(destinationId=dest, wantAck=True, channelIndex=channel_index)
    if on_ack:
        kw["onResponse"] = cb
        if "onResponseAckPermitted" in inspect.signature(iface.sendText).parameters:
            kw["onResponseAckPermitted"] = True     # call back on plain ACKs too
    return iface.sendText(text, **kw)


class MockRadio:
    """A pretend board. Reboots take about 5 seconds, like the real thing."""

    def __init__(self, hooks):
        self.h = hooks
        self.error = ""
        self.busy = False
        self._stop = threading.Event()
        self._down_until = 0.0
        self._t0 = time.time()
        self._people = 6
        self.conn = _new_conn()
        self.conn.update(connected_at=self._t0, last_connected=self._t0, connects=1,
                         device_path="/dev/cu.usbmodem1101 (simulated)",
                         usb={"usb_description": "USB JTAG/serial debug unit", "usb_manufacturer": "Espressif",
                              "usb_serial": "MOCK0938", "usb_vid_pid": "303a:1001"})
        self.last_board = None
        self.cfg = {"region": "NP_865", "preset": "LONG_FAST", "wifi": True,
                    "bluetooth": False, "paxcounter": False, "pax_interval": 60,
                    "mqtt": True, "mqtt_proxy": False, "map_reporting": True, "ok_to_mqtt": True,
                    "mqtt_root": "msh/NP_865", "uplink": True, "channel_name": ""}
        self.others = [
            {"id": "!a1f80460", "long": "Meshtastic 0460", "short": "0460",
             "hw": "SEEED_XIAO_S3", "snr": 5.5, "hops": 0, "battery": 101},
            {"id": "!433c7430", "long": "GOSH-Saad-gsh1", "short": "gsh1",
             "hw": "HELTEC_V3", "snr": -3.0, "hops": 1, "battery": 87}]
        for o in self.others:   # boards without a clock keep a stale "last heard"
            o["last_heard"] = int(time.time()) - 6 * 3600

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _up(self):
        return time.time() >= self._down_until

    def _run(self):
        tick = 0
        while not self._stop.wait(1.0):
            tick += 1
            if not self._up():
                continue
            now = time.time()
            if tick % 5 == 0:
                self.h.raw({"from": 2717321528, "to": 4294967295, "id": random.randrange(1 << 30),
                            "hopLimit": 3, "fromId": "!a1f80938", "toId": "^all",
                            "decoded": {"portnum": "TELEMETRY_APP",
                                        "telemetry": {"deviceMetrics": {"batteryLevel": 101, "voltage": 4.2}}}})
                self.h.packet({"port": "TELEMETRY_APP", "from": "!a1f80938",
                               "snr": None, "ts": now})
            if tick % 7 == 0:
                o = random.choice(self.others)
                o["snr"] = round(o["snr"] + random.uniform(-0.6, 0.6), 1)
                port = random.choice(["NODEINFO_APP", "POSITION_APP", "TEXT_MESSAGE_APP",
                                      "PAXCOUNTER_APP", "TELEMETRY_APP", "ENCRYPTED"])
                dec = {"portnum": port}
                dm = False
                if port == "TEXT_MESSAGE_APP":
                    t = random.choice(["namaste from the bench", "anyone on LongFast?", "signal check: hearing you 5/5",
                                       "paxcounter says 12 people in the lab", "testing from the roof"])
                    dec.update(text=t, payload=t.encode())
                    dm = random.random() < 0.3
                elif port == "NODEINFO_APP":
                    dec.update(user={"id": o["id"], "longName": o["long"], "hwModel": o["hw"]})
                elif port == "PAXCOUNTER_APP":
                    dec.update(paxcounter={"wifi": random.randint(0, 5), "ble": random.randint(2, 9)})
                elif port == "TELEMETRY_APP":
                    dec.update(telemetry={"deviceMetrics": {"batteryLevel": o["battery"], "voltage": 4.1,
                                                            "channelUtilization": 3.2}})
                elif port == "POSITION_APP":
                    dec.update(position={"latitude": 27.70, "longitude": 85.32})
                pkt = {"fromId": o["id"], "toId": "!a1f80938" if dm else "^all", "channel": 0,
                       "id": random.randrange(1, 1 << 31), "rxSnr": o["snr"], "rxRssi": -40 - random.randint(0, 40),
                       "hopStart": 3, "hopLimit": 3 - o["hops"]}
                if port != "ENCRYPTED":
                    pkt["decoded"] = dec
                else:
                    pkt["encrypted"] = b"\x00" * 24
                self.h.raw(pkt)
                self.h.packet({"port": port, "from": o["id"], "snr": o["snr"], "rssi": -40 - int(random.random() * 30),
                               "hops": o["hops"], "via_mqtt": False, "ts": now})
            if self.cfg["paxcounter"] and not self.cfg["wifi"] and tick % 5 == 0:
                self._people = max(0, self._people + random.choice([-2, -1, 0, 1, 2, 3]))
                ble = int(self._people * 0.55)
                self.h.pax({"ts": now, "from": "!a1f80938",
                            "wifi": self._people - ble, "ble": ble})
            if self.cfg["mqtt_proxy"] and self.cfg["mqtt"] and tick % 10 == 0:
                self.h.proxy("msh/NP_865/2/e/LongFast/!a1f80938", b"\x00", False)

    def snapshot(self):
        now = time.time()
        if not self._up() and self.conn["connected_at"]:
            self.conn.update(connected_at=None, last_lost=now)
        elif self._up() and not self.conn["connected_at"]:
            self.conn.update(connected_at=now, last_connected=now, connects=self.conn["connects"] + 1)
        base = {"connected": False, "port": "mock", "error": "",
                "busy": self.busy, "node": None, "config": None, "nodes": [],
                "conn": dict(self.conn), "last_board": self.last_board}
        if not self._up():
            return base
        up = int(time.time() - self._t0)
        base.update({
            "connected": True,
            "node": {"id": "!a1f80938", "long": "Meshtastic 0938 (simulated)",
                     "short": "0938", "hw": "SEEED_XIAO_S3", "fw": "2.5.2 (mock)",
                     "uptime": up, "battery": 101,
                     "chan_util": round(random.uniform(1, 6), 1),
                     "air_tx": round(random.uniform(0.01, 0.4), 2),
                     "mac": "a8:42:e3:a1:f8:09", "role": "CLIENT", "reboots": 3,
                     "has_wifi": True, "has_bluetooth": True, "has_pkc": True},
            "config": dict(self.cfg),
            "nodes": [dict(n, is_me=False) for n in self.others] + [
                {"id": "!a1f80938", "long": "Meshtastic 0938 (simulated)",
                 "short": "0938", "hw": "SEEED_XIAO_S3", "snr": None,
                 "last_heard": int(time.time()), "hops": 0, "battery": 101,
                 "is_me": True}]})
        self.last_board = {k: base["node"].get(k) for k in ("id", "long", "short", "hw", "fw", "mac")}
        base["last_board"] = self.last_board
        return base

    def channels(self):
        return [{"index": 0, "role": "PRIMARY", "name": "LongFast"}] if self._up() else []

    def send_text(self, text, dest="^all", channel_index=0, on_ack=None):
        if not self._up():
            raise RuntimeError("board not connected")
        pid = random.randrange(1, 1 << 31)
        if on_ack:   # pretend the mesh answers after a moment; DMs to unknown nodes fail
            known = dest == "^all" or any(o["id"] == dest for o in self.others)
            threading.Timer(random.uniform(1.5, 4), on_ack,
                            args=("NONE" if known and random.random() > 0.15 else "MAX_RETRANSMIT",)).start()
        return {"id": pid}

    def raw_info(self):
        c = self.cfg
        return {"myInfo": {"my_node_num": 2717321528, "reboot_count": 3},
                "metadata": {"firmware_version": "2.5.2 (mock)", "hw_model": "SEEED_XIAO_S3"},
                "localConfig": {"lora": {"region": c["region"], "modem_preset": c["preset"]},
                                "network": {"wifi_enabled": c["wifi"], "wifi_ssid": "example", "wifi_psk": "not-a-real-secret"},
                                "bluetooth": {"enabled": c["bluetooth"]},
                                "security": {"private_key": "bW9jay1wcml2YXRlLWtleQ==", "public_key": "bW9jay1wdWJsaWM="}},
                "moduleConfig": {"mqtt": {"enabled": c["mqtt"], "root": c["mqtt_root"], "password": "large4cats"},
                                 "paxcounter": {"enabled": c["paxcounter"]}},
                "channels": [{"index": 0, "role": "PRIMARY", "settings": {"psk": "AQ==", "uplink_enabled": c["uplink"]}}],
                "nodes": {n["id"]: {"user": {"id": n["id"], "longName": n["long"], "hwModel": n["hw"]}, "snr": n["snr"]} for n in self.others}}

    def apply_mode(self, mode_id, pax_interval=60):
        mode = MODES[mode_id]
        self.busy = True
        try:
            time.sleep(1.0)
            key = {"network.wifi_enabled": "wifi", "bluetooth.enabled": "bluetooth",
                   "paxcounter.enabled": "paxcounter", "mqtt.enabled": "mqtt",
                   "mqtt.proxy_to_client_enabled": "mqtt_proxy",
                   "mqtt.map_reporting_enabled": "map_reporting",
                   "lora.config_ok_to_mqtt": "ok_to_mqtt"}
            for path, value in mode["settings"].items():
                self.cfg[key[path]] = value
            if mode["pax"]:
                self.cfg["pax_interval"] = int(pax_interval)
            if mode["uplink"] is not None:
                self.cfg["uplink"] = mode["uplink"]
            self.h.event("settings sent for mode: " + mode["label"])
            self._down_until = time.time() + 5
        finally:
            self.busy = False
