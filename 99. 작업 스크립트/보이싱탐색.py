# -*- coding: utf-8 -*-
"""0악장 화성 보이싱 상한 탐색 (WBS 1.4.1 · B1)

`07` 11장이 "프롬나드 네 악장의 보이싱 상한을 63~65로 낮춘다"고 했다.
목소리(주제 A)가 MIDI 65~77에 앉으므로 그 자리를 비우는 것이 목적이다.

그런데 상한만 내리면 성부가 아래로 몰려 저역이 뭉친다(STAT["lowtight"]).
하한도 함께 올려야 하는지, 올린다면 얼마인지를 렌더 없이 계산으로 정한다.
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import 화성
from 화성 import voice_lead, STAT

PROG0 = [("Bb", 5), ("Gm7", 6), ("Ebmaj7", 5), ("Bb/D", 6),
         ("Cm7", 5), ("F", 6), ("Gm7", 5), ("Ebmaj7", 6),
         ("Bb/D", 5), ("Cm7", 6), ("F", 5), ("Bb", 6)]

VOICE_LO, VOICE_HI = 65, 77          # 주제 A 음역 = 목소리가 앉을 자리


def run(lo, hi):
    for k in STAT:
        STAT[k] = 0 if k != "move" else 0.0
    prev, vs = None, []
    for sym, _ in PROG0:
        v = voice_lead(sym, prev, lo, hi, 4)
        prev = v
        vs.append(v)
    n = STAT["chords"]
    return {
        "lo": lo, "hi": hi,
        "성부": min(len(v) for v in vs),
        "3성부수": sum(1 for v in vs if len(v) < 4),
        "이동": STAT["move"] / max(1, n - 1),
        "par5": STAT["par5"], "par8": STAT["par8"],
        "leap": STAT["leap"], "밀집": STAT["lowtight"],
        "최고": max(max(v) for v in vs),
        "최저": min(min(v) for v in vs),
        "침범": sum(1 for v in vs for m in v if VOICE_LO <= m <= VOICE_HI),
        "폭평균": sum(v[-1] - v[0] for v in vs) / len(vs),
        "vs": vs,
    }


CAND = [(50, 70)] + [(lo, hi) for lo in (50, 51, 52, 53, 54, 55)
                     for hi in (63, 64, 65, 66)]

print("  lo  hi | 평균이동  병행5/8  밀집  3성부 | 최저 최고  목소리침범  보이싱폭")
print("  " + "-" * 76)
rows = []
for lo, hi in CAND:
    r = run(lo, hi)
    rows.append(r)
    mark = " ←현행" if (lo, hi) == (50, 70) else ""
    print("  %2d  %2d |   %5.2f    %d / %d     %2d    %2d   |  %2d   %2d      %2d      %5.1f%s"
          % (r["lo"], r["hi"], r["이동"], r["par5"], r["par8"],
             r["밀집"], r["3성부수"], r["최저"], r["최고"], r["침범"], r["폭평균"], mark))

print()
print("목소리 자리 = MIDI %d~%d (주제 A). 「침범」은 화성 성부가 그 안에 들어간 횟수." % (VOICE_LO, VOICE_HI))
print()

# 후보 둘의 실제 보이싱을 나란히
for lo, hi in [(50, 70), (53, 65), (54, 66)]:
    r = run(lo, hi)
    print("── lo=%d hi=%d ──" % (lo, hi))
    for (sym, _), v in zip(PROG0, r["vs"]):
        print("   %-8s %s" % (sym, " ".join("%3d" % m for m in v)))
    print()
