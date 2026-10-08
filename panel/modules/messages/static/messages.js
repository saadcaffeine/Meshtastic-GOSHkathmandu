/* Messages add-on: a simplified chat view (channels + direct messages) for the control panel.
   Everything from the mesh is untrusted text, so it is only ever inserted with textContent. */
(function () {
  "use strict";
  const P = window.Panel, U = P.util, el = U.el;
  const READ_KEY = "panelMessagesRead";
  let root, data = { messages: [], channels: [], me: null, max_bytes: 200 }, ver = -1, cur = "ch:0";
  let lastRead = {}, loading = false, sending = false, convSig = "";
  function nodesSig() {
    const S = P.state();
    return S ? S.nodes.map((n) => n.id + ":" + (n.long || n.short || "")).join("|") : "";
  }
  try { lastRead = JSON.parse(localStorage.getItem(READ_KEY) || "{}"); } catch (e) { lastRead = {}; }
  const saveRead = () => { try { localStorage.setItem(READ_KEY, JSON.stringify(lastRead)); } catch (e) {} };
  const enc = new TextEncoder();

  /* ---------- helpers ---------- */
  function convName(conv) {
    if (conv.startsWith("ch:")) {
      const c = data.channels.find((x) => "ch:" + x.index === conv);
      return c ? c.name : "Channel " + conv.slice(3);
    }
    return U.nodeName(conv.slice(3));
  }
  function convs() {
    const map = new Map();
    data.channels.forEach((c) => map.set("ch:" + c.index, { id: "ch:" + c.index, last: null }));
    if (!map.size) map.set("ch:0", { id: "ch:0", last: null });
    data.messages.forEach((m) => {
      const c = map.get(m.conv) || { id: m.conv, last: null };
      c.last = m; map.set(m.conv, c);
    });
    if (cur.startsWith("dm:") && !map.has(cur)) map.set(cur, { id: cur, last: null });
    const list = [...map.values()];
    const chans = list.filter((c) => c.id.startsWith("ch:")).sort((a, b) => a.id.localeCompare(b.id));
    const dms = list.filter((c) => c.id.startsWith("dm:")).sort((a, b) => ((b.last && b.last.ts) || 0) - ((a.last && a.last.ts) || 0));
    return { chans, dms };
  }
  function unread(conv) {
    const t = lastRead[conv] || 0;
    return data.messages.filter((m) => m.conv === conv && m.dir === "in" && m.ts > t).length;
  }
  function when(ts) {
    const d = new Date(ts * 1000), today = new Date().toDateString() === d.toDateString();
    const t = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
    return today ? t : d.toLocaleDateString([], { day: "numeric", month: "short" }) + " " + t;
  }
  const STATUS = {
    sending: ["…", "sending"], sent: ["✓", "sent, waiting for an answer"],
    heard: ["✓✓", "heard by the mesh"], delivered: ["✓✓", "delivered"],
    "no-ack": ["?", "sent, but no node answered"], failed: ["✕", "not delivered"],
  };

  /* ---------- rendering ---------- */
  function renderConvs() {
    convSig = nodesSig();
    const box = root.querySelector(".msg-convs"); U.clear(box);
    const { chans, dms } = convs();
    const item = (c) => {
      const b = el("button", "msg-conv" + (c.id === cur ? " on" : "")); b.type = "button";
      b.setAttribute("aria-current", c.id === cur ? "true" : "false");
      const top = el("span", "msg-conv-top");
      if (c.id.startsWith("dm:")) top.appendChild(U.spot(c.id.slice(3))); else top.appendChild(el("span", "msg-hash", "#"));
      top.appendChild(el("span", "msg-conv-name", convName(c.id)));
      const n = unread(c.id);
      if (n && c.id !== cur) { const badge = el("span", "msg-badge", String(n)); badge.setAttribute("aria-label", n + " unread"); top.appendChild(badge); }
      b.appendChild(top);
      if (c.last) b.appendChild(el("span", "msg-conv-last", (c.last.dir === "out" ? "You: " : "") + c.last.text));
      b.addEventListener("click", () => { cur = c.id; render(true); root.querySelector("textarea").focus(); });
      return b;
    };
    box.appendChild(el("div", "msg-group", "Channels")); chans.forEach((c) => box.appendChild(item(c)));
    box.appendChild(el("div", "msg-group", "Direct messages"));
    dms.forEach((c) => box.appendChild(item(c)));
    // start a new direct message with any known node
    const S = P.state(), others = S ? S.nodes.filter((n) => !n.is_me && n.id) : [];
    const sel = el("select", "msg-new"); sel.setAttribute("aria-label", "Start a direct message");
    const o0 = el("option", "", "+ New direct message…"); o0.value = ""; sel.appendChild(o0);
    others.forEach((n) => { const o = el("option", "", n.long || n.short || n.id); o.value = n.id; sel.appendChild(o); });
    sel.disabled = !others.length;
    sel.addEventListener("change", () => { if (sel.value) { cur = "dm:" + sel.value; render(true); root.querySelector("textarea").focus(); } });
    box.appendChild(sel);
  }
  function bubble(m) {
    const out = m.dir === "out", b = el("div", "msg " + (out ? "out" : "in"));
    if (!out) {
      const who = el("div", "msg-who"); who.appendChild(U.spot(m.from)); who.appendChild(document.createTextNode(U.nodeName(m.from)));
      b.appendChild(who);
    }
    b.appendChild(el("div", "msg-text", m.text));
    const meta = el("div", "msg-meta");
    meta.appendChild(el("span", "", when(m.ts)));
    if (!out) {
      if (m.via_mqtt) meta.appendChild(el("span", "", "via MQTT"));
      if (m.snr != null) meta.appendChild(U.icoSnr(m.snr));
      if (m.hops != null) meta.appendChild(U.icoHops(m.hops));
    } else {
      const st = STATUS[m.status] || ["", m.status || ""];
      const s = el("span", "msg-status st-" + (m.status || "x"), st[0] + " " + st[1] + (m.reason ? " (" + m.reason + ")" : ""));
      meta.appendChild(s);
    }
    b.appendChild(meta);
    return b;
  }
  function renderThread(forceBottom) {
    const list = root.querySelector(".msg-list");
    const atEnd = forceBottom || list.scrollHeight - list.scrollTop - list.clientHeight < 60;
    U.clear(list);
    const msgs = data.messages.filter((m) => m.conv === cur);
    root.querySelector(".msg-title").textContent = (cur.startsWith("ch:") ? "# " : "") + convName(cur);
    root.querySelector(".msg-sub").textContent = cur.startsWith("ch:")
      ? "Everyone on this channel can read these."
      : "Direct message to " + cur.slice(3) + " (encrypted end to end on firmware 2.5+).";
    if (!msgs.length) list.appendChild(el("div", "msg-empty", cur.startsWith("ch:") ? "No messages on this channel yet." : "No messages yet. Say hello."));
    msgs.forEach((m) => list.appendChild(bubble(m)));
    if (atEnd) list.scrollTop = list.scrollHeight;
    if (msgs.length) { lastRead[cur] = Math.max(lastRead[cur] || 0, msgs[msgs.length - 1].ts); saveRead(); }
  }
  function renderCompose() {
    const S = P.state(), ta = root.querySelector("textarea"), btn = root.querySelector(".msg-send");
    const bytes = enc.encode(ta.value).length, max = data.max_bytes || 200;
    const cnt = root.querySelector(".msg-count");
    cnt.textContent = bytes + " / " + max + " bytes";
    cnt.classList.toggle("over", bytes > max);
    const connected = !!(S && S.connected);
    btn.disabled = sending || !connected || !ta.value.trim() || bytes > max;
    ta.placeholder = connected ? "Message " + (cur.startsWith("ch:") ? "#" : "") + convName(cur) + " (Enter to send, Shift+Enter for a new line)" : "Board not connected";
    root.querySelector(".msg-tok").hidden = !(S && S.auth_required) || !!P.token();
  }
  function render(forceBottom) { renderConvs(); renderThread(forceBottom); renderCompose(); }

  /* ---------- data ---------- */
  async function refresh(forceBottom) {
    if (loading) return; loading = true;
    try {
      const j = await P.api("/api/mod/messages/list");
      if (j.ok) { data = j; ver = j.version; render(forceBottom); }
    } finally { loading = false; }
  }
  async function send() {
    const ta = root.querySelector("textarea"), text = ta.value.trim(), msg = root.querySelector(".msg-err");
    if (!text) return;
    const tokIn = root.querySelector(".msg-tok input");
    if (tokIn && tokIn.value) P.setToken(tokIn.value);
    sending = true; renderCompose(); msg.textContent = "";
    try {
      const j = await P.api("/api/mod/messages/send", { method: "POST", body: { text, conv: cur } });
      if (!j.ok) { msg.textContent = j.message || "Could not send."; if (j.status === 403) root.querySelector(".msg-tok").hidden = false; }
      else { ta.value = ""; await refresh(true); }
    } catch (e) { msg.textContent = "Could not reach the panel server."; }
    finally { sending = false; renderCompose(); }
  }

  /* ---------- module ---------- */
  P.registerModule({
    id: "messages",
    mount(body) {
      root = el("div", "msg-wrap");
      root.appendChild(el("nav", "msg-convs"));
      const th = el("section", "msg-thread");
      const head = el("div", "msg-head"); head.appendChild(el("div", "msg-title")); head.appendChild(el("div", "msg-sub"));
      th.appendChild(head);
      const list = el("div", "msg-list"); list.setAttribute("role", "log"); list.setAttribute("aria-live", "polite"); list.tabIndex = 0;
      th.appendChild(list);
      const form = el("form", "msg-compose");
      const ta = el("textarea"); ta.rows = 2; ta.setAttribute("aria-label", "Message text");
      form.appendChild(ta);
      const bar = el("div", "msg-bar");
      bar.appendChild(el("span", "msg-count"));
      bar.appendChild(el("span", "msg-err")); bar.lastChild.setAttribute("role", "status");
      const tok = el("label", "msg-tok", "Access token "); const ti = el("input"); ti.type = "password"; ti.autocomplete = "off"; tok.appendChild(ti); tok.hidden = true;
      bar.appendChild(tok);
      const btn = el("button", "act msg-send", "Send"); btn.type = "submit"; bar.appendChild(btn);
      form.appendChild(bar);
      th.appendChild(form);
      root.appendChild(th);
      body.appendChild(root);
      ta.addEventListener("input", renderCompose);
      ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!root.querySelector(".msg-send").disabled) send(); } });
      form.addEventListener("submit", (e) => { e.preventDefault(); send(); });
      render(true);
      refresh(true);
    },
    update(S) {
      const st = S.modules && S.modules.messages;
      if (st && st.version !== ver) refresh(false);
      else if (root) {
        // rebuild the list only when node names change, so an open dropdown isn't closed under the user
        if (nodesSig() !== convSig && !root.querySelector(".msg-convs").contains(document.activeElement)) renderConvs();
        renderCompose();
      }
    },
  });
})();
