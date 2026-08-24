# -*- coding: utf-8 -*-
"""**검은 실루엣을 실제 사람으로 바꾼다** — 이미지 편집 모델. WBS 2.2 (G3).

## 왜 영상이 아니라 이미지인가 (2026-08-24 방향 전환)

**Seedance 2.5 로 네 편을 뽑아 보고 바꿨다.**

| 잰 것 | 값 | 뜻 |
|---|---|---|
| 배경 보존 | SSIM 0.905 | **V2 는 통과했다** |
| **첫 프레임 vs 마지막** | **SSIM 0.9946** | **거의 안 움직였다** |
| 한 편 값 | **$2.35** | **거의 정지 화면에 그 값을 냈다** |

**둘을 알았다.**

**① 넣은 것이 틀렸다.** 납작한 검은 벡터를 넣었으니 **영상 모델은 그것을 움직일
뿐**이다. 종이 오린 것을 여자로 바꿔 주지 않는다.

**② ★ 애초에 움직일 필요가 없었다.** **사진 244장 속 사람들은 전부 정지해 있다.**
그녀만 움직이면 오히려 튄다. **V4 의 뜻은 「그녀를 놓는다」이지 「움직인다」가
아니었다.** 「AI 영상 생성」이라는 말에 끌려 내가 혼자 정한 것이었다.

## 그래서

| | 영상 (Seedance) | **이미지 (여기)** |
|---|---|---|
| 한 장에 | $3.13 | **$0.08 — 39배 싸다** |
| 움직임 | 모델이 | **Remotion 이 공짜로** (이미 켄번스를 한다) |

## 왜 실루엣을 얹은 사진을 넣나

**빈 사진에 「여자를 넣어라」고 하면 모델이 자리와 크기를 자기 마음대로 정한다.**
검은 형태를 얹어 두면 **거기가 그녀 자리라는 것이 그림 안에 박혀 있고**,
모델은 **그리기만** 하면 된다. `실루엣.py` 가 이미 여섯 장을 만들어 뒀다.

## 자기검사 — 넷. 그리고 **낸 뒤에 배경을 잰다**
"""
import argparse
import io
import json
import mimetypes
import os
import sys
import time

import numpy as np
import requests
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

모델 = "fal-ai/nano-banana-2/edit"
큐 = "https://queue.fal.run/"
저장 = "https://rest.alpha.fal.ai/storage/upload/initiate"
장당 = 0.08                       # fal 크레딧 안내 기준 ($25 → 312장)

설정 = {
    "resolution": "1K",           # 우리 사진이 1024×768 이다. 그 위는 없는 것을 지어내는 것
    "num_images": 1,
    "output_format": "png",       # 다시 손댈 것이므로 무손실
    "aspect_ratio": "auto",       # ★ 원본 비율 그대로 — **V2 와 같은 뜻**
}

# ── 그녀를 그리는 말 ───────────────────────────────────────
#
# **금지를 먼저 적는다.** 모델은 시키지 않은 것을 한다.
# **V1(얼굴 금지) · V2(배경 변경 금지)를 문장에 박았다.**
#
# 그리고 **「2005년 소형 디카 사진」**이라고 못박는다 — 그녀만 최신 카메라처럼
# 또렷하면 **오려붙인 티가 난다.**
프롬프트 = (
    "Replace ONLY the flat black silhouette shape with a photorealistic woman, "
    "keeping her in exactly the same position, the same size and the same pose. "
    "Do not enlarge her and do not move her. "
    "She is seen strictly from behind: her face is completely hidden, no facial "
    "features are visible at all. "
    "She wears a long black flamenco dress that reaches the ground. Over her "
    "shoulders she wears a DEEP CRIMSON RED embroidered shawl (manton de Manila) "
    "with a long knotted fringe - the red shawl is the single most saturated "
    "colour anywhere in the picture and must read clearly as red. Her dark hair "
    "is gathered in a low bun. Real fabric folds, real hair, soft natural drape. "
    "Render her to match the photograph she stands in: same daylight direction, "
    "same colour temperature, same softness and grain of a 2005 compact digital "
    "camera. She must look photographed, not pasted in. Add a soft contact shadow "
    "where she meets the ground. "
    "CRITICAL: every other pixel of the photograph must stay exactly as it is - "
    "the architecture, sky, ground, other people, signs and lighting must not "
    "change, move or be regenerated. Do not crop, do not re-frame, do not restyle "
    "the photograph. Do not add any other person or object."
)

# **잘라낸 칸을 보낼 때는 문장이 조금 달라진다** — 「사진」이 아니라 「이 조각」이다.
칸프롬프트 = 프롬프트.replace(
    "the photograph she stands in",
    "the surroundings she stands in").replace(
    "every other pixel of the photograph",
    "every other pixel of this crop")


def 열쇠():
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        sys.exit("`.env` 가 없다. `24` 문서 4절대로 만든다")
    for ln in io.open(p, encoding="utf-8"):
        if ln.strip().startswith("FAL_KEY"):
            k = ln.split("=", 1)[1].strip()
            if len(k) < 40 or ":" not in k:
                sys.exit("FAL_KEY 모양이 아니다")
            return k
    sys.exit("`.env` 안에 FAL_KEY 줄이 없다")


def 올린다(H, 경로):
    형 = mimetypes.guess_type(경로)[0] or "image/png"
    이름 = "".join(c if c.isalnum() or c in "._-" else "_"
                   for c in os.path.basename(경로).encode("ascii", "replace").decode())
    r = requests.post(저장, headers=H, timeout=60,
                      json={"file_name": 이름, "content_type": 형})
    r.raise_for_status()
    d = r.json()
    with io.open(경로, "rb") as f:
        requests.put(d["upload_url"], data=f.read(),
                     headers={"Content-Type": 형}, timeout=300).raise_for_status()
    return d["file_url"]


def 부른다(H, 주소, 말=None):
    """**주소를 손으로 조립하지 않는다** — `Seedance.py` 에서 그러다 $4.70 을 버렸다.

    `큐 + 모델.split("/")[0] + "/requests/"` 로 만들었더니 `bytedance/requests/…`
    가 됐고, 맞는 것은 `bytedance/seedance-2.5/requests/…` 였다. **요청은 나갔고
    돈도 나갔는데 결과만 못 읽었다.** fal 이 응답에 정답 주소를 같이 준다.
    """
    몸 = dict(설정)
    몸["image_urls"] = [주소]
    몸["prompt"] = 말 or 프롬프트
    r = requests.post(큐 + 모델, headers=H, json=몸, timeout=60)
    r.raise_for_status()
    d0 = r.json()
    처음 = time.time()
    while True:
        s = requests.get(d0["status_url"], headers=H, timeout=30).json()
        상 = s.get("status")
        print("      %-12s %4.0f초" % (상, time.time() - 처음))
        if 상 == "COMPLETED":
            break
        if 상 in ("FAILED", "CANCELLED") or time.time() - 처음 > 600:
            return None, d0["request_id"], s
        time.sleep(6)
    return (requests.get(d0["response_url"], headers=H, timeout=60).json(),
            d0["request_id"], None)


def 얹기전(얹은길):
    """**실루엣을 얹기 전의 원본 사진**을 찾는다.

    얹은 파일 이름이 `그녀 2-47.15 PC090017.JPG` 꼴이라 **뒤 토막이 원본 이름**이다.
    **`론다`와 `바르셀로나`에 같은 이름이 열 장 있으므로**(`뼈대.py` 자검사가 잡았다)
    폴더를 훑어 **하나만 나올 때만** 쓴다.
    """
    파 = os.path.basename(얹은길).split(" ")[-1]
    소재 = os.path.join(ROOT, "2005년 12월 스페인")
    찾 = []
    for 폴, _, 들 in os.walk(소재):
        if 파 in 들:
            찾.append(os.path.join(폴, 파))
    if len(찾) != 1:
        return None
    try:
        return Image.open(찾[0])
    except Exception:
        return None


def 그녀칸(얹은길):
    """**그녀가 설 자리를 잘라 낼 칸**을 정한다.

    ## 왜 사진 전체를 안 보내나 (2026-08-24 · 첫 판의 결점)

    사진을 통째로 주면 **모델이 구도를 다시 잡는다.** 세고비아에서 실제로
    그랬다 —

    | 내가 놓은 자리 | 모델이 그린 자리 |
    |---|---|
    | 화면 왼쪽 30% · 키의 12% | **한가운데 · 키의 45%** |

    **실제 사람 키에 맞춰 놓은 것이 통째로 무너진다.** 그리고 원래 실루엣은
    **안 지우고 남겨 둔 채** 새 여자를 하나 더 그렸다.

    ## 그래서 — **그녀 칸만 잘라 보낸다**

    잘라낸 칸 안에서는 **그녀가 그림의 대부분**이므로 모델이 옮길 데가 없다.
    받아서 **원래 좌표에 되붙인다** — 자리와 크기가 **계산으로 고정된다.**

    칸은 그녀보다 **2.2배** 넓게 잡는다. 너무 딱 맞으면 모델이 발밑 그림자와
    옷자락 끝을 그릴 자리가 없다.
    """
    민 = 얹기전(얹은길)
    if 민 is None:
        return None
    a = Image.open(얹은길).convert("RGB")
    민 = 민.convert("RGB").resize(a.size)
    차 = np.abs(np.asarray(a, float) - np.asarray(민, float)).mean(axis=2) > 24
    ys, xs = np.where(차)
    if len(ys) < 50:
        return None
    cy, cx = (ys.min() + ys.max()) / 2.0, (xs.min() + xs.max()) / 2.0
    h, w = (ys.max() - ys.min()) * 2.2, (xs.max() - xs.min()) * 2.2
    변 = max(h, w, min(a.size) * 0.22)          # 너무 작으면 모델이 못 그린다
    변 = min(변, min(a.size))
    x0 = int(round(min(max(0, cx - 변 / 2), a.width - 변)))
    y0 = int(round(min(max(0, cy - 변 / 2), a.height - 변)))
    return (x0, y0, x0 + int(변), y0 + int(변))


# ── 낸 뒤에 잰다 — **V2 를 지켰는가** ──────────────────────
def 배경검사(원본길, 새길):
    """**그녀가 선 자리를 빼고** 나머지가 그대로인가.

    **전체 SSIM 으로는 못 가린다** — 그녀가 바뀌는 것은 당연하므로 값이 떨어지고,
    그게 배경 때문인지 그녀 때문인지 안 나뉜다. **검은 형태가 있던 칸을 지우고 잰다.**
    """
    # ## 개정 — **어두운 화소로 그녀를 찾지 않는다** (2026-08-24)
    #
    # 처음에는 **「어두운 화소가 그녀」**로 잡았다. **밝은 낮 사진에서는 맞았고,
    # 7악장 야경에서는 화면의 거의 전부가 어두워 칸이 사진 전체가 됐다.**
    # 남는 화소가 없으니 SSIM 이 `nan` 이 되고, 도구는 그것을 **「V2 위반」**으로
    # 찍었다 — **못 잰 것을 「위반」이라고 말한 것이다.**
    #
    # **그녀가 어디 있는지는 이미 안다.** `실루엣.py` 가 원본 사진 위에 얹었으므로
    # **원본과 얹은 것을 견주면 정확히 그 자리만 다르다.** 찾지 말고 빼면 된다.
    a = Image.open(원본길).convert("RGB")
    b = Image.open(새길).convert("RGB").resize(a.size, Image.LANCZOS)
    칸 = None
    민 = 얹기전(원본길)
    if 민 is not None:
        차 = np.abs(np.asarray(a.convert("L"), float)
                    - np.asarray(민.convert("L").resize(a.size), float)) > 24
        ys, xs = np.where(차)
        if len(ys) >= 50:
            여 = int(min(a.size) * 0.04)
            칸 = (int(max(0, xs.min() - 여)), int(max(0, ys.min() - 여)),
                  int(min(a.width, xs.max() + 여)), int(min(a.height, ys.max() + 여)))
    if 칸 is None:                       # 원본을 못 찾으면 어두운 화소로 (옛 방식)
        ys, xs = np.where(np.asarray(a.convert("L"), float) < 60)
        if len(ys) >= 50:
            여 = int(min(a.size) * 0.04)
            칸 = (int(max(0, xs.min() - 여)), int(max(0, ys.min() - 여)),
                  int(min(a.width, xs.max() + 여)), int(min(a.height, ys.max() + 여)))
    X = np.asarray(a.convert("L"), float)
    Y = np.asarray(b.convert("L"), float)
    쓸 = np.ones(X.shape, bool)
    if 칸:
        쓸[칸[1]:칸[3], 칸[0]:칸[2]] = False
    x, y = X[쓸], Y[쓸]
    # **못 잰 것을 「통과」나 「위반」으로 말하지 않는다.**
    if x.size < X.size * 0.15:
        return None, None, 칸
    mx, my, vx, vy = x.mean(), y.mean(), x.var(), y.var()
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    s = (((2 * mx * my + c1) * (2 * ((x - mx) * (y - my)).mean() + c2))
         / ((mx * mx + my * my + c1) * (vx + vy + c2)))
    return s, float(np.abs(x - y).mean()), 칸


def 자검사(일감, H):
    결과 = []
    결과.append(("배경 보존을 말에 박았는가",
                 None if "must stay exactly" in 프롬프트 else "프롬프트에 금지가 없다"))
    결과.append(("얼굴 금지를 말에 박았는가",
                 None if "no facial" in 프롬프트 else "V1 이 프롬프트에 없다"))
    없 = [p for _, p in 일감 if not os.path.exists(p)]
    결과.append(("넣을 사진이 다 있는가",
                 None if not 없 else "없는 것 — %s" % 없[0]))
    try:
        r = requests.get("https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=" + 모델,
                         headers=H, timeout=30)
        살 = r.status_code == 200 and "image_urls" in r.text
    except Exception:
        살 = False
    결과.append(("모델 경로가 살아 있는가", None if 살 else "규격서를 못 읽었다"))
    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-24s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자기검사 미달 — 아무것도 안 보냈다.**")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("사진", nargs="*")
    ap.add_argument("--진짜", action="store_true", help="없으면 안 보낸다")
    ap.add_argument("--낼곳", default=None)
    ap.add_argument("--통째로", action="store_true",
                    help="칸을 안 자르고 사진 전체를 보낸다 (옛 방식)")
    a = ap.parse_args()

    H = {"Authorization": "Key " + 열쇠()}
    얹 = os.path.join(ROOT, "산출물", "20260824 - 실루엣과 업스케일", "여섯 자리에 얹어 본 것")
    if a.사진:
        일감 = [(os.path.splitext(os.path.basename(p))[0], p) for p in a.사진]
    else:
        대 = os.path.join(얹, "지금 여섯.json")
        if not os.path.exists(대):
            sys.exit("`지금 여섯.json` 이 없다 — `실루엣.py` 를 먼저 돌린다")
        일감 = [(os.path.splitext(x["얹은것"])[0], os.path.join(얹, x["얹은것"]))
                for x in json.load(io.open(대, encoding="utf-8"))]

    자검사(일감, H)
    안 = a.낼곳 or os.path.join(ROOT, "산출물",
                                time.strftime("%Y%m%d") + " - 그녀를 사람으로")
    print("=== 보낼 것 ===")
    for 이, p in 일감:
        print("  %s" % 이)
    print("\n  값 : %d 장 x $%.2f = $%.2f" % (len(일감), 장당, len(일감) * 장당))
    if not a.진짜:
        print("\n**`--진짜` 를 안 줬으므로 여기서 멈춘다. 돈이 안 나갔다.**")
        return

    os.makedirs(안, exist_ok=True)
    대장 = []
    for n, (이, p) in enumerate(일감, 1):
        print("\n[%d/%d] %s" % (n, len(일감), 이))
        칸 = None if a.통째로 else 그녀칸(p)
        보낼 = p
        if 칸:
            원 = Image.open(p).convert("RGB")
            임 = os.path.join(안, "_보낸칸.png")
            원.crop(칸).save(임)
            보낼 = 임
            print("      칸 %dx%d 만 보낸다 (%d,%d)" %
                  (칸[2] - 칸[0], 칸[3] - 칸[1], 칸[0], 칸[1]))
        try:
            d, rid, 틀 = 부른다(H, 올린다(H, 보낼), 칸프롬프트 if 칸 else None)
        except Exception as e:
            print("      X %s" % e)
            대장.append({"이름": 이, "틀림": str(e)})
            continue
        if d is None:
            print("      X %s" % 틀)
            대장.append({"이름": 이, "요청": rid, "틀림": 틀})
            continue
        u = d["images"][0]["url"]
        낼 = os.path.join(안, 이 + ".png")
        받 = requests.get(u, timeout=600).content
        if 칸:
            # **받은 칸을 원래 좌표에 되붙인다** — 자리와 크기가 여기서 고정된다
            임2 = os.path.join(안, "_받은칸.png")
            with io.open(임2, "wb") as f:
                f.write(받)
            새칸 = Image.open(임2).convert("RGB").resize(
                (칸[2] - 칸[0], 칸[3] - 칸[1]), Image.LANCZOS)
            전 = Image.open(p).convert("RGB")
            전.paste(새칸, (칸[0], 칸[1]))
            전.save(낼)
            for t in (임, 임2):
                os.remove(t)
        else:
            with io.open(낼, "wb") as f:
                f.write(받)
        s, 바, 칸 = 배경검사(p, 낼)
        print("      -> %s" % os.path.basename(낼))
        if s is None:
            print("      배경: **못 쟀다** — 그녀 칸이 사진의 85%% 를 넘는다")
        else:
            print("      배경 SSIM %.4f · 화소당 차이 %.2f/255 %s"
                  % (s, 바, "**V2 통과**" if s >= 0.90
                     else "**X V2 위반 — 배경을 건드렸다**"))
        대장.append({"이름": 이, "요청": rid, "판": os.path.basename(낼),
                     "배경SSIM": None if s is None else round(s, 4),
                     "화소차": None if 바 is None else round(바, 2), "그녀칸": 칸})

    with io.open(os.path.join(안, "대장.json"), "w", encoding="utf-8") as f:
        json.dump(대장, f, ensure_ascii=False, indent=2)
    print("\n-> %s" % 안)


if __name__ == "__main__":
    main()
