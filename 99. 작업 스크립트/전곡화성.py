# -*- coding: utf-8 -*-
"""
《스페인 전람회의 그림》 — 전곡 화성 진행 (9분 40초 / 10악장)
v1.4 기준.  화성 우선 · 성부 진행 자동 최적화 · 테이프 마스터.

편성은 화성이 들리는 최소 구성으로 제한한다.
  피아노(주역) · 해먼드(패드) · 리켄배커 베이스(독립 대선율) · 현악(공기)
  나일론 기타(2·4악장) · 무그(7·9악장) · 팔마스·카혼(4악장만, 약하게)
"""
import numpy as np
from scipy import signal as sg

import piano
import ensemble as ens
import synth
from 화성 import (Desk, voice_lead, bassline, parse, pcset, STAT,
                  rick, hamm, moog, tape, pn, st, ny)

SR = 44100
RNG = np.random.default_rng(20260805)
TOTAL = 580.0

# perc 는 4악장의 팔마스·카혼 — **실제로 존재하는 악기**다(V3 의 정신).
# drum 은 드럼 키트다. 둘을 한 스템에 담으면 안 되는 이유가 셋이다.
#   ① 잔향 — perc 는 어택이 생명이라 말라야 하고, 드럼은 악장마다 다를 수 있다
#   ② 페이더 — 4악장의 팔마스를 줄이면 8악장의 드럼이 함께 줄어든다
#   ③ 서사 — 4악장은 실재의 악장이다. 드럼 키트가 섞이면 그 구분이 흐려진다
# 지금은 비어 있다. 편성이 정해지기 전에 그릇만 만든다 — WBS 1.1.6 에서 채운다.
GAINS = {"kb": 6.0, "org": -13.0, "bass": 2.0, "str": 2.0,
         "gtr": 5.0, "lead": 2.0, "perc": -5.0, "drum": -3.0}
D = Desk(TOTAL, list(GAINS), GAINS)
MARK = []
CHORDLOG = []          # (시각, 심볼, 보이싱) — 검증용


def H(t, vel, tj=0.010, vj=0.11):
    return max(0.0, t + RNG.normal(0, tj)), float(np.clip(vel * (1 + RNG.normal(0, vj)), 0.05, 1.0))


# 음계 (베이스 걸음용 pc 집합)
BB_MAJ = {10, 0, 2, 3, 5, 7, 9}          # B♭ 장조
G_MIN = {7, 9, 10, 0, 2, 3, 5}           # G 단조(자연)
D_PHR = {2, 3, 5, 7, 9, 10, 0}           # D 프리지안 = B♭장조와 같은 음
EB_LYD = {3, 5, 7, 9, 10, 0, 2}          # E♭ 리디안 = B♭장조와 같은 음집합
D_MIN = {2, 4, 5, 7, 9, 10, 0}           # D 단조

# 확정 주제 (MusicXML 원본 채보) — 9박 프레이즈
TH_A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
        (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]
TH_B = [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5), (77, 1.0),
        (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 1.0)]
# 피날레 — F♯이 F로 내려앉으며 B♭장조로 편입된다
TH_B_RES = TH_B[:-3] + [(77, 1.0), (74, 1.0), (70, 1.5)]


def mark(name, t, seed=None):
    """seed 를 주면 그 자리에서 흔들림 난수를 다시 심는다 (BL-25에서 발견).

    H() 가 모듈 전역 RNG 를 **순서대로** 소비하기 때문에, 한 악장에서 음을 하나
    더 넣거나 빼면 그 뒤 모든 악장의 타이밍·세기 흔들림이 통째로 달라진다.
    실제로 4·6악장 베이스를 손보자 손대지 않은 5·7·8·9악장의 크로마가 움직였고,
    1.4.8 수락 조건인 9:26 F♯ 값까지 음악적 이유 없이 0.119 → 0.124 로 흔들렸다.

    악장마다 스트림을 끊어두면 악장 하나를 고쳐도 다른 악장은 그대로다.
    WBS 1.4는 악장을 하나씩 다시 쓰는 작업이므로 이 격리가 없으면
    "무엇이 왜 바뀌었는지"를 매번 판별할 수 없다.
    0악장은 20260805 — 전역 초기값과 같으므로 이전 렌더와 그대로 이어진다.
    """
    MARK.append((name, t))
    if seed is not None:
        global RNG
        RNG = np.random.default_rng(seed)


# ══════════════════════════════════════════════════ 공통 텍스처 함수
def lay_chords(prog, t0, beat, lo, hi, *, org=0.0, pf=0.0, strg=0.0, gtr=0.0,
               nv=4, roll=0.016, pan=-0.10, sus=None, prev=None, hold=0.96):
    """화성 진행을 놓는다. 반환 (끝 시각, 마지막 보이싱, 각 화음 시각 리스트)"""
    t = t0
    ts = []
    for idx, (sym, beats) in enumerate(prog):
        s2 = sym
        v = voice_lead(s2, prev, lo, hi, nv)
        prev = v
        dur = beats * beat * hold
        ts.append(t)
        CHORDLOG.append((t, sym, tuple(v)))
        for k, m in enumerate(v):
            tt, vv = H(t + k * roll, 1.0)
            sp = pan + 0.09 * (k - (len(v) - 1) / 2.0)
            if pf > 0:
                D["kb"].put(pn(m, dur, pf * vv * (1 - 0.03 * k),
                               ring=min(3.0, beats * beat * 0.9)), tt, 1.0, sp)
            if org > 0:
                D["org"].put(hamm(m, dur, synth.REG_SOFT, org * vv), tt, 1.0, sp * 0.8)
            if strg > 0:
                D["str"].put(st(m, dur, strg * vv, voices=6, attack=0.30,
                                release=0.55, section="low"), tt, 1.0, sp * 1.6)
            if gtr > 0:
                D["gtr"].put(ny(m, dur * 0.7, gtr * vv, pluck=0.16,
                                ring=min(1.4, beats * beat)), tt, 1.0, -sp)
        # 지속음(sus4 → 3음) 처리: 지정된 인덱스에서 4도를 먼저, 3도를 뒤에
        t += beats * beat
    return t, prev, ts


def lay_bass(prog, t0, beat, scale, *, lo=28, hi=53, gain=1.0, density=2.0,
             leap_p=0.14, ring=0.5, seed=3, accent_every=4, hand=None):
    """hand 이 주어지면 알고리즘을 건너뛰고 손으로 쓴 음높이를 그대로 찍는다 (BL-25).

    hand = [[미디음, ...], ...] — prog 의 화음 하나당 리스트 하나.
    리듬·악센트·벨로시티 규칙은 `bassline()`과 같게 유지한다. 바뀌는 것은 음높이뿐이다.
    알고리즘 경로를 지우지 않는 이유는 R3와 같다 — 손 작업이 실패로 판정되면 되돌린다.
    """
    if hand is not None:
        if len(hand) != len(prog):
            raise ValueError("hand 길이 %d ≠ 화음 %d" % (len(hand), len(prog)))
        seq = []
        for (sym, beats), ms in zip(prog, hand):
            n = max(1, int(round(beats * density)))
            if len(ms) != n:
                raise ValueError("%s: 8분음표 %d개여야 하는데 %d개" % (sym, n, len(ms)))
            d = beats * beat / n
            for k, m in enumerate(ms):
                seq.append((m, d, 1.0 if k % accent_every == 0 else 0.72, k == 0))
    else:
        seq, dur = bassline(prog, scale, beat, lo=lo, hi=hi,
                            rng=np.random.default_rng(seed), leap_p=leap_p,
                            density=density, accent_every=accent_every)
    t = t0
    for m, d, vs, acc in seq:
        tt, vv = H(t, gain * (0.86 if acc else 0.66) * vs)
        D["bass"].put(rick(m, d * 0.92, vel=min(0.95, vv), ring=ring), tt, 1.0, -0.02)
        t += d
    return t


def lay_line(line, t0, beat, *, inst="kb", vel=0.7, ring=1.2, oct_=0, pan=-0.12,
             leg=0.95, glide=False, vib=0.0, bright=0.0):
    t = t0
    prev_m = None
    for m, b in line:
        mm = m + oct_
        tt, vv = H(t, vel)
        dur = b * beat * leg
        if inst == "kb":
            D["kb"].put(pn(mm, dur, vv, ring=ring), tt, 1.0, pan)
        elif inst == "gtr":
            D["gtr"].put(ny(mm, dur, vv, pluck=0.24, ring=ring), tt, 1.0, pan)
        elif inst == "org":
            D["org"].put(hamm(mm, dur, synth.REG_FULL, vv), tt, 1.0, pan)
        elif inst == "str":
            D["str"].put(st(mm, dur, vv, voices=7, attack=0.13,
                            release=0.30), tt, 1.0, pan)
        elif inst == "moog":
            # vib · bright 는 WBS 1.4.8 벨팅 (`01` WBS 1.4.8 · `07` 14장).
            # bright 는 컷오프를 Hz 로 더 밀어 배음을 연다.
            D["lead"].put(moog(mm, dur, gain=vv,
                               cut=4000 + bright + RNG.uniform(0, 1400),
                               res=0.30 + RNG.uniform(0, 0.10),
                               glide=prev_m if glide else None, vib=vib),
                          tt, 1.0, pan)
        prev_m = mm
        t += b * beat
    return t


# ═══════════════════════════════════════════ 0악장 · Promenade 제시 (0:00–0:50)
# 무소르그스키의 프롬나드는 기능화성이 아니라 선법적 화성이다.
# V–I를 피하고 IV·vi를 돌아 B♭에 도착한다. 첫 화음의 정체는 베이스가 알려준다.
mark("0악장 Promenade 제시 · B♭장조", 0.0, seed=20260805)
BT = 0.60                                    # ♩=100
PROG0 = [("Bb", 5), ("Gm7", 6), ("Ebmaj7", 5), ("Bb/D", 6),
         ("Cm7", 5), ("F", 6), ("Gm7", 5), ("Ebmaj7", 6),
         ("Bb/D", 5), ("Cm7", 6), ("F", 5), ("Bb", 6)]

# (a) 0–12초 : 피아노 단독. 아무것도 보지 않은 상태
t = lay_line(TH_A, 0.0, BT, vel=0.60, ring=1.6)
t = lay_line(TH_A, t + BT * 0.5, BT, vel=0.66, ring=1.6, oct_=12, pan=-0.20)
T0B = t + BT * 0.7

# (b) 베이스가 먼저 들어와 조성을 선포한다 — 현악·오르간보다 앞이다
#
# BL-25 — 걷기의 원형. 뒤의 모든 프롬나드(2·5·9악장)가 이 선을 되받는다.
# 규칙 셋. (1) 8분음표로 한 번도 멈추지 않는다  (2) B♭1~G3 을 오간다
#          (3) 주제 A가 오르면 베이스는 내린다 — 걷는 발과 보는 눈은 따로 움직인다
# 첫 음 B♭1 하나가 곡의 조성을 선포한다. 주제가 6도(G)로 시작해 첫 화음이
# B♭인지 Gm인지 애매한데, 그 애매함을 푸는 것이 이 한 음이다.
# 마지막 12개는 다시 B♭1로 내려앉아 마드리드에 걸음을 넘긴다.
BASS0 = [
    [34, 45, 43, 39, 50, 48, 46, 41, 43, 39],                # Bb      주제 1회
    [45, 41, 48, 43, 46, 41, 51, 46, 45, 50, 46, 43],        # Gm7     주제 1회
    [39, 50, 46, 43, 53, 46, 50, 43, 46, 43],                # Ebmaj7  주제 2회
    [48, 43, 51, 46, 50, 45, 55, 50, 48, 41, 45, 50],        # Bb/D    주제 2회
    [43, 39, 45, 41, 51, 46, 48, 41, 43, 39],                # Cm7     주제 3회
    [45, 41, 48, 41, 45, 50, 53, 48, 45, 39, 43, 48],        # F       주제 3회
    [43, 50, 46, 53, 48, 43, 39, 46, 50, 55],                # Gm7     주제 없이 혼자
    [51, 55, 50, 46, 51, 43, 46, 39, 43, 50, 46, 41],        # Ebmaj7  정점 G3
    [38, 45, 50, 43, 46, 38, 41, 48, 45, 39],                # Bb/D
    [36, 43, 48, 39, 45, 51, 46, 43, 39, 48, 45, 41],        # Cm7
    [45, 41, 48, 53, 45, 41, 36, 43, 48, 45],                # F
    [46, 41, 45, 50, 46, 43, 39, 41, 45, 43, 38, 34],        # Bb      착지
]
mark("  화성 진입 — 베이스가 조성을 선포", T0B)
lay_bass(PROG0, T0B, BT, BB_MAJ, gain=1.0, lo=34, hi=55, hand=BASS0)
# 보이싱 상한 65 는 목소리 자리를 비우기 위한 것이다 (WBS 1.4.1 · `07` 11장).
# 주제 A = MIDI 65~77 이므로 화성의 천장과 목소리의 바닥이 F4 한 음에서 맞닿는다.
#
# 63 까지 내리면 목소리 자리가 완전히 비지만 화성이 얇아진다 — B♭ 3화음의
# 구성음이 53~63 안에 셋뿐이라 4성부가 3성부로 무너지고, 저역 밀집이 오히려 는다.
# 하한 53 은 병행 8도를 막는다(50 이면 2건 생긴다). 음집합 밖인 52·64·66 은
# 후보에 들어오지 않으므로 50~53 과 63~64, 65~66 은 각각 같은 설정이다.
tend, LAST, ts0 = lay_chords(PROG0, T0B + BT * 1.0, BT, 53, 65,
                             pf=0.46, strg=0.13, org=0.16, prev=None)
# (c) 주제 A 재현 — 화성 위에서. 11박 간격이다 (프레이즈 9박 ↔ 마디 11박).
lay_line(TH_A, T0B + BT * 1.0, BT, vel=0.70, ring=1.8, oct_=12, pan=-0.22)
lay_line(TH_A, T0B + BT * 12.0, BT, vel=0.66, ring=1.8, oct_=12, pan=-0.22)
lay_line(TH_A, T0B + BT * 23.0, BT, vel=0.72, ring=2.0, oct_=12, pan=-0.22)

# (d) 여섯 번째 — 34번 칸을 건너뛰고 45번 칸(38.5초)에 놓는다.
#
# 건너뛴 34번 칸(31.9초)이 BASS0 의 정점 G3 구간이다. 곡 전체에서 베이스가
# 선율 노릇을 하는 유일한 자리이므로 주제를 얹어 그것을 뺏지 않는다.
# 여섯 번째 주제는 기억을 심으러 오는 것이 아니라 — 그건 앞의 다섯 번이 했다 —
# 말이 한 번 더 남았다는 것을 위해 온다. 그래서 약하게, 길게 울린다.
# 노랫말 4행 "I count out every step under my own feet" 가 여기 얹힌다 (`07` 11장).
#
# 검수 판정 — B판(이 줄 있음) 채택 (2026-08-08). A판은 침묵을 유지하는 안이었고
# 두 판을 발췌 mp3 로 대조받았다. 경위는 `05` 9.13절.
lay_line(TH_A, T0B + BT * 45.0, BT, vel=0.62, ring=2.2, oct_=12, pan=-0.22)

# ═════════════════════════════════════════════════ 1악장 · 마드리드 (0:50–1:30)
# 곡 전체에서 유일하게 기능화성이 또렷한 악장. ii–V–I 와 이차 딸림화음.
mark("1악장 마드리드 · ii–V–I 기능화성", 50.0, seed=20260806)
BT = 60 / 138.0
PROG1 = [("Bb", 4), ("Dm7", 4), ("Cm7", 4), ("F7", 4),
         ("Bb", 4), ("Bb/D", 4), ("Ebmaj7", 4), ("Cm7", 4),
         ("Gm7", 4), ("Cm7", 4), ("F7", 4), ("Bb/D", 4),
         ("Ebmaj7", 4), ("Cm7", 4), ("F7sus4", 2), ("F7", 2), ("Bb", 4)]
MEL1 = [(70, .5), (72, .5), (74, 1), (72, .5), (70, .5), (67, 1),
        (65, .5), (67, .5), (70, 1), (69, .5), (67, .5), (65, 1),
        (74, .5), (72, .5), (70, 1), (72, .5), (74, .5), (77, 1),
        (75, .5), (74, .5), (72, 1), (70, 1.5)]
t = 50.0
prev = LAST
for rep in range(2):
    lay_bass(PROG1, t, BT, BB_MAJ, gain=1.02, density=2.0, leap_p=0.12, seed=21 + rep)
    tn, prev, _ = lay_chords(PROG1, t, BT, 52, 70, pf=0.30, org=0.22, strg=0.09,
                             prev=prev, roll=0.010, hold=0.55)
    # 오른손 화음 반주 — 8분음표 백비트
    tt2 = t
    for sym, beats in PROG1:
        v = voice_lead(sym, None, 57, 74, 3)
        for k in range(int(beats * 2)):
            if k % 2 == 1:
                a, vv = H(tt2 + k * BT * 0.5, 0.20)
                for j, m in enumerate(v):
                    D["kb"].put(pn(m, BT * 0.34, vv, ring=0.14),
                                a + j * 0.007, 1.0, 0.16)
        tt2 += beats * BT
    lay_line(MEL1, t + 4 * BT, BT, vel=0.74, ring=0.6, oct_=12, pan=-0.24)
    t = tn
LAST = prev

# ═══════════════════════════════════════ 2악장 · Promenade 변주 I (1:30–1:45)
# 두 번째 기타가 한 마디 늦게 들어온다 — 두 번째 발소리
mark("2악장 Promenade 변주 I · 두 번째 발소리", 90.0, seed=20260807)
BT = 60 / 96.0
PROG2 = [("Bb", 3), ("Gm7", 3), ("Ebmaj7", 3), ("F", 3), ("Bb", 3)]
lay_chords(PROG2, 90.0, BT, 50, 68, gtr=0.30, strg=0.08, prev=LAST, roll=0.030)
lay_line(TH_A, 90.0, BT, inst="gtr", vel=0.62, ring=1.1, pan=0.18)
lay_line([(m, b) for m, b in TH_A[:8]], 90.0 + 2 * BT, BT, inst="gtr",
         vel=0.34, ring=1.1, oct_=-12, pan=-0.26)
LAST = voice_lead("Bb", LAST, 50, 68, 4)

# ═════════════════════════════════════════════════ 3악장 · 세고비아 (1:45–2:40)
# 코랄. 수도교의 아치가 반복되는 것처럼 하강 4음(G–F–E♭–D)이 반복된다.
# 이것이 4악장 안달루시아 종지와 같은 진행이다 — 씨앗.
mark("3악장 세고비아 · 코랄 / 하강 4음 G–F–E♭–D (씨앗)", 105.0, seed=20260808)
BT = 60 / 72.0
PROG3 = [("Gm", 4), ("F/A", 4), ("Ebmaj7", 4), ("D", 4),
         ("Gm", 4), ("Cm7", 4), ("D", 4), ("Gm", 4),
         ("Gm/Bb", 4), ("F", 4), ("Ebmaj7", 4), ("Dm", 4),
         ("Ebmaj7", 4), ("Cm7", 4), ("Dsus4", 2), ("D", 2), ("Gm", 4)]
t = 105.0
prev = LAST
while t < 156.0:
    lay_bass(PROG3, t, BT, G_MIN, gain=0.92, density=1.0, leap_p=0.18,
             ring=1.1, seed=31, accent_every=2)
    tn, prev, ts = lay_chords(PROG3, t, BT, 52, 71, org=0.90, pf=0.36, strg=0.17,
                              prev=prev, roll=0.022, hold=0.99)
    # 코랄의 4–3 지속음 — 몇 화음에서 4도를 먼저 울리고 3도로 내린다
    for i in (3, 7, 11, 16):
        if i < len(ts):
            sym = PROG3[i][0]
            r = parse(sym)[0]
            D["org"].put(hamm(_s4 := 52 + ((r + 5) - 52) % 12 + 12, BT * 1.6,
                              synth.REG_SOFT, 0.55), ts[i], 1.0, 0.10)
    t = tn
LAST = prev
# 저음의 프리지안 3음 단편 (D–E♭–F) — 알아채기 어려울 정도로
for i, m in enumerate([50, 51, 53]):
    D["kb"].put(pn(m, 2.0, 0.26, ring=2.4), 141.0 + i * 2.6, 1.0, 0.20)

# ══════════════════════════════ 4악장 · 세비야 — 주제 B 탄생 (2:40–4:20)
# 안달루시아 종지 Gm–F–E♭–D. 마지막 D는 장3화음(F♯) + ♭9(E♭) = 플라멩코 프리지안 화음.
# 베이스는 여기서 걷기를 멈춘다. 컴파스 강세에만 들어온다.
mark("4악장 세비야 · D 프리지안 / Gm–F–E♭–D♭9 · 베이스는 걷기를 멈춘다", 160.0, seed=20260809)
BB = 60 / 168.0                              # 12박 컴파스 = 4.29초
CAD = [("Gm7", 3), ("F/A", 3), ("Ebmaj7", 3), ("Dphr", 3)]
ACC = {0, 3, 6, 8, 10}
# BL-25 — 밀도 단계(lvl)별로 베이스가 앉는 자리. 강세 자리 ACC 의 부분집합이다.
BASS4 = {0: {0, 10},            # 컴파스의 두 극점만. 아직 듣고만 있다
         1: {0, 6, 10},         # E♭ 이 붙는다
         2: {0, 3, 6, 10},      # 종지 G–F–E♭–D 가 완성된다
         3: {0, 3, 6, 8, 10}}   # 전부
t = 160.0
prev = LAST

# (a) 팔세타 — 기타 혼자 공간을 연다
FALS = [(81, .55), (79, .3), (77, .3), (75, .5), (74, .8), (72, .3), (70, .3),
        (69, .55), (70, .35), (74, .5), (75, 1.2)]
t = lay_line(FALS, t, 0.42, inst="gtr", vel=0.56, ring=1.0, pan=0.16)
t += 0.45
# (b) 팔마스 sordas만 — 컴파스가 시작된다는 신호
for k in range(12):
    tt, vv = H(t + k * BB, 0.24 if k not in ACC else 0.34)
    D["perc"].put(ens.palma(vv, "sorda"), tt, 1.0, -0.36)
t += 12 * BB
# (c) 주제 B 첫 등장 — 나일론 기타 독주. 반주는 팔마스뿐
mark("  주제 B 첫 등장 · 기타 독주", t)
for k in range(18):
    tt, vv = H(t + k * BB, 0.26 if k not in ACC else 0.38)
    D["perc"].put(ens.palma(vv, "sorda" if k % 2 else "clara"), tt, 1.0, -0.38)
lay_line(TH_B, t, 60 / 112.0, inst="gtr", vel=0.68, ring=1.1, pan=0.12)
t += 18 * BB + 0.25

# (d~) 컴파스 진입 — 화성이 층으로 쌓인다
mark("  컴파스 진입 · 화성이 층으로 쌓인다", t)
comp = 0
while t < 254.0:
    lvl = min(3, comp // 3)                   # 0→3 단계로 밀도가 올라간다
    for ci, (sym, nb) in enumerate(CAD):
        v = voice_lead(sym, prev, 52, 71, 4)
        prev = v
        CHORDLOG.append((t, sym, tuple(v)))
        for b in range(nb):
            bi = ci * 3 + b
            hard = bi in ACC
            # 라스게아도 — 기타가 화성을 낸다
            for j, m in enumerate(v):
                tt, vv = H(t + j * 0.009, (0.50 if hard else 0.24) * (0.6 + 0.15 * lvl))
                D["gtr"].put(ny(m, BB * 0.9, vv, pluck=0.14, ring=0.34), tt, 1.0, 0.22)
            tt, vv = H(t, 0.58 if hard else 0.24)
            D["perc"].put(ens.palma(vv, "clara" if hard else "sorda"), tt, 1.0, -0.40)
            if hard:
                D["perc"].put(ens.cajon(vv * 0.80, "bass"), H(t, 1.0)[0], 1.0, 0.0)
                # BL-25 — 베이스는 강세 자리에만. 걷지 않는다. 곡에서 유일하다.
                # 그가 타블라오에 앉은 순간이고, 12박 컴파스는 그녀의 리듬이지
                # 그의 것이 아니다. 그러니 컴파스를 주도하지 않고 얹히기만 한다.
                #
                # 앉은 사람은 처음부터 박자를 다 짚지 않는다. 밀도(lvl)를 따라
                # 자리를 하나씩 늘려간다 — 컴파스의 두 극점 → E♭ → 종지 완성 → 전부.
                # 안달루시아 종지 G–F–E♭–D 가 lvl 2에서야 베이스로 다 들린다.
                if bi in BASS4[lvl]:
                    D["bass"].put(rick({0: 43, 1: 41, 2: 39, 3: 38}[ci],
                                       BB * 1.5, vel=0.72 + 0.04 * lvl, ring=0.5),
                                  H(t, 1.0)[0], 1.0, -0.02)
            if bi == 10 and lvl >= 2:
                D["perc"].put(ens.tacon(0.62), H(t, 1.0)[0], 1.0, -0.14)
            t += BB
    if lvl >= 1 and comp % 3 == 0:
        lay_line(TH_B, t - 12 * BB, 60 / 112.0, inst="gtr", vel=0.62, ring=1.0, pan=0.10)
    if lvl >= 2 and comp % 3 == 1:
        lay_line(TH_B, t - 12 * BB, 60 / 112.0, inst="org", vel=0.34, ring=0.5, pan=-0.24)
    if lvl >= 3 and comp % 3 == 2:            # 무그는 마지막 5분의 1에서만
        if t > 232.0:
            lay_line(TH_B, t - 12 * BB, 60 / 112.0, inst="moog", vel=0.42,
                     ring=0.4, pan=0.26, glide=True)
    comp += 1
# 종지 — 프리지안 화음 (F♯ + E♭)
vD = voice_lead("Dphr", prev, 52, 74, 4)
CHORDLOG.append((t, "Dphr", tuple(vD)))
D["perc"].put(ens.palma(0.86, "clara"), t, 1.0, -0.40)
D["perc"].put(ens.cajon(0.86, "bass"), t + 0.006, 1.0, 0.0)
D["perc"].put(ens.tacon(0.80), t + 0.010, 1.0, -0.12)
for k, m in enumerate(vD):
    D["gtr"].put(ny(m, 2.2, 0.70, pluck=0.16, ring=2.2), t + k * 0.012, 1.0, 0.20)
D["bass"].put(rick(26, 2.4, vel=0.86, ring=1.5), t, 1.0, 0.0)
LAST = vD

# ═════════════════════════════════════ 5악장 · Promenade 변주 II (4:20–4:35)
# 두 주제가 처음 겹친다. 불협을 해소하지 않는다.
# D7♭9 로 끝내고 해결 없이 E♭장조(6악장)로 넘어간다 — 기만적 전조.
mark("5악장 Promenade 변주 II · 두 주제 겹침 / 불협 미해소", 260.0, seed=20260810)
BT = 60 / 88.0
PROG5 = [("Gm7", 3), ("Ebmaj7", 3), ("Cm7", 3), ("D7b9", 3), ("D7b9", 2.5)]
lay_bass(PROG5, 260.0, BT, D_PHR, gain=0.98, density=2.0, leap_p=0.20, seed=51)
lay_chords(PROG5, 260.0, BT, 51, 70, pf=0.34, strg=0.14, org=0.20,
           prev=LAST, roll=0.020)
lay_line(TH_A, 260.0, BT, vel=0.60, ring=1.5, oct_=12, pan=-0.24)
lay_line(TH_B, 260.0 + 1.5 * BT, BT, vel=0.50, ring=1.5, pan=0.22)
LAST = voice_lead("D7b9", None, 51, 70, 4)

# ═════════════════════════════════════════════════ 6악장 · 론다 (4:35–5:25)
# 비움으로 만드는 광활함. ♩=56, 한 마디에 두세 음.
# 여기서 베이스가 처음으로 선율을 가져간다.
mark("6악장 론다 · E♭장조 / 비움으로 만드는 광활함", 275.0, seed=20260811)
BT = 60 / 56.0
PROG6 = [("Ebmaj9", 4), ("F/A", 4), ("Cm9", 4), ("Bb/D", 4),
         ("Ebmaj9", 4), ("Gm7", 4), ("F", 4), ("Ebmaj7", 4),
         ("Bbmaj7", 4), ("Ebmaj9", 4), ("Dm7", 4), ("F", 4), ("Ebmaj9", 6)]
MEL6 = [(75, 3), (77, 3), (75, 1), (74, 1), (72, 2),
        (70, 3), (72, 3), (75, 6)]
# BL-25 — 베이스가 선율을 나눠 든다. 더하는 것이 아니라 나누는 것이다.
#
# 이전 판은 주석만 그렇게 적어놓고 실제로는 화음의 근음·3음을 기계적으로 병행했다.
# MEL6 과 아무 관계가 없었으므로 "분담"이 아니라 반주가 하나 더 있는 것이었고,
# 그만큼 이 악장이 채워졌다. 이 악장의 존재 이유는 비어 있는 것이다.
#
# 그래서 선율을 반으로 자른다. 앞 절반(박 2~10)은 피아노가, 뒷 절반(박 10~24)은
# 베이스가 두 옥타브 아래에서 든다. 받는 동안 피아노는 쉰다 — 성부가 늘지 않는다.
# 나머지 구간의 베이스는 화음마다 한 음씩만, 길게. B♭1에서 E♭3까지 벌려 놓는다.
# 광활함은 음을 더해서가 아니라 **폭**에서 온다.
# 선율을 든 넷(★)은 반주보다 앞에 있어야 한다. 베드는 뒤로 물린다.
BASS6 = [                       # (진입 박, 미디음, 지속 박, 세기)
    (0.0, 39, 4.0, 0.70),       # E♭2 — 공간을 연다
    (6.0, 45, 2.0, 0.70),       # A2  — F/A 의 슬래시 저음. 떠 있는 소리
    (10.0, 48, 2.0, 0.88),      # ┐★ 선율을 받는다. MEL6 뒷 절반을 −2옥타브로
    (12.0, 46, 3.0, 0.88),      # │★ (72,2)(70,3)(72,3)(75,6) 의 리듬 그대로
    (15.0, 48, 3.0, 0.88),      # │★
    (18.0, 51, 6.0, 0.90),      # ┘★ E♭3 — 베이스가 이 악장에서 가장 높이 오른다
    (24.0, 41, 4.0, 0.70),      # ┐ 다시 베드. 화음당 한 음, 레지스터를 크게 벌린다
    (28.0, 51, 4.0, 0.70),      # │
    (32.0, 34, 4.0, 0.74),      # │ B♭1 — 곡에서 가장 낮은 자리
    (36.0, 46, 4.0, 0.70),      # │
    (40.0, 50, 4.0, 0.70),      # │
    (44.0, 41, 4.0, 0.70),      # │
    (48.0, 39, 6.0, 0.72),      # ┘ E♭2 로 착지
]
t = 275.0
prev = LAST
while t < 320.0:
    tn, prev, ts = lay_chords(PROG6, t, BT, 55, 74, pf=0.40, strg=0.11, org=0.10,
                              prev=prev, roll=0.042, hold=0.97, nv=4)
    for b0, m, bd, bv in BASS6:
        tt, vv = H(t + b0 * BT, bv)
        D["bass"].put(rick(m, bd * BT * 0.94, vel=vv, ring=2.6), tt, 1.0, -0.04)
    # 피아노는 앞 절반만 든다. 뒷 절반은 베이스에게 넘긴다
    lay_line(MEL6[:4], t + 2 * BT, BT, vel=0.60, ring=2.6, oct_=0, pan=-0.20)
    t = tn
LAST = prev

# ═══════════════════════════════════ 7악장 · 그라나다 (5:25–7:05)
# 6/8. ♭II(E♭maj7) → i(Dm) 프리지안 종지가 반복된다.
# 무그가 그녀의 목소리. 주제 A는 침묵한다.
mark("7악장 그라나다 · 6/8 / ♭II–i 프리지안 종지 · 무그 = 그녀의 목소리", 325.0, seed=20260812)
BT = 60 / 150.0                               # 8분음표
PROG7 = [("Dm7", 6), ("Bbmaj7", 6), ("Gm7", 6), ("Ebmaj7", 6),
         ("Dm7", 6), ("Cm7", 6), ("Bb6", 6), ("Ebmaj7", 6),
         ("Dm11", 6), ("F", 6), ("Gm7", 6), ("Ebmaj7", 6),
         ("Bbmaj7", 6), ("Cm7", 6), ("Ebmaj7", 6), ("Dm7", 6)]
t = 325.0
prev = LAST
bar = 0
while t < 420.0:
    tn, prev, ts = lay_chords(PROG7, t, BT, 52, 72, pf=0.0, org=0.20, strg=0.10,
                              prev=prev, roll=0.0, hold=0.99)
    # 알함브라의 물 — 6/8 아르페지오 (피아노)
    bt = t
    for i, (sym, beats) in enumerate(PROG7):
        v = voice_lead(sym, None, 57, 79, 4)
        pat = [0, 1, 2, 3, 2, 1]
        for k in range(6):
            tt, vv = H(bt + k * BT, 0.30 if k else 0.38, tj=0.006)
            D["kb"].put(pn(v[pat[k] % len(v)], BT * 1.7, vv, ring=1.3),
                        tt, 1.0, 0.10 - 0.04 * k)
        r = parse(sym)[0]
        bm = 26 + (r - 26) % 12
        tt, vv = H(bt, 0.72)
        D["bass"].put(rick(bm, 6 * BT * 0.85, vel=vv, ring=1.4), tt, 1.0, -0.04)
        # 그녀의 노래 — 네 마디마다
        if i % 4 == 0:
            lay_line([(m, b * 0.62) for m, b in TH_B], bt, BT * 2,
                     inst="moog", vel=0.44, ring=0.5, pan=0.24, glide=True)
        bt += 6 * BT
    t = tn
LAST = prev

# ══════════════════════════════════ 8악장 · 바르셀로나 (7:05–8:45)
# 7/8 = 2+2+3. 베이스가 마디를 쪼갠다.
# 하강 프리지안 4음선 + 반음계 매개화음. 주제 B가 조각난다.
mark("8악장 바르셀로나 · 7/8 (2+2+3) · 주제 B 파편화", 425.0, seed=20260813)
BT = 60 / 176.0
PROG8 = [("Dm", 7), ("Ebmaj7", 7), ("Dm", 7), ("Cm7", 7),
         ("Bbmaj7", 7), ("D", 7), ("Dm", 7), ("Gm7", 7),
         ("Ebmaj7", 7), ("D", 7), ("Gm", 7), ("F", 7),
         ("Ebmaj7", 7), ("Cm7", 7), ("Dm", 7), ("D", 7)]
GRP = [2, 2, 3]
t = 425.0
prev = LAST
bar = 0
while t < 520.0:
    for sym, _ in PROG8:
        if t >= 520.0:
            break
        v = voice_lead(sym, prev, 52, 71, 4)
        prev = v
        CHORDLOG.append((t, sym, tuple(v)))
        off = 0.0
        for gi, g in enumerate(GRP):
            for j, m in enumerate(v):
                tt, vv = H(t + off + j * 0.008, 0.80 if g == 3 else 0.58)
                D["org"].put(hamm(m, BT * g * 0.82, synth.REG_FULL, vv), tt, 1.0,
                             -0.20 + 0.08 * j)
                D["kb"].put(pn(m, BT * g * 0.7, vv * 0.80, ring=0.2),
                            tt, 1.0, 0.14)
            # 베이스가 2+2+3을 만든다
            r, degs, _ = parse(sym)
            bm = 26 + (r + [0, 7, degs[1]][gi] - 26) % 15
            bm = 28 + (r + [0, 7, degs[1]][gi] - 28) % 18
            tt, vv = H(t + off, 0.88 if gi == 2 else 0.74)
            D["bass"].put(rick(bm, BT * g * 0.8, vel=vv, ring=0.35), tt, 1.0, -0.02)
            D["perc"].put(synch := ens.cajon(0.42 if gi == 2 else 0.30, "bass"),
                          H(t + off, 1.0)[0], 1.0, 0.0)
            off += BT * g
        # 주제 B 파편 — 온전한 프레이즈가 나오지 못한다
        if bar % 2 == 0:
            nfrag = 5 if bar % 4 == 0 else 3
            lay_line([(m, .7) for m, _ in TH_B[:nfrag]], t, BT, inst="moog",
                     vel=0.40, ring=0.3, pan=0.26, glide=True)
        t += BT * 7
        bar += 1
LAST = prev

# ══════════════════════════════ 9악장 · The Great Gate (8:45–9:40)
# 플라갈 진행 B♭–E♭–B♭. 두 주제 총주.
# 그리고 F♯ → F : D–F♯–A 가 D–F–A 로, 다시 B♭maj7 로 흡수된다.
mark("9악장 The Great Gate · 플라갈 B♭–E♭–B♭ · F♯→F 해소", 525.0, seed=20260814)
BT = 60 / 63.0
PROG9 = [("Bb", 4), ("Ebmaj7", 4), ("Bb/D", 4), ("F", 4),
         ("Gm7", 4), ("Ebmaj7", 4), ("F7sus4", 2), ("F7", 2), ("Bb", 4),
         ("Ebmaj7", 4), ("Bb/D", 4), ("Cm7", 4), ("F", 4), ("Bb", 6)]
t = 525.0
prev = LAST
while t < 566.0:
    lay_bass(PROG9, t, BT, BB_MAJ, gain=1.05, density=2.0, leap_p=0.18,
             ring=1.0, seed=91)
    tn, prev, ts = lay_chords(PROG9, t, BT, 52, 72, pf=0.52, org=0.62, strg=0.18,
                              prev=prev, roll=0.020, hold=0.98)
    t = tn
LAST = prev

# 걸음 위에 컴파스가 겹친다 (WBS 1.4.8 — `07` 4장이 적어두고 구현되지 않았던 것)
#
#   "베이스는 여기서 걸음과 컴파스를 동시에 짚는다. 8분음표 행보 위에
#    컴파스의 강세가 겹친다. 두 리듬이 마지막에 만난다."
#
# 위의 lay_bass 가 8분음표 행보를 놓았고, 여기서 그 위에 4악장의 컴파스
# 강세 자리 {0,3,6,8,10} 을 12박 주기로 겹친다. 화음 주기는 4박이고
# 컴파스는 12박이라 둘이 계속 어긋나며 흐른다 — 그것이 이 곡의 엔진이다.
#
# **566초에서 멈춘다.** F♯ → F 가 일어나는 지점이고, 거기서 컴파스가
# 물러나며 걸음만 남는다. 그녀의 리듬이 그의 조성으로 편입되는 것과 같다.
# 그것이 "두 리듬이 마지막에 만난다"의 뜻이다.
# **8분음표 격자에 놓는다.** 4분음표에 놓으면 ♩=63 에서 한 주기가 11.4초가 되어
# 리듬으로 안 들리고 띄엄띄엄한 악센트가 된다(4악장은 4.29초다). 8분음표면
# 5.7초로 4악장에 가까워지고, 무엇보다 **걸음과 같은 격자**가 된다 —
# `07` 4장이 "8분음표 행보 **위에**" 겹친다고 쓴 것이 이 뜻이다.
EB = BT / 2.0
_C9 = [(ct, sy) for ct, sy, _ in CHORDLOG if 525.0 <= ct < 566.0]
tc = 525.0
while tc < 566.0:
    for bi in (0, 3, 6, 8, 10):
        tt = tc + bi * EB
        if tt >= 566.0:
            break
        sym = [s for ct, s in _C9 if ct <= tt + 1e-6][-1]
        r = parse(sym)[0]
        m = 33 + (r - 33) % 12                    # B♭1~A2 에서 근음을 짚는다
        vv = 0.46 if bi in (0, 6) else 0.32       # 컴파스의 두 극점이 세다
        a, v2 = H(tt, vv)
        D["bass"].put(rick(m, EB * 0.9, vel=min(0.9, v2), ring=0.34), a, 1.0, -0.05)
    tc += 12 * EB

# 두 주제 동시
lay_line(TH_A, 527.0, BT, vel=0.72, ring=2.8, oct_=12, pan=-0.24)
lay_line(TH_A, 527.0, BT, inst="org", vel=0.30, ring=0.4, oct_=12, pan=-0.10)
lay_line(TH_B_RES, 527.0, BT, inst="moog", vel=0.46, ring=0.5, pan=0.26, glide=True)
# 두 번째 총주에서 그녀가 벨팅한다 (WBS 1.4.8, v1.18)
#   ① 정점에서 비브라토 폭이 넓어진다  ② 배음이 밝아진다
# 지속음의 뒤로 갈수록 흔들림이 차오르므로, 짧은 음에는 거의 안 걸리고
# 프레이즈 끝의 긴 음에서만 드러난다 — 사람이 긴 음을 지탱할 때와 같다.
lay_line(TH_A, 549.0, BT, vel=0.76, ring=3.0, oct_=12, pan=-0.24)
lay_line(TH_B_RES, 549.0, BT, inst="moog", vel=0.50, ring=0.5, pan=0.26,
         glide=True, vib=0.30, bright=900)

# ── F♯ → F 해소를 명시적으로 들려준다 ────────────────────────────
# D–F♯–A (D장3화음, 그녀의 색채) → D–F–A (Dm) → B♭–D–F–A (B♭maj7)
mark("  F♯ → F · 그녀의 주제가 B♭장조로 편입된다", 566.0)
for k, m in enumerate([50, 54, 57, 62]):
    D["kb"].put(pn(m, 2.6, 0.52, ring=2.2), 566.0 + k * 0.018, 1.0, -0.10)
    D["org"].put(hamm(m, 2.2, synth.REG_SOFT, 0.24), 566.0 + k * 0.018, 1.0, 0.08)
D["bass"].put(rick(38, 2.6, vel=0.84, ring=1.4), 566.0, 1.0, -0.02)
# 이 두 음이 곡의 결론이다. F♯ 은 벨팅으로 끝까지 지탱하고,
# F 로 내려앉을 때 비브라토를 거둔다 — 버티다가 놓는 소리다.
D["lead"].put(moog(66, 2.2, gain=0.44, cut=3600, res=0.26, vib=0.34),
              566.05, 1.0, 0.24)
for k, m in enumerate([50, 53, 57, 62]):                      # F♯ → F
    D["kb"].put(pn(m, 2.4, 0.50, ring=2.4), 569.0 + k * 0.018, 1.0, -0.10)
    D["org"].put(hamm(m, 2.0, synth.REG_SOFT, 0.24), 569.0 + k * 0.018, 1.0, 0.08)
D["lead"].put(moog(65, 2.0, gain=0.42, cut=3400, res=0.24, glide=66, vib=0.0),
              569.05, 1.0, 0.24)
D["bass"].put(rick(38, 2.4, vel=0.80, ring=1.4), 569.0, 1.0, -0.02)
# 마지막 화음 — B♭maj7 이 아니라 순수 B♭. 편입이 끝났다.
FIN = [46, 50, 53, 58, 62, 65, 70, 74]
for k, m in enumerate(FIN):
    D["kb"].put(pn(m, 8.0, 0.62 - 0.02 * k, ring=6.0), 572.0 + k * 0.022, 1.0,
                -0.24 + 0.06 * k)
    D["org"].put(hamm(m, 6.0, synth.REG_FULL, 0.22), 572.0 + k * 0.022, 1.0, 0.0)
    D["str"].put(st(m, 6.5, 0.13, voices=6, attack=0.35, release=1.6),
                 572.0 + k * 0.02, 1.0, -0.30 + 0.09 * k)
D["bass"].put(rick(34, 6.0, vel=0.90, ring=3.0), 572.0, 1.0, 0.0)
D["bass"].put(rick(46, 5.5, vel=0.62, ring=3.0), 572.02, 1.0, -0.06)


# ═══════════════════════════════════════════════════════════ 출력
#
# 무그(그녀)의 잔향은 악장마다 다르다 — BL-32, WBS 1.4.4 에서 확정.
# 근거는 `07. 작곡 계획` 11장 「잔향이 실재와 상상을 가른다」의 표다.
#
#   마른 소리는 지금 여기에 있고, 젖은 소리는 기억 속에 있다.
#
# 4악장의 그녀는 2005년에 실제로 촬영된 무희다. V3 가 "여기서는 생성하지
# 않는다"고 못박은 유일한 악장이고, 그래서 **음악에서도 그녀가 말라야 한다.**
# 7악장에서 상상으로 넘어가며 가장 젖고, 8악장에서 흩어지고, 9악장에서
# 그의 조성으로 편입되며 중간으로 돌아온다.
#
#   4 세비야 (160~)  0.15  실재      — 가장 마르게
#   7 그라나다(325~)  1.00  상상      — 가장 젖게. 검수자가 정한 기준값
#   8 바르셀로나(425~) 0.70  흩어진다   — 파편이 남는다
#   9 대문   (525~)  0.45  편입      — 중간
#
# 값은 경계에서 2초에 걸쳐 건너간다. 잔향 **앞에** 곱하므로 앞 악장의 꼬리는
# 잘리지 않고 그대로 남는다 — 콘솔의 센드 페이더를 움직이는 것과 같다.
SEND_LEAD = [(160.0, 0.15), (325.0, 1.00), (425.0, 0.70), (525.0, 0.45)]

raw = D.stem_rms(TOTAL, check=True)
D.save_stems("스템", TOTAL)          # BL-29 — 믹스.py 가 이것으로 렌더 없이 믹스한다
out = D.mix(TOTAL, reverb=0.15, sends={"lead": ("plate", SEND_LEAD)})
piano.write_wav("전곡화성.wav", out)

print("렌더 %.1f초  peak %.3f  rms %.4f" %
      (len(out) / SR, np.abs(out).max(), np.sqrt((out ** 2).mean())))
print("\n[스템 RMS · 정규화 전 · dBFS]")
for k in ["kb", "org", "bass", "str", "gtr", "lead", "perc"]:
    v = raw[k]
    print("  %-5s %7.1f dB  → 페이더 %+5.1f dB  = %7.1f dB" %
          (k, 20 * np.log10(max(v, 1e-9)), GAINS[k],
           20 * np.log10(max(v, 1e-9)) + GAINS[k]))
print("\n[성부 진행 통계]")
print("  화음 수            %d" % STAT["chords"])
print("  평균 총이동량      %.2f 반음 / 화음전환 (4성부 합)" %
      (STAT["move"] / max(1, STAT["chords"] - 1)))
print("  외성 병행 5도      %d" % STAT["par5"])
print("  외성 병행 8도      %d" % STAT["par8"])
print("  7반음 초과 도약    %d" % STAT["leap"])
print("  저역 밀집(5도미만) %d" % STAT["lowtight"])
print()
for n, tt in MARK:
    print("  %5.1fs  %d:%02d  %s" % (tt, int(tt) // 60, int(tt) % 60, n))

np.save("chordlog.npy", np.array([(a, b, c) for a, b, c in CHORDLOG], dtype=object),
        allow_pickle=True)
