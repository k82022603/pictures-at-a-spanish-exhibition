# -*- coding: utf-8 -*-
"""**우리 사진 한 장을 움직이게 한다** — Seedance 2.5 image-to-video.

## 언제 쓰나

**「없던 것을 그려 넣는」 것이 아니라 「사진에 이미 있는 것을 움직이게」 할 때.**
`에필로그.py` 가 한 장에만 쓰던 것을 아무 사진에나 쓸 수 있게 뺀 것이다.

**첫 손님은 7:34 의 고양이다** — `P1010158.JPG`, 알함브라 타일 앞의 삼색 고양이.
**우리가 2005년에 찍은 실제 고양이**이므로 V2(배경 변경 금지)와 안 부딪힌다.

## 값

**720p 실측 초당 $0.469** ($9.38 / 4편 / 5초). 5초 = **$2.35**.

## 지켜야 할 것 넷 (2026-08-24 실측)

| # | |
|---|---|
| 1 | 모델 경로는 **`bytedance/seedance-2.5/…`** — `fal-ai/` 접두사 없음 |
| 2 | **`generate_audio` 기본값이 켜짐**이다. 반드시 끈다 |
| 3 | **주소를 손으로 조립하지 않는다** — fal 이 `status_url` 을 준다 |
| 4 | **사람 얼굴이 있으면 거부된다**(content_policy_violation). 과금은 없다 |

## 프롬프트 규칙 — **할 일을 먼저, 금지를 뒤에**

「restrained motion only」를 앞에 박았더니 **아무것도 안 움직였다**
(첫 프레임 vs 마지막 SSIM 0.9946).

## 자기검사 — 넷
"""
import argparse
import io
import json
import mimetypes
import os
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

모델 = "bytedance/seedance-2.5/image-to-video"
큐 = "https://queue.fal.run/"
저장 = "https://rest.alpha.fal.ai/storage/upload/initiate"
초당 = 0.469

# ── 미리 적어 둔 말 ───────────────────────────────────────
말들 = {
    "고양이": (
        "The calico cat sitting on the marble floor comes alive: she lifts her "
        "head and looks slowly around, blinks, licks one front paw and grooms "
        "her chest, shifts her weight and flicks her tail a few times, then "
        "settles again. Natural, unhurried cat behaviour. "
        "The camera is locked off and completely still. "
        "Everything else is motionless: the glazed tile wall, the green tile "
        "band, the marble floor and the shadows do not move or change. "
        "No camera movement, no zoom, no pan. No people or objects enter. "
        "No text, no titles, no captions."
    ),
}


def 열쇠():
    for ln in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if ln.strip().startswith("FAL_KEY"):
            return ln.split("=", 1)[1].strip()
    sys.exit("`.env` 안에 FAL_KEY 줄이 없다")


def 올린다(H, 경로):
    형 = mimetypes.guess_type(경로)[0] or "image/jpeg"
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


def 자검사(사진, 말, H):
    결과 = []
    결과.append(("사진이 있는가", None if os.path.exists(사진) else 사진))
    결과.append(("할 일이 금지보다 앞에 있는가",
                 None if "comes alive" in 말 and 말.index("comes alive") < 말.index("No camera")
                 else "금지가 앞에 있다 — 그러면 아무것도 안 움직인다"))
    결과.append(("카메라 고정을 박았는가",
                 None if "locked off" in 말 else "카메라가 움직일 수 있다"))
    try:
        r = requests.get("https://fal.ai/api/openapi/queue/openapi.json?endpoint_id="
                         + 모델, headers=H, timeout=30)
        살 = r.status_code == 200
    except Exception:
        살 = False
    결과.append(("모델 경로가 살아 있는가", None if 살 else "규격서를 못 읽었다"))
    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-28s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자기검사 미달 — 아무것도 안 보냈다.**")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("사진")
    ap.add_argument("--말", default="고양이", help="말들의 열쇠 또는 영어 문장")
    ap.add_argument("--초", type=int, default=5)
    ap.add_argument("--낼곳", default=None)
    ap.add_argument("--진짜", action="store_true")
    a = ap.parse_args()

    말 = 말들.get(a.말, a.말)
    H = {"Authorization": "Key " + 열쇠()}
    안 = a.낼곳 or os.path.join(ROOT, "산출물",
                                time.strftime("%Y%m%d") + " - 사진을 움직인다")
    자검사(a.사진, 말, H)

    값 = a.초 * 초당
    print("  %s · %d초 · 720p · 소리 끔  ·  약 $%.2f"
          % (os.path.basename(a.사진), a.초, 값))
    if not a.진짜:
        print("\n**`--진짜` 를 안 줬으므로 멈춘다. 돈이 안 나갔다.**")
        return

    os.makedirs(안, exist_ok=True)
    r = requests.post(큐 + 모델, headers=H, timeout=60, json={
        "image_url": 올린다(H, a.사진), "prompt": 말,
        "resolution": "720p", "duration": str(a.초),
        "generate_audio": False, "aspect_ratio": "auto"})
    r.raise_for_status()
    d0 = r.json()
    print("  요청 %s" % d0["request_id"])
    처음 = time.time()
    while True:
        s = requests.get(d0["status_url"], headers=H, timeout=30).json()
        print("      %-12s %4.0f초" % (s.get("status"), time.time() - 처음))
        if s.get("status") == "COMPLETED":
            break
        if s.get("status") in ("FAILED", "CANCELLED") or time.time() - 처음 > 1800:
            io.open(os.path.join(안, "받은 것.json"), "w", encoding="utf-8").write(
                json.dumps(s, ensure_ascii=False, indent=2))
            sys.exit("X 실패 — `받은 것.json` 에 전부 있다")
        time.sleep(8)
    d = requests.get(d0["response_url"], headers=H, timeout=60).json()
    # **받은 것을 먼저 남긴다.** 칸 이름을 가정하다 결과를 통째로 잃은 적이 있다
    io.open(os.path.join(안, "받은 것.json"), "w", encoding="utf-8").write(
        json.dumps({"요청": d0["request_id"], "초": a.초, "값추정": round(값, 2),
                    "받은것": d, "말": 말}, ensure_ascii=False, indent=2))
    v = (d.get("video") or {}).get("url")
    if not v:
        sys.exit("X 영상 주소가 없다 — `받은 것.json` 을 본다. 칸: %s" % list(d.keys()))
    낼 = os.path.join(안, os.path.splitext(os.path.basename(a.사진))[0]
                      + " - %d초.mp4" % a.초)
    io.open(낼, "wb").write(requests.get(v, timeout=900).content)
    print("      -> %s  (%.1f MB)" % (os.path.basename(낼),
                                      os.path.getsize(낼) / 1e6))


if __name__ == "__main__":
    main()
