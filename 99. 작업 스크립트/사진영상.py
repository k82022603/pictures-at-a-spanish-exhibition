# -*- coding: utf-8 -*-
"""**장면을 영상으로 굽는다 — 박에 맞춰, 화면을 채워, 효과를 넣어.**

2026-08-30. 검수자 — *"박에 맞춰 컷 ... 이번에는 가로사진들도 1920×1080에 맞추어
사진 넣어주시고요. 또 해보고 싶었던 효과 다 넣어서 만들어주세요."*

## 앞의 판과 무엇이 다른가

| | 앞의 판 | 이 판 |
|---|---|---|
| 컷 자리 | 구간을 **똑같이 나눔** | **박에 맞춤** (`박찾기.py` → `장면배치.py`) |
| 사진 크기 | **원본 화소 그대로** (화면의 53%) | **화면에 맞춰 키움** — 다만 **안 자른다** |
| 남는 자리 | 어두운 바탕 | **같은 사진을 흐리게 깔고 천천히 민다** |
| 도시 경계 | 검게 빈다 | **얼룩무늬로 녹아 넘어간다** |
| 도시 첫 컷 | 없음 | **초점이 맞아 들어오고 흰 섬광이 스친다** |

## ★ 켄번스를 사진에 못 거는 이유

**확대하면 잘린다.** 4:3 사진을 16:9 화면에서 조금이라도 키우면 위아래가 나간다.
**「가로 사진도 잘라내지 않는다」**(2026-08-24 검수자 지시)와 정면으로 부딪힌다.

**그래서 움직임을 배경에 걸었다** — 뒤에 깔린 흐린 판이 천천히 움직이고
**사진 자체는 온전히 가만히 있는다.** 자르는 것을 받아들이시면 사진에 걸 수 있다.

## 효과 일곱

| # | 무엇 | 어디 |
|---|---|---|
| 1 | 화면을 채우는 **흐린 배경** + 천천히 밀림 | 모든 컷 |
| 2 | 어둠에서 **떠오르며 미끄러짐** | 모든 컷 |
| 3 | **초점이 맞아 들어옴** | 도시의 첫 컷 |
| 4 | **흰 섬광** | 도시의 첫 컷 |
| 5 | 필름 **입자** | 모든 컷 |
| 6 | **비네트** | 모든 컷 |
| 7 | **얼룩무늬 전환** | 도시 경계 다섯 (무음 1.5초 자리) |

## 왜 조각으로 굽고 잇나

**ffmpeg 하나로 135장을 한 번에 못 건다.** 한 장면씩 굽고 이어 붙인 뒤,
**자막과 워터마크를 한 번에 굽고, 소리는 마스터에서 다시 먹싱한다.**

> **★ 이어 붙일 때 소리를 같이 넣지 않는다.** `concat` 이 AAC 인코더 지연 보정을
> 날려 **1024 표본(21.33 ms) 밀린다** — 2026-08-24 실측.
"""
import json
import os
import subprocess
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
사진밑 = os.path.join(HERE, "..", "2005년 12월 스페인")
밑 = os.path.join(HERE, "..", "산출물", "20260830 - 사진 고르기")
조각밑 = os.path.join(HERE, "_사진영상조각")
음원 = os.path.join(HERE, "..", "산출물", "20260829 - 재즈 2판",
                    "전곡 재즈 2판 - 원본 그대로 · 무음 1.5초.wav")
자막 = os.path.join(HERE, "사진자막.ass")
워터마크파일 = os.path.join(HERE, "_워터마크.txt")

W, H = 1920, 1080
바탕 = "0x0C0D10"
FPS = 30
페이드 = 0.6
미끄럼 = 40
초점 = 0.7           # 초점이 맞아 들어오는 시간
# **테두리를 없앴다** (2026-08-31 검수자 — *"얇은 테두리 없음"*).
# 0 으로 두면 `pad` 를 아예 안 건다.
테두리 = 0          # 세로 사진에 두르는 얇은 선 (화소). 0 이면 안 두른다
# **세로 사진도 화면 높이에 꽉 채운다** (2026-08-31 검수자 —
# *"세로 사진 가로 사진과 마찬가지로 화면에 맞춰 키움"*).
# 0 이면 위아래 여유 없이 1080 을 다 쓴다.
세로여유 = 0        # 세로 사진 위아래로 남기는 자리
섬광 = 0.10          # 흰 섬광

전부컬러 = "--컬러" in sys.argv
낼곳 = os.path.join(밑, "스페인 전람회의 그림 - 재즈판 14m04%s.mp4"
                    % (" (컬러)" if 전부컬러 else " (흑백)"))


def 컬러목록():
    s = set()
    f = os.path.join(밑, "컬러로 낼 것.txt")
    if os.path.exists(f):
        for L in open(f, encoding="utf-8"):
            L = L.strip()
            if L and not L.startswith("#"):
                s.add(L.split(".JPG")[0] + ".JPG")
    return s


컬러 = 컬러목록()


def 달리기(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print(" ".join(cmd[:8]), "...")
        print(r.stderr[-1800:])
        sys.exit("ffmpeg 실패")


def 색필터(경로):
    return "format=yuv420p" if (전부컬러 or 경로 in 컬러) else "format=gray"


def 바탕깔기(라벨입, 라벨출, 길이, 방향):
    """**같은 사진을 화면 가득 채워 흐리게 깔고 천천히 민다.**

    사진 자체는 안 자르므로 좌우(또는 위아래)가 빈다. 그 자리를 검게 두면
    화면이 좁아 보이고, **같은 사진의 흐린 판을 깔면 색이 이어진다.**
    """
    # 화면보다 크게 잡아 두고 `crop` 으로 천천히 민다 — **배경만 움직인다**
    큰W, 큰H = int(W * 1.12), int(H * 1.12)
    dx = (큰W - W)
    dy = (큰H - H)
    x = "(%d)*(%.4f)" % (dx, 0.0) if 방향 == 0 else "(%d)*(t/%.3f)" % (dx, 길이)
    y = "(%d)*(1-t/%.3f)" % (dy, 길이) if 방향 == 0 else "(%d)*0.5" % dy
    return ("[%s]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
            "boxblur=28:2,eq=brightness=-0.16:saturation=0.75,"
            "crop=%d:%d:x='%s':y='%s'[%s];"
            % (라벨입, 큰W, 큰H, 큰W, 큰H, W, H, x, y, 라벨출))


def 한장면(i, s, 도시첫컷):
    p = os.path.join(사진밑, s["경로"].replace("/", os.sep))
    길이 = max(0.5, s["끝"] - s["시작"])
    dx = 미끄럼 if i % 2 == 0 else -미끄럼
    색 = 색필터(s["경로"])

    # **가로와 세로를 다르게 다룬다** (2026-08-30 검수자 결정).
    #
    # | | 뒤에 무엇 | 왜 |
    # |---|---|---|
    # | 가로 | **흐린 배경이 흐른다** | 여백이 위아래라 좁고, 배경이 화면을 이어 준다 |
    # | 세로 | **어두운 바탕만** — 테두리도 흐린 배경도 없다 (2026-08-31) | 여백이 좌우로 579화소나 된다. 흐린 배경을
    #   깔면 산만하고, 사진 색 단색을 깔면 **경계가 무뎌진다** |
    ww, hh = Image.open(p).size
    세로 = hh > ww

    f = []
    f.append("[0:v]%s,split=3[c0][c1][c2];" % 색)
    if 세로:
        f.append("[c0]nullsink;")
        f.append("color=c=%s:s=%dx%d:r=%d:d=%.3f[bg];" % (바탕, W, H, FPS, 길이))
        # **얇은 테두리를 두른다** — 어두운 바탕과 사진의 경계를 또렷하게
        if 테두리:
            f.append("[c1]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "pad=iw+%d:ih+%d:%d:%d:color=0xE0E4EC,setsar=1,fps=30,settb=1/30[sharp];"
                     % (W - 2 * 테두리, H - 세로여유 - 2 * 테두리,
                        2 * 테두리, 2 * 테두리, 테두리, 테두리))
        else:
            f.append("[c1]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "setsar=1,fps=30,settb=1/30[sharp];" % (W, H - 세로여유))
    else:
        f.append(바탕깔기("c0", "bg", 길이, i % 2))
        # **사진은 화면에 맞춰 키우되 안 자른다** — `decrease` 라 비율이 유지된다
        f.append("[c1]scale=%d:%d:force_original_aspect_ratio=decrease,setsar=1,fps=30,settb=1/30[sharp];" % (W, H))

    if 도시첫컷:
        # **초점이 맞아 들어온다** — 흐린 판에서 또렷한 판으로 녹아 넘어간다
        if 세로:
            f.append("[c2]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "boxblur=18:2,setsar=1,fps=30,settb=1/30[soft];"
                     % (W, H - 세로여유))
        else:
            f.append("[c2]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "boxblur=18:2,setsar=1,fps=30,settb=1/30[soft];" % (W, H))
        f.append("[soft][sharp]xfade=transition=fade:duration=%.2f:offset=0[fg];" % 초점)
    else:
        f.append("[c2]nullsink;")
        f.append("[sharp]null[fg];")

    f.append("[bg][fg]overlay=x='(W-w)/2 + %d*(1-min(t/%.2f,1))':y=(H-h)/2[v0];"
             % (dx, 페이드))
    체인 = ("fade=t=in:st=0:d=%.2f,fade=t=out:st=%.3f:d=%.2f,"
            % (페이드, 길이 - 페이드, 페이드))
    if 도시첫컷:
        # **흰 섬광** — 도시가 바뀌었다는 신호. 아주 짧게만
        체인 += "fade=t=in:st=0:d=%.2f:color=white," % 섬광
    체인 += ("noise=alls=6:allf=t+u,vignette=PI/5,"
             "scale=in_range=full:out_range=tv,format=yuv420p")
    f.append("[v0]%s[vout]" % 체인)

    낼 = os.path.join(조각밑, "%04d.mp4" % i)
    달리기(["ffmpeg", "-hide_banner", "-v", "error", "-y",
            "-loop", "1", "-t", "%.3f" % 길이, "-i", p,
            "-filter_complex", "".join(f), "-map", "[vout]", "-t", "%.3f" % 길이,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-r", str(FPS), 낼])
    return 낼


def 얼룩전환(이름, 앞경로, 뒤경로, 길이):
    """**도시 경계 — 얼룩무늬로 녹아 넘어간다** (2026-08-30 검수자 채택).

    `xfade=transition=dissolve` 가 **화소마다 다른 문턱값**으로 지운다.
    통째로 투명해지는 것이 아니라 **점점이 바뀐다** — 그것이 얼룩무늬다.
    """
    a = os.path.join(사진밑, 앞경로.replace("/", os.sep))
    b = os.path.join(사진밑, 뒤경로.replace("/", os.sep))
    f = []
    for n, (경로, 라벨) in enumerate(((앞경로, "A"), (뒤경로, "B"))):
        여기 = os.path.join(사진밑, 경로.replace("/", os.sep))
        w2, h2 = Image.open(여기).size
        f.append("[%d:v]%s,split=2[%sc0][%sc1];" % (n, 색필터(경로), 라벨, 라벨))
        if h2 > w2:
            f.append("[%sc0]nullsink;" % 라벨)
            f.append("color=c=%s:s=%dx%d:r=%d:d=%.3f[%sbg];"
                     % (바탕, W, H, FPS, 길이, 라벨))
            f.append("[%sc1]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "setsar=1,fps=30,settb=1/30[%sf];"
                     % (라벨, W, H - 세로여유, 라벨))
        else:
            f.append(바탕깔기("%sc0" % 라벨, "%sbg" % 라벨, 길이, 0))
            f.append("[%sc1]scale=%d:%d:force_original_aspect_ratio=decrease,setsar=1,fps=30,settb=1/30[%sf];"
                     % (라벨, W, H, 라벨))
        f.append("[%sbg][%sf]overlay=x=(W-w)/2:y=(H-h)/2,fps=30,settb=1/30[%sv];" % (라벨, 라벨, 라벨))
    f.append("[Av][Bv]xfade=transition=dissolve:duration=%.3f:offset=0," % 길이)
    f.append("noise=alls=6:allf=t+u,vignette=PI/5,"
             "scale=in_range=full:out_range=tv,format=yuv420p[vout]")
    낼 = os.path.join(조각밑, 이름)
    달리기(["ffmpeg", "-hide_banner", "-v", "error", "-y",
            "-loop", "1", "-t", "%.3f" % 길이, "-i", a,
            "-loop", "1", "-t", "%.3f" % 길이, "-i", b,
            "-filter_complex", "".join(f), "-map", "[vout]", "-t", "%.3f" % 길이,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-r", str(FPS), 낼])
    return 낼


if __name__ == "__main__":
    os.makedirs(조각밑, exist_ok=True)
    장면 = json.load(open(os.path.join(밑, "장면.json"), encoding="utf-8"))["장면"]
    print("장면 %d개 · 총 %.2f초 · %s"
          % (len(장면), 장면[-1]["끝"], "컬러" if 전부컬러 else "흑백"))

    첫컷 = set()
    앞도시 = None
    for i, s in enumerate(장면):
        if s["도시"] != 앞도시:
            첫컷.add(i)
            앞도시 = s["도시"]

    목록 = []
    앞끝 = 0.0
    for i, s in enumerate(장면):
        틈 = s["시작"] - 앞끝
        if 틈 > 0.001:
            목록.append(얼룩전환("t%04d.mp4" % i, 장면[i - 1]["경로"], s["경로"], 틈))
        목록.append(한장면(i, s, i in 첫컷))
        앞끝 = s["끝"]
        if (i + 1) % 20 == 0 or i + 1 == len(장면):
            print("  %d/%d" % (i + 1, len(장면)))

    lst = os.path.join(조각밑, "목록.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in 목록:
            f.write("file '%s'\n" % os.path.abspath(p).replace("\\", "/"))

    영상만 = os.path.join(조각밑, "영상만.mp4")
    달리기(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", lst, "-c", "copy", 영상만])

    wm = os.path.basename(워터마크파일)
    vf = ("ass=%s,drawtext=fontfile='C\\:/Windows/Fonts/malgun.ttf'"
          ":textfile='%s':fontcolor=white@0.35:fontsize=30"
          ":x=w-tw-46:y=h-th-40:shadowcolor=black@0.4:shadowx=1:shadowy=1"
          % (os.path.basename(자막), wm))
    달리기(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", 영상만, "-i", 음원,
            "-vf", vf, "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-r", str(FPS), "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-c:a", "aac", "-b:a", "384k", "-ar", "48000", "-ac", "2",
            "-shortest", "-movflags", "+faststart", 낼곳])
    print("\n→ %s" % os.path.basename(낼곳))
