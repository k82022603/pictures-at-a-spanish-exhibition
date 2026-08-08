"""
《스페인 전람회의 그림》 — 전곡 코드 진행 스케치 (건반 단독)
9분 40초 / 10악장.  주제 A = B♭장조, 주제 B = D 프리지안(B♭장조의 상대 선법).
"""
import numpy as np
from piano import Score, write_wav

# ---------------------------------------------------------------- 화성 사전
Q = {
    "":     [0, 4, 7],      "m":    [0, 3, 7],     "dim": [0, 3, 6],
    "7":    [0, 4, 7, 10],  "m7":   [0, 3, 7, 10], "maj7": [0, 4, 7, 11],
    "sus4": [0, 5, 7],      "add9": [0, 4, 7, 14], "m add9": [0, 3, 7, 14],
    "6":    [0, 4, 7, 9],   "m6":   [0, 3, 7, 9],
}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6,
      "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}


def ch(sym, oct_=3, bass=None):
    """'Gm7' -> midi list. oct_ 3 => root near C3(48)."""
    i = 1
    if len(sym) > 1 and sym[1] in "#b":
        i = 2
    root, qual = sym[:i], sym[i:]
    r = PC[root] + 12 * oct_ + 12
    notes = [r + s for s in Q[qual]]
    if bass is not None:
        notes = [PC[bass] + 12 * oct_] + notes
    return notes


def voice(sym, low=48, high=72):
    """Keep a chord inside a register window — simple voice leading."""
    n = ch(sym)
    out = []
    for m in n:
        while m < low:
            m += 12
        while m > high:
            m -= 12
        out.append(m)
    return sorted(set(out))


TOTAL = 580.0
S = Score(TOTAL + 10)
MARKS = []


def mark(name, t):
    MARKS.append((name, t))


# ======================================================= 주제 (가안)
# 주제 A — B♭장조, 5/4 + 6/4 = 11박
THEME_A = [(70, 1), (72, 1), (65, 1), (67, 1), (70, 1),
           (72, 1), (74, 1), (77, 1), (74, 1), (72, 1), (70, 1)]
# 주제 B — D 프리지안, 같은 윤곽. ♭2(E♭)가 색채음
THEME_B = [(74, 1), (75, 1), (69, 1), (70, 1), (74, 1),
           (75, 1), (77, 1), (81, 1), (77, 1), (75, 1), (74, 1)]


def play_line(t, line, beat, vel=0.72, ring=0.9, oct_shift=0, leg=0.96):
    for m, b in line:
        if m is not None:
            S.add(m + oct_shift, t, b * beat * leg, vel, ring)
        t += b * beat
    return t


# ================================================== 0. Promenade 제시 (50s)
mark("0. Promenade 제시", 0.0)
BEAT = 0.6                                    # ♩=100
t = 0.0
prog0 = ["Bb", "Gm", "Eb", "Bb", "F", "Gm", "Eb", "F", "Bb", "Eb", "Bb", "F", "Bb"]
# 1구: 주제 A 단선율 (무반주) — 관람객이 홀로 걸어 들어온다
t = play_line(t, THEME_A, BEAT, vel=0.60, ring=1.4)
# 2구: 화성이 붙는다
for i, sym in enumerate(prog0):
    beats = 5 if i % 2 == 0 else 6
    v = voice(sym, 46, 64)
    S.chord(v, t, beats * BEAT * 0.95, 0.55 + 0.02 * (i % 3), ring=1.6, roll=0.014)
    S.add(v[0] - 12, t, beats * BEAT, 0.62, ring=2.0)
    if i < len(THEME_A):
        pass
    t += beats * BEAT
    if t > 44.0:
        break
# 주제 A 재현 (화성 위에서)
play_line(38.0, THEME_A, BEAT, vel=0.70, ring=1.6)
t = 50.0

# ============================================================ 1. 마드리드 (40s)
mark("1. 마드리드", 50.0)
BEAT = 60 / 138.0
t = 50.0
prog1 = [("Bb", 2), ("F", 2), ("Gm", 2), ("Dm", 2), ("Eb", 2), ("Bb", 2), ("Cm7", 2), ("F7", 2),
         ("Gm", 2), ("Cm", 2), ("F", 2), ("Bb", 2), ("Eb", 2), ("F", 2), ("Bb", 4)]
mel1 = [(70, .5), (72, .5), (74, 1), (72, .5), (70, .5), (67, 1),
        (65, .5), (67, .5), (70, 1), (69, .5), (67, .5), (65, 1),
        (74, .5), (72, .5), (70, 1), (72, .5), (74, .5), (77, 1),
        (75, .5), (74, .5), (72, 1), (70, 2)]
while t < 90.0:
    for sym, beats in prog1:
        if t >= 90.0:
            break
        v = voice(sym, 50, 69)
        # 좌: 옥타브 베이스 + 화음 반주
        S.add(v[0] - 24, t, BEAT * 0.9, 0.72, ring=0.5)
        for k in range(int(beats * 2)):
            S.chord(v, t + k * BEAT * 0.5, BEAT * 0.42, 0.40, ring=0.25)
        t += beats * BEAT
mt = 50.0 + 8 * BEAT
for _ in range(3):
    mt = play_line(mt, mel1, BEAT, vel=0.78, ring=0.5, oct_shift=12)
    if mt > 88:
        break
t = 90.0

# ================================================ 2. Promenade 변주 I (15s)
mark("2. Promenade 변주 I", 90.0)
BEAT = 60 / 96.0
t = 90.0
# 얇게. 두 번째 발소리가 한 마디 늦게 들어온다
play_line(t, THEME_A, BEAT, vel=0.58, ring=1.5)
play_line(t + 2 * BEAT, [(m - 12, b) for m, b in THEME_A[:7]], BEAT, vel=0.38, ring=1.5)
for i, sym in enumerate(["Bb", "Gm", "Eb", "F"]):
    S.chord(voice(sym, 44, 60), t + i * 3 * BEAT, 3 * BEAT, 0.42, ring=1.8, roll=0.02)
t = 105.0

# ============================================================ 3. 세고비아 (55s)
mark("3. 세고비아", 105.0)
BEAT = 60 / 72.0
t = 105.0
prog3 = [("Gm", 4), ("D", 4), ("Eb", 4), ("Bb", 4),
         ("Cm", 4), ("Gm", 4), ("Eb", 4), ("D", 4),
         ("Gm", 4), ("F", 4), ("Eb", 4), ("D", 4),
         ("Gm", 4), ("Cm", 4), ("D", 4), ("Gm", 4)]
while t < 158.0:
    for sym, beats in prog3:
        if t >= 158.0:
            break
        v = voice(sym, 48, 67)
        S.chord(v + [v[0] + 12], t, beats * BEAT * 0.98, 0.60, ring=2.2, roll=0.02)
        S.add(v[0] - 24, t, beats * BEAT, 0.68, ring=2.6)
        S.add(v[0] - 12, t + 2 * BEAT, 2 * BEAT, 0.44, ring=2.0)
        t += beats * BEAT
# 저음에 주제 B의 씨앗 3음 (D–E♭–F) — 알아채기 어려울 정도로
for i, m in enumerate([50, 51, 53]):
    S.add(m, 140.0 + i * 2.4, 2.2, 0.34, ring=2.5)
t = 160.0

# ================================================= 4. 세비야 — 플라멩코 (100s)
mark("4. 세비야 (주제 B 탄생)", 160.0)
BEAT = 60 / 200.0                              # ♩=200, 12박 compás = 3.6s
t = 160.0
CAD = ["Gm", "F", "Eb", "D"]                   # 안달루시아 종지 (D는 장3화음 = F♯)
ACC = {0, 3, 6, 8, 10}                          # 불레리아 악센트
comp = 0
while t < 258.0:
    for ci, sym in enumerate(CAD):
        v = voice(sym, 45, 64)
        for b in range(3):                      # 화음당 3박
            beat_i = ci * 3 + b
            hard = beat_i in ACC
            S.chord(v, t, BEAT * 0.8, 0.62 if hard else 0.34, ring=0.3)
            if hard:
                S.add(v[0] - 24, t, BEAT * 0.9, 0.70, ring=0.4)
            t += BEAT
    comp += 1
    # compás 2회마다 주제 B를 얹는다
    if comp == 2:
        play_line(t - 7.2, THEME_B, BEAT * 2, vel=0.74, ring=0.6)
    if comp in (6, 10, 16, 22):
        play_line(t - 7.2, THEME_B, BEAT * 2, vel=0.80, ring=0.6,
                  oct_shift=12 if comp > 10 else 0)
    if comp in (13, 19):                        # 팔세타 — 하강 아르페지오
        for k, m in enumerate([86, 84, 82, 81, 79, 77, 75, 74]):
            S.add(m, t - 3.6 + k * 0.15, 0.14, 0.55, ring=0.5)
t = 260.0

# ================================================ 5. Promenade 변주 II (15s)
mark("5. Promenade 변주 II", 260.0)
BEAT = 60 / 88.0
t = 260.0
# 두 주제가 처음 겹친다 — 불협을 남긴다
play_line(t, THEME_A, BEAT, vel=0.60, ring=1.4)
play_line(t + 1.5 * BEAT, [(m - 12, b) for m, b in THEME_B], BEAT, vel=0.50, ring=1.4)
for i, sym in enumerate(["Gm", "Eb", "Cm", "D"]):
    S.chord(voice(sym, 43, 60), t + i * 3.4 * BEAT, 3.4 * BEAT, 0.46, ring=1.9, roll=0.02)
t = 275.0

# ================================================================ 6. 론다 (50s)
mark("6. 론다", 275.0)
BEAT = 60 / 56.0
t = 275.0
prog6 = [("Eb", 4), ("Bb", 4), ("Cm", 4), ("Ab", 4),
         ("Eb", 4), ("Fm7", 4), ("Bb7", 4), ("Eb", 4),
         ("Ab", 4), ("Eb", 4), ("Fm", 4), ("Bb", 4), ("Eb", 8)]
mel6 = [(75, 2), (77, 2), (75, 1), (74, 1), (72, 2),
        (70, 2), (72, 2), (75, 4)]
while t < 323.0:
    for sym, beats in prog6:
        if t >= 323.0:
            break
        v = voice(sym, 51, 70)
        S.add(v[0] - 24, t, beats * BEAT, 0.62, ring=3.0)
        S.chord(v, t + 0.5 * BEAT, beats * BEAT * 0.9, 0.44, ring=2.6, roll=0.03)
        t += beats * BEAT
mt = 279.0
for _ in range(3):
    mt = play_line(mt, mel6, BEAT, vel=0.66, ring=2.0, oct_shift=0)
    if mt > 320:
        break
t = 325.0

# ============================================ 7. 그라나다 — 알함브라 (100s)
mark("7. 그라나다 (보칼리즈)", 325.0)
BEAT = 60 / 150.0                              # 6/8, 점4분 = 1.2s
t = 325.0
prog7 = ["Dm", "Bb", "Gm", "A", "Dm", "Eb", "Bb", "Dm",
         "Bb", "F", "Gm", "Eb", "Dm", "A", "Dm", "Dm"]
bar = 0
while t < 423.0:
    sym = prog7[bar % len(prog7)]
    v = voice(sym, 50, 69)
    S.add(v[0] - 24, t, 6 * BEAT, 0.55, ring=2.4)
    # 알람브라의 물 — 6/8 아르페지오
    arp = v + [v[0] + 12]
    for k in range(6):
        S.add(arp[k % len(arp)], t + k * BEAT, BEAT * 1.6, 0.34, ring=1.2)
    if bar % 4 == 0:                            # 주제 B — 그녀의 노래, 단독
        play_line(t, [(m, b * 0.55) for m, b in THEME_B], BEAT * 2,
                  vel=0.70, ring=1.8, oct_shift=0)
    t += 6 * BEAT
    bar += 1
t = 425.0

# ======================================== 8. 바르셀로나 — 가우디 (100s)
mark("8. 바르셀로나", 425.0)
BEAT = 60 / 176.0                              # 7/8
t = 425.0
prog8 = ["Dm", "Eb", "Dm", "C", "Bb", "A", "Dm", "Gm",
         "Eb", "D", "Gm", "F", "Eb", "D", "Dm", "A"]
GRP = [2, 2, 3]                                 # 7/8 = 2+2+3
bar = 0
while t < 523.0:
    sym = prog8[bar % len(prog8)]
    v = voice(sym, 47, 66)
    off = 0.0
    for g in GRP:
        S.chord(v, t + off, BEAT * g * 0.85, 0.66 if g == 3 else 0.52, ring=0.25)
        S.add(v[0] - 24, t + off, BEAT * 0.9, 0.72, ring=0.35)
        off += BEAT * g
    # 주제 B의 파편 — 7/8에 잘려나간다
    if bar % 2 == 0:
        frag = THEME_B[: (5 if bar % 4 == 0 else 3)]
        play_line(t, [(m, 0.7) for m, _ in frag], BEAT, vel=0.72, ring=0.4, oct_shift=12)
    t += BEAT * 7
    bar += 1
t = 525.0

# ================================== 9. The Great Gate — 피날레 (55s)
mark("9. 피날레 (두 주제 총주)", 525.0)
BEAT = 60 / 63.0
t = 525.0
prog9 = [("Bb", 4), ("Eb", 4), ("Bb", 4), ("F", 4),
         ("Gm", 4), ("Eb", 4), ("F", 4), ("Bb", 4),
         ("Eb", 4), ("Bb", 4), ("F", 4), ("Bb", 8)]
while t < 572.0:
    for sym, beats in prog9:
        if t >= 572.0:
            break
        v = voice(sym, 48, 69)
        S.chord(v + [v[0] + 12, v[-1] + 12], t, beats * BEAT * 0.97, 0.70, ring=3.0, roll=0.02)
        S.add(v[0] - 24, t, beats * BEAT, 0.78, ring=3.4)
        S.add(v[0] - 12, t + 2 * BEAT, 2 * BEAT, 0.50, ring=2.4)
        t += beats * BEAT
# 두 주제 동시 — A는 그대로, B는 F♯이 F로 내려앉으며 장조에 흡수된다
play_line(529.0, THEME_A, BEAT, vel=0.76, ring=2.6, oct_shift=12)
THEME_B_RES = THEME_B[:-3] + [(77, 1), (74, 1), (70, 2)]   # ...F–D–B♭ 로 착지
play_line(529.0, THEME_B_RES, BEAT, vel=0.62, ring=2.6, oct_shift=0)
play_line(551.0, THEME_A, BEAT, vel=0.80, ring=3.0, oct_shift=12)

# 마지막 화음 — B♭장조
S.chord([34, 46, 58, 62, 65, 70, 74, 77], 570.0, 8.0, 0.85, ring=6.0, roll=0.03)

# ------------------------------------------------------------------ 출력
out = S.render(trim=TOTAL)
write_wav("sketch.wav", out)
print("렌더 완료  %.1f초  peak %.3f  rms %.4f" %
      (len(out) / 44100.0, np.abs(out).max(), np.sqrt((out ** 2).mean())))
print()
for name, tt in MARKS:
    print("  %5.1fs  %d:%02d   %s" % (tt, int(tt) // 60, int(tt) % 60, name))
