"""Download Lumean results and render the final MP4.

usage: python3 render.py [--skip-download] OUT.mp4
"""
import json, os, re, subprocess, sys, urllib.request

B = os.environ.get("LUMEAN_API_URL", "")
KEY = os.environ.get("LUMEAN_API_KEY", "")
ORDERS = {  # name -> order id
    "voice": "01a111a4-f0bf-7041-9e61-592ed5626220",
    "wind": "01a111a5-1056-70c3-b665-f5e3aded9c0b",
    "whisper": "01a111a5-14b0-7348-92f1-dfdb71d9cc28",
    "stinger": "01a111a5-17c2-7022-a0da-b77a37d0e2e7",
    "heartbeat": "01a111a5-1ad6-7290-b709-6243f4603d70",
    "music": "01a111a5-1e35-7310-ba0d-29d5acaf1468",
}
N_CARDS = 9
FPS = 30


def api(path, body=None):
    req = urllib.request.Request(B + path, headers={"X-API-KEY": KEY, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body else None)
    return json.load(urllib.request.urlopen(req, timeout=60))["data"]


def download():
    os.makedirs("dl", exist_ok=True)
    for name, oid in ORDERS.items():
        order = api(f"/orders/{oid}")
        assert order["status"] == "completed", (name, order["status"])
        url = api("/storage/url", {"path": order["result"]["files"][0]})["url"]
        urllib.request.urlretrieve(url, f"dl/{name}.mp3")
        print("downloaded", name)


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(f):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).stdout)


def cut_points(voice, total):
    """Card boundaries = middles of the N_CARDS-1 longest pauses in the voice."""
    err = run(["ffmpeg", "-i", voice, "-af", "silencedetect=n=-38dB:d=0.35", "-f", "null", "-"]).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    gaps = [(e - s, (s + e) / 2) for s, e in zip(st, en) if s > 0.5 and e < total - 0.5]
    gaps.sort(reverse=True)
    mids = sorted(m for _, m in gaps[:N_CARDS - 1])
    if len(mids) < N_CARDS - 1:  # fallback: even split
        mids = [total * k / N_CARDS for k in range(1, N_CARDS)]
    return mids


def main():
    out = sys.argv[-1]
    if "--skip-download" not in sys.argv:
        download()
    lead, tail = 1.0, 2.5  # silence before the voice / after it
    vdur = duration("dl/voice.mp3")
    total = lead + vdur + tail
    cuts = [0.0] + [lead + c for c in cut_points("dl/voice.mp3", vdur)] + [total]
    print("cuts", [round(c, 2) for c in cuts])

    # video: each card is a slow push-in with grain + flicker, faded in/out
    inputs, chains = [], []
    for i in range(N_CARDS):
        d = cuts[i + 1] - cuts[i]
        n = int(round(d * FPS))
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", f"frames/{i:02d}.png"]
        chains.append(
            f"[{i}:v]scale=2304:1296,zoompan=z='1+0.06*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
            f":d=1:s=1920x1080:fps={FPS},noise=alls=14:allf=t,"
            f"eq=brightness='-0.03+0.025*sin(t*23)*sin(t*7)',"
            f"fade=in:st=0:d=0.35,fade=out:st={max(d - 0.3, 0):.3f}:d=0.3,setsar=1[v{i}]")
    vcat = "".join(f"[v{i}]" for i in range(N_CARDS)) + f"concat=n={N_CARDS}:v=1:a=0[vout]"

    # audio
    a0 = N_CARDS
    inputs += ["-i", "dl/voice.mp3",
               "-stream_loop", "-1", "-i", "dl/music.mp3",
               "-stream_loop", "-1", "-i", "dl/wind.mp3",
               "-i", "dl/whisper.mp3", "-i", "dl/whisper.mp3",
               "-i", "dl/heartbeat.mp3"]
    stingers = cuts[2:N_CARDS - 1]  # every encounter card (#1 .. #17) and the outro
    for _ in stingers:
        inputs += ["-i", "dl/stinger.mp3"]
    ms = lambda t: int(t * 1000)
    hb_at = cuts[5]  # heartbeat under #13 → #17
    a = [
        f"[{a0}:a]adelay={ms(lead)}|{ms(lead)},volume=1.0[voice]",
        f"[{a0+1}:a]atrim=0:{total},volume=0.22,afade=in:d=2,afade=out:st={total-3}:d=3[music]",
        f"[{a0+2}:a]atrim=0:{total},volume=0.30,afade=in:d=1.5,afade=out:st={total-2.5}:d=2.5[wind]",
        f"[{a0+3}:a]volume=0.55,adelay=0|0[wh1]",
        f"[{a0+4}:a]volume=0.45,adelay={ms(cuts[6]-0.2)}|{ms(cuts[6]-0.2)}[wh2]",
        f"[{a0+5}:a]volume=0.5,adelay={ms(hb_at)}|{ms(hb_at)}[hb]",
    ]
    labels = ["[voice]", "[music]", "[wind]", "[wh1]", "[wh2]", "[hb]"]
    for k, t in enumerate(stingers):
        a.append(f"[{a0+6+k}:a]volume=0.4,adelay={ms(t-0.05)}|{ms(t-0.05)}[st{k}]")
        labels.append(f"[st{k}]")
    a.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,"
             f"atrim=0:{total},loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    fc = ";".join(chains + [vcat] + a)
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
           "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-t", f"{total:.3f}", out]
    subprocess.run(cmd, check=True)
    print("wrote", out, round(duration(out), 2), "s")


if __name__ == "__main__":
    main()
