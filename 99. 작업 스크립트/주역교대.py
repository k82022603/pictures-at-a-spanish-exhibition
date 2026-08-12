# -*- coding: utf-8 -*-
"""**주역이 도는가**를 잰다 — 프로그레시브 록 대조용 (2026-08-12).

`악장표.py` 는 악장 **전체**의 평균으로 「주인공」을 하나 찍는다. 그래서
**악장 안에서 주역이 바뀌는지는 안 보인다.** 8악장은 4마디마다 주역이 바뀌게
설계했는데(`07` 18장) 그 표에는 「주인공: 피아노, 베이스」로만 나온다.

프로그레시브 록에서 성부가 대등하다는 것은 **평균이 고르다**는 뜻이 아니라
**시간에 따라 앞에 나오는 악기가 바뀐다**는 뜻이다. 그래서 시간축으로 썬다.

재는 것
    1. 창(窓)마다 **가장 앞에 나온 악기**가 무엇인가
    2. 악장 안에서 그 악기가 **몇 번 바뀌는가**  ← 주고받기
    3. 한 악장에서 주역을 한 번이라도 맡은 악기가 **몇 종인가**
    4. 1등과 2등의 **격차** — 작을수록 대등하다
    5. 악장 안 음량의 **최대 낙차**

    python 주역교대.py            화면 출력
    python 주역교대.py --win 2.0  창 크기를 바꿔서

**스템은 페이더를 곱하기 전이다** (`악장표.py` 가 같은 함정에 빠졌던 자리 —
`05` 9.21절). `전곡화성.py` 의 GAINS 를 읽어 곱한다.
"""
import io
import os
import re
import sys

import numpy as np
from scipy.io import wavfile

import 화성

SR = 44100
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "전곡화성.py")
STEMS = os.path.join(HERE, "스템")

NAME = {"kb": "피아노", "org": "해먼드", "bass": "베이스", "str": "현악",
        "gtr": "기타", "lead": "무그", "perc": "팔마스", "drum": "드럼"}

# 악장 경계는 `CLAUDE.md` 6절이 정본이고 코드 네 곳이 공유한다.
MOV = [0, 50, 90, 105, 160, 260, 275, 325, 425, 525, 580]
TITLE = ["Promenade 제시", "마드리드", "변주 I", "세고비아", "세비야",
         "변주 II", "론다", "그라나다", "바르셀로나", "The Great Gate"]

WIN = 2.0          # 창 크기(초). 8악장 한 마디가 약 1.7~2.4초다
FLOOR = -60.0      # 이보다 작으면 「없는 것」으로 본다


def read_gains():
    src = io.open(SRC, encoding="utf-8").read()
    m = re.search(r"GAINS = (\{.*?\})", src, re.S)
    return eval(m.group(1)) if m else {}


def db(x):
    r = float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    return 20.0 * np.log10(r) if r > 1e-12 else -np.inf


def load():
    """스템을 읽어 페이더를 곱한 모노 배열로 돌려준다.

    **자료형을 먼저 본다.** `wavfile.read` 는 int16 도 float32 도 돌려주고,
    2026-08-11 에 float32 를 int16 으로 읽어 32768 로 나눠 −118 dB 를 얻었다.
    """
    gains, out = read_gains(), {}
    for k in NAME:
        p = os.path.join(STEMS, "스템-%s.wav" % k)
        if not os.path.exists(p):
            continue
        sr, a = 화성.read_wav(p)                    # 공용 함수 (`11` 문서 6절)
        if a.ndim > 1:
            a = a.mean(axis=1)
        out[k] = a * (10.0 ** (gains.get(k, 0.0) / 20.0))
    return out


def main():
    win = WIN
    if "--win" in sys.argv:
        win = float(sys.argv[sys.argv.index("--win") + 1])
    st = load()
    if not st:
        print("스템이 없다. 먼저 전곡화성.py 를 돌린다.")
        return

    print("주역이 도는가 — 창 %.1f초" % win)
    print("=" * 78)
    print("**스템에 페이더를 곱해서 읽는다.** 곱하기 전 값으로 재면 해먼드가")
    print("거의 모든 악장의 주인공으로 나온다 (`05` 9.21절).")
    print()

    rows = []
    for m in range(10):
        t0, t1 = MOV[m], MOV[m + 1]
        n = int((t1 - t0) / win)
        lead_seq, gaps = [], []
        for i in range(n):
            a = int((t0 + i * win) * SR)
            b = int((t0 + (i + 1) * win) * SR)
            vals = []
            for k, arr in st.items():
                if b <= len(arr):
                    d = db(arr[a:b])
                    if np.isfinite(d) and d > FLOOR:
                        vals.append((d, k))
            if not vals:
                lead_seq.append(None)
                continue
            vals.sort(reverse=True)
            lead_seq.append(vals[0][1])
            if len(vals) > 1:
                gaps.append(vals[0][0] - vals[1][0])

        real = [x for x in lead_seq if x]
        switches = sum(1 for i in range(1, len(real)) if real[i] != real[i - 1])
        kinds = sorted(set(real), key=lambda k: -real.count(k))
        share = (real.count(kinds[0]) / len(real) * 100.0) if real else 0.0

        # 앞줄의 두께 — 1등에서 6 dB 안에 몇 개가 같이 있는가.
        # 프로그레시브 록의 밀도는 「하나가 크다」가 아니라 「여럿이 같이 앞에
        # 있다」이다. 한 번에 여러 개가 들리고 다시 들으면 다른 것이 들리는 것.
        front = []
        for i in range(n):
            a, b = int((t0 + i * win) * SR), int((t0 + (i + 1) * win) * SR)
            ds = [db(arr[a:b]) for arr in st.values() if b <= len(arr)]
            ds = sorted([d for d in ds if np.isfinite(d) and d > FLOOR], reverse=True)
            if ds:
                front.append(sum(1 for d in ds if d >= ds[0] - 6.0))
        front_avg = float(np.mean(front)) if front else 0.0

        # 악장 안 음량 낙차 — 전체 믹스가 아니라 스템 합으로 잰다
        tot = None
        for arr in st.values():
            seg = arr[int(t0 * SR):int(t1 * SR)]
            tot = seg.copy() if tot is None else tot + seg[:len(tot)]
        wins = [db(tot[int(i * win * SR):int((i + 1) * win * SR)])
                for i in range(int((t1 - t0) / win))]
        wins = [w for w in wins if np.isfinite(w)]
        drop = (max(wins) - min(wins)) if wins else 0.0
        # 이웃한 창 사이의 가장 큰 도약 — 급격한가, 완만한가
        jump = max((abs(wins[i] - wins[i - 1]) for i in range(1, len(wins))),
                   default=0.0)

        rows.append((m, switches, len(kinds), kinds, share,
                     float(np.mean(gaps)) if gaps else 0.0, drop,
                     len(real), front_avg, jump))

        print("%d악장 · %s   (%d~%d초)" % (m, TITLE[m], t0, t1))
        print("  주역 교대   %2d회  /  창 %d개" % (switches, len(real)))
        print("  주역을 맡은 악기 %d종 — %s"
              % (len(kinds), " · ".join(NAME[k] for k in kinds)))
        print("  1등이 차지한 비율  %.0f%%   (%s)" % (share, NAME[kinds[0]]))
        print("  1등과 2등의 격차   %.1f dB" % (np.mean(gaps) if gaps else 0))
        print("  앞줄의 두께        %.1f개  (1등에서 6 dB 안)" % front_avg)
        print("  악장 안 음량 낙차  %.1f dB  · 가장 급한 도약 %.1f dB"
              % (drop, jump))
        print()

    print("=" * 78)
    print("요약 — 교대가 많고 격차가 작을수록 「성부가 대등하다」")
    print()
    print("악장 | 교대 | 주역종수 | 1등비율 | 1등2등격차 | 앞줄두께 | 낙차 | 도약 | 1등")
    print("-" * 78)
    for (m, sw, nk, kinds, sh, gp, dr, _, fr, jp) in rows:
        print("%3d  | %3d  |    %d     |  %3.0f%%   |   %4.1f dB  |  %.1f개  |%5.1f |%5.1f | %s"
              % (m, sw, nk, sh, gp, fr, dr, jp, NAME[kinds[0]]))
    print()
    tot_sw = sum(r[1] for r in rows)
    print("전곡 교대 합계 %d회 · 앞줄 평균 %.1f개"
          % (tot_sw, float(np.mean([r[8] for r in rows]))))

    # 무그(그녀)가 앞에 나온 시간 — 서사가 걸린 값이라 따로 센다
    lead_win = sum(r[7] * (r[3][0] == "lead") for r in rows)
    print()
    print("무그가 1등인 악장 수: %d" % sum(1 for r in rows if r[3][0] == "lead"))
    print("무그가 주역 목록에 든 악장: %s"
          % ", ".join("%d" % r[0] for r in rows if "lead" in r[3]))
    print()
    print("**교대가 0에 가까운 악장은 한 악기가 끝까지 앞에 있다는 뜻이다.**")
    print("프로그레시브 록에서 그것은 「반주 위의 선율」이지 「대등한 층」이 아니다.")


if __name__ == "__main__":
    main()
