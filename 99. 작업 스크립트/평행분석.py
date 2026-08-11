# -*- coding: utf-8 -*-
"""화음 기록 두 벌을 악장별로 대조해 **평행 이동**을 센다. BL-34 ① 근거.

    python 평행분석.py "기준선 v4.2 chordlog.npy" chordlog.npy

**`STAT["par5"]`·`par8` 로는 이것을 못 잰다.** 그 지표는 *외성 간격*이
5도·8도로 유지되는 경우만 세는데, 라스게아도는 **네 성부가 전부 같은 간격으로
움직이는 것**이라 외성 간격이 무엇이든 상관이 없다.

2026-08-11 에 이것 때문에 한 번 속을 뻔했다 — 벌점을 풀고 평행을 보상해
실제로 미끄러지게 만들어 놓고도 `par5 0 / par8 0` 이 찍혔다. **지표 이름이
가리키는 것과 내가 만들려는 것이 달랐다.**
"""
import sys, io, numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MOV = [("0 프롬나드", 0, 50), ("1 마드리드", 50, 90), ("2 변주 I", 90, 105),
       ("3 세고비아", 105, 160), ("4 세비야", 160, 260), ("5 변주 II", 260, 275),
       ("6 론다", 275, 325), ("7 그라나다", 325, 425),
       ("8 바르셀로나", 425, 525), ("9 대문", 525, 580)]


def load(p):
    return [(float(t), str(s), list(v)) for t, s, v in np.load(p, allow_pickle=True)]


def movement(t):
    for nm, s, e in MOV:
        if s <= t < e:
            return nm
    return "?"


def scan(log):
    """악장별 (화음 수, 평행 전환 수, 최저음, 평균 총이동량)"""
    acc = {}
    for (t0, s0, v0), (t1, s1, v1) in zip(log, log[1:]):
        nm = movement(t0)
        a = acc.setdefault(nm, [0, 0, 999, 0.0, 0])
        a[0] += 1
        a[2] = min(a[2], min(v0))
        if len(v0) == len(v1) and len(v0) >= 3:
            # **윗 성부 평행**을 센다 — 최저 성부는 빼고.
            #
            # 처음엔 네 성부 전부가 같은 간격일 때만 셌고, 그 판으로 재니
            # **74건이 0건으로 찍혔다.** 설계가 「윗줄 평행」으로 바뀌었는데
            # 도구가 옛 정의를 들고 있었던 것이다 (2026-08-11).
            #
            # 오늘 아침에 「이 이름이 이 값을 가리키는 게 맞나」를 규칙으로
            # 적어놓고 내 도구가 그대로 밟았다. `par5` 에 이어 두 번째다.
            d = v1[1] - v0[1]
            if d != 0 and all(y - x == d for x, y in zip(v0[1:], v1[1:])):
                a[1] += 1
                a[4] += 1
            a[3] += sum(abs(y - x) for x, y in zip(v0, v1))
    return acc


def main():
    a, b = scan(load(sys.argv[1])), scan(load(sys.argv[2]))
    print("%-12s %14s %14s %12s" % ("악장", "평행 전환", "최저 화음음", "평균 이동량"))
    print("-" * 56)
    for nm, _s, _e in MOV:
        x, y = a.get(nm), b.get(nm)
        if not x or not y:
            continue
        mark = "  ★" if x[1] != y[1] else ""
        print("%-12s %6d → %-6d %6d → %-6d %5.1f → %-5.1f%s" %
              (nm, x[1], y[1], x[2], y[2],
               x[3] / max(1, x[0]), y[3] / max(1, y[0]), mark))
    print("-" * 56)
    print("%-12s %6d → %-6d" % ("합", sum(v[1] for v in a.values()),
                                sum(v[1] for v in b.values())))


if __name__ == "__main__":
    main()
