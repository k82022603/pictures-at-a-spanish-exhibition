# -*- coding: utf-8 -*-
"""**에필로그 — 문 앞에 남은 붉은 만톤.** 곡이 끝난 뒤 15초.

## 왜 이 그림인가

**우리 영상의 마지막 컷이 세고비아 성벽의 돌문**(`PC090035`)이고, 그 안은
**새까맣다.** 그리고 **9악장의 제목이 `The Great Gate`** 다. 우연히 맞았다.

**그 문 앞에 붉은 만톤만 남는다.**

`03` 4장이 1악장 그림으로 **「빈 의자 위의 붉은 숄 — 흔적만」**을 적어 뒀다.
그 사진은 실재하지 않아 못 썼는데(`03` 8장 개정), **끝에서 갚는다.**

| 이 그림이 한꺼번에 푸는 것 |
|---|
| **V1 위험이 없다** — 사람이 아예 없다. 얼굴도 일관성도 걱정할 것이 없다 |
| **움직임이 단순하다** — 술이 바람에 흔들리는 것 하나. 생성 모델이 잘하는 일 |
| **끝맺음이 그림 안에 있다** — 빛이 잦아들어 문의 어둠만 남는다. **그대로 영상 끝** |
| **서사가 닫힌다** — 그녀는 없고 흔적만 있다. `03` 이 처음부터 그렇게 설계했다 |

## 두 단계 · 값

| # | 무엇 | 도구 | 값 |
|---|---|---|---|
| 1 | 만톤을 문지방에 놓는다 | Nano Banana 2 편집 | **$0.08** |
| 2 | 15초 영상 | Seedance 2.5 720p | **약 $7.04** |

**2 를 한 번 돌리면 재시도할 잔액이 없다.** 그래서 **1 을 먼저 내고 멈춘다.**
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

바탕사진 = os.path.join(ROOT, "2005년 12월 스페인", "2005.12.09-세고비아",
                        "PC090035.JPG")
그림모델 = "fal-ai/nano-banana-2/edit"
영상모델 = "bytedance/seedance-2.5/image-to-video"
큐 = "https://queue.fal.run/"
저장 = "https://rest.alpha.fal.ai/storage/upload/initiate"
초당 = 0.469          # 720p 실측 ($9.38 / 4편 / 5초)

# ── ① 만톤을 놓는 말 ──────────────────────────────────────
그림말 = (
    "Add a deep crimson red embroidered flamenco shawl (manton de Manila) with "
    "long knotted fringe, lying crumpled on the grey stone paving directly in "
    "front of the dark doorway, as if someone had just let it fall there. "
    "It must look like real heavy silk fabric with natural folds, photographed "
    "with the same 2005 compact digital camera: the same flat overcast daylight, "
    "the same softness and grain, with a soft contact shadow where it touches "
    "the stone. It is the only saturated colour in the picture. "
    "CRITICAL: every other pixel of the photograph must stay exactly as it is - "
    "the stone sentry box, the walls, the paving, the sky and the two people on "
    "the right must not change or move. Do not crop or re-frame. Add nothing else."
)

# ── ② 15초를 움직이는 말 ──────────────────────────────────
#
# **금지를 앞이 아니라 뒤에 몰아 적는다** — 앞서 Seedance 에 「restrained motion
# only」를 먼저 박았더니 **아무것도 안 움직였다**(첫 프레임 vs 마지막 SSIM 0.9946).
# **할 일을 먼저 또렷하게, 하지 말 것을 그 다음에.**
영상말 = (
    "The camera is locked off and completely still. "
    "The red embroidered shawl lying on the stone floor comes alive in a light "
    "breeze: its long knotted fringe lifts and falls, the silk ripples and one "
    "corner turns over slowly. "
    "In the first seconds the two people on the right walk quietly out of the "
    "frame to the right and do not come back. "
    "Through the second half the overcast daylight fades steadily and evenly, "
    "the stone loses its brightness, and by the end the whole scene has gone "
    "almost completely dark - the open doorway staying the deepest black. "
    "Everything else is motionless: the stone sentry box, the walls, the paving "
    "and the sky do not move. "
    "No camera movement, no zoom, no pan. No new people or objects enter. "
    "No text, no titles, no captions."
)


def 열쇠():
    for ln in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if ln.strip().startswith("FAL_KEY"):
            return ln.split("=", 1)[1].strip()
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


def 부른다(H, 모델, 몸):
    """**주소는 fal 이 준 것을 쓴다** — 손으로 조립하다 $4.70 을 버렸다."""
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
        if 상 in ("FAILED", "CANCELLED") or time.time() - 처음 > 1800:
            return None, d0["request_id"], s
        time.sleep(8)
    return (requests.get(d0["response_url"], headers=H, timeout=60).json(),
            d0["request_id"], None)


def 배경검사(원본길, 새길):
    """**만톤 자리 말고는 그대로인가.** 그림 단계에서만 쓴다."""
    a = Image.open(원본길).convert("RGB")
    b = Image.open(새길).convert("RGB").resize(a.size, Image.LANCZOS)
    d = np.abs(np.asarray(a, float) - np.asarray(b, float)).mean(axis=2)
    붉 = ((np.asarray(b, float)[:, :, 0]
           - np.maximum(np.asarray(b, float)[:, :, 1],
                        np.asarray(b, float)[:, :, 2])) > 45)
    return float(np.median(d)), float(붉.mean() * 100)


def 자검사(단계, H):
    결과 = []
    결과.append(("바탕 사진이 있는가", None if os.path.exists(바탕사진)
                 else 바탕사진))
    결과.append(("배경 보존을 말에 박았는가",
                 None if "must stay exactly" in 그림말 else "그림말에 금지가 없다"))
    결과.append(("영상말이 「할 일」을 먼저 적는가",
                 None if 영상말.index("comes alive") < 영상말.index("No camera")
                 else "금지가 앞에 있다 — 앞서 그래서 아무것도 안 움직였다"))
    모델 = 그림모델 if 단계 == 1 else 영상모델
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
    ap.add_argument("단계", type=int, choices=(1, 2),
                    help="1 = 만톤을 놓는다 ($0.08) · 2 = 15초 영상 (약 $7)")
    ap.add_argument("--초", type=int, default=15)
    ap.add_argument("--진짜", action="store_true")
    a = ap.parse_args()

    H = {"Authorization": "Key " + 열쇠()}
    안 = os.path.join(ROOT, "산출물", "20260824 - 에필로그")
    os.makedirs(안, exist_ok=True)
    # **자른 판이 있으면 그것을 쓴다** — 원본 프레임에는 관광객 둘의 얼굴이 있어
    # fal 이 **내용 정책(실제 인물의 초상)으로 거부한다.** 2026-08-24 실측.
    첫프레임 = os.path.join(안, "첫 프레임 - 자른 판 (사람 없음).png")
    if not os.path.exists(첫프레임):
        첫프레임 = os.path.join(안, "첫 프레임 - 문 앞의 만톤.png")
    자검사(a.단계, H)

    if a.단계 == 1:
        print("  ① 만톤을 문지방에 놓는다  ·  $%.2f" % 0.08)
        if not a.진짜:
            print("\n**`--진짜` 를 안 줬으므로 멈춘다.**")
            return
        d, rid, 틀 = 부른다(H, 그림모델, {
            "image_urls": [올린다(H, 바탕사진)], "prompt": 그림말,
            "resolution": "1K", "num_images": 1,
            "output_format": "png", "aspect_ratio": "auto"})
        if d is None:
            sys.exit("X %s" % 틀)
        with io.open(첫프레임, "wb") as f:
            f.write(requests.get(d["images"][0]["url"], timeout=600).content)
        중, 붉비 = 배경검사(바탕사진, 첫프레임)
        print("      -> %s" % os.path.basename(첫프레임))
        print("      바뀐 정도 가운뎃값 %.1f/255 · 붉은 화소 화면의 %.2f%%"
              % (중, 붉비))
        if 붉비 < 0.15:
            print("      **X 만톤이 안 그려졌거나 너무 작다**")
        return

    # ── ② 15초 ────────────────────────────────────────────
    if not os.path.exists(첫프레임):
        sys.exit("첫 프레임이 없다 — 단계 1 을 먼저 돌린다")
    값 = a.초 * 초당
    print("  ② %d초 영상  ·  약 $%.2f" % (a.초, 값))
    print("     **한 번 돌리면 재시도할 잔액이 없다**")
    if not a.진짜:
        print("\n**`--진짜` 를 안 줬으므로 멈춘다. 돈이 안 나갔다.**")
        return
    # ## ★ **결과를 먼저 남기고 그 다음에 해석한다** (2026-08-24)
    #
    # **오늘 같은 실패를 세 번 했다.**
    #
    # | # | 무엇 |
    # |---|---|
    # | 1 | 상태 주소를 손으로 조립해 **영상 두 편($4.70)을 못 받았다** |
    # | 2 | `d["video"]` 를 가정했다가 **15초 요청의 결과를 통째로 잃었다** |
    #
    # **둘 다 「돈은 나갔는데 내가 못 읽었다」이다.**
    # **그래서 받은 것을 무조건 먼저 파일로 떨어뜨린다.** 해석은 그 다음이다.
    d, rid, 틀 = 부른다(H, 영상모델, {
        "image_url": 올린다(H, 첫프레임), "prompt": 영상말,
        "resolution": "720p", "duration": str(a.초),
        "generate_audio": False, "aspect_ratio": "auto"})
    대 = os.path.join(안, "받은 것 %d초.json" % a.초)
    with io.open(대, "w", encoding="utf-8") as f:
        json.dump({"요청": rid, "초": a.초, "값추정": round(값, 2),
                   "받은것": d, "틀림": 틀, "말": 영상말},
                  f, ensure_ascii=False, indent=2)
    print("      요청 %s" % rid)
    print("      -> %s  (무슨 일이 있었든 여기 다 있다)" % os.path.basename(대))
    if d is None:
        sys.exit("X 실패 — %s" % 틀)
    주소 = None
    if isinstance(d, dict):
        for 칸 in ("video", "videos", "output", "url"):
            v = d.get(칸)
            if isinstance(v, dict) and "url" in v:
                주소 = v["url"]
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                주소 = v[0].get("url")
            elif isinstance(v, str) and v.startswith("http"):
                주소 = v
            if 주소:
                break
    if not 주소:
        print("\n  **영상 주소가 응답에 없다.** 받은 칸: %s"
              % (list(d.keys()) if isinstance(d, dict) else type(d).__name__))
        sys.exit(1)
    낼 = os.path.join(안, "에필로그 %d초 - 문 앞의 만톤.mp4" % a.초)
    with io.open(낼, "wb") as f:
        f.write(requests.get(주소, timeout=900).content)
    print("      -> %s  (%.1f MB)" % (os.path.basename(낼),
                                      os.path.getsize(낼) / 1e6))


if __name__ == "__main__":
    main()
