# -*- coding: utf-8 -*-
"""내려둔 스템으로 믹스만 다시 한다 (BL-29 단계 3).

`전곡화성.py`가 3분 넘게 걸리는 것은 **소리를 계산하기 때문**이다. 페이더 하나를
바꾸자고 그것을 매번 다시 돌 이유는 없다. 스템이 디스크에 있으면 이 스크립트가
몇 초 만에 새 믹스를 낸다 — 믹스를 세 번 시도하고 끝내던 것을 스무 번 할 수 있다.

    python 전곡화성.py          # 렌더 → 스템/ 에 저장 (한 번)
    python 믹스.py              # 현행 설정 그대로. 전곡화성.py 출력과 같아야 한다
    python 믹스.py --out 시험.wav --gain org=-11 --send lead=plate:0.42

**같은 설정이면 `전곡화성.py`와 소수점 끝까지 같은 결과가 나와야 한다.**
그것이 이 스크립트의 수락 조건이다.
"""
import argparse
import os
import sys

import piano
from 화성 import Desk

STEMS = "스템"
# 전곡화성.py 와 같아야 한다. 여기 하나뿐이면 어긋날 일이 없다
# perc 는 4악장의 팔마스·카혼 — **실제로 존재하는 악기**다(V3 의 정신).
# drum 은 드럼 키트다. 둘을 한 스템에 담으면 안 되는 이유가 셋이다.
#   ① 잔향 — perc 는 어택이 생명이라 말라야 하고, 드럼은 악장마다 다를 수 있다
#   ② 페이더 — 4악장의 팔마스를 줄이면 8악장의 드럼이 함께 줄어든다
#   ③ 서사 — 4악장은 실재의 악장이다. 드럼 키트가 섞이면 그 구분이 흐려진다
# 지금은 비어 있다. 편성이 정해지기 전에 그릇만 만든다 — WBS 1.1.6 에서 채운다.
GAINS = {"kb": 6.0, "org": -13.0, "bass": 2.0, "str": 2.0,
         "gtr": 5.0, "lead": 2.0, "perc": -5.0, "drum": 2.0}
TOTAL = 580.0


def parse_send(s):
    """lead=plate:0.42                       곡 전체에 같은 양
       lead=plate:160@0.15,325@1.0,425@0.7   악장마다 다른 양 (BL-32)

    `초@값` 을 쉼표로 잇는다. 값은 다음 지점까지 유지되고 경계에서 2초에 걸쳐
    선형으로 건너간다. 악장 시작 시각은 `CLAUDE.md` 6절 타임라인이 정본이다 —
    0 · 50 · 90 · 105 · 160 · 260 · 275 · 325 · 425 · 525 · 580.
    """
    name, rest = s.split("=", 1)
    kind, amt = rest.split(":", 1)
    if kind not in ("room", "plate"):
        raise ValueError("잔향 종류는 room 또는 plate — 받은 것 %r" % kind)
    if "@" not in amt:
        return name, (kind, float(amt))
    pts = []
    for seg in amt.split(","):
        t, v = seg.split("@", 1)
        pts.append((float(t), float(v)))
    return name, (kind, pts)


def show_send(kind, amt):
    if isinstance(amt, list):
        return "%s %s" % (kind, " ".join("%g초→%g" % p for p in amt))
    return "%s %g" % (kind, amt)


ap = argparse.ArgumentParser(description="스템으로 믹스만 다시 한다")
ap.add_argument("--stems", default=STEMS, help="스템 폴더 (기본 %s)" % STEMS)
ap.add_argument("--out", default="전곡화성.wav", help="출력 wav")
ap.add_argument("--reverb", type=float, default=0.15, help="전역 홀 양")
ap.add_argument("--gain", action="append", default=[],
                metavar="스템=dB", help="페이더 덮어쓰기. 예 org=-11")
ap.add_argument("--send", action="append", default=[],
                metavar="스템=종류:양", help="성부별 잔향. 예 lead=plate:0.42")
a = ap.parse_args()

if not os.path.isdir(a.stems):
    sys.exit("스템 폴더가 없다: %s\n먼저 `python 전곡화성.py` 를 돌려 스템을 만든다." % a.stems)

gains = dict(g.split("=", 1) for g in a.gain)
gains = {k: float(v) for k, v in gains.items()}
sends = dict(parse_send(s) for s in a.send)
for n in list(gains) + list(sends):
    if n not in GAINS:
        sys.exit("모르는 스템 이름: %r  (있는 것: %s)" % (n, ", ".join(GAINS)))

print("스템 %s" % a.stems)
if gains:
    print("페이더 덮어쓰기  " + "  ".join("%s %+.1f dB" % kv for kv in gains.items()))
if sends:
    print("성부별 잔향      " + "  ".join("%s → %s" % (n, show_send(k, v))
                                          for n, (k, v) in sends.items()))

D = Desk.load_stems(a.stems, list(GAINS), GAINS)
out = D.mix(TOTAL, gains=gains or None, reverb=a.reverb, sends=sends or None)
piano.write_wav(a.out, out)

import numpy as np
print("믹스 %.1f초  peak %.3f  rms %.4f  →  %s"
      % (len(out) / 44100, np.abs(out).max(), np.sqrt((out ** 2).mean()), a.out))
