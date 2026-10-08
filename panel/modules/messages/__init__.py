"""Messages: a simplified chat view - channel messages and direct messages, with sending.

Stores history in data/messages.jsonl (one JSON object per line) so it survives restarts.
"""
import json
import os
import threading
import time

from flask import jsonify, request

from modules import BaseModule

MAX_BYTES = 200          # Meshtastic text payloads must stay under ~230 bytes; 200 is a safe limit
KEEP = 1000              # messages kept in memory / returned


class Module(BaseModule):
    id = "messages"
    title = "Messages"
    description = "Channel and direct messages, like a simplified Meshtastic app."
    order = 20

    def __init__(self, panel):
        super().__init__(panel)
        self.lock = threading.Lock()
        self.msgs = []           # newest last
        self.by_seq = {}
        self.seen_ids = set()    # de-duplicate packets the library may report twice
        self.seq = 0
        self.version = 0
        self.path = os.path.join(panel.args.data_dir, "messages.jsonl")
        self._load()

    # ---------- storage ----------
    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if "update" in r:
                        m = self.by_seq.get(r["update"])
                        if m:
                            m.update(r.get("set", {}))
                    else:
                        self._add(r, persist=False)
        except OSError:
            pass

    def _write(self, rec):
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError as e:
            self.panel.event("messages: could not save (%s)" % e)

    def _add(self, m, persist=True):
        with self.lock:
            if m.get("seq"):
                self.seq = max(self.seq, m["seq"])
            else:
                self.seq += 1
                m["seq"] = self.seq
            self.msgs.append(m)
            self.by_seq[m["seq"]] = m
            if m.get("pid"):
                self.seen_ids.add((m.get("from"), m["pid"]))
            if len(self.msgs) > KEEP:
                old = self.msgs.pop(0)
                self.by_seq.pop(old["seq"], None)
            self.version += 1
        if persist:
            self._write(m)
        return m

    def _set(self, seq, **fields):
        with self.lock:
            m = self.by_seq.get(seq)
            if not m:
                return
            m.update(fields)
            self.version += 1
        self._write({"update": seq, "set": fields})

    # ---------- incoming ----------
    def _my_id(self):
        if not self.panel.my_id:
            try:
                node = self.panel.radio.snapshot().get("node") or {}
                self.panel.my_id = node.get("id")
            except Exception:
                pass
        return self.panel.my_id

    def on_packet(self, p):
        d = p.get("decoded") or {}
        if d.get("portnum") != "TEXT_MESSAGE_APP":
            return
        text = d.get("text")
        if text is None and isinstance(d.get("payload"), (bytes, bytearray)):
            text = d["payload"].decode("utf-8", "replace")
        if text is None:
            return
        frm = p.get("fromId") or ("!%08x" % p["from"] if isinstance(p.get("from"), int) else None)
        to = p.get("toId") or ("!%08x" % p["to"] if isinstance(p.get("to"), int) else None)
        pid = p.get("id")
        if pid and (frm, pid) in self.seen_ids:
            return
        me = self._my_id()
        if frm and frm == me:
            return                              # our own sends are recorded when we send them
        broadcast = to in (None, "^all", "!ffffffff")
        conv = "ch:%d" % (p.get("channel") or 0) if broadcast else "dm:%s" % frm
        hs, hl = p.get("hopStart"), p.get("hopLimit")
        self._add({"ts": time.time(), "conv": conv, "dir": "in", "from": frm, "to": "^all" if broadcast else to,
                   "text": text, "pid": pid, "snr": p.get("rxSnr"), "rssi": p.get("rxRssi"),
                   "hops": (hs - hl) if isinstance(hs, int) and isinstance(hl, int) else None,
                   "via_mqtt": bool(p.get("viaMqtt"))})

    # ---------- outgoing ----------
    def send(self, text, conv):
        if conv.startswith("dm:"):
            dest, ch = conv[3:], 0
        else:
            dest, ch = "^all", int(conv.split(":", 1)[1])
        m = self._add({"ts": time.time(), "conv": conv, "dir": "out", "from": self._my_id(), "to": dest,
                       "text": text, "status": "sending"})
        seq = m["seq"]

        def on_ack(reason):
            if reason in (None, "NONE"):
                self._set(seq, status="delivered" if dest != "^all" else "heard", acked=time.time())
            else:
                self._set(seq, status="failed", reason=str(reason))

        try:
            r = self.panel.radio.send_text(text, dest=dest, channel_index=ch, on_ack=on_ack)
            self._set(seq, status="sent", pid=r.get("id"))
            # no answer within 60 s: leave it as "sent" but say we never heard back
            threading.Timer(60, lambda: self.by_seq.get(seq, {}).get("status") == "sent"
                            and self._set(seq, status="no-ack")).start()
        except Exception as e:
            self._set(seq, status="failed", reason=str(e)[:120])
        return m

    # ---------- API ----------
    def routes(self, bp):
        @bp.get("/list")
        def list_():
            with self.lock:
                items = [dict(m) for m in self.msgs]
                ver = self.version
            try:
                chans = self.panel.radio.channels()
            except Exception:
                chans = []
            return jsonify(ok=True, version=ver, messages=items, channels=chans,
                           me=self._my_id(), max_bytes=MAX_BYTES)

        @bp.post("/send")
        def send_():
            if not bp.authorized():
                return jsonify(ok=False, message="wrong or missing access token"), 403
            body = request.get_json(silent=True) or {}
            text = (body.get("text") or "").strip()
            conv = body.get("conv") or "ch:0"
            if not text:
                return jsonify(ok=False, message="empty message"), 400
            if len(text.encode("utf-8")) > MAX_BYTES:
                return jsonify(ok=False, message="message too long (max %d bytes)" % MAX_BYTES), 400
            if not (conv.startswith("ch:") and conv[3:].isdigit()) and not (conv.startswith("dm:!") and len(conv) == 12):
                return jsonify(ok=False, message="unknown conversation"), 400
            if not self.panel.radio.snapshot()["connected"]:
                return jsonify(ok=False, message="board not connected"), 409
            m = self.send(text, conv)
            return jsonify(ok=True, message=m)

    def state(self):
        with self.lock:
            return {"version": self.version, "count": len(self.msgs)}
