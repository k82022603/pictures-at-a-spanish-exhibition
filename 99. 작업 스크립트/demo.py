"""30-second ELP-style demo: E Phrygian, 5/4, 160 BPM."""
import numpy as np
from synth import (Mix, hammond, organ_chord, moog, bass, kick, snare, hat,
                   tom, crash, write_wav, REG_FULL, REG_SOFT)

BPM = 160.0
BEAT = 60.0 / BPM          # 0.375 s
BAR = 5 * BEAT             # 1.875 s  (5/4)
E8 = BEAT / 2              # eighth note

mx = Mix(34.0)


def bar_t(b):
    return b * BAR


# --------------------------------------------------------- I. organ fanfare
Em = [52, 55, 59, 64]
F = [53, 57, 60, 65]
G = [55, 59, 62, 67]
Am = [57, 60, 64, 69]
Dm = [50, 53, 57, 62]

fanfare = [(Em, 1.0), (F, 0.5), (G, 0.5), (Am, 1.0), (G, 0.5), (F, 0.5), (Em, 1.0)]
for b in (0, 1):
    t = bar_t(b)
    for ch, d in fanfare:
        reg = REG_FULL if b == 1 else REG_SOFT
        sig = organ_chord(ch, d * BEAT * 0.97, reg=reg, gain=0.62)
        mx.add(sig, t, pan=-0.12)
        # lower octave doubling for weight
        mx.add(organ_chord([m - 12 for m in ch[:2]], d * BEAT * 0.97,
                           reg=REG_SOFT, gain=0.34), t, pan=0.12)
        t += d * BEAT

# --------------------------------------------------- II. main riff (5/4)
# E Phrygian: E F G A B C D
riffA = [(52, .5), (52, .5), (55, .5), (57, .5), (53, 1.), (52, .5), (50, .5), (52, 1.)]
riffB = [(57, .5), (57, .5), (60, .5), (59, .5), (55, 1.), (53, .5), (52, .5), (52, 1.)]


def play_riff(b, riff, organ=True, org_gain=0.5, bass_gain=0.85):
    t = bar_t(b)
    for m, d in riff:
        dur = d * BEAT * 0.94
        mx.add(bass(m - 24, dur, gain=bass_gain), t, pan=0.0)
        if organ:
            mx.add(hammond(m, dur, reg=REG_FULL, gain=0.30), t, pan=-0.35)
            mx.add(hammond(m + 12, dur, reg=REG_FULL, gain=0.20), t, pan=0.35)
        t += d * BEAT


def drums(b, fill=False, crash_hit=False, busy=False):
    t = bar_t(b)
    for e in (0, 3, 5, 8):
        mx.add(kick(0.95), t + e * E8)
    for e in (2, 6, 9):
        mx.add(snare(0.72), t + e * E8, pan=-0.06)
    for e in range(10):
        acc = 0.5 if e % 2 == 0 else 0.28
        mx.add(hat(open_=(e == 4), gain=acc), t + e * E8, pan=0.34)
    if busy:
        for e in (1, 4, 7):
            mx.add(snare(0.30, tau=0.05), t + e * E8 + E8 / 2, pan=-0.2)
    if crash_hit:
        mx.add(crash(0.85), t, pan=-0.3)
    if fill:
        for i, (e, m) in enumerate([(6, 55), (7, 52), (8, 48), (9, 45)]):
            mx.add(tom(m, 0.85), t + e * E8, pan=-0.4 + 0.27 * i)


for i, b in enumerate(range(2, 8)):
    play_riff(b, riffA if b % 2 == 0 else riffB)
    drums(b, crash_hit=(b == 2), fill=(b == 7), busy=(b >= 6))

# ------------------------------------------------- III. moog lead over riff
lead = [
    [(76, 1.), (74, .5), (72, .5), (71, 1.), (69, 1.), (67, 1.)],
    [(69, .5), (71, .5), (72, 1.), (71, .5), (69, .5), (67, 2.)],
    [(77, 1.), (76, 1.), (74, .5), (72, .5), (71, 1.), (72, 1.)],
    [(71, .5), (69, .5), (67, .5), (65, .5), (64, 3.)],
]
for i, b in enumerate(range(8, 12)):
    play_riff(b, riffA if b % 2 == 0 else riffB, org_gain=0.34)
    drums(b, busy=True, crash_hit=(b == 8), fill=(b == 11))
    t = bar_t(b)
    prev = None
    for m, d in lead[i]:
        mx.add(moog(m, d * BEAT * 0.98, gain=1.0, glide_from=prev,
                    cut_hi=6000, res=0.6), t, pan=0.18)
        prev = m
        t += d * BEAT

# ------------------------------------------------------ IV. finale / cadence
for b in (12, 13):
    play_riff(b, riffA if b % 2 == 0 else riffB, bass_gain=0.95)
    drums(b, busy=True, fill=(b == 13), crash_hit=(b == 12))

# bar 14: unison stabs climbing
t = bar_t(14)
for ch, d in [(Em, .5), (F, .5), (G, .5), (Am, .5), (Dm, 1.), (F, .5), (G, .5), (Am, 1.)]:
    mx.add(organ_chord(ch, d * BEAT * 0.9, reg=REG_FULL, gain=0.66), t, pan=-0.15)
    mx.add(bass(ch[0] - 24, d * BEAT * 0.9, gain=0.95), t)
    mx.add(kick(0.9), t)
    mx.add(snare(0.5), t, pan=-0.1)
    mx.add(moog(ch[0] + 24, d * BEAT * 0.9, gain=0.85, cut_hi=7000, res=0.62), t, pan=0.25)
    t += d * BEAT

# bar 15: big held E minor
t = bar_t(15)
mx.add(crash(1.0), t, pan=-0.35)
mx.add(crash(0.9), t + 0.02, pan=0.35)
mx.add(kick(1.0), t)
mx.add(organ_chord([40, 47, 52, 55, 59, 64], BAR * 1.5, reg=REG_FULL, gain=0.78), t)
mx.add(bass(28, BAR * 1.2, gain=1.0), t)
mx.add(moog(64, BAR * 1.3, gain=0.7, cut_hi=4200, cut_lo=380, res=0.5), t, pan=0.2)
for i, m in enumerate([57, 55, 52, 48, 45]):
    mx.add(tom(m, 0.7), t + i * E8 * 0.7, pan=-0.4 + 0.2 * i)

out = mx.stereo(trim=32.0, reverb=0.15)
write_wav("demo.wav", out)
print("rendered demo.wav", out.shape, out.shape[0] / 44100.0, "s")
print("peak", np.abs(out).max(), "rms", np.sqrt((out ** 2).mean()))
