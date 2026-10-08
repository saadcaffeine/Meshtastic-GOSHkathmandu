"""Add-on modules for the control panel.

A module is a sub-package of this folder (``modules/<id>/``) whose ``__init__.py``
defines ``class Module(BaseModule)``. Turn modules on with ``--modules id1,id2``
(default: ``messages``), or ``--modules none`` to run without any.

What a module can do:

* react to every packet the board passes over USB   -> ``on_packet(packet)``
* react to panel events (connect, mode change, ...)  -> ``on_event(message)``
* add its own HTTP endpoints under /api/mod/<id>/    -> ``routes(bp)``
* put a small summary into /api/state                -> ``state()``
* ship a browser part: modules/<id>/static/<id>.js (and optional <id>.css),
  which calls ``Panel.registerModule({...})`` - see static/index.html, "module API".

See modules/README.md for a template.
"""
import importlib
import os
import pkgutil

from flask import Blueprint, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODULES = ["messages"]


class BaseModule:
    id = "base"
    title = "Module"
    description = ""
    order = 50                  # where the card sits on the page (lower = higher up)

    def __init__(self, panel):
        self.panel = panel      # access to panel.radio, panel.event(), panel.data_dir, panel.lock ...

    # --- hooks (all optional) ---
    def start(self):
        pass

    def on_packet(self, packet):
        """Called for every packet the board passes on (the raw dict from the Meshtastic library)."""

    def on_event(self, message):
        pass

    def routes(self, bp):
        """Add Flask routes to ``bp`` (mounted at /api/mod/<id>/)."""

    def state(self):
        """Small JSON-able summary added to /api/state under modules[<id>]."""
        return {}

    # --- helpers ---
    def static_dir(self):
        return os.path.join(HERE, self.id, "static")

    def assets(self):
        d, out = self.static_dir(), {}
        for kind in ("js", "css"):
            if os.path.exists(os.path.join(d, "%s.%s" % (self.id, kind))):
                out[kind] = "mod/%s/%s.%s" % (self.id, self.id, kind)
        return out

    def info(self):
        return {"id": self.id, "title": self.title, "description": self.description,
                "order": self.order, "assets": self.assets()}


def available():
    return sorted(m.name for m in pkgutil.iter_modules([HERE]) if m.ispkg)


def load(names, panel):
    """Import and construct the requested modules. Unknown names are reported, not fatal."""
    out = []
    for name in names:
        try:
            mod = importlib.import_module("modules.%s" % name)
            inst = mod.Module(panel)
            out.append(inst)
        except Exception as e:      # a broken add-on must never take the panel down
            panel.event("module %s could not load: %s" % (name, e))
    return out


def mount(app, panel, modules, authorized):
    """Register each module's API routes and static files."""
    for m in modules:
        bp = Blueprint("mod_" + m.id, __name__, url_prefix="/api/mod/" + m.id)
        bp.authorized = authorized
        m.routes(bp)
        app.register_blueprint(bp)

    @app.get("/mod/<mid>/<path:name>")
    def module_static(mid, name):
        for m in modules:
            if m.id == mid:
                return send_from_directory(m.static_dir(), name)
        return ("not found", 404)

    @app.get("/api/modules")
    def module_list():
        from flask import jsonify
        return jsonify(enabled=[m.info() for m in sorted(modules, key=lambda m: m.order)],
                       available=available())
