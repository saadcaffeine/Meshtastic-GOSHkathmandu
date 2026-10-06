"""Meshtastic control panel: a small web server for one USB-connected board.

Run:   python server.py            (real board on USB)
       python server.py --mock     (simulated board, no hardware needed)

Then open http://127.0.0.1:8080
"""
import argparse
import base64
import csv
import hmac
import json
import os
import threading
import time
from collections import Counter, deque
from datetime import datetime

from flask import Flask, Response, jsonify, request, send_from_directory

from radio import MODES, MockRadio, RealRadio, detect_mode, preset_channel_name

HERE = os.path.dirname(os.path.abspath(__file__))


SECRET_KEYS = {"privatekey", "psk", "wifipsk", "password"}


def redact(o):
    """Copy of o with keys, passwords and the WiFi password hidden."""
    if isinstance(o, dict):
        return {k: ("<hidden>" if str(k).replace("_", "").lower() in SECRET_KEYS and v else redact(v))
                for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [redact(v) for v in o]
    return o


def _json_default(o):
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(bytes(o)).decode()
    return str(o)


def to_text(o):
    return json.dumps(redact(o), indent=2, default=_json_default, sort_keys=True)


class Broker:
    """Talks to the public MQTT server: confirms the node's uplink and, in USB
    proxy mode, forwards the node's messages. Shows nothing secret."""

    def __init__(self, host, port, user, password, simulate=False):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.simulate = simulate
        self.client = None
        self.connected = False
        self.topic = None
        self.count = 0
        self.last_ts = None
        self.forwarded = 0
        self.error = ""
        self._lock = threading.Lock()

    def _ensure(self):
        if self.client is not None or self.simulate:
            return
        import paho.mqtt.client as mqtt
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            c = mqtt.Client()
        c.username_pw_set(self.user, self.password)

        def on_connect(client, userdata, flags, rc, *extra):
            failed = getattr(rc, "is_failure", rc != 0)
            self.connected = not failed
            self.error = "" if not failed else "broker refused login: %s" % rc
            if self.topic and not failed:
                client.subscribe(self.topic)

        def on_disconnect(client, userdata, *a):
            self.connected = False

        def on_message(client, userdata, msg):
            with self._lock:
                self.count += 1
                self.last_ts = time.time()

        c.on_connect, c.on_disconnect, c.on_message = on_connect, on_disconnect, on_message
        try:
            c.connect_async(self.host, self.port)
            c.loop_start()
            self.client = c
        except Exception as e:
            self.error = str(e)[:120]

    def watch(self, topic):
        """Subscribe to the node's own uplink topic (restarts the count if it changes)."""
        if topic == self.topic:
            return
        old, self.topic = self.topic, topic
        with self._lock:
            self.count, self.last_ts = 0, None
        if self.simulate:
            return
        self._ensure()
        if self.client is not None and self.connected:
            try:
                if old:
                    self.client.unsubscribe(old)
                self.client.subscribe(topic)
            except Exception as e:
                self.error = str(e)[:120]

    def publish(self, topic, payload, retained=False):
        if self.simulate:
            self.forwarded += 1
            with self._lock:
                self.count += 1
                self.last_ts = time.time()
            return
        self._ensure()
        if self.client is not None and self.connected:
            self.client.publish(topic, payload, retain=retained)
            self.forwarded += 1

    def sim_uplink(self):
        """Mock mode: pretend the node's WiFi uplink reached the server."""
        with self._lock:
            self.count += 1
            self.last_ts = time.time()

    def stats(self):
        return {"connected": True if self.simulate else self.connected,
                "simulated": self.simulate, "topic": self.topic, "count": self.count,
                "last_ts": self.last_ts, "forwarded": self.forwarded,
                "error": self.error}


class Panel:
    def __init__(self, args):
        self.args = args
        self.lock = threading.RLock()
        self.counts = Counter()
        self.heard = Counter()           # own vs others
        self.pax_hist = deque(maxlen=5000)
        self.events = deque(maxlen=80)
        self.raw_log = deque(maxlen=300)
        self.live = {}                   # node id -> what this panel itself has heard
        self.started = time.time()
        self.switch = {"state": "idle", "mode": None, "message": "", "since": None}
        self.token = args.token or os.environ.get("PANEL_TOKEN", "")
        self.broker = Broker(args.broker, args.broker_port, args.broker_user,
                             args.broker_pass, simulate=args.mock)
        self.radio = MockRadio(self) if args.mock else RealRadio(args.port, self)
        self.my_id = None
        os.makedirs(args.data_dir, exist_ok=True)
        self.csv_path = os.path.join(args.data_dir, "pax_log.csv")
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                csv.writer(f).writerow(["time", "from", "wifi", "ble", "total"])
        self._last_sim = 0.0

    # ----- hooks called by the radio layer -----
    def event(self, msg):
        with self.lock:
            self.events.appendleft({"ts": time.time(), "msg": msg})

    def packet(self, p):
        with self.lock:
            self.counts[p["port"]] += 1
            own = self.my_id and p.get("from") == self.my_id
            self.heard["own" if own else "others"] += 1
            frm = p.get("from")
            if frm and not own:
                n = self.live.setdefault(frm, {"first": p["ts"], "count": 0, "ports": Counter()})
                n["count"] += 1
                n["ports"][p["port"]] += 1
                n.update(last=p["ts"], port=p["port"], via_mqtt=p.get("via_mqtt", False))
                for k in ("snr", "rssi", "hops"):
                    if p.get(k) is not None:
                        n[k] = p[k]

    def raw(self, p):
        d = p.get("decoded") or {}
        port = d.get("portnum", "ENCRYPTED")
        frm = p.get("fromId") or ("!%08x" % p["from"] if isinstance(p.get("from"), int) else None)
        to = p.get("toId") or ("!%08x" % p["to"] if isinstance(p.get("to"), int) else None)
        hs, hl = p.get("hopStart"), p.get("hopLimit")
        payload = d.get("payload")
        item = {"ts": time.time(), "port": port, "from": frm,
                "to": "everyone" if to in ("^all", "!ffffffff") else to,
                "snr": p.get("rxSnr"), "rssi": p.get("rxRssi"),
                "hops": (hs - hl) if isinstance(hs, int) and isinstance(hl, int) else None,
                "via_mqtt": bool(p.get("viaMqtt")),
                "size": len(payload) if isinstance(payload, (bytes, bytearray)) else None,
                "summary": self._summary(port, d),
                "body": to_text(p)}
        item["head"] = "%s  %s  from %s" % (datetime.now().strftime("%H:%M:%S"), port, frm)
        with self.lock:
            self.raw_log.append(item)

    @staticmethod
    def _summary(port, d):
        """One short human line per packet type (never keys or secrets)."""
        try:
            if port == "TEXT_MESSAGE_APP" and d.get("text"):
                t = d["text"]
                return '"%s"' % (t[:60] + ("…" if len(t) > 60 else ""))
            if port == "NODEINFO_APP" and d.get("user"):
                u = d["user"]
                return "%s · %s" % (u.get("longName", "?"), u.get("hwModel", "?"))
            if port == "TELEMETRY_APP" and d.get("telemetry"):
                t = d["telemetry"]
                dm = t.get("deviceMetrics") or {}
                if dm:
                    parts = []
                    if dm.get("batteryLevel") is not None:
                        parts.append("battery %s%%" % dm["batteryLevel"] if dm["batteryLevel"] <= 100 else "on USB power")
                    if dm.get("voltage") is not None:
                        parts.append("%.2f V" % dm["voltage"])
                    if dm.get("channelUtilization") is not None:
                        parts.append("channel %.1f%%" % dm["channelUtilization"])
                    return " · ".join(parts) or "device metrics"
                return ", ".join(k for k in t if k != "time") or "telemetry"
            if port == "POSITION_APP":
                pos = d.get("position") or {}
                if pos.get("latitude") is not None:
                    return "%.3f, %.3f" % (pos["latitude"], pos["longitude"])
                return "position"
            if port == "PAXCOUNTER_APP":
                pc = d.get("paxcounter") or {}
                if pc:
                    return "%s WiFi · %s Bluetooth" % (pc.get("wifi", 0), pc.get("ble", 0))
                return "device count"
            if port == "ROUTING_APP":
                r = d.get("routing") or {}
                return "ack" if r.get("errorReason", "NONE") == "NONE" else "error: %s" % r.get("errorReason")
            if port == "ENCRYPTED":
                return "could not decrypt (different key or channel)"
        except Exception:
            pass
        return ""

    def pax(self, r):
        with self.lock:
            self.pax_hist.append(r)
            if r.get("from") in self.live:
                self.live[r["from"]]["pax"] = {"wifi": r["wifi"], "ble": r["ble"], "ts": r["ts"]}
        with open(self.csv_path, "a", newline="") as f:
            csv.writer(f).writerow([datetime.fromtimestamp(r["ts"]).isoformat(timespec="seconds"),
                                    r.get("from"), r["wifi"], r["ble"], r["wifi"] + r["ble"]])

    def proxy(self, topic, payload, retained):
        self.broker.publish(topic, payload, retained)

    # ----- switching modes -----
    def request_mode(self, mode_id, pax_interval):
        with self.lock:
            if self.switch["state"] in ("applying", "waiting"):
                return False, "a mode change is already in progress"
            self.switch = {"state": "applying", "mode": mode_id,
                           "message": "sending settings to the board", "since": time.time()}
        threading.Thread(target=self._switch_worker, args=(mode_id, pax_interval),
                         daemon=True).start()
        return True, "started"

    def _set_switch(self, state, message):
        with self.lock:
            self.switch.update(state=state, message=message)

    def _switch_worker(self, mode_id, pax_interval):
        try:
            self.radio.apply_mode(mode_id, pax_interval)
        except Exception as e:
            self._set_switch("failed", "could not apply: %s" % str(e)[:160])
            self.event("mode change failed: %s" % e)
            return
        self._set_switch("waiting", "board is restarting, waiting for it to come back")
        deadline = time.time() + 120
        time.sleep(2)
        while time.time() < deadline:
            snap = self.radio.snapshot()
            if snap["connected"] and snap["config"] and detect_mode(snap["config"]) == mode_id:
                self._set_switch("done", "mode is active")
                self.event("mode active: " + MODES[mode_id]["label"])
                return
            time.sleep(2)
        self._set_switch("failed", "board did not report the new mode within 2 minutes; "
                                   "check the USB cable and the event log")

    # ----- building the state the page shows -----
    def merged_nodes(self, db_nodes):
        """Board's node list + what this panel heard itself (timed by this computer's clock,
        which is reliable even when the board has no GPS or time)."""
        with self.lock:
            live = {k: dict(v, ports=dict(v["ports"])) for k, v in self.live.items()}
        out, seen = [], set()
        for n in db_nodes:
            n = dict(n)
            seen.add(n.get("id"))
            n["board_last_heard"] = n.get("last_heard")
            lv = live.get(n.get("id"))
            if lv:
                n["live"] = lv
                n["last_heard"] = lv["last"]
                for k in ("snr", "hops"):
                    if lv.get(k) is not None:
                        n[k] = lv[k]
            elif not n.get("is_me"):
                n["last_heard"] = None     # board's own record is not trustworthy without a clock
            out.append(n)
        for nid, lv in live.items():       # heard, but not (yet) in the board's list
            if nid not in seen:
                out.append({"id": nid, "long": None, "short": None, "hw": None, "is_me": False,
                            "snr": lv.get("snr"), "hops": lv.get("hops"), "battery": None,
                            "last_heard": lv["last"], "board_last_heard": None, "live": lv})
        return out

    def state(self):
        snap = self.radio.snapshot()
        node, cfg = snap["node"], snap["config"]
        if node and node.get("id"):
            self.my_id = node["id"]
        now = time.time()
        if cfg and node:
            name = cfg["channel_name"] or preset_channel_name(cfg["preset"])
            root = cfg["mqtt_root"] or "msh/" + cfg["region"]
            self.broker.watch("%s/2/e/%s/%s" % (root, name, node["id"]))
            if self.args.mock and cfg["mqtt"] and cfg["uplink"] and not cfg["mqtt_proxy"] \
                    and now - self._last_sim > 15:
                self._last_sim = now
                self.broker.sim_uplink()
        with self.lock:
            history = list(self.pax_hist)[-1500:]
            by_port = dict(self.counts.most_common())
            heard = dict(own=self.heard["own"], others=self.heard["others"])
            events = list(self.events)[:40]
            switch = dict(self.switch)
        current = detect_mode(cfg)
        return {
            "now": now,
            "mock": self.args.mock,
            "auth_required": bool(self.token),
            "connected": snap["connected"], "busy": snap["busy"],
            "error": snap["error"], "port": snap["port"],
            "conn": snap.get("conn"), "last_board": snap.get("last_board"),
            "node": node, "config": cfg,
            "mode": {"current": current,
                     "label": MODES[current]["label"] if current in MODES else
                              ("Custom settings" if current else None)},
            "modes": [dict(id=k, label=v["label"], summary=v["summary"],
                           note=v["note"], pax=v["pax"]) for k, v in MODES.items()],
            "switch": switch,
            "pax": {"history": [[round(r["ts"], 1), r["wifi"], r["ble"]] for r in history]},
            "nodes": self.merged_nodes(snap["nodes"]),
            "panel_started": self.started,
            "packets": {"total": sum(by_port.values()), "by_port": by_port, **heard},
            "broker": self.broker.stats(),
            "events": events,
        }


def create_app(panel):
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(os.path.join(HERE, "static"), "index.html")

    def authorized():
        return (not panel.token) or hmac.compare_digest(
            request.headers.get("X-Panel-Token", ""), panel.token)

    @app.get("/api/raw/info")
    def raw_info():
        if not authorized():
            return jsonify(ok=False, message="wrong or missing access token"), 403
        try:
            return jsonify(ok=True, text=to_text(panel.radio.raw_info()))
        except Exception as e:
            return jsonify(ok=False, message=str(e)[:200]), 503

    @app.get("/api/raw/packets")
    def raw_packets():
        if not authorized():
            return jsonify(ok=False, message="wrong or missing access token"), 403
        try:
            since = float(request.args.get("since", 0))
        except ValueError:
            since = 0.0
        with panel.lock:
            items = [r for r in panel.raw_log if r["ts"] > since]
        return jsonify(ok=True, items=items[-200:])

    @app.get("/devices/<path:name>")
    def device_image(name):
        # optional local copies of device pictures; the page falls back to meshtastic.org
        return send_from_directory(os.path.join(HERE, "static", "devices"), name)

    @app.get("/api/state")
    def state():
        return jsonify(panel.state())

    @app.post("/api/mode")
    def mode():
        if panel.token:
            sent = request.headers.get("X-Panel-Token", "")
            if not hmac.compare_digest(sent, panel.token):
                return jsonify(ok=False, message="wrong or missing access token"), 403
        body = request.get_json(silent=True) or {}
        mode_id = body.get("mode")
        if mode_id not in MODES:
            return jsonify(ok=False, message="unknown mode"), 400
        try:
            interval = max(30, min(3600, int(body.get("pax_interval", 60))))
        except (TypeError, ValueError):
            return jsonify(ok=False, message="pax_interval must be a number"), 400
        ok, message = panel.request_mode(mode_id, interval)
        return jsonify(ok=ok, message=message), (200 if ok else 409)

    @app.get("/api/pax.csv")
    def pax_csv():
        with open(panel.csv_path, "r") as f:
            data = f.read()
        return Response(data, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=pax_log.csv"})

    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port, e.g. /dev/cu.usbmodem1101 (default: auto)")
    ap.add_argument("--mock", action="store_true", help="simulate a board")
    ap.add_argument("--host", default="127.0.0.1",
                    help="address to listen on (0.0.0.0 to open to your network)")
    ap.add_argument("--web-port", type=int, default=8080)
    ap.add_argument("--token", help="require this token to change modes "
                                    "(or set PANEL_TOKEN)")
    ap.add_argument("--data-dir", default=os.path.join(HERE, "data"))
    ap.add_argument("--broker", default="mqtt.meshtastic.org")
    ap.add_argument("--broker-port", type=int, default=1883)
    ap.add_argument("--broker-user", default="meshdev")      # public default login
    ap.add_argument("--broker-pass", default="large4cats")   # public default login
    args = ap.parse_args()

    panel = Panel(args)
    panel.radio.start()
    if args.host != "127.0.0.1" and not panel.token:
        print("WARNING: listening on %s with no --token. Anyone who can reach this "
              "page can change your board's settings." % args.host)
    print("Panel running at http://%s:%d%s" % (
        "127.0.0.1" if args.host in ("0.0.0.0", "127.0.0.1") else args.host,
        args.web_port, "  (simulated board)" if args.mock else ""))
    create_app(panel).run(host=args.host, port=args.web_port, threaded=True)


if __name__ == "__main__":
    main()
