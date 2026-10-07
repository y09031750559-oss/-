"""Audio mix for episode 1 -> mix.wav (timed to episode.py's timeline)."""
import subprocess, sys
sys.argv = ["x", "info"]
import episode as E

TP, T = E.TP, E.T


def span(start, end, after=0.0):
    """Voice-time span from the first subtitle after `after` starting with `start`
    to the end of the first one from there starting with `end`."""
    i = next(k for k, s in enumerate(E.SUBS) if s[0] >= after and s[2].startswith(start))
    j = next(k for k in range(i, len(E.SUBS)) if E.SUBS[k][2].startswith(end))
    return E.SUBS[i][0], E.SUBS[j][1]


inputs, chains, labels = [], [], []
n_in = [0]


def add(src, t, dur=None, vol=1.0, loop=False, fin=0.0, fout=0.0, af="", trim=None):
    """Place `src` at video time t. trim=(a, b) cuts a piece of the source first."""
    k = n_in[0]
    n_in[0] += 1
    inputs.extend((["-stream_loop", "-1"] if loop else []) + ["-i", src])
    f = [f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo"]
    if trim:
        f.append(f"atrim={trim[0]:.3f}:{trim[1]:.3f},asetpts=PTS-STARTPTS")
    if dur:
        f.append(f"atrim=0:{dur:.3f}")
    if af:
        f.append(af)
    if fin:
        f.append(f"afade=in:d={fin}")
    if fout and dur:
        f.append(f"afade=out:st={max(dur - fout, 0):.3f}:d={fout}")
    ms = int(t * 1000)
    f.append(f"volume={vol},adelay={ms}|{ms}")
    lab = f"a{k}"
    chains.append(",".join(f) + f"[{lab}]")
    return lab


def bed(src, t0, t1, vol, fin=1.5, fout=1.5):
    labels.append(add(f"dl/{src}.mp3", t0, t1 - t0, vol, loop=True, fin=fin, fout=fout))


def hit(src, t, vol, af=""):
    labels.append(add(f"dl/{src}.mp3", t, None, vol, af=af))


# -- voice: cut at the inserts, each piece lands at its video time
cuts = [0.0] + [c for c, _, _ in E.INSERTS] + [E.VOICE_END + 1]
voice = []
for a, b in zip(cuts, cuts[1:]):
    voice.append(add("dl/voice.mp3", T(a) if a > 0 else E.LEAD, None, 1.0, trim=(a, b)))

# -- mimic lines get a cold, distant double
for s, e in (span('"Danny."', '"Danny."'), span('"Danny.', 'I need to show', after=E.at("Then it called again")), span('"Claire.', 'Open the tent'),
             span('"Claire, come outside', 'I need to show', after=E.at("Until last spring"))):
    labels.append(add("dl/voice.mp3", T(s) + 0.09, None, 0.42, trim=(s, e + 0.3),
                      af="highpass=f=300,lowpass=f=3200,aecho=0.8:0.6:180|420:0.45|0.3,apad=pad_dur=1.2"))

ch = [T(c) - g for c, g, _ in E.INSERTS]  # card starts
title = ch[0]
END = E.TOTAL

# -- ambience beds per scene
bed("forest_day", 0, title + 0.5, 0.35)
bed("wind", 0, title + 1, 0.25)
bed("wind", title, ch[1] + 0.5, 0.35)
bed("forest_day", ch[1] + 2.5, ch[2] + 0.5, 0.4)
bed("river", TP("Old growth cedar") - 1, ch[2] + 0.5, 0.35)
bed("forest_day", ch[2] + 2.5, TP("Then it called again"), 0.25)
bed("wind", ch[2] + 2.5, ch[3] + 0.5, 0.3)
bed("night", ch[3] + 2.5, ch[4] + 0.5, 0.45)
bed("wind", ch[4] + 2.5, ch[5] + 0.5, 0.28)
bed("frost_steps", TP("They packed in"), TP("They packed in") + 15, 0.35, fout=3)
bed("forest_day", ch[5] + 2.5, ch[6] + 0.5, 0.3)
bed("wind", ch[5] + 2.5, ch[6] + 0.5, 0.2)
bed("night", ch[6] + 2.5, TP("People who study"), 0.35)
bed("kitchen", TP("Claire was home alone") - 0.5, TP("Claire was home alone") + 9.5, 0.3, fin=0.5, fout=2)
bed("wind", TP("People who study") - 1, END, 0.35, fout=4)

# -- music, ducked under the voice
music = []
for src, t0, t1, v in (("music_intro", title, ch[2] + 1, 0.30), ("music_tense", ch[2] + 2.5, ch[5] + 1, 0.26),
                       ("music_intro", ch[5] + 2.5, ch[6] + 1, 0.22), ("music_outro", ch[6] + 2.5, END, 0.30)):
    music.append(add(f"dl/{src}.mp3", t0, t1 - t0, v, loop=True, fin=2.5, fout=2.5))

# -- hits
hit("impact", title + 0.35, 0.7)
for t in ch[1:]:
    hit("stinger", t + 0.15, 0.45)
hit("riser", TP('"Danny."') - 7.6, 0.45)
hit("impact", TP('"Danny."') - 0.05, 0.35)
hit("whisper", TP("Then it called again") - 0.8, 0.5)
hit("steps_tent", TP("Something was walking") - 0.3, 0.6)
hit("steps_tent", TP("Then it said the same"), 0.45)
hit("heartbeat", TP('"Claire.') - 0.5, 0.55)
hit("heartbeat", TP("Daniel was lying") + 1, 0.4)
hit("tent", TP("Daniel unzipped"), 0.6)
hit("riser", TP("Their conversation") - 2, 0.35)
hit("stinger", TP("Then it's still"), 0.4)
hit("heartbeat", TP("The voice called her"), 0.5)
hit("riser", TP("The last time") - 5, 0.45)
hit("impact", TP("it was much closer") + 0.2, 0.6)
hit("whisper", TP("keep walking") - 1.5, 0.4)
hit("impact", TP("And never, ever") + 0.2, 0.55)

n_v, n_m, n_o = len(voice), len(music), len(labels)
fc = chains + [
    "".join(f"[{l}]" for l in voice) + f"amix=inputs={n_v}:normalize=0:duration=longest,apad=whole_dur={END:.3f},asplit=2[vo][key]",
    "".join(f"[{l}]" for l in music) + f"amix=inputs={n_m}:normalize=0:duration=longest[mu]",
    "[mu][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[mud]",
    "".join(f"[{l}]" for l in labels) + f"amix=inputs={n_o}:normalize=0:duration=longest[fx]",
    f"[vo][mud][fx]amix=inputs=3:normalize=0:duration=first,atrim=0:{END:.3f},"
    "alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11[out]",
]
cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
       "-ar", "48000", "-c:a", "pcm_s16le", "mix.wav"]
subprocess.run(cmd, check=True)
print("mix.wav", END)
