# -*- coding: utf-8 -*-
"""7악장 빠르기를 바꾸면 무엇이 어떻게 움직이는가 — 렌더 없이 악보에서 센다.

2026-08-14. 검수자 지시로 7악장을 ♩.=60 → 72 두 단계에서 **60 고정**으로
되돌린다. 그런데 이 악장에는 마디 수에 매달린 것이 셋이다.

  ① 그녀(무그)      네 마디마다 부른다        → 마디가 줄면 부르는 횟수가 준다
  ② 플루트          두 마디에 재료 하나       → 자리가 줄어 재료가 남는다
  ③ 두 선율의 길이  8분음표 길이에 비례한다   → **느려지면 프레이즈가 길어진다**

②와 ③이 반대 방향이라 **자리는 줄어드는데 우는 시간은 늘 수 있다.** 손으로
곱하면 틀리므로(8/12 에 실제로 틀렸다) 악보에서 직접 센다.

렌더가 필요 없다 — `전곡화성.py` 에서 표만 뽑아 쓴다. 3초면 끝난다.

    python 7악장타이밍.py
"""
import re
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "전곡화성.py"), encoding="utf-8").read()

NS = {}
for pat in (r"^WPHR_J = \{.*?^\}", r"^WORDER = \(.*?\.split\(\)", r"^TH_B = \[.*?\]"):
    m = re.search(pat, SRC, re.S | re.M)
    if m:
        exec(m.group(0), NS)

WPHR_J = NS["WPHR_J"]
WORDER = NS["WORDER"]
# 주제 B — `CLAUDE.md` 6절이 정본. 여기서는 길이만 쓴다
TH_B = NS.get("TH_B") or [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5),
                          (77, 1.0), (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 1.0)]

MOOG_UNITS = sum(b for _, b in TH_B) * 0.62 * 2   # ×0.62 세기 아닌 길이 배율, 단위는 BT×2
NPROG = 16                                        # PROG7 화음 개수 = 한 바퀴 마디 수


def bars(tempos):
    """(시작초, 8분음표 길이) 를 마디마다. `전곡화성.py` 의 루프와 같은 셈이다."""
    out = []
    for s0, s1, dq in tempos:
        bt = 60.0 / (3 * dq)                      # ♩.(부점4분) = 8분음표 셋
        t = s0
        i = 0
        while t < s1 - 1e-9:
            out.append((t, bt, i % NPROG))        # i%16 = PROG7 안의 자리 → 무그 판정에 쓴다
            t += 6 * bt
            i += 1
    return out


def lay(tempos, name):
    bs = bars(tempos)
    flute, moog = [], []
    for wb, (t, bt, i) in enumerate(bs):
        if wb % 2 == 0 and wb // 2 < len(WORDER):
            k = WORDER[wb // 2]
            flute.append((t, k, sum(b for _, b in WPHR_J[k]) * bt, 12 * bt))
        if i % 4 == 0:
            moog.append((t, MOOG_UNITS * bt, 8 * bt))
    return name, bs, flute, moog


def show(r):
    name, bs, fl, mg = r
    ft = sum(d for _, _, d, _ in fl)
    mt = sum(d for _, d, _ in mg)
    print(f"\n━━ {name}")
    print(f"  마디            {len(bs)}개 · {bs[0][1]*6:.3f}초 → {bs[-1][1]*6:.3f}초")
    print(f"  그녀(무그)      {len(mg)}번 · 한 번에 {mt/len(mg):.2f}초 · 합 {mt:.1f}초 "
          f"({mt:.0f}%) · 간격 {mg[1][0]-mg[0][0]:.1f}→{mg[-1][0]-mg[-2][0]:.1f}초")
    print(f"  플루트          {len(fl)}번 · 한 번에 {ft/len(fl):.2f}초 · 합 {ft:.1f}초 "
          f"({ft:.0f}%) · 쉬는 칸 {sum(s-d for _,_,d,s in fl)/len(fl):.2f}초")
    print(f"  플루트 : 그녀   {ft/mt:.2f} : 1   (우는 시간 비)")
    print(f"  가장 빠른 음    {bs[-1][1]:.3f}초")
    print(f"  쓴 재료         {''.join(k for _, k, _, _ in fl)}")
    if len(fl) < len(WORDER):
        print(f"  ※ 남는 재료     {''.join(WORDER[len(fl):])} ({len(WORDER)-len(fl)}개가 자리를 못 받는다)")
    return ft, mt


A = lay([(325.0, 375.0, 60), (375.0, 425.0, 72)], "지금 — ♩.=60 → 72 (v4.21 채택판)")
B = lay([(325.0, 425.0, 60)], "바꾼 뒤 — ♩.=60 고정")

print("7악장 그라나다 · 325.0~425.0초 (100초) · 6/8")
fa, ma = show(A)
fb, mb = show(B)

print("\n━━ 무엇이 어느 쪽으로 움직이는가")
print(f"  플루트 우는 시간   {fa:.1f}초 → {fb:.1f}초   ({fb-fa:+.1f}초)")
print(f"  그녀 우는 시간     {ma:.1f}초 → {mb:.1f}초   ({mb-ma:+.1f}초)")
print(f"  비율               {fa/ma:.2f} → {fb/mb:.2f}   ({(fb/mb)/(fa/ma)-1:+.0%})")
print("\n  자리는 줄었는데 우는 시간은 늘어난다 — 프레이즈가 길어지는 쪽이 이긴다.")
print("  **느리게 하면 플루트가 앞으로 나온다.** 8/13 에 검수자가 물린 것이"
      "\n  「플루트가 메인이 되어버렸네」였으므로 이 방향은 되돌아가는 쪽이다.")
