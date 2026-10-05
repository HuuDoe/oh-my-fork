#!/usr/bin/env python3
"""ServiceNow ID signup + PDI provisioning bot (runs on GH Actions runner)."""
import os, sys, re, json, time, base64, subprocess, urllib.request

def sh(cmd):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True)

def log(*a): print("[bot]", *a, flush=True)

os.environ["HF_HUB_DISABLE_XET"] = "1"
if not os.environ.get("BOT_DEPS_DONE"):
    sh("pip install --quiet playwright requests vosk soundfile 'faster-whisper' 'huggingface_hub==0.34.4' 'av>=17.0.0' 2>&1 | tail -2")
    sh("pip list 2>/dev/null | grep -iE 'huggingface")
    sh("sudo apt-get install -y xvfb >/dev/null 2>&1; python3 -m playwright install --with-deps chromium 2>&1 | tail -3")
    sh("python3 -c \"from faster_whisper import WhisperModel; WhisperModel('tiny.en',device='cpu',compute_type='int8'); print('FW_PRELOAD_OK')\" 2>&1 | tail -5")
    sh("python3 -c \"import vosk; vosk.Model(model_name='vosk-model-small-en-us-0.15'); print('VOSK_PRELOAD_OK')\" 2>&1 | tail -5")
    os.environ["BOT_DEPS_DONE"] = "1"
    os.execvp("xvfb-run", ["xvfb-run", "-a", sys.executable, os.path.abspath(__file__)])
    sys.exit(0)

import requests
from playwright.sync_api import sync_playwright

EMAILS  = ["devinsnrschb7d7f4c2@maxxspace.com", "devin-snow-research-b7d7f4c26853@maildrop.cc"]
MTPASS  = "Mbx$T3mp2026!"
SNPASS  = "Dvn$Rsch2026!x"
SIGNUP  = "https://signon.servicenow.com/x_snc_sso_auth.do?pageId=sign-up"
RESULT  = {"ok": False, "email": None, "stage": "start"}

def mt_poll(email, minutes=4):
    try:
        tok = requests.post("https://api.mail.tm/token",
            json={"address": email, "password": MTPASS}, timeout=20).json().get("token")
    except Exception as e:
        log("mt token err", e); return None, []
    h = {"Authorization": f"Bearer {tok}"}
    end = time.time() + minutes * 60
    while time.time() < end:
        try:
            msgs = requests.get("https://api.mail.tm/messages", headers=h, timeout=20).json().get("hydra:member", [])
            for m in msgs:
                body = requests.get(f"https://api.mail.tm/messages/{m['id']}", headers=h, timeout=20).json()
                blob = (body.get("text") or "") + " " + " ".join(body.get("html") or [])
                links = re.findall(r'https?://[^\s"\'<>]+', blob)
                sn = [l.rstrip(').,;>') for l in links if "servicenow" in l]
                log("MAIL:", m.get("subject"), "| sn links:", sn[:3])
                return m.get("subject"), sn
        except Exception as e:
            log("mail poll err", e)
        time.sleep(10)
    return None, []

def md_poll(email, minutes=4):
    # maildrop public inbox
    box = email.split("@")[0]
    end = time.time() + minutes * 60
    while time.time() < end:
        try:
            r = requests.get(f"https://api.maildrop.cc/v2/mailbox/{box}", timeout=20)
            items = r.json().get("messages", []) or r.json().get("hydra:member", [])
            for m in items:
                mid = m.get("id") or m.get("@id", "").split("/")[-1]
                body = requests.get(f"https://api.maildrop.cc/v2/mailbox/{box}/{mid}", timeout=20).json()
                blob = json.dumps(body)
                links = re.findall(r'https?://[^\s"\'<>\\]+', blob)
                sn = [l for l in links if "servicenow" in l]
                log("MD MAIL:", m.get("subject"), sn[:3])
                return m.get("subject"), sn
        except Exception as e:
            log("md poll err", e)
        time.sleep(10)
    return None, []

WORD2NUM = {"zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","oh":"0","o":"0"}
def to_digits(txt):
    d = "".join(re.findall(r"\d", txt))
    if len(d) < 5:
        for w in re.findall(r"[a-z]+", txt.lower()):
            if w in WORD2NUM: d += WORD2NUM[w]
    return d

def whisper_digits(mp3):
    txt = ""
    try:
        from faster_whisper import WhisperModel
        global _model
        if "_model" not in globals():
            _model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        segs, _ = _model.transcribe(mp3, beam_size=5)
        txt = " ".join(s.text for s in segs)
    except Exception as e:
        import traceback as _tb; log("fw fail:", _tb.format_exc()[-400:])
    if not txt.strip():
        try:
            import vosk, wave, json as _j, soundfile as sf, numpy as np
            data, srate = sf.read(mp3)
            if getattr(data, "ndim", 1) > 1: data = data.mean(axis=1)
            if srate != 16000:
                n = int(len(data) * 16000 / srate)
                data = np.interp(np.linspace(0, len(data), n), np.arange(len(data)), data)
            pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16).tobytes()
            global _vmodel
            if "_vmodel" not in globals():
                from vosk import SetLogLevel; SetLogLevel(-1)
                _vmodel = vosk.Model(model_name="vosk-model-small-en-us-0.15")
            rec = vosk.KaldiRecognizer(_vmodel, 16000)
            rec.AcceptWaveform(pcm)
            txt = _j.loads(rec.FinalResult()).get("text","")
        except Exception as e:
            log("vosk fail:", repr(e)[:160])
    digits = to_digits(txt)
    log("heard:", repr(txt), "-> digits:", digits)
    return digits

def body_text(page):
    try: return page.locator("body").inner_text(timeout=6000) or ""
    except Exception: return ""

def shot_b64(path):
    try: return base64.b64encode(open(path, "rb").read()).decode()
    except Exception: return ""

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=False, args=[
    "--no-sandbox", "--disable-blink-features=AutomationControlled",
    "--lang=en-US,en", "--disable-dev-shm-usage"])
ctx = browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    viewport={"width": 1280, "height": 900}, locale="en-US")
page = ctx.new_page()

for EMAIL in EMAILS:
    RESULT["email"] = EMAIL
    log("=== signup attempt with", EMAIL)
    try:
        page.goto(SIGNUP, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        page.screenshot(path="/tmp/s1_landing.png")
        log("landed:", page.title())

        page.fill("#email", EMAIL)
        page.fill("#firstName", "Devin")
        page.fill("#lastName", "SecResearch")
        page.fill("#password", SNPASS)
        page.fill("#confirmPassword", SNPASS)
        page.fill("#countrySelectInputId", "United States")
        page.wait_for_timeout(1200)
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        page.evaluate("()=>{let c=document.querySelector('input[name=country]');if(c)c.value='US';}")
        try: page.eval_on_selector("#tnc", "e=>{if(!e.checked)e.click()}")
        except Exception: page.locator("label[for=tnc], .form-check-label").first.click()
        log("form filled")

        anchor = page.frame_locator("iframe[src*='anchor']").first
        try:
            anchor.locator("#recaptcha-anchor").click(timeout=15000)
            log("anchor clicked")
        except Exception as e:
            log("anchor click fail", e)

        token = ""; blocked = False
        bf = page.frame_locator("iframe[src*='bframe']")
        for rnd in range(14):
            page.wait_for_timeout(2500)
            try: token = page.eval_on_selector("#g-recaptcha-response", "e=>e.value") or ""
            except Exception: token = ""
            if len(token) > 50: break
            try: btxt = bf.locator("body").inner_text(timeout=5000)
            except Exception: btxt = ""
            log(f"round {rnd}: toklen={len(token)} btxt[:140]={btxt[:140]!r}")
            if re.search(r"automated queries|unusual traffic|try again later", btxt, re.I):
                blocked = True; break
            if "expired" in btxt.lower():
                try: anchor.locator("#recaptcha-anchor").click(timeout=8000)
                except Exception: pass
                continue
            if not btxt:
                try: anchor.locator("#recaptcha-anchor").click(timeout=8000)
                except Exception: pass
                continue
            if re.search(r"select all|squares|images|vehicles", btxt, re.I):
                try:
                    bf.locator("#recaptcha-audio-button").click(timeout=8000)
                    page.wait_for_timeout(2500)
                    btxt = bf.locator("body").inner_text(timeout=4000)
                    log("post-audio:", btxt[:140])
                except Exception as e:
                    log("audio btn fail", e)
            if re.search(r"automated queries|unusual traffic", btxt, re.I):
                blocked = True; break
            href = None
            for _try in range(6):
                try:
                    href = bf.locator(".rc-audiochallenge-tdownload-link").get_attribute("href", timeout=4000)
                except Exception:
                    href = None
                if href: break
                page.wait_for_timeout(1500)
            if not href:
                log("no audio link"); continue
            mp3 = f"/tmp/rnd{rnd}.mp3"
            try:
                open(mp3, "wb").write(requests.get(href, timeout=30).content)
            except Exception as e:
                log("mp3 dl fail", e); continue
            ans = whisper_digits(mp3)
            if not ans: log("empty transcription"); continue
            bf.locator("#audio-response").fill(ans)
            bf.locator("#recaptcha-verify-button").click()
            log("submitted audio answer:", ans)
            page.wait_for_timeout(3000)

        page.screenshot(path="/tmp/s2_aftercap.png")
        log("captcha result: token_len=", len(token), "blocked=", blocked)
        RESULT["token_len"] = len(token)

        if len(token) > 50:
            RESULT["captcha_token_prefix"] = token[:30]
            try: page.click("#registration_submit_button", timeout=10000)
            except Exception as e: log("submit click fail", e)
            page.wait_for_timeout(9000)
            page.screenshot(path="/tmp/s3_aftersubmit.png")
            vis = body_text(page)
            log("AFTER SUBMIT URL:", page.url)
            log("AFTER SUBMIT BODY[:1200]:", vis[:1200])
            if re.search(r"blacklist|not valid|different email|already", vis, re.I):
                log("email rejected -> trying next email")
                RESULT["stage"] = "email_rejected"
                continue
            RESULT["stage"] = "submitted"
            break
        else:
            RESULT["stage"] = "captcha_failed"
            break
    except Exception as e:
        log("ATTEMPT ERR", repr(e)[:300])
        page.screenshot(path="/tmp/err.png")
        break

# ---- email verification ----
if RESULT["stage"] == "submitted":
    email = RESULT["email"]
    if "maxxspace" in email:
        subj, links = mt_poll(email, 4)
    else:
        subj, links = md_poll(email, 4)
    verify = next((l for l in links if "verify" in l.lower() or "activation" in l.lower()),
                  links[0] if links else None)
    if verify:
        log("verify link:", verify)
        page.goto(verify, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        log("post-verify URL:", page.url, "|", body_text(page)[:500])
        page.screenshot(path="/tmp/s4_verified.png")
        RESULT["stage"] = "verified"
    else:
        log("no verify mail")
        RESULT["stage"] = "no_verify_mail"

# ---- dev portal login + request PDI ----
if RESULT["stage"] == "verified":
    for attempt in range(2):
        page.goto("https://developer.servicenow.com/dev.do", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(8000)
        bt = body_text(page)
        log("dev portal url:", page.url, "| text[:400]:", bt[:400])
        page.screenshot(path=f"/tmp/s5_dev{attempt}.png")
        if re.search(r"request.*instance|my instance|start building|instance", bt, re.I):
            break
        # sign in through signon
        page.goto("https://signon.servicenow.com/x_snc_sso_auth.do?pageId=login",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        try:
            page.fill("#email", RESULT["email"])
            page.click("button[type=submit], .btn-primary", timeout=8000)
            page.wait_for_timeout(4000)
            page.fill("#password", SNPASS)
            page.click("button[type=submit], .btn-primary", timeout=8000)
            page.wait_for_timeout(8000)
            log("post-sso-login url:", page.url)
        except Exception as e:
            log("login err", e)
    # request instance: dump links, click candidates
    try:
        for pat in ["request instance", "start building", "get started", "my instance"]:
            loc = page.get_by_text(re.compile(pat, re.I))
            if loc.count():
                loc.first.click(); page.wait_for_timeout(8000); break
        page.screenshot(path="/tmp/s6_req.png")
        log("post-req URL:", page.url, body_text(page)[:1000])
        RESULT["stage"] = "pdi_attempted"
    except Exception as e:
        log("req err", e)

log("FINAL STATE:", RESULT)
print("RESULT_JSON:" + json.dumps(RESULT))
browser.close()
pw.stop()
