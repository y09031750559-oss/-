# Episode 1 — never answer the voice in the woods (story #1, full episode)

~6:09, English, 1920×1080 @ 24 fps. Story #1 from the teaser (`../mimic`) told in full:
cold open → title → the rule → six parts (THE QUIET FOREST, THE FIRST CALL, 2 A.M., FIRST LIGHT,
THE RANGER, LAST SPRING) → outro.

| File | What it does |
| --- | --- |
| `script.txt` | narration; `{{pause=…}}` are free Lumean pauses |
| `orders.py` | creates the Lumean orders (voice via template «Допутим», 9 SFX, 3 music beds) → `orders.json` |
| `episode.py` | timeline (from the TTS subtitles), procedural scene art, animated elements, frame renderer |
| `mix.py` | audio: voice with gaps for title/chapter cards, echoed mimic lines, per-scene ambience, hits, ducked music → `mix.wav` |
| `thumbnail.py` | 1280×720 thumbnail |

```bash
python3 orders.py                     # needs LUMEAN_API_KEY / LUMEAN_API_URL
# download finished orders into dl/ (voice.mp3 + voice.srt, sfx/music by name)
python3 episode.py info               # timeline
python3 episode.py frames 0 92.25 parts/p0.mp4   # … render in chunks, in parallel
python3 mix.py
ffmpeg -f concat -safe 0 -i parts/list.txt -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k ep1.mp4
```
