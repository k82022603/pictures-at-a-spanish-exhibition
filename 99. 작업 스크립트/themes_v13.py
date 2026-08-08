"""
주제 데모 v1.3 — 지적 두 건 반영
  1) 베이스가 진짜 대선율이 된다 (리켄배커, Jon Camp 방식)
  2) 주제 B는 밀도를 쌓아 올린다 — 등장의 순간을 만든다
  + 모든 음에 연주 흔들림(타이밍·세기)
"""
import numpy as np
import piano
import ensemble as ens
import synth
from demo60 import TL, vc

SR = 44100
RNG = np.random.default_rng(20260805)


def H(t, vel, tj=0.011, vj=0.14):
    return max(0.0, t + RNG.normal(0, tj)), float(np.clip(vel * (1 + RNG.normal(0, vj)), 0.06, 1.0))


A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
     (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]          # 9박
B = [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5), (77, 1.0),
     (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 1.0)]

# Jon Camp 방식 대선율 — 8분음표로 계속 움직이고, 옥타브를 뛰고, G3까지 올라간다.
# 선율이 내려갈 때 베이스는 올라간다 (반진행).
BASS = [(34, .5), (41, .5), (46, .5), (50, .5), (53, .5), (50, .5),   # B♭
        (43, .5), (46, .5), (50, .5), (55, .5), (53, .5), (50, .5),   # Gm
        (39, .5), (46, .5), (51, .5), (55, .5), (53, .5), (48, .5)]   # E♭ → F
BASS_ACC = {0, 3, 6, 9, 12, 15}          # 픽이 세게 들어가는 자리

T = TL(70)
MARK = []
BEAT = 60 / 112.0
t = 0.0

# ═══ 1. 주제 A — 피아노 단독
MARK.append(('주제 A · 피아노 단독', t))
for m, d in A:
    tt, vv = H(t, 0.64)
    T.put(piano.note(m, d * BEAT * 0.95, vv, ring=1.3), tt, 0.98, -0.04)
    t += d * BEAT
t += BEAT * 0.8

# ═══ 2. 베이스 대선율 단독 — 이게 얼마나 움직이는지 먼저 들려준다
MARK.append(('베이스 대선율 단독 (리켄배커)', t))
bt = t
for i, (m, d) in enumerate(BASS):
    tt, vv = H(bt, 0.80 if i in BASS_ACC else 0.60)
    T.put(ens.rick(m, d * BEAT * 0.92, vel=vv, ring=0.5), tt, 1.0, -0.02)
    bt += d * BEAT
t = bt + BEAT * 0.8

# ═══ 3. 둘이 함께 — 선율과 베이스가 반대로 움직인다
MARK.append(('주제 A + 베이스 대선율 (반진행)', t))
bt = t
for i, (m, d) in enumerate(BASS):
    tt, vv = H(bt, 0.78 if i in BASS_ACC else 0.58)
    T.put(ens.rick(m, d * BEAT * 0.92, vel=vv, ring=0.5), tt, 1.0, -0.02)
    bt += d * BEAT
bt = t
for sym, beats in [('Bb', 3), ('Gm', 3), ('Eb', 2), ('F', 1)]:
    v = vc(sym, 55, 72)
    for mm in v:
        T.put(ens.strings(mm, beats * BEAT * 0.95, vel=0.12, voices=6,
                          attack=0.30, release=0.5, section='low'),
              bt, 1.0, -0.34 + 0.16 * v.index(mm))
    bt += beats * BEAT
mt = t
for m, d in A:
    tt, vv = H(mt, 0.66)
    T.put(piano.note(m + 12, d * BEAT * 0.95, vv, ring=1.5), tt, 1.0, -0.14)
    mt += d * BEAT
t = mt + BEAT * 1.4

# ═══ 4. 주제 B — 밀도를 쌓아 올린다
SEV = t
BB = 60 / 168.0
CAD = ['Gm', 'F', 'Eb', 'D']

# (a) 나일론 기타 팔세타 혼자 — 공간을 연다
MARK.append(('주제 B ① 팔세타 · 기타 혼자', t))
FALS = [(81, .55), (79, .3), (77, .3), (75, .5), (74, .8), (72, .3), (70, .3),
        (69, .55), (70, .35), (74, .5), (75, 1.1)]
for m, d in FALS:
    tt, vv = H(t, 0.58, tj=0.020)
    T.put(ens.nylon(m, d * 0.42, vel=vv, ring=0.8), tt, 1.0, 0.16)
    t += d * 0.42
t += 0.5

# (b) 팔마스 sordas만 — 컴파스가 시작된다는 신호
MARK.append(('주제 B ② 팔마스만 · 컴파스 예고', t))
for k in range(12):
    tt, vv = H(t + k * BB, 0.26 if k not in (0, 3, 6, 8, 10) else 0.38)
    T.put(ens.palma(vv, 'sorda'), tt, 1.0, -0.34)
t += 12 * BB

# (c) 주제 B 첫 등장 — 나일론 기타가 혼자 노래한다. 반주는 팔마스뿐
MARK.append(('주제 B ③ 첫 등장 · 기타 독주', t))
bt = t
for k in range(18):
    tt, vv = H(t + k * BB, 0.30 if k not in (0, 3, 6, 8, 10, 12, 15) else 0.44)
    T.put(ens.palma(vv, 'sorda' if k % 2 else 'clara'), tt, 1.0, -0.36)
for m, d in B:
    tt, vv = H(bt, 0.70)
    T.put(ens.nylon(m, d * BEAT * 0.9, vel=vv, pluck=0.24, ring=1.0), tt, 1.0, 0.10)
    bt += d * BEAT
t = max(bt, t + 18 * BB) + 0.25

# (d) 컴파스 진입 — 라스게아도·카혼이 붙고 오르간이 주제를 받는다
MARK.append(('주제 B ④ 컴파스 · 오르간이 받는다', t))
bt = t
for ci, sym in enumerate(CAD):
    v = vc(sym, 52, 69)
    for b in range(3):
        bi = ci * 3 + b
        hard = bi in (0, 3, 6, 8, 10)
        for j, mm in enumerate(v):
            tt, vv = H(bt + j * 0.009, 0.58 if hard else 0.28)
            T.put(ens.nylon(mm, BB * 0.9, vel=vv, pluck=0.14, ring=0.35), tt, 1.0, 0.24)
        tt, vv = H(bt, 0.66 if hard else 0.26)
        T.put(ens.palma(vv, 'clara' if hard else 'sorda'), tt, 1.0, -0.40)
        if hard:
            T.put(ens.cajon(vv * 0.9, 'bass'), *H(bt, 1.0)[:1], 1.0, 0.0)
        if bi in (2, 5, 9):
            T.put(ens.cajon(0.45, 'slap'), *H(bt, 1.0)[:1], 1.0, 0.16)
        bt += BB
mt = t
for m, d in B:
    tt, vv = H(mt, 0.40)
    T.put(synth.hammond(m, d * BEAT * 0.9, reg=synth.REG_SOFT, gain=vv), tt, 1.0, -0.26)
    T.put(ens.rick(m - 24, d * BEAT * 0.85, vel=0.70, ring=0.4), *H(mt, 1.0)[:1], 1.0, -0.02)
    mt += d * BEAT
t = max(bt, mt) + 0.2

# (e) 무그가 올라온다 — 절정과 종지
MARK.append(('주제 B ⑤ 무그 · 종지', t))
bt = t
for ci, sym in enumerate(CAD):
    v = vc(sym, 52, 69)
    for b in range(3):
        bi = ci * 3 + b
        hard = bi in (0, 3, 6, 8, 10)
        for j, mm in enumerate(v):
            tt, vv = H(bt + j * 0.009, 0.62 if hard else 0.30)
            T.put(ens.nylon(mm, BB * 0.9, vel=vv, pluck=0.13, ring=0.35), tt, 1.0, 0.24)
        tt, vv = H(bt, 0.72 if hard else 0.28)
        T.put(ens.palma(vv, 'clara' if hard else 'sorda'), tt, 1.0, -0.40)
        if hard:
            T.put(ens.cajon(vv * 0.95, 'bass'), *H(bt, 1.0)[:1], 1.0, 0.0)
        if bi == 10:
            T.put(ens.tacon(0.8), *H(bt, 1.0)[:1], 1.0, -0.14)
        bt += BB
mt = t
for i, (m, d) in enumerate(B):
    tt, vv = H(mt, 0.52)
    # 음마다 필터 곡선을 흔든다 — 같은 소리가 반복되지 않게
    T.put(synth.moog(m + 12, d * BEAT * 0.88, gain=vv,
                     cut_hi=4200 + RNG.uniform(0, 2600),
                     res=0.42 + RNG.uniform(0, 0.22)), tt, 1.0, 0.28)
    T.put(synth.hammond(m, d * BEAT * 0.9, reg=synth.REG_FULL, gain=0.28), tt, 1.0, -0.28)
    T.put(ens.rick(m - 24, d * BEAT * 0.85, vel=0.76, ring=0.4), *H(mt, 1.0)[:1], 1.0, -0.02)
    mt += d * BEAT
t = max(bt, mt) + 0.25

# 종지 — D장3화음 (F♯)
T.put(ens.palma(0.92, 'clara'), t, 1.0, -0.40)
T.put(ens.cajon(0.95, 'bass'), t + 0.006, 1.0, 0.0)
T.put(ens.tacon(0.92), t + 0.010, 1.0, -0.12)
for k, mm in enumerate([50, 54, 57, 62, 66]):
    T.put(ens.nylon(mm, 2.0, vel=0.76, pluck=0.16, ring=2.0), t + k * 0.011, 1.0, 0.20)
T.put(ens.rick(26, 2.2, vel=0.88, ring=1.4), t, 1.0, 0.0)
T.put(synth.hammond(50, 2.4, reg=synth.REG_FULL, gain=0.36), t, 1.0, -0.22)
TOTAL = t + 3.2

out = T.out(TOTAL)
piano.write_wav('themes_v13.wav', out)
print('v1.3 렌더 %.1f초  peak %.3f' % (len(out) / SR, np.abs(out).max()))
for n, tt in MARK:
    print('  %5.1fs  %s' % (tt, n))
