# Synthesizes a calm background track (soft pad + plucked arpeggio) to music.wav.
# Usage: python3 music.py [seconds]
import sys
import wave
import numpy as np

SR = 44100
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
BPM = 64
BEAT = 60 / BPM

# C - G - Am - F, one chord per bar of 4 beats
CHORDS = [[60, 64, 67, 72], [55, 62, 67, 71], [57, 64, 69, 72], [53, 60, 65, 69]]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


n = int(DUR * SR)
t = np.arange(n) / SR
pad = np.zeros(n)
arp = np.zeros(n)
bar = 4 * BEAT

for b in range(int(np.ceil(DUR / bar))):
    chord = CHORDS[b % len(CHORDS)]
    s, e = int(b * bar * SR), min(n, int((b + 1) * bar * SR + 0.6 * SR))
    if s >= n:
        break
    seg = t[s:e] - t[s]
    # slow attack, gentle release overlapping into the next bar
    env = np.minimum(1, seg / 0.8) * np.clip((bar + 0.6 - seg) / 0.9, 0, 1)
    for m in chord:
        f = hz(m - 12)
        pad[s:e] += env * (np.sin(2 * np.pi * f * seg) + 0.25 * np.sin(2 * np.pi * 2 * f * seg + 0.3))
    # eighth-note arpeggio up and down the chord
    pattern = chord + chord[-2:0:-1] + chord[:2]
    for i in range(8):
        ns = int((b * bar + i * BEAT / 2) * SR)
        if ns >= n:
            break
        ne = min(n, ns + int(1.4 * SR))
        nt = t[ns:ne] - t[ns]
        f = hz(pattern[i % len(pattern)] + 12)
        arp[ns:ne] += np.exp(-nt * 3.2) * np.minimum(1, nt / 0.005) * (
            np.sin(2 * np.pi * f * nt) + 0.15 * np.sin(2 * np.pi * 3 * f * nt))

mix = 0.55 * pad / np.max(np.abs(pad)) + 0.45 * arp / np.max(np.abs(arp))
# simple stereo widening via a short delay on the right channel
d = int(0.012 * SR)
left, right = mix, np.concatenate([np.zeros(d), mix[:-d]])
fade = np.minimum(1, t / 1.5) * np.clip((DUR - t) / 2.5, 0, 1)
stereo = np.stack([left, right], axis=1) * fade[:, None]
stereo *= 0.25 / np.max(np.abs(stereo))  # quiet: background level, around -12 dBFS peak

with wave.open('music.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype('<i2').tobytes())
