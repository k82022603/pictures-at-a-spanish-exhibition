# -*- coding: utf-8 -*-
"""**그녀가 물방울처럼 맺혔다 사라진다** — 생성 없이, 사진 두 장으로.

## 무엇을 하나

**같은 사진 두 장**을 겹친다 — **그녀가 없는 원본**과 **그녀가 있는 판**.
위 장을 시간에 따라 지웠다 되살리면 **그녀가 맺혔다 사라진다.**

**AI 가 아니다. 계산이다. 돈이 안 든다.**

## 왜 이것이 맞나 — 셋

**① 서사가 그렇게 되어 있다.** `03` 이 그녀를 **상상 속 인물**로 설계했고
*"등장하는 샷은 전체의 20% 이하로 제한한다. 흔해지면 힘이 없다"*고 적었다.
**맺혔다 사라지는 것은 그 설계를 화면으로 옮긴 것이다.**

**② ★ 이음매를 덮는다.** 생성된 인물을 6초 동안 가만히 세워 두면 **오려붙인 티를
볼 시간이 생긴다.** 나타나고 사라지면 **볼 시간이 없다.**

**③ 영상 생성으로는 이걸 못 한다.** Seedance 가 낸 5초 클립은 **원본과 견줄 짝이
없다** — 첫 프레임부터 그녀가 있다. **사라지게 하려면 「그녀 없는 판」이 필요하고,
그것은 원본 사진이다.**

## 어떻게 사라지나 — **물방울**

**투명도를 통째로 내리면 유령이 된다.** 그것 말고 **얼룩덜룩한 무늬**를 하나 깔고,
**그 무늬의 낮은 데부터 지운다.** 물방울이 맺히듯 점점이 나타나고, 마르듯 점점이
사라진다.

| 때 | 무슨 일 |
|---|---|
| 0 ~ 28% | **맺힌다** — 점점이 나타나며 흐림이 걷힌다 |
| 28 ~ 72% | **머문다** |
| 72 ~ 100% | **마른다** — 점점이 사라지며 살짝 떠오른다 |

## 자기검사 — **여섯**
"""
import argparse
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FPS = 30
맺힘, 마름 = 0.28, 0.72        # 언제까지 맺히고 언제부터 마르나
번짐 = 0.22                    # 물방울 가장자리의 부드러움
떠오름 = 10                    # 사라질 때 몇 픽셀 떠오르나
흐림 = 9.0                     # 맺히기 전 얼마나 흐린가


def 물방울무늬(폭, 높이, 씨앗=20051212):
    """**얼룩덜룩한 무늬 하나.** 낮은 데부터 지우면 물방울처럼 보인다.

    **씨앗을 박는다** — 씨앗 없는 난수를 쓰면 구울 때마다 달라져
    「어제 것과 뭐가 달라졌나」를 못 가린다(BL-30 과 같은 이유).
    """
    rng = np.random.default_rng(씨앗)
    작 = rng.random((max(2, 높이 // 18), max(2, 폭 // 18)))
    n = np.asarray(Image.fromarray((작 * 255).astype(np.uint8))
                   .resize((폭, 높이), Image.BICUBIC)
                   .filter(ImageFilter.GaussianBlur(폭 / 90.0)), float) / 255.0
    n -= n.min()
    return n / max(1e-6, n.max())


def 알파(t):
    """때에 따라 얼마나 나타나 있나 — 0 은 없음, 1 은 온전히."""
    if t < 맺힘:
        return t / 맺힘
    if t < 마름:
        return 1.0
    return 1.0 - (t - 마름) / (1.0 - 마름)


def 다른자리(원본, 그녀):
    """**두 장이 실제로 다른 곳** — 곧 그녀가 있는 자리.

    ## 왜 필요한가 (2026-08-24 · 첫 판의 결점)

    처음에는 **무늬를 화면 전체에 깔았다.** 그랬더니 **맺히는 동안 화면 전체가
    흐려졌다** — 흐린 「그녀판」이 배경 자리에도 조금씩 섞였기 때문이다.
    **그녀만 흐려야 하는데 알함브라 벽이 같이 흐렸다.**

    **두 장이 같은 곳은 아예 안 건드리면 된다.** 거기는 원본이 그대로 지나간다.
    """
    A = np.asarray(원본, float)
    B = np.asarray(그녀, float)
    다 = (np.abs(A - B).mean(axis=2) > 10).astype(float)
    # 흐림이 그녀 바깥으로 번지므로 자리를 조금 넓혀 준다
    d = Image.fromarray((다 * 255).astype(np.uint8))
    d = d.filter(ImageFilter.MaxFilter(9)).filter(
        ImageFilter.GaussianBlur(원본.width / 110.0))
    return np.clip(np.asarray(d, float) / 255.0 * 1.6, 0, 1)


def 한장(원본, 그녀, 무늬, t, 자리=None):
    a = 알파(t)
    # **무늬의 낮은 데부터 나타난다.** 가장자리를 번짐만큼 부드럽게
    m = np.clip((a * (1 + 번짐) - 무늬) / 번짐, 0, 1)
    if 자리 is not None:
        m = m * 자리                 # ★ **그녀가 있는 자리 밖은 절대 안 건드린다**
    위 = 그녀
    if a < 0.999:
        # 맺히기 전·마른 뒤에는 **흐리고 살짝 떠 있다**
        ㅎ = 흐림 * (1 - a)
        위 = 위.filter(ImageFilter.GaussianBlur(ㅎ)) if ㅎ > 0.3 else 위
        if t >= 마름:
            떠 = int(떠오름 * (1 - a))
            위 = Image.fromarray(np.roll(np.asarray(위), -떠, axis=0))
    A = np.asarray(원본, float)
    B = np.asarray(위, float)
    M = m[:, :, None]
    return Image.fromarray((A * (1 - M) + B * M).astype(np.uint8))


def 자검사(원본, 그녀, 무늬, 자리):
    결과 = []
    결과.append(("두 장 크기가 같은가",
                 None if 원본.size == 그녀.size
                 else "%s vs %s" % (원본.size, 그녀.size)))
    # **t=0 에서 원본과 같아야 한다** — 아니면 「없다가 나타난다」가 아니다
    처음 = np.asarray(한장(원본, 그녀, 무늬, 0.0, 자리), float)
    결과.append(("처음에 그녀가 없는가",
                 None if np.abs(처음 - np.asarray(원본, float)).mean() < 0.5
                 else "차이 %.2f/255" % np.abs(처음 - np.asarray(원본, float)).mean()))
    # **t=0.5 에서 그녀가 온전해야 한다**
    가운 = np.asarray(한장(원본, 그녀, 무늬, 0.5, 자리), float)
    결과.append(("가운데서 그녀가 온전한가",
                 None if np.abs(가운 - np.asarray(그녀, float)).mean() < 0.5
                 else "차이 %.2f/255" % np.abs(가운 - np.asarray(그녀, float)).mean()))
    끝 = np.asarray(한장(원본, 그녀, 무늬, 1.0, 자리), float)
    결과.append(("끝에 그녀가 사라지는가",
                 None if np.abs(끝 - np.asarray(원본, float)).mean() < 0.5
                 else "차이 %.2f/255" % np.abs(끝 - np.asarray(원본, float)).mean()))
    # ── ★ **맺히는 동안 배경이 흔들리지 않는가** (2026-08-24 신설) ──
    #
    # **첫 판이 이 검사를 통과 못 했을 것이다.** 화면 전체가 흐려졌는데
    # 앞의 넷은 **시작·가운데·끝만** 보므로 **중간을 아무도 안 봤다.**
    # **끝점만 재는 검사는 도중에 무슨 일이 나든 통과한다.**
    #
    # ## 개정 — **처음에 이 검사가 틀려 있었다** (같은 날)
    #
    # 처음에는 **「자리 값이 0.02 미만인 곳」**을 배경으로 보고 **한 화소도 안
    # 움직여야 한다**고 했다. **그런데 자리의 가장자리는 일부러 부드럽게 깎아 뒀다** —
    # 안 그러면 그녀 둘레에 **오려낸 테두리**가 보인다. 그 깃털 자리에서
    # **2/255 가 움직이는 것은 고장이 아니라 설계다.**
    #
    # **검사가 재야 할 것은 「한 화소도 안 움직였나」가 아니라
    # 「손대는 자리가 그녀에 갇혀 있나」다.** 그래서 둘로 나눴다.
    #
    # **문턱을 느슨하게 해서 통과시키지 않았다** — 재는 대상을 바꿨다.
    결과.append(("손대는 자리가 화면의 20%% 이내인가",
                 None if float((자리 > 0.01).mean()) <= 0.20
                 else "화면의 %.1f%% — `03` 3.7절이 20%% 이하로 못박았다"
                      % (float((자리 > 0.01).mean()) * 100)))

    밖 = 자리 <= 0.0            # **손댈 뜻이 아예 없는 자리**
    최 = 0.0
    for t in (0.08, 0.15, 0.22, 0.80, 0.90, 0.96):
        f = np.asarray(한장(원본, 그녀, 무늬, t, 자리), float)
        최 = max(최, float(np.abs(f - np.asarray(원본, float)).mean(axis=2)[밖].max()))
    결과.append(("그 밖에서는 한 화소도 안 움직이는가",
                 None if 최 < 0.51 else "가장 크게 바뀐 화소 %.1f/255" % 최))

    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-24s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자기검사 미달 — 안 만들었다.**")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("그녀판", help="그녀가 있는 판 (png)")
    ap.add_argument("--원본", default=None, help="안 주면 파일 이름에서 찾는다")
    ap.add_argument("--길이", type=float, default=5.0)
    ap.add_argument("--낼곳", default=None)
    a = ap.parse_args()

    그녀 = Image.open(a.그녀판).convert("RGB")
    if a.원본:
        원 = a.원본
    else:
        파 = os.path.splitext(os.path.basename(a.그녀판))[0].split(" ")[-1]
        찾 = [os.path.join(p, f) for p, _, fs in os.walk(os.path.join(ROOT, "2005년 12월 스페인"))
              for f in fs if os.path.splitext(f)[0] == os.path.splitext(파)[0]]
        if len(찾) != 1:
            sys.exit("원본을 하나로 못 좁혔다 (%d 개) — `--원본` 으로 준다" % len(찾))
        원 = 찾[0]
    원본 = Image.open(원).convert("RGB")
    그녀 = 그녀.resize(원본.size, Image.LANCZOS)     # **원본 크기가 기준이다**
    print("  원본  : %s  %s" % (os.path.basename(원), 원본.size))
    print("  그녀판: %s\n" % os.path.basename(a.그녀판))

    무늬 = 물방울무늬(원본.width, 원본.height)
    자리 = 다른자리(원본, 그녀)
    print("  그녀가 차지한 자리 : 화면의 %.1f%%\n" % (float((자리 > 0.5).mean()) * 100))
    자검사(원본, 그녀, 무늬, 자리)

    안 = a.낼곳 or os.path.join(ROOT, "산출물", "20260824 - 그녀를 사람으로", "맺혔다 사라진다")
    os.makedirs(안, exist_ok=True)
    칸 = os.path.join(안, "_프레임")
    os.makedirs(칸, exist_ok=True)
    n = int(a.길이 * FPS)
    for i in range(n):
        한장(원본, 그녀, 무늬, i / (n - 1.0), 자리).save(
            os.path.join(칸, "%04d.png" % i))
    이름 = os.path.splitext(os.path.basename(a.그녀판))[0] + " - 맺혔다 사라진다.mp4"
    낼 = os.path.join(안, 이름)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                    "-i", os.path.join(칸, "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-color_range", "tv",
                    "-colorspace", "bt709", "-movflags", "+faststart", 낼],
                   check=True)
    for f in os.listdir(칸):
        os.remove(os.path.join(칸, f))
    os.rmdir(칸)
    print("-> %s  (%.1f MB)" % (낼, os.path.getsize(낼) / 1e6))
    print("\n  **AI 를 안 썼다. 값 $0.**")


if __name__ == "__main__":
    main()
