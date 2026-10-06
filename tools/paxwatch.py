import argparse
import threading
import time
from collections import Counter

import meshtastic.serial_interface
from pubsub import pub

try:
    from meshtastic.protobuf import paxcount_pb2, mqtt_pb2
except ImportError:
    from meshtastic import paxcount_pb2, mqtt_pb2

ap = argparse.ArgumentParser()
ap.add_argument("--port", help="serial port, e.g. /dev/cu.usbmodem1101")
ap.add_argument("--mqtt", action="store_true",
                help="also count messages on the public broker")
ap.add_argument("--topic", default="msh/NP_865/#")
ap.add_argument("--nodes", nargs="*", default=[],
                help="node IDs to track on the broker, e.g. !433c7430")
ap.add_argument("--every", type=int, default=30, help="summary seconds")
args = ap.parse_args()

lock = threading.Lock()
mesh, proxy, broker = Counter(), Counter(), Counter()
pax = {"wifi": 0, "ble": 0}


def on_receive(packet, interface):
    d = packet.get("decoded", {})
    port = d.get("portnum", "ENCRYPTED")
    with lock:
        mesh[port] += 1
    if port == "PAXCOUNTER_APP":
        p = paxcount_pb2.Paxcount()
        p.ParseFromString(d["payload"])
        with lock:
            pax.update(wifi=p.wifi, ble=p.ble)
        total = p.wifi + p.ble
        print(f"{time.strftime('%H:%M:%S')}  PAX {packet.get('fromId')}  "
              f"wifi={p.wifi} ble={p.ble} total={total}  "
              f"{'#' * min(total, 60)}")


def on_proxy(proxymessage, interface):
    with lock:
        proxy["total"] += 1


def start_broker():
    import paho.mqtt.client as mqtt
    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        c = mqtt.Client()
    c.username_pw_set("meshdev", "large4cats")  # public default login

    def on_connect(client, userdata, flags, rc, *extra):
        print("broker connect result:", rc)
        client.subscribe(args.topic)

    def on_message(client, userdata, msg):
        with lock:
            broker["total"] += 1
        try:
            env = mqtt_pb2.ServiceEnvelope()
            env.ParseFromString(msg.payload)
            nid = f"!{getattr(env.packet, 'from'):08x}"
            if nid in args.nodes:
                with lock:
                    broker[nid] += 1
        except Exception:
            pass  # JSON topics and other formats

    c.on_connect, c.on_message = on_connect, on_message
    c.on_subscribe = lambda *a: print("subscribe result:", a[3:])
    c.on_disconnect = lambda *a: print("broker disconnected:", a[2:])
    c.connect("mqtt.meshtastic.org", 1883)
    c.loop_start()


def summary():
    while True:
        time.sleep(args.every)
        with lock:
            line = (f"{time.strftime('%H:%M:%S')}  SUMMARY  "
                    f"mesh={sum(mesh.values())} {dict(mesh)}  "
                    f"proxy={proxy['total']}  pax={pax}")
            if args.mqtt:
                line += f"  broker={dict(broker)}"
        print(line)


pub.subscribe(on_receive, "meshtastic.receive")
pub.subscribe(on_proxy, "meshtastic.mqttclientproxymessage")
iface = meshtastic.serial_interface.SerialInterface(devPath=args.port)
if args.mqtt:
    start_broker()
threading.Thread(target=summary, daemon=True).start()
print("Watching (Ctrl+C to stop)...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    iface.close()