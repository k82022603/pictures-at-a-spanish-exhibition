# -*- coding: utf-8 -*-
"""**그녀를 움직이게 한다** — fal.ai 를 통해 Seedance 2.5 를 부른다. WBS 2.2 (G3).

## 무엇을 하나

**실루엣을 얹은 사진 한 장**을 넣으면 **그녀가 움직이는 5초 영상**이 나온다.
사진은 `실루엣.py` 가 만든 것을 그대로 쓴다.

## ★ 돈이 나가는 도구다 — 그래서 안전장치가 넷이다

| # | 무엇 | 왜 |
|---|---|---|
| **1** | **`--진짜` 를 안 주면 안 보낸다** | 실수로 여섯 장이 나가는 것을 막는다 |
| **2** | **`generate_audio=False` 를 못 끄게 박아 뒀다** | **fal 기본값이 `True` 다.** 우리는 곡이 이미 있어 **켜면 값만 오르고 버린다** |
| **3** | **보내기 전에 값을 찍고 멈춘다** | 몇 편에 얼마인지 보고 나서 누른다 |
| **4** | **★ 받은 영상을 반드시 파일로 남긴다** | 링크는 만료된다. **다시 못 뽑으면 영상을 다시 못 만든다**(`CLAUDE.md` 저작권 절) |

## 왜 `fal_client` 를 안 쓰나

**꾸러미를 안 깔아도 되게 `requests` 만 쓴다.** 올리는 것도 REST 로 한다 —
`fal_client` 가 하는 일이 그것뿐이다.

## 자기검사 — 셋

**돌리기 전에 스스로 확인한다. 하나라도 틀리면 안 보낸다.**
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

# ── 값 (2026-08-24 fal 규격서 실측) ─────────────────────────
#
# **`generate_audio` 의 fal 기본값은 `True` 다.** 여기서 `False` 로 박는다.
설정 = {
    "resolution": "720p",     # 우리 사진 세로가 768 이다. 그 위는 없는 것을 지어내는 것
    "duration": "5",          # 그녀가 서 있는 컷이 3~6초
    "generate_audio": False,  # ★ 끈다. 곡이 이미 있다
    "aspect_ratio": "auto",   # 원본 비율 그대로 — **V2(배경 변경 금지)** 와 같은 뜻
}


def 열쇠():
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        sys.exit("`.env` 가 없다. `24` 문서 4절대로 만든다")
    for ln in io.open(p, encoding="utf-8"):
        if ln.strip().startswith("FAL_KEY"):
            k = ln.split("=", 1)[1].strip()
            if len(k) < 40 or ":" not in k:
                sys.exit("FAL_KEY 모양이 아니다 (UUID:해시 꼴이어야 한다)")
            return k
    sys.exit("`.env` 안에 FAL_KEY 줄이 없다")


def 올린다(H, 경로):
    """**로컬 사진을 fal 저장소에 올려 주소를 받는다.** 돈이 안 든다."""
    형 = mimetypes.guess_type(경로)[0] or "image/png"
    # **파일 이름을 아스키로 바꿔 올린다.** 한글 이름을 그대로 주면 주소에
    # `%3F%3F`(물음표)로 뭉개진다 — 2026-08-24 실측. 올라가긴 하지만
    # **모델이 그 주소를 다시 받아올 때 무엇이 될지 보장이 없다.**
    이름 = os.path.basename(경로).encode("ascii", "replace").decode()
    이름 = "".join(c if c.isalnum() or c in "._-" else "_" for c in 이름)
    r = requests.post(저장, headers=H, timeout=60,
                      json={"file_name": 이름, "content_type": 형})
    r.raise_for_status()
    d = r.json()
    with io.open(경로, "rb") as f:
        u = requests.put(d["upload_url"], data=f.read(),
                         headers={"Content-Type": 형}, timeout=300)
    u.raise_for_status()
    return d["file_url"]


def 부른다(H, 주소, 프롬프트):
    몸 = dict(설정)
    몸["image_url"] = 주소
    몸["prompt"] = 프롬프트
    r = requests.post(큐 + 모델, headers=H, json=몸, timeout=60)
    r.raise_for_status()
    # ## ★ **주소를 손으로 조립하지 않는다** (2026-08-24)
    #
    # `큐 + 모델.split("/")[0] + "/requests/"` 로 만들었더니 **`bytedance/requests/…`**
    # 가 됐다 — 맞는 것은 **`bytedance/seedance-2.5/requests/…`** 다.
    # **모델 경로가 몇 토막인지를 내가 가정하고 있었다.**
    #
    # **fal 이 응답에 `status_url` 과 `response_url` 을 그대로 준다.** 그것을 쓴다.
    d0 = r.json()
    rid = d0["request_id"]
    상태주소 = d0["status_url"]
    결과주소 = d0["response_url"]
    처음 = time.time()
    while True:
        s = requests.get(상태주소, headers=H, timeout=30).json()
        상 = s.get("status")
        print("      %-12s %4.0f초" % (상, time.time() - 처음), end="\r")
        if 상 == "COMPLETED":
            break
        if 상 in ("FAILED", "CANCELLED"):
            print()
            return None, rid, s
        if time.time() - 처음 > 900:
            print()
            return None, rid, {"오류": "15분을 넘겼다"}
        time.sleep(5)
    print()
    return requests.get(결과주소, headers=H, timeout=60).json(), rid, None


# ── 자기검사 셋 ────────────────────────────────────────────
def 자검사(일감, H):
    결과 = []

    결과.append(("소리를 껐는가",
                 None if 설정.get("generate_audio") is False
                 else "generate_audio 가 켜져 있다 — 안 쓸 소리에 돈이 나간다"))

    없 = [p for _, p, _ in 일감 if not os.path.exists(p)]
    결과.append(("넣을 사진이 다 있는가",
                 None if not 없 else "없는 것 %d 장 — %s" % (len(없), 없[0])))

    # **모델 경로가 살아 있는가** — 틀린 경로도 큐가 받아 놓고 404 를 낸다(2026-08-24 실측).
    # 규격서를 읽어 확인한다. **돈이 안 든다.**
    try:
        r = requests.get("https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=" + 모델,
                         headers=H, timeout=30)
        살 = r.status_code == 200 and "Seedance" in r.text
    except Exception:
        살 = False
    결과.append(("모델 경로가 살아 있는가",
                 None if 살 else "규격서를 못 읽었다 — 경로가 바뀌었을 수 있다"))

    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-24s %s" % (이, "OK" if 틀 is None else "✗ " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자기검사 미달 — 아무것도 안 보냈다.**")
    print()


# ── 그녀의 프롬프트 ────────────────────────────────────────
#
# **V1(얼굴 금지) · V2(배경 변경 금지)를 문장에 박는다.**
# 지시가 아니라 **금지**를 적는 것이 핵심이다 — 모델은 시키지 않은 것을 한다.
프롬프트 = (
    "The dark silhouette of a woman in a long flamenco dress and shawl "
    "moves very subtly: the hem and shawl fringe sway gently, she shifts her "
    "weight slightly. She stays a flat black silhouette with no visible face "
    "or facial features. "
    "The background photograph is completely static and unchanged — the "
    "architecture, sky, ground and lighting must not move, morph or regenerate. "
    "No camera movement. No zoom. No new objects. No people added. "
    "Subtle, slow, restrained motion only."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("사진", nargs="*", help="넣을 png (없으면 실루엣 결과 전부)")
    ap.add_argument("--진짜", action="store_true", help="★ 없으면 안 보낸다")
    ap.add_argument("--낼곳", default=None)
    a = ap.parse_args()

    H = {"Authorization": "Key " + 열쇠()}
    안 = a.낼곳 or os.path.join(ROOT, "산출물", time.strftime("%Y%m%d") + " - 그녀 PoC")

    if a.사진:
        일감 = [(os.path.splitext(os.path.basename(p))[0], p, "") for p in a.사진]
    else:
        # **폴더를 훑지 않는다.** `실루엣.py` 가 적어 둔 「지금 여섯」만 읽는다 —
        # **R11 때문에 옛 판이 폴더에 남아 있고, 훑으면 그것까지 보낸다.**
        얹 = os.path.join(ROOT, "산출물", "20260824 - 실루엣과 업스케일",
                          "여섯 자리에 얹어 본 것")
        대 = os.path.join(얹, "지금 여섯.json")
        if not os.path.exists(대):
            sys.exit("`지금 여섯.json` 이 없다 — `실루엣.py` 를 먼저 돌린다")
        일감 = [(os.path.splitext(x["얹은것"])[0],
                 os.path.join(얹, x["얹은것"]), "")
                for x in json.load(io.open(대, encoding="utf-8"))]
    if not 일감:
        sys.exit("보낼 사진이 없다. `실루엣.py` 를 먼저 돌린다")

    자검사(일감, H)

    print("=== 보낼 것 ===")
    for 이, p, _ in 일감:
        print("  %-34s %s" % (이, os.path.basename(p)))
    print("\n  설정 : %s · %s초 · 소리 %s" %
          (설정["resolution"], 설정["duration"],
           "끔" if not 설정["generate_audio"] else "★켬"))
    print("  편수 : %d" % len(일감))

    if not a.진짜:
        print("\n**`--진짜` 를 안 줬으므로 여기서 멈춘다. 돈이 안 나갔다.**")
        return

    os.makedirs(안, exist_ok=True)
    대장 = []
    for n, (이, p, _) in enumerate(일감, 1):
        print("\n[%d/%d] %s" % (n, len(일감), 이))
        try:
            주소 = 올린다(H, p)
            print("      올림 OK")
            d, rid, 틀 = 부른다(H, 주소, 프롬프트)
        except Exception as e:
            print("      ✗ %s" % e)
            대장.append({"이름": 이, "틀림": str(e)})
            continue
        if d is None:
            print("      ✗ %s" % 틀)
            대장.append({"이름": 이, "요청": rid, "틀림": 틀})
            continue
        v = (d.get("video") or {}).get("url")
        낼 = os.path.join(안, 이 + ".mp4")
        with io.open(낼, "wb") as f:
            f.write(requests.get(v, timeout=600).content)
        print("      → %s  (%.1f MB)" % (os.path.basename(낼),
                                         os.path.getsize(낼) / 1e6))
        대장.append({"이름": 이, "요청": rid, "판": os.path.basename(낼), "링크": v})

    with io.open(os.path.join(안, "대장.json"), "w", encoding="utf-8") as f:
        json.dump(대장, f, ensure_ascii=False, indent=2)
    print("\n→ %s" % 안)


if __name__ == "__main__":
    main()
