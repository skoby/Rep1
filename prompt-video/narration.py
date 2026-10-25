# Generates the English voice-over (narration.wav) from cues.js with Kokoro TTS.
# Each line starts at its cue time; a line that runs long is re-spoken faster.
# Usage: python3 narration.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin> [seconds]
# Model files: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
import json
import os
import sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

VOICE = 'af_heart'
LEAD = 0.1      # seconds after the cue starts before speaking
MAX_SPEED = 1.2

model_dir = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'cues.js'), encoding='utf-8').read()
cues = json.loads(src[src.index('['):src.rindex(']') + 1])

kokoro = Kokoro(os.path.join(model_dir, 'kokoro-v1.0.onnx'), os.path.join(model_dir, 'voices-v1.0.bin'))
out, sr = None, None
for start, end, _he, en in cues:
    slot = end - start - LEAD - 0.15
    speed = 1.0
    while True:
        samples, sr = kokoro.create(en, voice=VOICE, speed=speed, lang='en-us')
        length = len(samples) / sr
        if length <= slot or speed >= MAX_SPEED:
            break
        speed = min(MAX_SPEED, speed * length / slot + 0.02)
    if out is None:
        out = np.zeros(int(dur * sr), dtype=np.float32)
    i = int((start + LEAD) * sr)
    out[i:i + len(samples)] += samples[:len(out) - i]
    flag = '' if length <= slot else '  <-- overruns slot'
    print(f'{start:5.1f}s  {length:4.2f}/{slot:4.2f}s  x{speed:.2f}  {en}{flag}')

out *= 0.89 / np.max(np.abs(out))
sf.write(os.path.join(here, 'narration.wav'), out, sr)
