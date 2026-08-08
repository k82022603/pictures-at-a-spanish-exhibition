"""
주제 데모 v1.2 — 현악 축소판.
현악은 배경 베드로 내리고 선율은 건반이 가져간다 (3성부 원칙: 건반=주역).
"""
import numpy as np
import piano
import ensemble as ens
import synth
from demo60 import TL, vc

SR = 44100

STR_PAD = 0.42     # v1.1 대비 현악 패드 배율
STR_MEL = 0.0      # 현악은 더 이상 선율을 들지 않는다

A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
     (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]
B = [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5), (77, 1.0),
     (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 1.0)]

T = TL(60)
MARK = []
BEAT = 60 / 112.0
t = 0.0

# ── 1. 주제 A — 피아노 단독
MARK.append(('주제 A · 피아노 단독', t))
for rep in range(2):
    for m, d in A:
        T.put(piano.note(m, d * BEAT * 0.95, 0.64, ring=1.3), t, 0.98, -0.04)
        t += d * BEAT
t += BEAT * 1.2

# ── 2. 주제 A — 피아노가 선율, 현악은 얇은 베드
MARK.append(('주제 A · 피아노 선율 + 현악 베드', t))
PROG = [('Bb', 3), ('Gm', 3), ('Eb', 3)]
bl = [46, 48, 50, 46, 45, 43, 41, 43, 46]
bt = t
for sym, beats in PROG:
    v = vc(sym, 55, 74)
    for mm in v:
        # 성부 수를 줄이고 어택을 더 느리게 — 앞으로 나오지 않게
        T.put(ens.strings(mm, beats * BEAT * 0.95, vel=0.30 * STR_PAD, voices=6,
                          attack=0.28, release=0.5, section='low'),
              bt, 1.0, -0.34 + 0.16 * v.index(mm))
    T.put(ens.strings(v[0] - 24, beats * BEAT * 0.95, vel=0.24 * STR_PAD, voices=6,
                      attack=0.34, release=0.55, section='low'), bt, 1.0, 0.08)
    bt += beats * BEAT
for i, bm in enumerate(bl):
    T.put(synth.bass(bm, BEAT * 0.85, gain=0.60), t + i * BEAT, 1.0, -0.04)
for m, d in A:
    T.put(piano.note(m + 12, d * BEAT * 0.95, 0.66, ring=1.5), t, 1.0, -0.10)
    T.put(piano.note(m, d * BEAT * 0.5, 0.34, ring=0.8), t, 0.55, 0.26)
    t += d * BEAT
t += BEAT * 1.4

# ── 3. 주제 B — D 프리지안 (현악 없음)
MARK.append(('주제 B · D 프리지안 · 현악 없음', t))
BB = 60 / 168.0
CAD = ['Gm', 'F', 'Eb', 'D']
ACC = {0, 3, 6, 8, 10}
bt = t
for ci, sym in enumerate(CAD):
    v = vc(sym, 52, 71)
    for b in range(3):
        bi = ci * 3 + b
        hard = bi in ACC
        for j, mm in enumerate(v):
            T.put(ens.nylon(mm, BB * 0.9, vel=(0.64 if hard else 0.33),
                            pluck=0.14, ring=0.35), bt + j * 0.008, 1.0, 0.22)
        if hard:
            T.put(ens.palma(0.72, 'clara'), bt, 1.0, -0.42)
            T.put(ens.cajon(0.66, 'bass'), bt, 1.0, 0.0)
        else:
            T.put(ens.palma(0.28, 'sorda'), bt, 1.0, -0.30)
        if bi == 10:
            T.put(ens.tacon(0.75), bt, 1.0, -0.12)
        bt += BB
for m, d in B:
    T.put(synth.hammond(m, d * BEAT * 0.9, reg=synth.REG_SOFT, gain=0.36), t, 1.0, -0.24)
    T.put(synth.moog(m + 12, d * BEAT * 0.85, gain=0.50, cut_hi=5200, res=0.55), t, 1.0, 0.26)
    t += d * BEAT
t += BEAT * 1.4

# ── 4. 두 주제 동시 — A는 피아노, B는 무그. 현악은 아주 얇게
MARK.append(('두 주제 동시 · A=피아노 B=무그', t))
CH = [('Bb', 3), ('Gm', 3), ('Eb', 2), ('F', 1)]
bt = t
for sym, beats in CH:
    v = vc(sym, 50, 70)
    for mm in v:
        T.put(ens.strings(mm, beats * BEAT * 0.95, vel=0.26 * STR_PAD, voices=6,
                          attack=0.30, release=0.55, section='low'),
              bt, 1.0, -0.32 + 0.15 * v.index(mm))
    bt += beats * BEAT
bt = t
for (ma, d), (mb, _) in zip(A, B):
    T.put(piano.note(ma + 12, d * BEAT * 0.95, 0.70, ring=1.8), bt, 1.0, -0.16)
    T.put(ens.nylon(ma, d * BEAT * 0.9, vel=0.40, pluck=0.2, ring=0.7), bt, 0.8, -0.30)
    T.put(synth.moog(mb, d * BEAT * 0.88, gain=0.44, cut_hi=4600, res=0.5), bt, 1.0, 0.28)
    T.put(synth.bass(ma - 24, d * BEAT * 0.9, gain=0.64), bt, 1.0, 0.0)
    bt += d * BEAT
t = bt + 0.4
T.put(piano.note(58, 3.2, 0.74, ring=3.2), t, 0.95, 0.0)
T.put(piano.note(70, 3.0, 0.60, ring=3.0), t + 0.02, 0.8, -0.12)
for mm in [46, 58, 62, 65]:
    T.put(ens.strings(mm, 2.6, vel=0.30 * STR_PAD, voices=6, attack=0.10,
                      release=1.3, section='low'), t, 1.0, -0.18 + 0.09 * (mm % 5))
TOTAL = t + 3.4

out = T.out(TOTAL)
piano.write_wav('themes_v12.wav', out)
print('v1.2 렌더 %.1f초  peak %.3f' % (len(out) / SR, np.abs(out).max()))
for n, tt in MARK:
    print('  %5.1fs  %s' % (tt, n))
