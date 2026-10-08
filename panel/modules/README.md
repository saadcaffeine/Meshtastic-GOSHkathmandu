# Panel add-on modules

Add-on modules add their own card to the control panel without touching the core code. **Messages** is the first one; use it as a working example.

```bash
python server.py                        # loads the default modules (messages)
python server.py --modules messages     # choose modules, comma-separated
python server.py --modules none         # core panel only
```

A module that fails to load is reported in the event log; the rest of the panel keeps running.

## Layout

```
modules/
  __init__.py            # BaseModule, loader, routes
  <id>/
    __init__.py          # class Module(BaseModule)
    static/
      <id>.js            # browser part (required for a visible card)
      <id>.css           # optional styles
```

## Server side (`modules/<id>/__init__.py`)

```python
from flask import jsonify, request
from modules import BaseModule

class Module(BaseModule):
    id = "hello"                 # must match the folder name
    title = "Hello"
    description = "What this module does, in one line."
    order = 30                   # card position: lower = higher on the page

    def on_packet(self, packet):           # every packet from the board (Meshtastic library dict)
        if (packet.get("decoded") or {}).get("portnum") == "TEXT_MESSAGE_APP":
            self.last = packet["decoded"].get("text")

    def routes(self, bp):                  # mounted at /api/mod/hello/
        @bp.get("/last")
        def last():
            return jsonify(ok=True, text=getattr(self, "last", None))

        @bp.post("/do")
        def do():
            if not bp.authorized():        # respects --token
                return jsonify(ok=False, message="wrong or missing access token"), 403
            ...

    def state(self):                       # small summary, appears in /api/state as modules.hello
        return {"seen": bool(getattr(self, "last", None))}
```

Available to a module: `self.panel.radio` (`snapshot()`, `channels()`, `send_text(text, dest, channel_index, on_ack)`), `self.panel.event(msg)` for the event log, `self.panel.my_id`, and `self.panel.args.data_dir` for files (git-ignored).

## Browser side (`modules/<id>/static/<id>.js`)

```js
(function () {
  const P = window.Panel, U = P.util;
  let box;
  P.registerModule({
    id: "hello",
    mount(el) { box = U.el("div", "", "Waiting…"); el.appendChild(box); },   // once, into the module's card
    async update(S) {                                                         // after every 2 s poll
      if (!S.modules.hello.seen) return;
      const j = await P.api("/api/mod/hello/last");                           // adds the access token
      box.textContent = j.text;                                               // untrusted text: textContent only
    },
  });
})();
```

`Panel.util` offers the panel's helpers: `el`, `sv`, `clear`, `spot(nodeId)` and `nodeColor(nodeId)` (the node's colour, the same everywhere), `nodeName`, `ago`, `clock`, `icoSnr`, `icoRssi`, `icoHops` and `flash`. Use the CSS variables (`--surface`, `--ink`, `--ink2`, `--muted`, `--border`, `--s1`, `--good`, `--crit` …) so the card follows light and dark mode.

## Ideas for further modules

Range test logger, traceroute viewer, telemetry and sensor charts (environment modules), a map of node positions, or an alert when a node goes quiet.
