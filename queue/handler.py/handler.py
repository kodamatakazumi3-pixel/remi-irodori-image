import base64, json, os, subprocess, sys, time, urllib.request, urllib.error
import runpod

BASE = "http://127.0.0.1:8088"
_proc = None

def _req(method, path, body=None, headers=None, timeout=1200):
    r = urllib.request.Request(BASE + path, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def ensure_server():
    global _proc
    if _proc is not None and _proc.poll() is None:
        return
    env = dict(os.environ)
    env.setdefault("IRODORI_HF_CHECKPOINT", "Aratako/Irodori-TTS-v4.1-Small-MF")
    _proc = subprocess.Popen([sys.executable, "-m", "irodori_openai_tts"], env=env)
    for _ in range(180):
        try:
            st, _b = _req("GET", "/health", timeout=5)
            if st == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("server did not become healthy")

def handler(job):
    inp = job.get("input") or {}
    action = inp.get("action", "health")
    ensure_server()
    if action == "health":
        st, b = _req("GET", "/health")
        return {"status": st, "body": b.decode("utf-8", "replace")}
    if action == "voices":
        st, b = _req("GET", "/v1/audio/voices")
        return {"status": st, "body": b.decode("utf-8", "replace")}
    if action == "upload_voice":
        data = base64.b64decode(inp["file_b64"])
        vid = inp.get("voice_id", "remi")
        boundary = "----remi-boundary"
        parts = []
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"voice_id\"\r\n\r\n%s\r\n" % (boundary, vid)).encode())
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"voice.wav\"\r\nContent-Type: audio/wav\r\n\r\n" % boundary).encode() + data + b"\r\n")
        parts.append(("--%s--\r\n" % boundary).encode())
        body = b"".join(parts)
        hdr = {"Content-Type": "multipart/form-data; boundary=%s" % boundary}
        st, b = _req("POST", "/v1/audio/voices", body, hdr)
        if st == 409:
            st, b = _req("PUT", "/v1/audio/voices/%s" % vid, body, hdr)
        return {"status": st, "body": b.decode("utf-8", "replace")}
    if action == "speech":
        payload = {"model": "irodori-tts", "input": inp["text"], "voice": inp.get("voice", "remi"),
                   "response_format": "wav", "irodori": {"caption": inp.get("caption", "")}}
        st, b = _req("POST", "/v1/audio/speech", json.dumps(payload).encode(),
                     {"Content-Type": "application/json"}, timeout=1800)
        if st != 200:
            return {"status": st, "body": b.decode("utf-8", "replace")[:500]}
        return {"status": st, "audio_b64": base64.b64encode(b).decode()}
    return {"error": "unknown action %s" % action}

runpod.serverless.start({"handler": handler})
