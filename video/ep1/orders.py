"""Create Lumean orders for episode 1; writes orders.json (name -> order id)."""
import json, os, sys, urllib.request
B, KEY = os.environ["LUMEAN_API_URL"], os.environ["LUMEAN_API_KEY"]
TEMPLATE = "01a1112f-6727-72c1-aa13-c5cfe9ae571e"  # «Допутим»

def post(body):
    req = urllib.request.Request(B + "/orders", data=json.dumps(body).encode(),
                                 headers={"X-API-KEY": KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["data"]["id"]

SFX = {
    "forest_day": ("quiet old growth forest in autumn, distant river, light wind in cedar trees, no birds", 22),
    "river": ("cold mountain river flowing over rocks, steady, close", 20),
    "night": ("dead silent forest at night, faint low wind, very sparse, ominous", 22),
    "steps_tent": ("slow heavy footsteps on dry leaves circling, stopping, then stepping again, close", 12),
    "tent": ("nylon tent fabric rustling, zipper slowly opening", 6),
    "frost_steps": ("hurried footsteps crunching on frosty ground and gravel, hiking fast, backpack straps", 15),
    "impact": ("deep cinematic horror impact boom with long tail", 5),
    "riser": ("slow horror tension riser, dissonant strings swelling", 8),
    "kitchen": ("kitchen sink running water, dishes clinking, then water turned off, quiet house", 10),
}
MUSIC = {
    "music_intro": "dark ambient documentary score, low cello drone, distant piano notes, mysterious, slow",
    "music_tense": "horror tension underscore, slow pulsing low synth, ticking, dissonant strings, building dread",
    "music_outro": "melancholic eerie outro, detuned music box melody over dark pad, haunting",
}
ids = json.load(open("orders.json")) if os.path.exists("orders.json") else {}
if "voice" not in ids:
    ids["voice"] = post({"template_id": TEMPLATE, "name": "ep1 voice in the woods",
                         "input_text": open("script.txt").read().strip()})
for n, (text, dur) in SFX.items():
    if n not in ids:
        ids[n] = post({"task_type": "sfx", "name": n, "task_data": {"text": text, "duration_seconds": dur}})
for n, prompt in MUSIC.items():
    if n not in ids:
        ids[n] = post({"task_type": "music", "name": n, "task_data": {
            "prompt": prompt, "force_instrumental": True, "music_length_ms": 30000, "n_variants": 1}})
json.dump(ids, open("orders.json", "w"), indent=1)
print(json.dumps(ids, indent=1))
