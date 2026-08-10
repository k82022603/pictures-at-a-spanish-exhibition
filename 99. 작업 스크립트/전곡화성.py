# -*- coding: utf-8 -*-
"""
《스페인 전람회의 그림》 — 전곡 화성 진행 (9분 40초 / 10악장)
v1.4 기준.  화성 우선 · 성부 진행 자동 최적화 · 테이프 마스터.

편성은 화성이 들리는 최소 구성으로 제한한다.
  피아노(주역) · 해먼드(패드) · 리켄배커 베이스(독립 대선율) · 현악(공기)
  나일론 기타(2·4악장) · 무그(7·9악장) · 팔마스·카혼(4악장만, 약하게)
"""
import re

import numpy as np
from scipy import signal as sg

import piano
import ensemble as ens
import synth
from 화성 import (Desk, voice_lead, bassline, parse, pcset, STAT,
                  rick, hamm, moog, tape, pn, st, ny,
                  drum, lay_drum, pat_promenade, pat_finale, pat_break)

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
         "gtr": 5.0, "lead": 2.0, "perc": -5.0, "drum": 2.0}
D = Desk(TOTAL, list(GAINS), GAINS)
MARK = []
CHORDLOG = []          # (시각, 심볼, 보이싱) — 검증용
# 화음이 **어느 악장 것인가.** 시각만으로는 알 수 없다 — 슬롯을 넘긴 화음은
# 다음 악장의 시각대에 있기 때문이다. 그래서 놓는 순간에 적어 둔다.
#
# 2026-08-10 — 이것이 없어서 `악장표.py` 의 넘침 탐지가 **간격을 좇다가 다음
# 악장의 화음을 자기 것으로 이어 세고** 있었다. 깨끗한 렌더에 1·6악장 넘침
# 경고가 떴다. 오탐이 뜨는 탐지기는 다음에 진짜를 놓치게 만든다.
CHORDMOV = []          # CHORDLOG 와 같은 길이. 악장 번호
MOVN = 0


def clog(t, sym, v):
    """화음 하나를 기록한다. 시각·심볼·보이싱에 **악장 번호**를 함께 남긴다."""
    CHORDLOG.append((t, sym, tuple(v)))
    CHORDMOV.append(MOVN)


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
    global MOVN
    MARK.append((name, t))
    _m = re.match(r"(\d)악장", name)
    if _m:                              # 하위 표시("  컴파스 진입")는 악장을 안 바꾼다
        MOVN = int(_m.group(1))
    if seed is not None:
        global RNG
        RNG = np.random.default_rng(seed)


# ══════════════════════════════════════════════════ 공통 텍스처 함수
def lay_chords(prog, t0, beat, lo, hi, *, org=0.0, pf=0.0, strg=0.0, gtr=0.0,
               nv=4, roll=0.016, pan=-0.10, sus=None, prev=None, hold=0.96,
               until=None):
    """화성 진행을 놓는다. 반환 (끝 시각, 마지막 보이싱, 각 화음 시각 리스트)

    `until` — 이 시각을 넘는 화음은 놓지 않는다. **악장 경계다.**

    2026-08-08 실측에서 1악장이 슬롯(50~90초)을 13.9초, 7악장이 12.8초
    넘겨 다음 악장을 덮고 있었다. 마드리드(♩=138)가 변주 I(♩=96) 위에
    15초를 겹쳐 울렸고, **두 템포가 동시에 들리니 둘 다 흐려졌다.**
    "138인데 138로 안 들린다"의 원인이 이것이다.
    """
    t = t0
    ts = []
    for idx, (sym, beats) in enumerate(prog):
        if until is not None and t >= until - 1e-6:
            break
        s2 = sym
        v = voice_lead(s2, prev, lo, hi, nv)
        prev = v
        dur = beats * beat * hold
        ts.append(t)
        clog(t, sym, v)
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
             leap_p=0.14, ring=0.5, seed=3, accent_every=4, hand=None, until=None):
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
        if until is not None and t >= until - 1e-6:      # 악장 경계
            break
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

# (e) 드럼이 여기서 처음 들어온다 — 31.9초 (WBS 1.1.6 · `07` 16.7절)
#
# 앞의 31.9초를 비워두는 것이 설계다. 4장의 층 쌓기(피아노 혼자 → 베이스가
# 조성을 선포 → 화성)를 지켜야 하고, 무엇보다 **베이스가 조성을 선포하는
# 자리를 드럼이 뺏으면 안 된다.**
#
# 31.9초는 주제가 다섯 번 지나간 뒤 베이스만 남는 자리다. 눈(주제)이 감기고
# 발(베이스)만 남았을 때 **처음으로 발소리에 바닥이 생긴다.**
#
# 그리고 38.5초에 여섯 번째 주제가 이 마디 위를 지나간다 — 프레이즈 9박이
# 마디 11박(5+6)에 대해 어긋나는 것이 **곡에서 처음 들리는 순간**이다.
#
# 하이햇은 4분음표다. 베이스가 이미 8분음표라 8분으로 깔면 같은 격자를
# 두 번 말하게 되고, 그러면 마디가 아니라 질감만 는다 (`07` 16.2절).
#
# **스네어가 아니라 사이드 스틱(림샷)이다.** 프롬나드는 절제된 구간이고,
# 스네어를 세게 치면 백비트가 되어 드럼이 앞으로 나선다. 오픈 스네어는
# 고조되는 9악장에서만 쓴다 (`07` 16.9절).
#
# 그리고 **마디마다 다르다.** 매 마디 똑같이 치면 성긴 것이 아니라 기계다.
_off0 = 0
_nd0 = 0
for _i, (_sym, _nb) in enumerate(PROG0):
    _ts = T0B + BT * (1.0 + _off0)
    if _i >= 6:                                   # 뒤 여섯 화음 = 31.9초부터
        lay_drum(lambda y, a, g, p: D["drum"].put(y, a, g, p),
                 _ts, BT, pat_promenade(_nb, _nd0),
                 gain=0.68 + 0.05 * _nd0,         # 들어오면서 조금씩 자란다
                 n=_i, jitter=lambda a, v: H(a, v))
        _nd0 += 1
    _off0 += _nb

# ═════════════════════════════════════════════════ 1악장 · 마드리드 (0:50–1:30)
# 곡 전체에서 유일하게 기능화성이 또렷한 악장. ii–V–I 와 이차 딸림화음.
mark("1악장 마드리드 · ii–V–I 기능화성", 50.0, seed=20260806)
# BL-33 (`07` 19장) — 한 악장 안에서 템포가 단계로 오른다. 132 → 144.
# 도착의 흥분이 밖에서 주어지는 게 아니라 **자기 안에서 커진다.**
# 연속 가속이 아니라 단계다 — 단계 안에서는 그리드가 고정이므로 컷을 붙일 수 있다.
# **음악적 숫자를 그대로 적는다.** 기계값(BT)은 여기서 유도한다 — 그래야
# 악보를 읽는 사람과 코드가 같은 숫자를 본다. 단위 ♩ (4분음표)
TEMPO1 = [(50.0, 70.0, 132),                  # 도착        · 단위 ♩
          (70.0, 90.0, 144)]                  # 흥분
PROG1 = [("Bb", 4), ("Dm7", 4), ("Cm7", 4), ("F7", 4),
         ("Bb", 4), ("Bb/D", 4), ("Ebmaj7", 4), ("Cm7", 4),
         ("Gm7", 4), ("Cm7", 4), ("F7", 4), ("Bb/D", 4),
         ("Ebmaj7", 4), ("Cm7", 4), ("F7sus4", 2), ("F7", 2), ("Bb", 4)]
MEL1 = [(70, .5), (72, .5), (74, 1), (72, .5), (70, .5), (67, 1),
        (65, .5), (67, .5), (70, 1), (69, .5), (67, .5), (65, 1),
        (74, .5), (72, .5), (70, 1), (72, .5), (74, .5), (77, 1),
        (75, .5), (74, .5), (72, 1), (70, 1.5)]
prev = LAST
END1 = 90.0                                   # 악장 경계. 넘기면 2악장을 덮는다
# 단계마다 진행을 처음부터 돌린다. 20초에 64박 진행이 다 안 들어가므로 잘리는데,
# **잘리는 자리가 곧 단계 경계**이고 거기서 템포가 오른다. 원래도 잘려 있었다.
for rep, (s0, s1, _q) in enumerate(TEMPO1):
    BT = 60.0 / _q
    t = s0
    if t >= END1:
        break
    lay_bass(PROG1, t, BT, BB_MAJ, gain=1.02, density=2.0, leap_p=0.12, seed=21 + rep,
             until=s1)
    tn, prev, _ = lay_chords(PROG1, t, BT, 52, 70, pf=0.30, org=0.22, strg=0.09,
                             prev=prev, roll=0.010, hold=0.55, until=s1)
    # 오른손 화음 반주 — 8분음표 백비트
    tt2 = t
    for sym, beats in PROG1:
        if tt2 >= s1:
            break
        v = voice_lead(sym, None, 57, 74, 3)
        for k in range(int(beats * 2)):
            if k % 2 == 1 and tt2 + k * BT * 0.5 < s1:
                a, vv = H(tt2 + k * BT * 0.5, 0.20)
                for j, m in enumerate(v):
                    D["kb"].put(pn(m, BT * 0.34, vv, ring=0.14),
                                a + j * 0.007, 1.0, 0.16)
        tt2 += beats * BT
    if t + 4 * BT < s1:
        lay_line(MEL1, t + 4 * BT, BT, vel=0.74, ring=0.6, oct_=12, pan=-0.24)
LAST = prev

# ═══════════════════════════════════════ 2악장 · Promenade 변주 I (1:30–1:45)
# 두 번째 기타가 한 마디 늦게 들어온다 — 두 번째 발소리
mark("2악장 Promenade 변주 I · 두 번째 발소리", 90.0, seed=20260807)
# BL-33 — 96 → 104. **프롬나드는 같은 사람의 걸음이다.**
# 0악장 100 · 2악장 96 · 5악장 88 로 조금씩 처지고 있었다. 같은 사람이 같은
# 전람회를 걷는데 왜 갈수록 느려지는가. 0악장 100 을 기준으로 모은다.
# 정확히 100 이 아니라 104 인 것은 이 악장이 **두 번째** 발소리이기 때문이다 —
# 처음보다 조금 익숙해진 걸음. 5악장이 100 으로 되돌아온다.
BT = 60 / 104.0
PROG2 = [("Bb", 3), ("Gm7", 3), ("Ebmaj7", 3), ("F", 3), ("Bb", 3)]
END2 = 105.0
# 2026-08-08 — 1악장 슬롯 넘침을 고치자 **이 악장이 비어 있다는 것이 드러났다.**
# 15초 슬롯에 화성은 9.4초뿐이었고 **베이스·피아노·오르간이 아예 없었다.**
# 마드리드가 위에 15초를 겹쳐 울려서 그 빈 것이 안 들렸을 뿐이다 (`05` 9.18절).
#
# 프롬나드인데 **걷는 몸이 없었다.** `07` 3장이 세운 것이 무너져 있었다.
# 여기서는 최소한만 채운다 — 화성·베이스·드럼으로 다른 프롬나드 수준까지.
# **주제 배치는 1.4.10 소관이다** (연결 프롬나드는 양쪽이 있어야 놓는다).
_p2, _n2 = LAST, 0
for _rep in range(2):                                  # 15초를 채운다
    _t2 = 90.0 + _rep * 15 * BT
    if _t2 >= END2:
        break
    lay_bass(PROG2, _t2, BT, BB_MAJ, gain=0.96, density=2.0, leap_p=0.13,
             seed=22 + _rep, until=END2)               # 걷는 몸
    _tn2, _p2, _ = lay_chords(PROG2, _t2, BT, 50, 68, gtr=0.30, strg=0.08,
                              org=0.12, pf=0.16, prev=_p2, roll=0.030, until=END2)
    for _sym, _nb2 in PROG2:                           # 드럼 — 3박 마디
        if _t2 >= END2:
            break
        lay_drum(lambda y, a, g, p: D["drum"].put(y, a, g, p),
                 _t2, BT, pat_promenade(_nb2, _n2), gain=0.62,
                 n=_n2, jitter=lambda a, v: H(a, v))
        _t2 += _nb2 * BT
        _n2 += 1
# 두 번째 발소리 — 기타 캐논. 이 악장의 정체다
lay_line(TH_A, 90.0, BT, inst="gtr", vel=0.62, ring=1.1, pan=0.18)
lay_line([(m, b) for m, b in TH_A[:8]], 90.0 + 2 * BT, BT, inst="gtr",
         vel=0.34, ring=1.1, oct_=-12, pan=-0.26)
LAST = _p2

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
# BL-33 (`07` 19장) — **플라멩코는 실제로 조인다.**
# 이 악장은 밀도를 무에서 쌓아 올리는데 템포만 고정이었다. 밀도가 오르면서
# 속도는 그대로면, 쌓이는 것이 층이 아니라 겹으로만 들린다.
#
# 컴파스 여섯 개마다 한 단계씩 조인다. 12박 한 바퀴가 4.74 → 4.29 → 3.75 초.
# ♩ 로는 76 → 84 → 96 이고, BB 는 그 절반(8분음표)이다.
TEMPO4 = [76, 84, 96]                        # 단위 ♩ · BB 는 8분음표 = 30/♩
BB = 30.0 / TEMPO4[0]                        # 들머리는 가장 느린 단계
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
    # 템포는 컴파스 6개마다. 밀도(3개마다)와 주기가 다르므로 **둘이 어긋나며
    # 오른다** — 같이 오르면 계단 하나로 뭉쳐 들린다
    BB = 30.0 / TEMPO4[min(2, comp // 6)]
    for ci, (sym, nb) in enumerate(CAD):
        v = voice_lead(sym, prev, 52, 71, 4)
        prev = v
        clog(t, sym, v)
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
clog(t, "Dphr", vD)
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
# BL-33 — 88 → 100. 0악장의 걸음으로 되돌아온다.
# 이 악장에서 두 주제가 처음 겹치므로 **걸음이 0악장과 같아야** 겹침이 들린다.
# 88 은 세비야(4악장)의 여운으로 처져 있던 것이었다.
BT = 60 / 100.0
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
# BL-33 (`07` 19장) — ♩.=50 으로 100초를 가면 늘어진다. 60 → 72 두 단계.
# **그녀가 다가올수록 조인다.** 무그가 네 마디마다 부르는 간격도 함께 좁아진다.
# BT 는 8분음표. 부점4분(♩.) = 3 × BT 이므로 ♩.=60 이면 ♪=180.
TEMPO7 = [(325.0, 375.0, 60),                 # 멀리서   · 단위 ♩. (부점4분)
          (375.0, 425.0, 72)]                 # 가까이
PROG7 = [("Dm7", 6), ("Bbmaj7", 6), ("Gm7", 6), ("Ebmaj7", 6),
         ("Dm7", 6), ("Cm7", 6), ("Bb6", 6), ("Ebmaj7", 6),
         ("Dm11", 6), ("F", 6), ("Gm7", 6), ("Ebmaj7", 6),
         ("Bbmaj7", 6), ("Cm7", 6), ("Ebmaj7", 6), ("Dm7", 6)]
prev = LAST
bar = 0
END7 = 425.0                                  # 악장 경계. 넘기면 8악장을 덮는다
for _s0, _s1, _dq in TEMPO7:
  BT = 60.0 / (3 * _dq)
  t = _s0
  while t < _s1:
    tn, prev, ts = lay_chords(PROG7, t, BT, 52, 72, pf=0.0, org=0.20, strg=0.10,
                              prev=prev, roll=0.0, hold=0.99, until=_s1)
    # 알함브라의 물 — 6/8 아르페지오 (피아노)
    bt = t
    for i, (sym, beats) in enumerate(PROG7):
        if bt >= _s1:
            break
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
mark("8악장 바르셀로나 · 7/8 (2+2+3) · 인스트루멘털 브레이크", 425.0, seed=20260813)
# WBS 1.4.7 — **이 곡의 유일한 연주 구간이다.** (`07` 18장)
#
# 검수자 지적 — "건반하고 드럼이 제대로 놀아야 하는 구간이 있어야 하는데,
# 전반적으로 곡이 심심합니다." 실사해 보니 맞았다. 열 악장이 조성·박자·편성은
# 달라도 **하는 일이 같았다** — 화성을 깔고 그 위에 주제를 얹는 것.
# 프로그레시브 록의 심장인 인스트루멘털 브레이크가 없었다.
#
# 옛 8악장은 오르간과 피아노가 **같은 음을 같은 자리에** 쳤다. 두꺼울 뿐
# 주고받지 않았고, 41마디가 처음부터 끝까지 같은 텍스처였다.
#
# 셋을 바꾼다.
#   ① 템포  ♪=176 → 216. 7/8 마디가 2.39초 → 1.94초 (체감 ♩≈75 → 93)
#   ② 화성 리듬  마디당 1화음 → **2화음 (4+3박)**. 2+2+3 의 그룹 경계와 맞다.
#      템포만 올리면 안 빨라진다 — 화음이 느리게 바뀌면 완만하게 들린다
#   ③ 텍스처  **4마디마다 주역이 바뀐다.** 16마디가 한 바퀴다
#
#      마디 0~3    해먼드 리드    빠른 8분 라인. 드럼은 받쳐만
#      마디 4~7    드럼 주도      오르간은 스탭. 탐으로 굴린다
#      마디 8~11   무그           주제 B 파편 + **비명** (`07` 14장이 여기로 정했다)
#      마디 12~15  총주           전부. 크래시
# BL-33 (`07` 19장) — **곡의 정점은 자기 안에서 오른다.**
#
# v3.4 에서 ♪=176 → 216 으로 올렸는데 검수자 판정은 "뭔가 아쉽다"였다.
# 빠르기는 맞았지만 **고정값 하나를 더 박은 것**이라 극적이지 않았다.
# 지적은 세 번 다 "곡 전체"를 가리켰는데 나는 세 번 다 한 곳을 고쳤다.
#
# 여기서 세는 ♩은 4분음표가 아니라 **2+2+3 의 그룹 맥박**이다. 마디에 셋.
# 마디 길이 = 180/P 초이고 8분음표는 그 1/7 이다.
#   P= 88  마디 2.045초   16마디  425.0 → 457.7
#   P=104  마디 1.731초   20마디  457.7 → 492.3
#   P=120  마디 1.500초   끝까지  492.3 → 525.0
#
# 16·20 마디로 끊은 것은 **역할 회전(4마디)의 배수**여서다. 템포가 오르는
# 순간이 주역이 바뀌는 순간과 겹쳐야 계단이 들린다.
TEMPO8 = [(16, 88), (20, 104), (10 ** 9, 120)]   # 단위 2+2+3 그룹 맥박 (마디에 셋)


def bt8(nbar):
    """마디 번호로 8분음표 길이를 준다. 누적 마디 수로 단계를 고른다."""
    acc = 0
    for n, p in TEMPO8:
        acc += n
        if nbar < acc:
            return 180.0 / p / 7          # 마디 = 180/P 초, 8분음표는 그 1/7
    return 180.0 / TEMPO8[-1][1] / 7


BT = bt8(0)
# 마디마다 두 화음. 4+3 이 2+2+3 의 그룹 경계와 맞는다
PROG8 = [("Dm", 4), ("Ebmaj7", 3), ("Dm", 4), ("Cm7", 3),
         ("Bbmaj7", 4), ("D", 3), ("Dm", 4), ("Gm7", 3),
         ("Ebmaj7", 4), ("D", 3), ("Gm", 4), ("F", 3),
         ("Ebmaj7", 4), ("Cm7", 3), ("Dm", 4), ("D", 3),
         ("Gm7", 4), ("F", 3), ("Ebmaj7", 4), ("Dm", 3),
         ("Cm7", 4), ("Bbmaj7", 3), ("D", 4), ("Dm", 3),
         ("Ebmaj7", 4), ("Gm", 3), ("F", 4), ("Ebmaj7", 3),
         ("Dm", 4), ("D", 3), ("Gm7", 4), ("Dm", 3)]
GRP = [2, 2, 3]
# 해먼드 리드 — D 프리지안 7음. ♭2(E♭)를 앞세워 이 선법의 색을 낸다.
# 7/8 한 마디에 8분음표 일곱. 두 마디가 한 프레이즈다
RIFF = [62, 63, 65, 67, 65, 63, 62,
        70, 69, 67, 65, 63, 65, 62]
END8 = 525.0
t = 425.0
prev = LAST
bar = 0
while t < END8:
    for ci in range(0, len(PROG8), 2):
        if t >= END8:
            break
        role = ("org", "drum", "moog", "tutti")[(bar // 4) % 4]
        BT = bt8(bar)                       # BL-33 — 마디마다 단계를 다시 묻는다
        # 한 마디 = 두 화음 (4박 + 3박). 화성 리듬이 옛 판의 두 배다
        off = 0.0
        for sym, nb in PROG8[ci:ci + 2]:
            v = voice_lead(sym, prev, 52, 71, 4)
            prev = v
            clog(t + off, sym, v)
            # 오르간 — 역할에 따라 길이가 다르다. 스탭이면 짧게 끊는다
            hold = {"org": 0.86, "drum": 0.30, "moog": 0.55, "tutti": 0.90}[role]
            og = {"org": 0.66, "drum": 0.42, "moog": 0.38, "tutti": 0.82}[role]
            for j, m in enumerate(v):
                tt, vv = H(t + off + j * 0.008, og)
                D["org"].put(hamm(m, BT * nb * hold, synth.REG_FULL, vv), tt, 1.0,
                             -0.20 + 0.08 * j)
            # 피아노는 오르간을 겹쳐 치지 않는다. 총주에서만 함께 간다
            if role == "tutti":
                for j, m in enumerate(v):
                    tt, vv = H(t + off + j * 0.006, 0.60)
                    D["kb"].put(pn(m, BT * nb * 0.7, vv, ring=0.2), tt, 1.0, 0.14)
            off += BT * nb
        # 베이스가 2+2+3 을 만든다 — 이 악장의 뼈대
        off = 0.0
        r0 = parse(PROG8[ci][0])
        for gi, g in enumerate(GRP):
            sym = PROG8[ci][0] if gi < 2 else PROG8[ci + 1][0]
            r, degs, _ = parse(sym)
            bm = 28 + (r + [0, 7, degs[1]][gi] - 28) % 18
            tt, vv = H(t + off, 0.90 if gi == 2 else 0.76)
            D["bass"].put(rick(bm, BT * g * 0.8, vel=vv, ring=0.35), tt, 1.0, -0.02)
            # **음정 있는 킥** — 피아노 저역이 막드럼을 대신한다.
            #
            # 2026-08-08 청취 판정: "드럼 북 때문에 지저분하다. 차라리 건반을
            # 킥으로 쓰는 것이 낫겠다." 이 곡의 소리는 전부 음정을 갖는데
            # 킥·탐만 음정 없는 막이라 **음집합 밖에 혼자 있었다.**
            #
            # 베이스보다 한 옥타브 아래를 아주 짧게(ring 0.12) 친다. 길게 두면
            # 화성이 되고, 짧게 끊으면 타격이 된다.
            kv = {"org": 0.34, "drum": 0.66, "moog": 0.30, "tutti": 0.72}[role]
            if gi == 2:
                kv *= 1.18                      # 2+2+3 의 긴 그룹이 세다
            kb_m = bm - 12
            while kb_m < 24:
                kb_m += 12
            ka, kvv = H(t + off, kv)
            D["kb"].put(pn(kb_m, BT * 1.1, kvv, ring=0.12), ka, 1.0, -0.06)
            off += BT * g
        # 금속과 나무 — 하이햇·림샷·크래시. 막드럼은 없다
        lay_drum(lambda y, a, g, p: D["drum"].put(y, a, g, p),
                 t, BT, pat_break(bar, role), gain=0.70, n=bar,
                 jitter=lambda a, v: H(a, v))
        # 탐 롤을 대신하는 피아노 저역 하강. 음정이 있으므로 화성 안에 있다
        if role == "drum" and bar % 4 == 3:
            for k, mm in enumerate((38, 36, 33, 31, 29, 26)):
                ka, kvv = H(t + BT * (4.0 + k * 0.5), 0.44 + 0.06 * k)
                D["kb"].put(pn(mm, BT * 1.4, kvv, ring=0.16), ka, 1.0, -0.10)
        # ── 주역 ─────────────────────────────────────────────
        if role == "org":
            # 해먼드가 8분음표로 달린다. 두 마디에 걸친 프레이즈
            k0 = (bar % 4) * 7
            for k in range(7):
                m = RIFF[(k0 + k) % len(RIFF)]
                tt, vv = H(t + k * BT, 0.52 if k in (0, 2, 4) else 0.38)
                D["org"].put(hamm(m + 12, BT * 1.5, synth.REG_FULL, vv),
                             tt, 1.0, 0.24)
        elif role == "moog":
            nfrag = 5 if bar % 4 in (0, 2) else 3
            lay_line([(m, .7) for m, _ in TH_B[:nfrag]], t, BT, inst="moog",
                     vel=0.44, ring=0.3, pan=0.26, glide=True)
            if bar % 4 == 3:
                # **비명.** `07` 14장이 9악장이 아니라 여기로 자리를 정했다 —
                # 9악장의 서사는 편입이고 자기발진은 저항·파열의 소리다.
                # 8악장은 주제 B 가 부서지는 악장이므로 여기가 맞다
                D["lead"].put(moog(74, BT * 5, gain=0.50, cut=5200, res=0.42,
                                   scream=0.72, vib=0.20),
                              H(t + BT * 2, 1.0)[0], 1.0, 0.30)
        elif role == "tutti":
            lay_line([(m, .7) for m, _ in TH_B[:7]], t, BT, inst="moog",
                     vel=0.46, ring=0.3, pan=0.26, glide=True)
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

# 드럼 — 성긴 4/4. 하이햇은 4분음표다 (`07` 16.2절)
# 9악장은 마디가 4박이라 프롬나드의 5+6 이 아니지만, 하이햇을 4분에 두는
# 규칙은 같다. 여기는 곡에서 가장 두꺼운 텍스처이므로 더 그렇다.
# **드럼이 실제로 놓인 마디만 센다.**
#
# 처음에는 화음 인덱스를 그대로 셌는데, `PROG9` 의 7번째가 2박짜리
# `F7sus4`/`F7` 이라 `_nb >= 4` 에서 걸러진다. 그런데 탐 롤 조건이
# `n % 8 == 7` 이어서 **하필 그 걸러지는 마디에만 걸렸고, 9악장은 한 바퀴만
# 돌기 때문에 두 번째 기회도 없었다 — 탐 롤이 곡에 한 번도 안 들어갔다.**
#
# 검수자에게 "8마디마다 탐이 굴러 내려간다"고 말하고 그것을 들으라고까지
# 했다. T-02 가 이름 붙인 실수를 코드가 아니라 말로 저지른 것이다.
_t9 = 525.0
_nd9 = 0                                          # 드럼이 놓인 마디만
while _t9 < 570.0:
    for _sym, _nb in PROG9:
        if _t9 >= 570.0:
            break
        if _nb >= 4:
            lay_drum(lambda y, a, g, p: D["drum"].put(y, a, g, p),
                     _t9, BT, pat_finale(_nd9), gain=0.66, n=_nd9,
                     jitter=lambda a, v: H(a, v))
            _nd9 += 1
        _t9 += _nb * BT

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
# 악장 번호는 **별도 파일**이다. chordlog.npy 의 모양을 바꾸면
# 자막생성.py·검증화성.py 가 함께 깨지므로 건드리지 않는다.
np.save("chordmov.npy", np.array(CHORDMOV, dtype=np.int16))
