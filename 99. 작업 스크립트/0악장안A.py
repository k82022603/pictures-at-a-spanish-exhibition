# -*- coding: utf-8 -*-
"""
《스페인 전람회의 그림》 — 전곡 화성 진행 (9분 40초 / 10악장)
v1.4 기준.  화성 우선 · 성부 진행 자동 최적화 · 테이프 마스터.

편성은 화성이 들리는 최소 구성으로 제한한다.
  피아노(주역) · 해먼드(패드) · 리켄배커 베이스(독립 대선율) · 현악(공기)
  나일론 기타(2·4악장) · 무그(7·9악장) · 팔마스·카혼(4악장만, 약하게)
"""
import os
import re

import numpy as np
from scipy import signal as sg

import piano
import ensemble as ens
import synth
from 화성 import (Desk, voice_lead, bassline, parse, pcset, STAT, fla,
                  rick, hamm, moog, tape, pn, st, ny, hps, flt, pic,
                  drum, lay_drum, pat_promenade, pat_finale, pat_break)

SR = 44100
RNG = np.random.default_rng(20260805)
TOTAL = 50.0
OUT = "0악장 안A.wav"

# perc 는 4악장의 팔마스·카혼 — **실제로 존재하는 악기**다(V3 의 정신).
# drum 은 드럼 키트다. 둘을 한 스템에 담으면 안 되는 이유가 셋이다.
#   ① 잔향 — perc 는 어택이 생명이라 말라야 하고, 드럼은 악장마다 다를 수 있다
#   ② 페이더 — 4악장의 팔마스를 줄이면 8악장의 드럼이 함께 줄어든다
#   ③ 서사 — 4악장은 실재의 악장이다. 드럼 키트가 섞이면 그 구분이 흐려진다
# 지금은 비어 있다. 편성이 정해지기 전에 그릇만 만든다 — WBS 1.1.6 에서 채운다.
# **`wind` 는 2026-08-13 에 늘었다** (BL-36 ②) — 플루트가 7악장에서
# 그녀의 말을 되받는다. **자기 페이더를 준다** — 무그(`lead`)에 얹으면
# 그녀를 조절할 때 메아리가 함께 움직여서 둘을 못 가른다.
GAINS = {"kb": 6.0, "org": -13.0, "bass": 2.0, "str": 2.0,
         "gtr": 5.0, "lead": 2.0, "perc": -5.0, "drum": 2.0,
         "wind": 1.0}
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
               until=None, gtr_oct=0):
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
                # gtr_oct — **기타만** 옥타브를 옮긴다 (2026-08-11 시청용).
                # 화음은 그대로 두고 기타 층만 올리므로 피아노·현악과 어긋나지 않는다.
                D["gtr"].put(ny(m + gtr_oct, dur * 0.7, gtr * vv, pluck=0.16,
                                ring=min(1.4, beats * beat)), tt, 1.0, -sp)
        # 지속음(sus4 → 3음) 처리: 지정된 인덱스에서 4도를 먼저, 3도를 뒤에
        t += beats * beat
    return t, prev, ts


def lay_bass(prog, t0, beat, scale, *, lo=28, hi=53, gain=1.0, density=2.0,
             leap_p=0.14, ring=0.5, seed=3, accent_every=4, hand=None, until=None,
             bar_every=None):
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
    # ── BL-34 ⑤ (2026-08-11) — 마디 격자를 들리게 한다 ──────────────────
    #
    # `CLAUDE.md` 6절이 이 곡의 **엔진**이라고 부르는 것은 프레이즈 9박과
    # 마디 11박(5/4↔6/4)의 어긋남이다. 그런데 세어 보니 **11박 마디가
    # 0악장에만 있고**, 있는 그 악장에서도 안 들렸다.
    #
    # 안 들린 이유가 여기 있었다 — 악센트가 `accent_every=4`, 곧 **화음 안에서
    # 4개마다 다시 센다.** 5박 화음도 6박 화음도 똑같이 0·4·8 번째에 악센트가
    # 붙으므로 **마디 경계가 아무 표시도 안 난다.** 걸음을 세는 격자가 안
    # 들리면 프레이즈가 그것과 어긋나는 것도 들릴 수 없다.
    #
    # `bar_every=2` 는 "화음 두 개가 한 마디"라는 뜻이다(5+6). 마디 첫 음을
    # 세우고 **화음 안쪽 악센트는 죽인다** — 셋 다 같은 세기면 격자가 셋이 된다.
    if bar_every:
        ci, s2 = -1, []
        for m, d, vs, acc in seq:
            if acc:
                ci += 1
                vs = 1.28 if ci % bar_every == 0 else 1.00
            else:
                vs *= 0.86
            s2.append((m, d, vs, acc))
        seq = s2
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
        elif inst == "flute":
            # 숨소리·비브라토는 `ensemble.flute` 가 갖는다. 여기서는
            # **울림만 조금 길게** — 되받는 소리이므로 꼬리가 남아야 한다
            D["wind"].put(flt(mm, dur, vv, breath=1.0, vib=0.9),
                          tt, 1.0, pan)
        elif inst == "piccolo":
            D["wind"].put(pic(mm, dur, vv, breath=1.0, vib=0.6),
                          tt, 1.0, pan)
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

# ═══════════════════ 0악장 · 안 A — 발이 눈보다 먼저 (0:00–0:50)
#
# **왜 다시 만드는가.** 기존 0악장은 피아노 독주가 주제를 그대로 제시하며
# 시작했다. 그 첫 12초가 Suno 의 지문 대조에 걸렸고(2026-08-22), 개별 해제는
# 없다는 답을 받았다 — 검출기가 「원작자가 올린 것」과 「무단 사용」을
# 구분하지 못한다는 것이 사유다. 악장 열 개를 하나씩 올려 확인한 결과
# **0악장 하나만** 막힌다(`산출물/20260821 …/Suno 저작권 지도`).
#
# **순서를 뒤집는다.** `07` 3장이 못박은 것 — "베이스는 걷는 몸이고 주제는
# 보는 눈이다." 그런데 기존 0악장은 **보고 나서 걷는다.** 여행자는 걷기
# 시작한 다음에 본다. 서사의 순서가 거꾸로였고, 지문이 그것을 드러냈다.
#
# 기존 코드의 주석이 이미 답을 갖고 있었다 —
# *"첫 음 B♭1 하나가 곡의 조성을 선포한다."* **그 한 음이 이제 곡의 첫 소리다.**
mark("0악장 안A · 베이스가 먼저 걷는다 · B♭장조", 0.0, seed=20260822)
BT = 0.60                                    # ♩=100 — 기존과 같다

# 앞에 세 마디를 덧댄다 (17박 = 10.2초). **베이스 혼자 걷는 자리다.**
# B♭ → Gm7 → B♭ 의 왕복이다. 주제 A 가 6도로 시작해 첫 화음이 B♭ 인지
# Gm 인지 애매한 것을, 베이스가 **혼자 만들었다 푸는 것을 보여준다.**
PRE0 = [("Bb", 5), ("Gm7", 6), ("Bb", 6)]
PROG0 = PRE0 + [("Bb", 5), ("Gm7", 6), ("Ebmaj7", 5), ("Bb/D", 6),
                ("Cm7", 5), ("F", 6), ("Gm7", 5), ("Ebmaj7", 6),
                ("Bb/D", 5), ("Cm7", 6), ("F", 5), ("Bb", 6)]

# BL-25 규칙 그대로 — (1) 8분음표로 멈추지 않는다 (2) B♭1~G3
# 앞 세 줄은 주제가 없으므로 규칙 (3)(주제가 오르면 베이스는 내린다)은
# 해당이 없다. 대신 **혼자 걷는 선**이라 위로 한 번 올랐다 내려온다.
BASS_PRE = [
    [34, 41, 38, 45, 41, 46, 43, 39, 43, 38],                # Bb   첫 음이 조성이다
    [43, 39, 46, 43, 50, 46, 43, 39, 41, 45, 43, 39],        # Gm7  위로 걸어 오른다
    [34, 41, 45, 41, 46, 43, 50, 46, 43, 39, 38, 34],        # Bb   돌아와 착지
]
BASS0 = BASS_PRE + [
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

T0 = 0.0
lay_bass(PROG0, T0, BT, BB_MAJ, gain=1.0, lo=34, hi=55, hand=BASS0, bar_every=2)

# 화성은 네 번째 마디부터다. **베이스가 이미 열 걸음을 걸은 뒤에 눈이 뜬다.**
T0H = T0 + BT * 17.0
mark("  화성 진입 — 이제 본다", T0H)
tend, LAST, ts0 = lay_chords(PROG0[3:], T0H, BT, 53, 65,
                             pf=0.46, strg=0.13, org=0.16, prev=None)

# 주제 A — **화성과 함께 처음 나온다.** 피아노 독주 제시가 없어졌으므로
# 이것이 곡에서 주제가 들리는 첫 순간이다. 11박 간격은 그대로 (`07` 2장).
lay_line(TH_A, T0H + BT * 1.0, BT, vel=0.70, ring=1.8, oct_=12, pan=-0.22)
lay_line(TH_A, T0H + BT * 12.0, BT, vel=0.66, ring=1.8, oct_=12, pan=-0.22)
lay_line(TH_A, T0H + BT * 23.0, BT, vel=0.72, ring=2.0, oct_=12, pan=-0.22)
# 34번 칸은 건너뛴다 — 베이스 정점 G3 구간이다 (기존 판과 같은 이유).
lay_line(TH_A, T0H + BT * 45.0, BT, vel=0.62, ring=2.2, oct_=12, pan=-0.22)

# 드럼 — 앞 세 마디(베이스 혼자)와 그다음 여섯 마디를 비우고 들어온다.
_off0 = 0
_nd0 = 0
for _i, (_sym, _nb) in enumerate(PROG0):
    _ts = T0 + BT * _off0
    if _i >= 9:
        lay_drum(lambda y, a, g, p: D["drum"].put(y, a, g, p),
                 _ts, BT, pat_promenade(_nb, _nd0),
                 gain=0.68 + 0.05 * _nd0,
                 n=_i, jitter=lambda a, v: H(a, v))
        _nd0 += 1
    _off0 += _nb



# --- 0akjang only (test harness) ---
SEND_LEAD = [(160.0, 0.15), (325.0, 1.00), (425.0, 0.70), (525.0, 0.45)]
SEND_WIND = [(0.0, 0.0), (325.0, 1.00), (425.0, 0.0)]
out = D.mix(TOTAL, reverb=0.15, sends={"lead": ("plate", SEND_LEAD),
                                       "wind": ("plate", SEND_WIND)})
piano.write_wav(OUT, out)
print("")
print(OUT + "  %.2f sec" % (len(out) / SR))
for n, tt in MARK:
    print("  %5.1fs  %s" % (tt, n))