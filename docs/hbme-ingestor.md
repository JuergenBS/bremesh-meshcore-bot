# HBME Ingestor Service

Forwards captured MeshCore packets to the [HBME API](https://hbme.sh) for centralized mesh network analysis and visualization.

---

## Quick Start

1. **Enable the service** in `config.ini`:

```ini
[HBMEIngestor]
enabled = true
api_url = https://api.hbme.sh/ingestor/auth/packet
auth_url = https://auth.hbme.sh/api/firstfactor
preview_mode = true
```

2. **Configure credentials** via the Web Viewer's Services page (`/services`):
   - Enter your HBME username and password
   - Credentials are stored in the bot database (not in config files)

3. **Start in preview mode** (default):
   - Packets are captured and queued for inspection but **not** sent to the API
   - View captured packets in the real-time packet monitor on the Services page

4. **Switch to live mode** when ready:
   - Toggle the mode switch on the Services page
   - Packets are now forwarded to the HBME API

---

## Configuration

### `[HBMEIngestor]` Section

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `false` | Enable/disable the HBME Ingestor service |
| `api_url` | `https://api.hbme.sh/ingestor/auth/packet` | HBME API endpoint for packet submission |
| `auth_url` | `https://auth.hbme.sh/api/firstfactor` | Authelia SSO authentication endpoint |
| `preview_mode` | `true` | `true`: capture only (no API calls), `false`: send packets to API |
| `username` | *(empty)* | HBME username (prefer setting via Web UI) |
| `password` | *(empty)* | HBME password (prefer setting via Web UI) |
| `timeout` | `30` | HTTP request timeout in seconds |
| `max_retries` | `3` | Maximum retry attempts for failed API calls |
| `retry_delay` | `5` | Delay in seconds between retries |
| `debug` | `false` | Enable debug logging |

> **Security Note:** Credentials set via the Web Viewer are stored in the bot's SQLite database, not in the config file. This avoids exposing passwords in plain-text config files.

---

## How It Works

### Authentication

The service authenticates with the HBME API using **Authelia SSO first-factor** authentication:

1. POST credentials to `auth_url` (Authelia first-factor endpoint)
2. Authelia returns a session cookie
3. The session cookie is used for subsequent API requests
4. Sessions are automatically re-authenticated when expired

### Packet Flow

```
MeshCore Radio → Bot (RX_LOG_DATA event) → HBME Ingestor → HBME API
                                                ↓
                                         Preview Queue (DB)
                                                ↓
                                         Web Viewer (WebSocket)
```

1. Raw packet hex data is received from the radio via `RX_LOG_DATA` events
2. The ingestor decodes the packet (route type, payload type, path, SNR/RSSI)
3. In **preview mode**: packet is added to the preview queue (last 50 packets, stored in DB as JSON)
4. In **live mode**: packet is additionally sent to the HBME API as structured JSON

### Statistics

The service tracks:
- **Packets captured**: Total packets received (preview + live)
- **Packets sent**: Successfully forwarded to API (live mode only)
- **Packets failed**: Failed API submissions
- **Average response time**: API response latency
- **Last error**: Most recent error message

Statistics are persisted to the database and displayed on the Services page.

---

## Web Viewer Integration

### Services Page (`/services`)

The Web Viewer includes a dedicated services management page:

- **Status overview**: Success/failure/total packet counts at a glance
- **Mode toggle**: Switch between preview and live mode
- **Credential management**: Set HBME username/password
- **Real-time packet monitor**: Live feed of captured packets

### WebSocket Updates

The services page uses WebSocket (Socket.IO) for real-time updates:

- `hbme_packet` — new packet captured
- `hbme_stats` — updated statistics
- `hbme_clear` — preview queue cleared

Falls back to HTTP polling every 30 seconds if WebSocket is unavailable.

---

## Troubleshooting

### Service Not Starting

```bash
tail -f meshcore_bot.log | grep -i hbme
```

Common issues:
- `enabled = false` in config
- Missing `aiohttp` library: `pip install aiohttp`

### Authentication Failing

- Verify credentials on the Services page
- Check that `auth_url` is reachable: `curl -I https://auth.hbme.sh`
- Look for `401` or `403` errors in the log

### Packets Not Appearing on Services Page

1. Check the bot is connected to the radio (packets flowing in log)
2. Verify Web Viewer is running (`/services` page loads)
3. Check browser console for WebSocket connection errors
4. Try refreshing the page to re-establish the WebSocket connection

### Preview Queue Not Updating

The Web Viewer polls the database for preview queue changes. If the bot and viewer run as separate processes, there may be a short delay (1-3 seconds).

---

## FAQ

**Q: Do I need an HBME account?**
A: Yes. Register at [hbme.sh](https://hbme.sh) to get credentials.

**Q: Can I run HBME Ingestor and Packet Capture (MQTT) simultaneously?**
A: Yes. They are independent services that both listen to radio events. You can capture packets to MQTT and forward them to HBME at the same time.

**Q: What data is sent to the HBME API?**
A: Structured packet data including: origin device, timestamp, route type, payload type, path, raw hex, SNR, and RSSI. DM content is **not** sent — only packet metadata and public channel data.

**Q: Is preview mode safe to leave on?**
A: Yes. In preview mode, no data leaves your machine. Packets are stored locally in the database preview queue (last 50 packets).
