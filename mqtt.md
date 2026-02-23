# MQTT Configuration

Credentials are stored in `.env` (not committed to git).

## Broker

- **Host**: `$MQTT_HOST` (default `10.0.0.100`)
- **Port**: `$MQTT_PORT` (default `1883`)

## Devices

### Light 1 (tasmota_952D74)
- **Topic**: `cmnd/tasmota_952D74/POWER`
- **Payloads**: `ON`, `OFF`

### Light 2 (tasmota_93D272)
- **Topic**: `cmnd/tasmota_93D272/POWER`
- **Payloads**: `ON`, `OFF`

## Testing

```bash
source ~/.env
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t "cmnd/tasmota_952D74/POWER" -m "ON"
```
