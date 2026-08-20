# -*- coding: utf-8 -*-
"""**Suno 가 뽑아 준 것을 잰다** — 우리 가락을 부르는가.

2026-08-20. 8-19 에는 이 표를 손으로 만들었고, 그때 쓴 자가 틀려 있었다
(`97. 회고` **T-12** — 440 Hz 를 146 Hz 로 읽었다). **이제 자는 `음높이.py`
한 곳이고, 이 도구는 돌리기 전에 그 자를 스스로 검사한다.**

무엇을 재나 — **「우리 가락을 부르는가」 하나**다.

  | 재는 것 | 우리 선율 |
  |---|---|
  | 가운데 음 | **C5** |
  | **최저음(F4) 위 비율** | **100%** |
  | C5 위 비율 | **36%** |

**8-19 판은 최저음 위가 30.6% 였다**(다시 잰 값. `14` 11.2절이 정본).
**50% 를 넘으면 길이 열린 것**이고, 20% 아래면 두 번째 경로도 막힌 것이다.

**길이도 함께 본다.** 올린 것이 55.00초인데 나온 것이 다르면 **Suno 가 시간축을
다시 짠 것**이고, 그러면 9악장의 8:47·8:58·9:09·9:16 에 그대로 못 붙인다.

    python Suno재기.py "…/Suno-20260820/분리/htdemucs"
    python Suno재기.py "…/htdemucs" --올린길이 55.0
"""
import glob
import os
import sys

import numpy as np

import 화성
import 음높이

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
LO, MID = 65, 72                                 # F4 · C5 — 우리 선율 기준
우리 = ("C5", 100.0, 36.0)                        # `14` 10.2절이 정본
어제 = ("C4", 30.6, 11.5)                         # `14` 11.2절 (다시 잰 값)


def 판정(f4위):
    if f4위 >= 90:
        return "★ 우리 가락"
    if f4위 >= 50:
        return "길이 열렸다"
    if f4위 >= 20:
        return "어제와 비슷"
    return "더 나빠졌다"


def main():
    인자 = [a for a in sys.argv[1:] if not a.startswith("--")]
    올린 = 55.0
    if "--올린길이" in sys.argv:
        올린 = float(sys.argv[sys.argv.index("--올린길이") + 1])
        인자 = [a for a in 인자 if a != str(올린)]
    if not 인자:
        raise SystemExit('쓰는 법:  python Suno재기.py "…/분리/htdemucs"')
    뿌리 = 인자[0]

    print("Suno 가 우리 가락을 부르는가\n")

    # **자부터 검사한다.** 넉 달 동안 아무도 안 했다가 T-12 가 났다
    print("=== 0. 자가 맞는가 ===")
    if not 음높이.자검사(verbose=False):
        raise SystemExit("  **자가 틀렸다.** 재지 않는다")
    print("  아는 음 여덟이 전부 10센트 안 — 통과\n")

    길 = sorted(glob.glob(os.path.join(뿌리, "*", "vocals.wav")))
    if not 길:
        raise SystemExit("목소리 파일을 못 찾았다 — %s/*/vocals.wav" % 뿌리)

    print("=== 1. 길이 — 시간축을 다시 짰는가 ===")
    print("  올린 것 %.2f초\n" % 올린)
    잰것 = []
    for p in 길:
        이름 = os.path.basename(os.path.dirname(p))
        sr, x = 화성.read_wav(p)
        if sr != SR:
            raise SystemExit("%s 가 %d Hz 다" % (이름, sr))
        x = x.mean(1) if x.ndim > 1 else x
        초 = len(x) / SR
        print("  %-16s %6.2f초   %+5.2f초" % (이름[-14:], 초, 초 - 올린))
        잰것.append((이름, x))

    print("\n=== 2. 어느 높이로 부르는가 ===")
    print("  %-16s %-6s %10s %10s   %s"
          % ("", "가운데", "최저음 위", "C5 위", "판정"))
    print("  %-16s %-6s %9.1f%% %9.1f%%   %s"
          % ("★ 우리 선율", 우리[0], 우리[1], 우리[2], "—"))
    print("  %-16s %-6s %9.1f%% %9.1f%%   %s"
          % ("어제 (8-19)", 어제[0], 어제[1], 어제[2], "기각됐다"))
    print("  " + "─" * 62)

    결과 = []
    for 이름, x in 잰것:
        r = 음높이.요약(음높이.재기(x), 최저=LO, 가운데=MID)
        if not r:
            print("  %-16s 노래하는 구간을 못 찾았다" % 이름[-14:])
            continue
        print("  %-16s %-6s %9.1f%% %9.1f%%   %s"
              % (이름[-14:], 음높이.이름(r[0]), r[1], r[2], 판정(r[1])))
        결과.append((이름, r))

    if not 결과:
        return
    best = max(결과, key=lambda t: t[1][1])
    print("\n=== 3. 판정 ===")
    print("  가장 나은 것 — %s  (최저음 위 %.1f%%)" % (best[0][-14:], best[1][1]))
    f4 = best[1][1]
    if f4 >= 50:
        print("  **어제 30.6%% 에서 올라갔다. 선율을 들려준 것이 통했다.**")
    elif f4 >= 20:
        print("  **어제와 비슷하다.** 선율을 앞에 놓아도 안 따라온다는 뜻이고,")
        print("  **「Suno 로는 가락을 못 준다」가 두 경로에서 확인된 것**이 된다.")
    else:
        print("  **어제보다 나쁘다.**")
    print("\n  어느 쪽이든 **가락은 `보컬가락.py` 가 입힌다.** 여기서 고르는 것은")
    print("  **어느 목소리에 입힐 것인가**이다.")


if __name__ == "__main__":
    main()
