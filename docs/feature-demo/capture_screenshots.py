"""Drive the real website with a fake webcam and save feature screenshots.

Needs the stack running (../../run_local.sh), ffmpeg, and Playwright:
    uv venv /tmp/shots && uv pip install -p /tmp/shots/bin/python playwright
    /tmp/shots/bin/python -m playwright install chromium
    /tmp/shots/bin/python capture_screenshots.py screenshots/
Chromium plays the photos in sample-images/ as its webcam. Use a fresh database
(python backend/seed_db.py --reset) so the counts start at zero.
"""
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

IMAGES = Path(__file__).parent / "sample-images"
VIDEOS = Path(tempfile.mkdtemp())
OUT = Path(sys.argv[1])
SENT_TOAST = re.compile(r"^\d+ SMS sent")
OUT.mkdir(parents=True, exist_ok=True)
WEB, API = "http://localhost:3000", "http://localhost:8000"
DESKTOP = dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
             user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36")


def api(path, body=None, token=None, method=None):
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode() if body is not None else None,
                                 method=method or ("POST" if body is not None else "GET"))
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def token(email, portal):
    return api("/api/v1/auth/login", {"email": email, "password": "demo1234", "portal": portal})["access_token"]


WARD = token("ward17@kathmandu.gov.np", "ward")
KMC = token("anita.shrestha@kathmandu.gov.np", "kmc")


def context(browser, portal, device, no_camera=False):
    ctx = browser.new_context(**device, permissions=["camera"])
    tok = WARD if portal == "ward" else KMC
    ctx.add_init_script(f"sessionStorage.setItem('kwm-token-{portal}', '{tok}');")
    if no_camera:  # what a phone sees on plain http over Wi-Fi: no camera API
        ctx.add_init_script("Object.defineProperty(navigator, 'mediaDevices', {value: undefined}); Object.defineProperty(window, 'isSecureContext', {value: false});")
    return ctx


def shot(page, name, full=False):
    page.add_style_tag(content="nextjs-portal { display: none !important; }")  # hide the dev-mode badge
    page.wait_for_timeout(400)
    size = page.viewport_size
    if full:  # grow the viewport instead of full_page, so the fixed sidebar spans the whole image
        page.set_viewport_size({"width": size["width"], "height": page.evaluate("document.documentElement.scrollHeight")})
        page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{name}.png"))
    page.set_viewport_size(size)
    print("saved", name)


def fake_webcam(image, rotate=False):
    """A 640x480 .y4m clip of one photo, for Chromium's fake camera."""
    out = VIDEOS / f"{image}.y4m"
    fit = "scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=0xd8d2c4"
    vf = ("transpose=2," if rotate else "") + fit
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(IMAGES / image), "-t", "1", "-r", "5",
                    "-vf", vf, "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def launch(p, video):
    return p.chromium.launch(args=[
        "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
        f"--use-file-for-fake-video-capture={video}",
    ])


with sync_playwright() as p:
    # --- Identify: photo mode (banana peel in front of the camera) ---
    b = launch(p, fake_webcam("banana-peel.jpg"))
    for device, tag in ((DESKTOP, "desktop"), (PHONE, "phone")):
        page = context(b, "ward", device).new_page()
        page.goto(f"{WEB}/ward/identify")
        page.get_by_label("Take photo").wait_for()
        page.wait_for_timeout(800)
        shot(page, f"01-identify-camera-{tag}")
        page.get_by_label("Take photo").click()
        page.get_by_role("button", name="Retake").wait_for()
        page.get_by_text("confident").wait_for()
        shot(page, f"02-identify-photo-result-{tag}", full=tag == "phone")
        page.context.close()
    b.close()

    # --- Identify: live video (crushed plastic bottle) ---
    b = launch(p, fake_webcam("plastic-bottle.jpg", rotate=True))
    for device, tag in ((DESKTOP, "desktop"), (PHONE, "phone")):
        page = context(b, "ward", device).new_page()
        page.goto(f"{WEB}/ward/identify")
        page.get_by_role("button", name="Live video").click()
        page.get_by_text("ms per frame").wait_for()
        page.wait_for_timeout(1500)
        shot(page, f"03-identify-live-{tag}")
        if tag == "desktop":
            page.get_by_role("button", name="Save this result").click()
            page.get_by_text("Saved:").wait_for()
            shot(page, "04-identify-live-saved-desktop", full=True)
        page.context.close()
    b.close()

    # --- Identify: upload + phone without camera API ---
    b = p.chromium.launch()
    page = context(b, "ward", DESKTOP).new_page()
    page.goto(f"{WEB}/ward/identify")
    page.get_by_role("button", name="Upload").click()
    page.get_by_text("Drop a photo here").wait_for()
    shot(page, "05-identify-upload-empty-desktop")
    with page.expect_file_chooser() as fc:
        page.get_by_role("button", name="Choose image").click()
    fc.value.set_files(str(IMAGES / "crushed-cans.jpg"))
    page.get_by_text("confident").wait_for()
    shot(page, "06-identify-upload-result-desktop")
    page.context.close()

    page = context(b, "ward", PHONE, no_camera=True).new_page()
    page.goto(f"{WEB}/ward/identify")
    page.get_by_text("Live camera needs HTTPS").wait_for()
    shot(page, "07-identify-phone-fallback-native-camera")
    page.context.close()

    # --- SMS: ward portal ---
    page = context(b, "ward", DESKTOP).new_page()
    page.goto(f"{WEB}/ward/sms")
    page.get_by_text("Dummy mode").wait_for()
    shot(page, "08-sms-ward-overview", full=True)
    page.get_by_role("button", name="Collection delayed").click()
    shot(page, "09-sms-ward-template-selected")
    page.get_by_role("button", name="Send to").click()
    page.get_by_text(SENT_TOAST).wait_for()
    shot(page, "10-sms-ward-broadcast-sent", full=True)
    page.get_by_label("Subscriber name").fill("Nabin Shrestha")
    page.get_by_label("Subscriber phone").fill("984-1234567")
    page.get_by_role("button", name="Add", exact=True).click()
    page.get_by_text("Subscriber added").wait_for()
    shot(page, "11-sms-ward-subscriber-added")
    page.get_by_label("Or send a test to one number").fill("9841234567")
    page.get_by_label("Message").fill("Test message from the SMS page")
    page.get_by_role("button", name="Send test").click()
    page.get_by_text(SENT_TOAST).wait_for()

    # Automatic alerts: a driver reports a delay; the route time changes.
    api("/api/v1/wards/17/routes/2/driver-update", {"outcome": "delayed"}, WARD)
    api("/api/v1/wards/17/routes/3", {"time": "07:30"}, WARD, method="PATCH")
    page.reload()
    page.get_by_text("Dummy mode").wait_for()
    page.get_by_role("button", name="Automatic").click()
    shot(page, "12-sms-ward-automatic-alerts", full=True)
    page.context.close()

    page = context(b, "ward", PHONE).new_page()
    page.goto(f"{WEB}/ward/sms")
    page.get_by_text("Dummy mode").wait_for()
    shot(page, "13-sms-ward-phone", full=True)
    page.context.close()

    # --- SMS: KMC portal (all wards; KMC schedule change alerts Ward 12) ---
    api("/api/v1/kmc/wards/12/schedule", {"time": "09:30", "kind": "Organic"}, KMC, method="PUT")
    page = context(b, "kmc", DESKTOP).new_page()
    page.goto(f"{WEB}/kmc/sms")
    page.get_by_text("Dummy mode").wait_for()
    shot(page, "14-sms-kmc-all-wards", full=True)
    page.context.close()
    b.close()
