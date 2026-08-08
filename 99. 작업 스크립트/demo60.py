"""
60초 데모 (WBS 1.3.1) — 0악장 Promenade 제시 + 4악장 세비야
3성부 분리 원칙 적용: 건반=주역 / 베이스=독립 대선율 / 타악=하나의 목소리
"""
import numpy as np
from scipy import signal as sg

import piano
import ensemble as ens
import synth

SR = 44100


def ns(s):
    return int(round(s * SR))


class TL:
    """임의 신호를 놓는 스테레오 타임라인."""

    def __init__(self, sec):
        n = ns(sec) + SR * 6
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def put(self, sig, at, gain=1.0, pan=0.0):
        i = ns(at)
        j = i + len(sig)
        if j > len(self.L):
            p = j - len(self.L) + 1
            self.L = np.pad(self.L, (0, p))
            self.R = np.pad(self.R, (0, p))
        gl = np.cos((pan + 1) * np.pi / 4) * 1.414 * gain
        gr = np.sin((pan + 1) * np.pi / 4) * 1.414 * gain
        self.L[i:j] += sig * gl
        self.R[i:j] += sig * gr

    def out(self, trim, peak=0.90):
        L, R = self.L[:ns(trim)], self.R[:ns(trim)]
        L = sg.lfilter(*sg.butter(2, 30 / (SR / 2), btype="high"), L)
        R = sg.lfilter(*sg.butter(2, 30 / (SR / 2), btype="high"), R)
        # 홀 잔향
        L = L + 0.17 * piano._room(L, 0, amount=1.0)
        R = R + 0.17 * piano._room(R, 1, amount=1.0)
        # 마스터 EQ — 합성 음원은 기본적으로 어두우므로 프레즌스와 에어를 보강한다
        def shelf(x, fc, db, kind="high"):
            g = 10 ** (db / 20.0)
            sos = sg.butter(2, min(fc, 0.45 * SR) / (SR / 2),
                            btype="high" if kind == "high" else "low", output="sos")
            return x + (g - 1.0) * sg.sosfilt(sos, x)

        def mstr(x):
            b, a = sg.iirpeak(330 / (SR / 2), 1.1)
            x = x - 0.16 * sg.lfilter(b, a, x)      # 박스한 로우미드 정리
            x = shelf(x, 2400, 6.0, "high")          # 프레즌스
            x = shelf(x, 8000, 4.0, "high")          # 에어
            x = shelf(x, 70, -2.0, "low")            # 저역 정돈
            return x

        L, R = mstr(L), mstr(R)
        # 미드/사이드 확장 — 저역은 중앙 유지
        M, S = (L + R) / 2, (L - R) / 2
        S = sg.sosfilt(sg.butter(2, 200 / (SR / 2), btype="high", output="sos"), S)
        L, R = M + 1.7 * S, M - 1.7 * S
        # 글루 컴프
        det = np.maximum(np.abs(L), np.abs(R))
        blk = 128
        pk = np.array([det[i:i + blk].max() for i in range(0, len(det), blk)])
        e, env = 0.0, np.zeros(len(pk))
        ac, rc = np.exp(-1 / (0.006 * SR / blk)), np.exp(-1 / (0.20 * SR / blk))
        for i, p in enumerate(pk):
            c = ac if p > e else rc
            e = c * e + (1 - c) * p
            env[i] = e
        g = np.maximum(np.interp(np.arange(len(det)),
                                 np.arange(len(env)) * blk, env) / 0.40, 1.0) ** (1 / 3.0 - 1)
        L, R = L * g, R * g
        m = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
        return np.stack([L / m * peak, R / m * peak], axis=1)


T = TL(66)
MARK = []

# 화성 사전
PC = {"C": 0, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "A": 9, "Bb": 10}
QU = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10]}


def ch(sym, oct_=4):
    i = 2 if len(sym) > 1 and sym[1] in "#b" else 1
    r = PC[sym[:i]] + 12 * oct_
    return [r + s for s in QU[sym[i:]]]


def vc(sym, lo=52, hi=74):
    out = []
    for m in ch(sym):
        while m < lo:
            m += 12
        while m > hi:
            m -= 12
        out.append(m)
    return sorted(set(out))


# 주제 (가안)
TH_A = [70, 72, 65, 67, 70, 72, 74, 77, 74, 72, 70]
TH_B = [74, 75, 69, 70, 74, 75, 77, 81, 77, 75, 74]

# ══════════════════════════════════════ 1부 · Promenade 제시 (0:00–33)
MARK.append(("0악장 Promenade 제시 — 주제 A / B♭장조", 0.0))
B = 0.6                                   # ♩=100
t = 0.0

# (a) 주제 A — 현악 단독. 관람객이 홀로 걸어 들어온다
for i, m in enumerate(TH_A):
    dur = B * (1.6 if i == len(TH_A) - 1 else 1.0)
    T.put(ens.strings(m, dur, vel=0.62, attack=0.16, release=0.30), t, 1.0, -0.10)
    T.put(ens.strings(m - 12, dur, vel=0.30, attack=0.22, release=0.35, section="low"),
          t, 1.0, 0.14)
    t += B
t += B * 0.6

# (b) 화성이 붙는다 — 현악 패드 + 피아노 액센트 + 독립 베이스
MARK.append(("  화성 진입 · 3성부 분리", t))
PROG = [("Bb", 5), ("Gm", 6), ("Eb", 5), ("Bb", 6), ("F", 5), ("Gm", 6), ("Eb", 5), ("F", 6)]
# 베이스는 근음을 짚지 않는다 — 독립 대선율 (Jon Camp 방식)
BASSLINE = [[46, 48, 50, 46, 43], [46, 45, 43, 41, 43, 46],
            [39, 41, 43, 46, 48], [46, 50, 53, 50, 46, 45],
            [45, 46, 48, 50, 48], [46, 45, 43, 41, 39, 41],
            [39, 43, 46, 48, 46], [45, 48, 50, 53, 50, 48]]
seg_start = t
for k, (sym, beats) in enumerate(PROG):
    v = vc(sym, 55, 76)
    # 현악 패드
    for m in v:
        T.put(ens.strings(m, beats * B * 0.96, vel=0.34, attack=0.20, release=0.4),
              t, 1.0, -0.28 + 0.12 * v.index(m))
    T.put(ens.strings(v[0] - 24, beats * B * 0.96, vel=0.26, attack=0.25,
                      release=0.45, section="low"), t, 1.0, 0.05)
    # 피아노 액센트 (Mother Russia 도입부 방식)
    T.put(piano.note(v[0] + 12, B * 0.5, 0.55, ring=1.4), t, 0.75, 0.30)
    T.put(piano.note(v[-1] + 12, B * 0.4, 0.42, ring=1.2), t + B * 2, 0.65, 0.36)
    # 독립 베이스 대선율
    bl = BASSLINE[k]
    step = beats * B / len(bl)
    for bi, bm in enumerate(bl):
        T.put(synth.bass(bm, step * 0.88, gain=0.62), t + bi * step, 1.0, -0.05)
    t += beats * B

# (c) 주제 A 재현 — 피아노가 받는다
mt = seg_start + B * 11
for i, m in enumerate(TH_A):
    T.put(piano.note(m + 12, B * 0.92, 0.60, ring=1.6), mt, 0.9, 0.22)
    mt += B

END1 = t

# ══════════════════════════════════════ 전환 · 팔세타 (33–36)
MARK.append(("전환 — 나일론 기타 팔세타", END1))
t = END1
FALSETA = [81, 79, 77, 75, 74, 72, 70, 69, 70, 74, 75, 74]
for i, m in enumerate(FALSETA):
    T.put(ens.nylon(m, 0.22, vel=0.62 + 0.02 * (i % 3), ring=0.6), t, 1.0, 0.18)
    t += 0.185
T.put(ens.nylon(50, 1.4, vel=0.75, ring=1.6), t, 1.0, 0.0)
t += 0.9

# ══════════════════════════════════════ 2부 · 세비야 (36–60)
SEV = t
MARK.append(("4악장 세비야 — 주제 B 탄생 / D 프리지안", SEV))
BB = 60 / 200.0                            # ♩=200 → 12박 compás = 3.6초
CAD = ["Gm", "F", "Eb", "D"]               # 안달루시아 종지 (D장3화음 = F♯)
ACC = {0, 3, 6, 8, 10}                     # 불레리아 악센트
comp = 0
t = SEV
while t < SEV + 23.0:
    cs = t
    for ci, sym in enumerate(CAD):
        v = vc(sym, 52, 71)
        for b in range(3):
            bi = ci * 3 + b
            hard = bi in ACC
            # 나일론 기타 라스게아도
            for j, m in enumerate(v):
                T.put(ens.nylon(m, BB * 0.9, vel=(0.66 if hard else 0.34),
                                pluck=0.14, ring=0.35),
                      t + j * 0.008, 1.0, 0.22)
            # 팔마스 — 하나의 목소리로서의 타악
            if hard:
                T.put(ens.palma(0.75, "clara"), t, 1.0, -0.42)
                T.put(ens.palma(0.55, "clara"), t + 0.012, 1.0, 0.40)
                T.put(ens.cajon(0.7, "bass"), t, 1.0, 0.0)
            else:
                T.put(ens.palma(0.30, "sorda"), t, 1.0, -0.30)
            if bi in (2, 5, 9):
                T.put(ens.cajon(0.55, "slap"), t, 1.0, 0.16)
            if bi == 10:
                T.put(ens.tacon(0.8), t, 1.0, -0.12)
            # 독립 베이스 — 근음 유니즌이 아니라 걸어다닌다
            if bi % 2 == 0:
                walk = [38, 41, 43, 38, 36, 41, 43, 45, 46, 43, 41, 38]
                T.put(synth.bass(walk[(bi + ci) % 12], BB * 1.7, gain=0.72),
                      t, 1.0, -0.04)
            t += BB
    comp += 1
    # 주제 B — 오르간과 무그가 주역
    if comp in (2, 4, 6):
        mt = cs
        for i, m in enumerate(TH_B):
            d = BB * 1.9
            if comp == 2:
                T.put(synth.hammond(m, d * 0.95, reg=synth.REG_SOFT, gain=0.34),
                      mt, 1.0, -0.24)
            else:
                T.put(synth.hammond(m, d * 0.95, reg=synth.REG_FULL, gain=0.30),
                      mt, 1.0, -0.26)
                T.put(synth.moog(m + 12, d * 0.9, gain=0.55, cut_hi=5200, res=0.55),
                      mt, 1.0, 0.26)
            mt += d

# 종지 — D장3화음(F♯) 을 세게 박아 끝낸다
t = SEV + 23.0
T.put(ens.palma(0.9, "clara"), t, 1.0, -0.4)
T.put(ens.palma(0.9, "clara"), t + 0.01, 1.0, 0.4)
T.put(ens.cajon(0.95, "bass"), t, 1.0, 0.0)
T.put(ens.tacon(0.95), t + 0.005, 1.0, -0.1)
for m in [50, 54, 57, 62, 66]:                       # D F♯ A D F♯
    T.put(ens.nylon(m, 1.8, vel=0.8, pluck=0.16, ring=1.8), t + (m % 7) * 0.006, 1.0, 0.2)
T.put(synth.hammond(50, 2.4, reg=synth.REG_FULL, gain=0.42), t, 1.0, -0.2)
T.put(synth.hammond(66, 2.4, reg=synth.REG_FULL, gain=0.30), t, 1.0, 0.2)
T.put(synth.bass(26, 2.4, gain=0.9), t, 1.0, 0.0)

TOTAL = SEV + 25.4
print("SEV=%.4f" % SEV)
out = T.out(TOTAL)
piano.write_wav("demo60.wav", out)
print("렌더 완료  %.1f초  peak %.3f  rms %.4f" %
      (len(out) / SR, np.abs(out).max(), np.sqrt((out ** 2).mean())))
print()
for name, tt in MARK:
    print("  %5.1fs  %d:%02d  %s" % (tt, int(tt) // 60, int(tt) % 60, name))
print("  %5.1fs  종료" % TOTAL)
