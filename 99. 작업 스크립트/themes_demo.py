"""
주제 확정 데모 — 무소르그스키 원곡 주제 A와 D 프리지안 변형 주제 B
"""
import numpy as np
import piano
import ensemble as ens
import synth
from demo60 import TL, vc

SR = 44100

# MusicXML에서 추출한 원곡 주제 (퍼블릭 도메인)
A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
     (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]        # 9박
# 같은 도수를 D 프리지안으로
B = [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5), (77, 1.0),
     (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 1.0)]

T = TL(60)
MARK = []
BEAT = 60 / 112.0          # 원곡 지시 ♩=112
t = 0.0

# ── 1. 주제 A — 피아노 단독 (원곡 그대로)
MARK.append(('주제 A · 원곡 · 피아노 단독', t))
for rep in range(2):
    for m, d in A:
        T.put(piano.note(m, d * BEAT * 0.95, 0.62, ring=1.2), t, 0.95, -0.05)
        t += d * BEAT
t += BEAT * 1.2

# ── 2. 주제 A — 현악 + 피아노 액센트 + 독립 베이스 (0악장 편성)
MARK.append(('주제 A · 현악 편성', t))
PROG = [('Bb', 3), ('Gm', 3), ('Eb', 3)]
bl = [46, 48, 50, 46, 45, 43, 41, 43, 46]
bt = t
for k, (sym, beats) in enumerate(PROG):
    v = vc(sym, 55, 74)
    for mm in v:
        T.put(ens.strings(mm, beats * BEAT * 0.95, vel=0.30, attack=0.16,
                          release=0.35), bt, 1.0, -0.30 + 0.14 * v.index(mm))
    T.put(ens.strings(v[0] - 24, beats * BEAT * 0.95, vel=0.24, attack=0.22,
                      release=0.4, section='low'), bt, 1.0, 0.06)
    bt += beats * BEAT
for i, bm in enumerate(bl):
    T.put(synth.bass(bm, BEAT * 0.85, gain=0.60), t + i * BEAT, 1.0, -0.04)
for m, d in A:
    T.put(ens.strings(m + 12, d * BEAT * 0.95, vel=0.52, attack=0.10,
                      release=0.22), t, 1.0, -0.12)
    T.put(piano.note(m, d * BEAT * 0.6, 0.40, ring=0.9), t, 0.7, 0.30)
    t += d * BEAT
t += BEAT * 1.4

# ── 3. 주제 B — D 프리지안. 같은 선율이 스페인에 도착한다
MARK.append(('주제 B · D 프리지안 · 안달루시아 종지', t))
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
            T.put(ens.nylon(mm, BB * 0.9, vel=(0.62 if hard else 0.32),
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
    T.put(synth.hammond(m, d * BEAT * 0.9, reg=synth.REG_SOFT, gain=0.34), t, 1.0, -0.24)
    T.put(synth.moog(m + 12, d * BEAT * 0.85, gain=0.48, cut_hi=5200, res=0.55), t, 1.0, 0.26)
    t += d * BEAT
t += BEAT * 1.4

# ── 4. 두 주제 동시 — 같은 선율이었다
MARK.append(('두 주제 동시 · 같은 선율', t))
for k, (sym, beats) in enumerate([('Bb', 3), ('Gm', 3), ('Eb', 2), ('F', 1)]):
    v = vc(sym, 50, 72)
    for mm in v:
        T.put(ens.strings(mm, beats * BEAT * 0.95, vel=0.28, attack=0.14,
                          release=0.4), t + sum(x[1] for x in
                          [('Bb', 3), ('Gm', 3), ('Eb', 2), ('F', 1)][:k]) * BEAT,
              1.0, -0.26 + 0.13 * v.index(mm))
bt = t
for (ma, d), (mb, _) in zip(A, B):
    T.put(ens.strings(ma + 12, d * BEAT * 0.95, vel=0.50, attack=0.09,
                      release=0.2), bt, 1.0, -0.22)
    T.put(synth.moog(mb, d * BEAT * 0.88, gain=0.42, cut_hi=4600, res=0.5), bt, 1.0, 0.28)
    T.put(synth.bass(ma - 24, d * BEAT * 0.9, gain=0.62), bt, 1.0, 0.0)
    bt += d * BEAT
t = bt + 0.4
T.put(piano.note(58, 3.0, 0.7, ring=3.0), t, 0.9, 0.0)
for mm in [46, 58, 62, 65, 70, 74]:
    T.put(ens.strings(mm, 2.6, vel=0.34, attack=0.05, release=1.2), t, 1.0,
          -0.2 + 0.08 * (mm % 5))
TOTAL = t + 3.4

out = T.out(TOTAL)
piano.write_wav('themes.wav', out)
print('렌더 %.1f초  peak %.3f' % (len(out) / SR, np.abs(out).max()))
for n, tt in MARK:
    print('  %5.1fs  %s' % (tt, n))
