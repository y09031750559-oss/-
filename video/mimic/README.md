# never answer the voice in the woods: 17 disturbing mimic encounters

~1-minute English video in the Zoanfly "N disturbing … encounters" format.

- `script.txt` — narration (Lumean TTS, template «Допутим», ElevenLabs v3; `{{pause=…}}` are free Lumean pauses)
- `frames.py` — renders 9 dark-forest title cards into `frames/`
- `render.py` — downloads voice + SFX + music from Lumean orders, times cards to the voice pauses, mixes audio, writes MP4

```bash
python3 frames.py
python3 render.py mimic.mp4   # needs LUMEAN_API_KEY, LUMEAN_API_URL and access to s3.lumean.app
```
