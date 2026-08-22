# -*- coding: utf-8 -*-
"""**검토 영상이 원본과 어긋나지 않았는가.**

2026-08-20 신설. `review-video` 스킬 5절의 검증을 도구로 옮긴 것이다.
**옮기면서 두 가지를 고쳤다.**

  ① **셸 heredoc(`python - <<'PY'`)을 안 쓴다.** 8-19 에 두 번 깨졌고
     그날 규칙으로 못박았는데 **스킬에는 그 꼴이 남아 있었다**
  ② **`/ 32768` 을 안 쓴다.** 마스터가 float 로 바뀐 뒤 그 나눗셈이
     악장별 RMS 를 −110 dB 로 찍은 적이 있다(8-12). `화성.read_wav` 가
     자료형을 보고 나눈다

**세 가지를 잰다.**

  (a) **영상 ↔ 소리 동기** — 영상에서 오디오를 다시 뽑아 원본과 교차상관.
      **접합점을 반드시 포함**한다. 통과선은 **전 지점 0 샘플**
  (b) **규격** — High profile · 1920×1080 · 30fps · yuv420p · 48 kHz
  (c) **프레임 수** — 재생시간 × 30

    python 영상검증.py "전곡 v4.24 - 화성 검토 영상.mp4"
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import signal as sg

import 화성

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

# ── **견줄 원본은 인자로 받는다** (2026-08-22) ────────────────────
#
# 여기 `전곡화성.wav` 가 박혀 있었다. 우리 곡만 만들던 동안은 맞았다.
# **그런데 Suno 판 영상을 재려고 돌렸더니 닮은 정도가 0.09 로 나왔다** —
# 「어긋났다」가 다섯 줄 찍혔고, **동기가 틀린 것이 아니라 다른 곡과
# 견주고 있었다.** 원본을 안 주면 여전히 우리 마스터를 쓴다.
#
# > **같은 모양을 하루에 세 번 만났다** — `악장표.py`(우리 악보 전제) ·
# > `자막생성.py`(chordlog 전제) · 여기. **도구가 조용히 「우리 곡」을
# > 가정하고 있었고, 남의 음원을 넣으면 그럴듯한 틀린 값을 낸다.**
#
# **표본율도 안 박는다.** 44100 을 박아놓고 48 kHz 파일을 리샘플하면
# 비교가 한 겹 더 흐려진다. 영상에서 뽑은 소리의 표본율을 그대로 쓴다.
def _원본경로():
    for i, a in enumerate(sys.argv):
        if a == "--from" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return os.path.join(HERE, "전곡화성.wav")


원본 = _원본경로()
볼곳 = (30, 160, 275, 425, 540)                  # 접합점 275·425 포함


def 규격(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", p],
        capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main():
    if len(sys.argv) < 2:
        raise SystemExit('쓰는 법:  python 영상검증.py "…​.mp4"')
    영상 = sys.argv[1]
    if not os.path.exists(영상):
        raise SystemExit("파일이 없다 — %s" % 영상)

    print("검토 영상 검증 —", os.path.basename(영상))

    # ── (b) 규격 ──────────────────────────────────────────────
    j = 규격(영상)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next(s for s in j["streams"] if s["codec_type"] == "audio")
    길이 = float(j["format"]["duration"])
    크기 = int(j["format"]["size"]) / 1048576.0

    print("\n=== 규격 ===")
    표 = [
        ("영상 코덱", v["codec_name"], "h264"),
        ("프로파일", v.get("profile", "?"), "High"),
        ("해상도", "%dx%d" % (v["width"], v["height"]), "1920x1080"),
        ("프레임", v["r_frame_rate"], "30/1"),
        ("픽셀", v["pix_fmt"], "yuv420p"),
        ("소리 코덱", a["codec_name"], "aac"),
        ("갈래", "%s Hz" % a["sample_rate"], "48000 Hz"),
        ("채널", str(a["channels"]), "2"),
    ]
    나쁨 = 0
    for 이름, 값, 기대 in 표:
        ok = str(값) == 기대
        나쁨 += 0 if ok else 1
        print("  %-10s %-12s %s" % (이름, 값, "OK" if ok else "← %s 여야 한다" % 기대))
    print("  %-10s %.2f초 · %.1f MB" % ("길이", 길이, 크기))

    if v.get("profile") == "Constrained Baseline":
        print("\n  ⚠ **ultrafast 로 인코딩됐다.** veryfast crf 20 으로 다시 굽는다")

    # ── (c) 프레임 수 ─────────────────────────────────────────
    n = v.get("nb_frames")
    if n:
        기대 = round(길이 * 30)
        print("  %-10s %s  (기대 %d)" % ("프레임 수", n, 기대))

    # ── (a) 동기 ──────────────────────────────────────────────
    print("\n=== 영상 ↔ 소리 동기 ===")
    print("  견줄 원본   %s" % os.path.basename(원본))
    임시 = os.path.join(HERE, "_동기확인.wav")
    sr1, x0 = 화성.read_wav(원본)
    # **원본의 표본율로 뽑는다** — 리샘플을 한 겹 줄인다
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", 영상,
                    "-ar", str(sr1), "-ac", "2", 임시], check=True)
    SR = sr1
    sr2, y0 = 화성.read_wav(임시)
    x0 = x0.mean(1) if x0.ndim > 1 else x0
    y0 = y0.mean(1) if y0.ndim > 1 else y0

    어긋남 = 0
    최고닮음 = 0.0
    for t0 in 볼곳:
        s, w = int(t0 * SR), int(4 * SR)
        if s + w > min(len(x0), len(y0)):
            continue
        x, y = x0[s:s + w], y0[s:s + w]
        c = sg.correlate(y - y.mean(), x - x.mean(), mode="same")
        lag = int(np.argmax(np.abs(c)) - len(x) // 2)
        r = float(np.corrcoef(x, np.roll(y, -lag)[:len(x)])[0, 1])
        최고닮음 = max(최고닮음, abs(r))
        if lag != 0:
            어긋남 += 1
        print("  %4d초  지연 %+3d 샘플 (%+.2f ms)  닮은 정도 %.4f  %s"
              % (t0, lag, lag / SR * 1000, r, "OK" if lag == 0 else "← 어긋났다"))
    os.remove(임시)

    if 어긋남 and 최고닮음 < 0.5:
        print()
        print("  ★ 닮은 정도가 %.2f 로 너무 낮습니다 — **동기가 아니라 「견줄 원본」을 먼저 의심하세요.**"
              % 최고닮음)
        print("     지금 견준 것: %s" % os.path.basename(원본))
        print("     다른 음원이면  --from \"<그 음원.wav>\"  을 붙입니다.")

    print("\n=== 판정 ===")
    if 나쁨 == 0 and 어긋남 == 0:
        print("  **통과** — 규격 여덟 항목 · 동기 전 지점 0 샘플")
    else:
        print("  **실패** — 규격 %d · 동기 %d" % (나쁨, 어긋남))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
