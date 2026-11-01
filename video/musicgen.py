# The media-use engine's inline MusicGen recipe (bgm.mjs musicgenScript), run in a local venv.
import math, os, sys
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from transformers import MusicgenForConditionalGeneration, AutoProcessor

prompt = sys.argv[1]
out_path = sys.argv[2]
target_s = float(sys.argv[3])
seed_s = 28.0
token_rate = 50
crossfade_s = 0.3
torch.manual_seed(7)

def apply_fade(arr, sr, fade_in_s=1.5, fade_out_s=3.0):
    n_in = int(fade_in_s * sr); n_out = int(fade_out_s * sr)
    arr[:n_in] *= np.linspace(0.0, 1.0, n_in, dtype="float32")
    arr[-n_out:] *= np.linspace(1.0, 0.0, n_out, dtype="float32")
    return arr

def loop_crossfade(seed, target_len, xf):
    t = np.linspace(0.0, 1.0, xf, dtype="float32")
    fade_out = np.cos(t * (math.pi / 2)); fade_in = np.sin(t * (math.pi / 2))
    out = seed.copy()
    while out.shape[0] < target_len:
        out = np.concatenate([out[:-xf], out[-xf:] * fade_out + seed[:xf] * fade_in, seed[xf:]])
    return out[:target_len]

Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)
processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
model.eval()
sr = int(model.config.audio_encoder.sampling_rate)
inputs = processor(text=[prompt], padding=True, return_tensors="pt")
audio = model.generate(**inputs, max_new_tokens=int(seed_s * token_rate), do_sample=True, guidance_scale=3.0)
seed = audio[0, 0].detach().cpu().numpy().astype("float32")
seed = seed * (0.89 / max(1e-6, float(np.max(np.abs(seed)))))
final = loop_crossfade(seed, int(target_s * sr), int(crossfade_s * sr))
final = apply_fade(final, sr)
sf.write(out_path, final, sr)
print(f"[musicgen] wrote {out_path} samples={final.shape[0]} sr={sr}", flush=True)
