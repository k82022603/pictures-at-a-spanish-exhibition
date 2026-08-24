# -*- coding: utf-8 -*-
"""**생성된 판에서 그녀만 오려 원본에 되붙인다** — V2 를 계산으로 보장한다.

## 왜 필요한가 — 두 가지가 드러났다 (2026-08-24)

**`그녀그리기.py` 가 낸 판을 원본과 화소 단위로 견줘 보고 알았다.**

### ① **모델이 사진 전체를 다시 그린다**

| 잰 것 | 값 |
|---|---|
| 배경 SSIM | **0.9925** — 구조는 거의 같다 |
| **화소 차이 중앙값** | **6.7 / 255** — **그런데 전 화소가 조금씩 다르다** |
| 문턱 10 이상인 화소 | **화면의 36.4%** |

**「거의 같다」는 「그대로다」가 아니다.** `00` 의 **V2 는 「배경 변경 금지」**이지
「배경 거의 유지」가 아니다. **SSIM 만 봤으면 통과라고 보고했을 것이다.**

### ② **바꾸라고 했는데 하나 더 그린다**

세고비아 판에서 **원래 검은 실루엣이 왼쪽에 그대로 남고**, 모델은 **가운데에 새
여자를 크게 그렸다.** 없던 것이 추가됐으니 **이것도 V2 위반이다.**

## 그래서 — **찾지 말고 빼서 붙인다**

**원본은 우리가 갖고 있다.** 생성판에서 **가장 크게 달라진 덩어리 하나**만 오려
**손 안 댄 원본 위에 얹는다.**

| 이 방법이 한꺼번에 푸는 것 |
|---|
| **배경이 원본과 바이트 단위로 같아진다** — V2 가 증명된다 |
| **덩어리 하나만 쓰므로** 왼쪽에 남은 옛 실루엣이 **떨어져 나간다** |
| **`나타나기.py` 의 물방울이 그녀에게만 걸린다** — 두 장이 그녀 자리에서만 다르므로 |

## 자기검사 — **다섯**
"""
import argparse
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

문턱 = 40           # ① 그녀가 **어디 있는지** 찾는 문턱 (분포를 재서 골랐다)
채움문턱 = 12       # ② 찾은 칸 **안에서만** 쓰는 문턱. 어두운 치마까지 담는다
가장자리 = 2.5      # 오린 자리의 부드러움 (픽셀)
최대비율 = 0.30     # 그녀가 화면의 이보다 크면 잘못 오린 것이다


def 얹은판(생성길):
    """**실루엣을 얹은 판**을 찾는다 — `실루엣.py` 가 낸 것. **그것이 정답이다.**"""
    D = os.path.join(ROOT, "산출물", "20260824 - 실루엣과 업스케일",
                     "여섯 자리에 얹어 본 것")
    이 = os.path.splitext(os.path.basename(생성길))[0]
    for 끝 in (".JPG", ".jpg", ".png"):
        p = os.path.join(D, 이 + 끝)
        if os.path.exists(p):
            return p
    sys.exit("실루엣 얹은 판을 못 찾았다 — %s" % 이)


def 원본찾기(얹은길):
    """얹은 파일 이름 `그녀 2-47.15 PC090017.png` 의 **뒤 토막이 원본 이름**이다.

    **`론다`와 `바르셀로나`에 같은 이름이 열 장 있다**(`뼈대.py` 자검사가 잡았다).
    **하나로 안 좁혀지면 멈춘다** — 엉뚱한 도시 사진에 붙이느니 안 하는 게 낫다.
    """
    파 = os.path.splitext(os.path.basename(얹은길))[0].split(" ")[-1]
    찾 = [os.path.join(p, f)
          for p, _, fs in os.walk(os.path.join(ROOT, "2005년 12월 스페인"))
          for f in fs if os.path.splitext(f)[0] == 파]
    return 찾


def 오린다(원본, 생성, 얹은):
    """**실루엣이 있던 자리**를 조금 넓혀 그녀로 삼는다.

    ## ★ 개정 — **짐작하기를 그만둔다** (2026-08-24, 세 번째)

    앞의 두 판은 **「두 장이 얼마나 다른가」로 그녀를 짐작**했다. 문턱을 두 단계로
    나누고, 덩어리를 이어 붙이고, 작은 것을 버리고… **그때마다 새 사고가 났다.**

    | 판 | 무슨 일 |
    |---|---|
    | 1 | 검은 치마가 어두운 배경 앞이면 **구멍이 뚫려 성벽이 비쳤다** |
    | 2 | 목이 끊겨 **머리가 딴 덩어리가 되고 버려졌다** |
    | 3 | 이어붙이기를 키웠더니 **33화소짜리 잔티**가 검사를 걸리게 했다 |

    **셋 다 같은 병이다 — 아는 것을 안 쓰고 짐작했다.**

    > **`실루엣.py` 가 그녀를 어디에 얼마만 하게 그렸는지 우리가 정했다.**
    > **원본과 「실루엣 얹은 판」을 견주면 그 자리가 정확히 나온다.**

    그려진 사람은 실루엣보다 조금 **넘친다** — 머리카락, 술, 발밑 그림자.
    그래서 키의 **7%** 만큼 넓히고 가장자리를 부드럽게 깎는다.
    **덩어리를 세지 않는다. 문턱이 하나도 없다.**
    """
    검 = np.abs(np.asarray(원본, float)
                - np.asarray(얹은, float)).mean(axis=2) > 24
    ys, xs = np.where(검)
    if len(ys) < 50:
        return None, 0, 0, 0
    키 = ys.max() - ys.min()
    차 = np.abs(np.asarray(생성, float) - np.asarray(원본, float)).mean(axis=2)

    # ## ★ **짐작을 그만둔다** (2026-08-24, 마지막 판)
    #
    # 「얼마나 넓힐지」를 **재서 정하려다 세 번 틀렸다.**
    #
    # | 잰 방법 | 왜 틀렸나 |
    # |---|---|
    # | 경계에서 두 장이 얼마나 다른가 | **야경은 배경을 통째로 다시 그려** 영영 통과 못 한다 |
    # | 붉은 만톤이 자리 밖에 있는가 | **원본에 빨간 외투를 입은 아이**가 있다 (세고비아) |
    # | 〃 | **알함브라 지붕이 테라코타**다 — 붉기가 만톤과 겹친다 |
    #
    # **셋 다 「그녀에게만 있는 표시」를 찾으려던 것이고, 그런 표시는 없었다.**
    # `03` 3.7절이 이미 적어 뒀다 — *"원본 사진에 이미 있는 붉은 요소와
    # 구분되도록"*. **구분이 필요하다는 말은 곧 안 구분된다는 말이다.**
    #
    # > **그래서 재지 않는다. 실루엣 자리를 키의 15% 만큼 넉넉히 넓혀 쓴다.**
    #
    # 넉넉히 잡으면 **그녀 둘레에 다시 그려진 배경이 조금 딸려 온다.** 그 값이
    # 얼마인지는 아래 자기검사가 재서 찍는다 — **모르는 채로 넘어가지 않는다.**
    넓힘 = max(8, int(키 * 0.15))
    m = ndimage.binary_fill_holes(
        ndimage.binary_dilation(검, np.ones((넓힘 * 2 + 1, 넓힘 * 2 + 1))))
    부 = np.asarray(Image.fromarray((m * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(넓힘 * 0.45)), float) / 255.0
    return 부, float((부 > 0.5).mean()), 넓힘, 0


def 자검사(원본, 생성, 마스크, 비율, 붙임, 샌):
    결과 = []
    결과.append(("크기가 같은가",
                 None if 원본.size == 생성.size else "%s vs %s" % (원본.size, 생성.size)))
    결과.append(("그녀를 찾았는가",
                 None if 마스크 is not None else "달라진 덩어리가 없다"))
    결과.append(("그녀가 화면의 %d%% 를 안 넘는가" % int(최대비율 * 100),
                 None if 비율 <= 최대비율
                 else "화면의 %.1f%% — 잘못 오렸다" % (비율 * 100)))
    # ★ **배경이 원본과 완전히 같은가** — 이 도구의 존재 이유다
    밖 = 마스크 < 0.002 if 마스크 is not None else None
    if 밖 is not None:
        차 = np.abs(np.asarray(붙임, float) - np.asarray(원본, float)).mean(axis=2)
        결과.append(("배경이 원본과 **완전히** 같은가",
                     None if 차[밖].max() < 0.51
                     else "가장 크게 바뀐 화소 %.1f/255" % 차[밖].max()))
    # ── ★ **그녀 몸 위의 덩어리를 안 버렸는가** (2026-08-24 신설) ──
    #
    # **넷이 머리 없이 나갔는데 자기검사 넷이 전부 OK 였다.**
    # 「배경이 같은가」·「크기가 같은가」는 봤지만 **오려낸 것이 사람인지는
    # 아무도 안 봤다.** 그때 도구는 **「버린 덩어리 3 개」라고 찍고 있었고,
    # 그중 하나가 머리였다** — **세기만 하고 무엇인지는 안 봤다.**
    # ── ★ **자리 안에 그녀가 실제로 들어 있는가** ──────────
    #
    # 넉넉히 잡은 자리가 **엉뚱한 데를 가리키고 있지 않은지** 본다.
    # 그녀가 들어 있으면 그 안은 원본과 **크게** 다르다.
    if 마스크 is not None:
        안 = 마스크 > 0.5
        차 = np.abs(np.asarray(생성, float)
                    - np.asarray(원본, float)).mean(axis=2)
        가장 = float(np.percentile(차[안], 98))
        곁 = float(np.median(차[안]))
        print("     자리 안 — 가장 크게 다른 데 %.0f/255 · 가운뎃값 %.1f/255"
              % (가장, 곁))
        결과.append(("자리 안에 그녀가 들어 있는가",
                     None if 가장 > 40 else "가장 큰 차이가 %.0f/255 뿐" % 가장))

    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-30s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자기검사 미달 — 파일을 안 냈다.**")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("생성판", nargs="+")
    ap.add_argument("--낼곳", default=None)
    a = ap.parse_args()
    안 = a.낼곳 or os.path.join(ROOT, "산출물", "20260824 - 그녀를 사람으로",
                                "그녀만 오려 붙인 것")
    os.makedirs(안, exist_ok=True)
    대장 = []
    for p in a.생성판:
        print("=== %s ===" % os.path.basename(p))
        찾 = 원본찾기(p)
        if len(찾) != 1:
            print("  X 원본을 하나로 못 좁혔다 (%d 개) — 건너뛴다\n" % len(찾))
            continue
        원본 = Image.open(찾[0]).convert("RGB")
        생성 = Image.open(p).convert("RGB").resize(원본.size, Image.LANCZOS)
        얹 = Image.open(p if "오려" in p else 얹은판(p)).convert("RGB")
        마, 비율, 넓힘, 샌 = 오린다(원본, 생성, 얹.resize(원본.size))
        if 마 is None:
            print("  X 달라진 데가 없다\n")
            continue
        M = 마[:, :, None]
        붙임 = Image.fromarray(
            (np.asarray(원본, float) * (1 - M) + np.asarray(생성, float) * M
             ).astype(np.uint8))
        print("  그녀 = 화면의 %.1f%% · 실루엣을 %d 화소 넓혔다" % (비율 * 100, 넓힘))
        자검사(원본, 생성, 마, 비율, 붙임, 샌)
        낼 = os.path.join(안, os.path.basename(p))
        붙임.save(낼)
        print("  -> %s\n" % os.path.basename(낼))
        대장.append({"판": os.path.basename(낼), "원본": os.path.basename(찾[0]),
                     "그녀비율": round(비율 * 100, 2), "넓힘": 넓힘})
    with io.open(os.path.join(안, "대장.json"), "w", encoding="utf-8") as f:
        json.dump(대장, f, ensure_ascii=False, indent=2)
    print("-> %s" % 안)


if __name__ == "__main__":
    main()
