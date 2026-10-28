# Feature demo: camera identification and SMS alerts

Screenshots and logs from a real run of the full stack (model service, FastAPI backend, Next.js site) on 28 Oct 2026. Every screenshot comes from the running app. The "camera" is Chromium's test webcam playing the photos in `sample-images/`, so the classifier results are real model outputs. To capture them again, see `capture_screenshots.py`.

## 1. Identify Waste: camera, live video, upload

**Before:** staff picked a file with a file input and then pressed *Identify*. On a laptop that meant saving a photo first.

**Now:** the page opens the camera, and there are three tabs:

| Mode | What happens |
| --- | --- |
| **Camera** | The camera preview starts when the page opens (back camera on phones). Tap the shutter, or press **Space** on a laptop. The photo is identified straight away, with no second button. **Retake** starts again. Phones with several cameras get a switch-camera button. |
| **Live video** | About once a second, a frame goes to the classifier and the label over the video updates ("Non-biodegradable · 100%", LIVE badge). These frames are **not saved** (`save=false`), so history only holds what staff keep with **Save this result**. One request is in flight at a time, and it pauses when the tab is hidden. |
| **Upload** | Drag and drop a photo, or use *Choose image*. JPEG/PNG/WebP/HEIC. |

On phones:
- **Open phone camera** opens the phone's own camera app (`capture="environment"`). It works on plain `http://` over Wi-Fi.
- Browsers only allow the in-page camera on HTTPS or localhost. `npm run dev:mobile` in the website repo serves the site over HTTPS on the LAN. It makes a self-signed certificate for the laptop's IP and proxies `/api/v1` to the backend, so the phone needs only one address. This was checked with a phone-sized Chromium at `https://192.168.16.126:3000`: the page reported a secure context, the camera started, and the photo was identified through the proxy (screenshot 15).
- Photos are shrunk in the browser before upload: frames to 1024 px, about 50 KB instead of several MB. Live frames are 512 px, about 34 KB.

| Screenshot | Shows |
| --- | --- |
| `01-identify-camera-desktop.png`, `01-identify-camera-phone.png` | Camera open, shutter button |
| `02-identify-photo-result-desktop.png`, `02-identify-photo-result-phone.png` | One tap → banana peel identified as Biodegradable 100%, Retake button, history updated |
| `03-identify-live-desktop.png`, `03-identify-live-phone.png` | Live video: plastic bottle → Non-biodegradable 100%, LIVE badge, milliseconds per frame |
| `04-identify-live-saved-desktop.png` | *Save this result* adds the live result to history |
| `05-identify-upload-empty-desktop.png`, `06-identify-upload-result-desktop.png` | Upload tab: drop zone, then crushed cans → Non-biodegradable 91% |
| `07-identify-phone-fallback-native-camera.png` | Phone on plain http: explains why, and offers *Open phone camera* |
| `15-phone-over-wifi-https.png` | Phone-sized browser over Wi-Fi HTTPS (`npm run dev:mobile`), in-page camera working |

## 2. SMS alerts (dummy gateway, ready to switch to a real one)

New **SMS Alerts** page in both portals (`/ward/sms`, `/kmc/sms`):

- **Subscribers**: residents' phone numbers per ward. Numbers are checked as Nepali mobiles and stored as `+977…`, and duplicates are rejected. Ward staff see only their own ward, and KMC sees all wards or one ward.
- **Send SMS**: templates (Collection delayed, Time change, Segregation reminder, Awareness program), a character and SMS-part counter (160 characters per SMS, 70 for Nepali Unicode text), *Send to N subscribers*, and *Send test* to one number.
- **Automatic alerts**, with no one pressing send:
  - A driver reports a route **delayed** → "KMC Waste: Collection on Route 2 (Tinkune) is delayed today by a vehicle problem…"
  - A ward changes a **route's time**, or KMC changes a **ward's schedule** → "…changes from 8:00 AM to 7:30 AM."
  - An **awareness program** is announced (created, or approved by KMC) → "KMC Waste: <program> on <date>, <time> at <place>. Everyone is welcome."
- **Outbox**: every message with its type, number, ward, status, time and gateway reference. Filters: All / Automatic / Broadcast / Failed. Failed sends show the gateway's error.

**Dummy mode** (`SMS_PROVIDER=dummy`, the default) sends nothing. Each message is written to the backend log and recorded as "Logged (dummy)", and the page shows a yellow *Dummy mode* badge. **To go live**, set `SMS_PROVIDER=sparrow`, `SPARROW_SMS_TOKEN` and `SMS_SENDER` (Sparrow SMS, Nepal), restart the backend, and send a test to your own number first. The Sparrow client follows their v2 API docs but has not been run against the real gateway. Other gateways go in `backend/app/sms.py` (one class with `send(phone, text)`). The main README has details.

| Screenshot | Shows |
| --- | --- |
| `08-sms-ward-overview.png` | Ward 17 SMS page: dummy badge, stats, 5 demo subscribers |
| `09-sms-ward-template-selected.png` | Template filled in, character / part counter |
| `10-sms-ward-broadcast-sent.png` | Broadcast to 5 subscribers, outbox entries |
| `11-sms-ward-subscriber-added.png` | New subscriber added (`984-1234567`) |
| `12-sms-ward-automatic-alerts.png` | Automatic filter: delay alert and schedule change texts |
| `13-sms-ward-phone.png` | SMS page on a phone |
| `14-sms-kmc-all-wards.png` | KMC portal, all wards: Ward 12 schedule change alert plus Ward 17 messages |

## Logs

| File | Contents |
| --- | --- |
| `logs/feature-events.txt` | **Best for slides.** Only the feature events: each photo or live frame classified (label, confidence, model time, size, ward, user) and each SMS (`[dummy] SMS to +977… ref=dummy-…`), with per-alert summaries |
| `logs/backend-full.txt` | Full backend log for the same run, including HTTP access lines |
| `logs/model-service.txt` | Model service log (YOLOv8s-cls loading, `/classify` calls) |
| `logs/frontend.txt`, `logs/frontend-phone-https.txt` | Next.js dev server: normal mode, and `npm run dev:mobile` with HTTPS on the LAN |
| `logs/backend-tests.txt` | `pytest -v`: 46 passed (13 new: 12 SMS, 1 live-frame) |

Sample lines:

```
INFO app.sms: SMS provider: dummy (messages are logged, not delivered)
INFO app.identify: Saved camera-….jpg -> Bio (100%) in 15ms, 58 KB, ward=17, user=ward17@kathmandu.gov.np
INFO app.identify: Live frame live-frame.jpg -> Non_Bio (100%) in 11ms, 34 KB, ward=17, user=ward17@kathmandu.gov.np
INFO app.sms: [dummy] SMS to +9779800000001 (117 chars, 1 part(s)) ref=dummy-…: KMC Waste: Collection on Route 2 (Tinkune) is delayed today …
INFO app.sms: Ward 17 delay alert sent to 6 subscriber(s)
```

## Known limitations (worth saying in the presentation)

- The classifier is good on single items (banana peel 100% Bio, plastic bottle 100% Non-bio, cans 91–94% Non-bio). A **cage full of green PET bottles was labelled Biodegradable**, probably because of the green colour. Photos of one item, close up, work best, and the page tells users this when confidence is below 70%.
- On a phone, the HTTPS dev mode uses a self-signed certificate, so the browser shows a warning once. A real deployment needs a proper certificate (any HTTPS host).
- SMS sends run inside the request, one number at a time. That is fine for ward-sized lists, but large city-wide broadcasts should move to a background job.

## Sample image credits (Wikimedia Commons)

- `banana-peel.jpg`: *Banana peel on the ground.jpg*, Vladiator360, CC BY-SA 4.0 (cropped)
- `plastic-bottle.jpg`: *Air pressure crushing a plastic bottle p1180559.jpg*, David Monniaux, CC BY-SA 3.0
- `crushed-cans.jpg`: *Crushed cans (9691248780).jpg*, Ruth Hartnup, CC BY 2.0
