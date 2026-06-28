# MQTT Reference

The two shoulder-adjacent face buttons (X and Y) toggle smart plugs over MQTT.
All connection details live in `.env` (gitignored) and are read from the
environment at runtime — nothing here is host-specific.

## Broker

| Setting | Env var | Example |
|---------|---------|---------|
| Host | `MQTT_HOST` | `192.0.2.10` |
| Port | `MQTT_PORT` | `1883` |
| User | `MQTT_USER` | — |
| Password | `MQTT_PASS` | — |

## Devices

These are [Tasmota](https://tasmota.github.io/docs/) smart plugs. Each one
listens on a `cmnd/<device>/POWER` topic and accepts `ON` / `OFF` payloads.

| Plug | Env var | Topic pattern |
|------|---------|---------------|
| Light 1 (button X) | `MQTT_TOPIC_LIGHT1` | `cmnd/<device_1>/POWER` |
| Light 2 (button Y) | `MQTT_TOPIC_LIGHT2` | `cmnd/<device_2>/POWER` |

Find your Tasmota device's topic under **Configuration → Configure MQTT** in
its web UI (it defaults to `tasmota_XXXXXX`, derived from the chip's MAC).

## Quick test

```bash
source .env
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" \
  -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t "$MQTT_TOPIC_LIGHT1" -m "ON"
```
