# -*- coding: utf-8 -*-
"""**사진 영상의 제목·도시 이름·워터마크를 만든다.**

2026-08-30. 검수자 — *"영상 제목 같은 것 있어야 하는 것 아닌가? 지난 번 영상 참고해서
만들어주면 안되나? 워터마크도 포함해주고."*

## 지난 영상과 무엇이 같고 무엇이 다른가

**같은 것** — ASS 자막을 ffmpeg 이 화면에 굽는다. `\\pos()` 로 자리를 못박는다.

**다른 것** — 지난 것은 **검토 영상**이라 제목이 14분 내내 떠 있었다.
**이것은 뮤직비디오다.** 글자가 계속 떠 있으면 사진을 가린다.

| 무엇 | 언제 |
|---|---|
| **제목·부제** | **앞 9초**에만. 뜨고 사라진다 |
| **도시 이름** | 구간이 바뀔 때 **5초**. 왼쪽 아래 |
| **워터마크** | **여기서 안 만든다** — ffmpeg `drawtext` 가 지난 판과 똑같이 건다 |
| **맺음말** | 마지막 8초 |

## 자검사 — 답을 아는 문제 넷

| 무엇 | 나와야 하는 값 |
|---|---|
| 역슬래시 | **벨 문자(0x07)가 없다** — `r"..."` 로 써야 한다 |
| 위치 지정 | 줄 수만큼 `{\\an5\\pos(` 가 있다 |
| 도시 이름 | 구간 수만큼 |

**미달이면 `sys.exit`.**
"""
import json
import os
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
밑 = os.path.join(HERE, "..", "산출물", "20260830 - 사진 고르기")

제목 = "스페인 전람회의 그림"
부제 = "2005년 12월, 스페인 — 재즈판"
# **워터마크는 여기서 안 만든다.** 지난 판과 똑같이 ffmpeg `drawtext` 가 건다
# (`95. 영상 프로젝트/워터마크.txt` = `© 2026 BLUEBUG`).
# 검수자 (2026-08-30) — *"워터마크는 지난 영상과 동일하게"*
맺음말 = "사진 2005년 12월 · 음악 2026년"

# **세로 사진의 왼쪽 여백에 붙이는 글** (2026-08-30 검수자 요청).
# 세로 사진은 좌우에 579화소씩 빈다. **그 자리를 글자가 쓴다.**
# 가로 사진은 여백이 위아래라 글자 놓을 자리가 마땅치 않아 안 붙인다.
사진밑 = os.path.join(HERE, "..", "2005년 12월 스페인")
여백X, 여백Y = 96, 840          # 왼쪽 여백의 글자 자리
캡션여유 = 0.5                  # 사진이 자리 잡은 뒤에 뜬다


def 장소읽기():
    """`장소 이름.txt` — 비어 있으면 도시와 날짜만 나온다."""
    d = {}
    f = os.path.join(밑, "장소 이름.txt")
    if not os.path.exists(f):
        return d
    for L in open(f, encoding="utf-8"):
        L = L.strip()
        if not L or L.startswith("#") or "|" not in L:
            continue
        칸 = [x.strip() for x in L.split("|")]
        if len(칸) >= 3 and 칸[0]:
            d[칸[0].split(".JPG")[0] + ".JPG"] = (칸[1], 칸[2])
    return d


def 세로인가(경로):
    w, h = Image.open(os.path.join(사진밑, 경로.replace("/", os.sep))).size
    return h > w


def 날짜(경로):
    """폴더 이름 `2005.12.12-그라나다` 에서 뽑는다."""
    return 경로.split("/")[0].split("-")[0]


def 도시(경로):
    """**사진이 찍힌 도시.** 폴더 이름의 뒤쪽이다.

    **구간 이름을 쓰면 안 된다** — 프롬나드 구간에는 여러 도시의 사진이 섞여 있어
    알람브라 사진에 「프롬나드」가 붙었다 (2026-08-31 검수자 지적).
    """
    return 경로.split("/")[0].split("-", 1)[1]

제목띄움 = (0.8, 9.0)        # 제목이 떠 있는 구간
캡션수 = 0
도시띄움 = 5.0               # 도시 이름이 떠 있는 시간


def 시각(t):
    return "%d:%02d:%05.2f" % (int(t // 3600), int(t % 3600 // 60), t % 60)


머리 = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: 제목,Malgun Gothic,64,&H00F0F4FA,&H00000000,&H80000000,-1,0,0,0,100,100,4,0,1,0,3,5,0,0,0,1
Style: 부제,Malgun Gothic,28,&H00B8C6D8,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,5,0,0,0,1
Style: 도시,Malgun Gothic,34,&H00E4ECF6,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,0,3,5,0,0,0,1
Style: 워터,Malgun Gothic,20,&H50C0CCDC,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,2,5,0,0,0,1
Style: 캡션1,Malgun Gothic,48,&H00E2E8F2,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,0,2,7,0,0,0,1
Style: 캡션2,Malgun Gothic,30,&H0092A2B6,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,7,0,0,0,1
Style: 캡션3,Malgun Gothic,26,&H006E7C8E,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,0,2,7,0,0,0,1
Style: 맺음,Malgun Gothic,26,&H00B8C6D8,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def 만들기(구간, 총길이, 장면들):
    줄 = []

    def 넣기(a, b, st, x, y, txt, 효과=""):
        # **r"..." 로 쓴다.** 그냥 쓰면 파이썬이 \a 를 벨 문자로 바꿔
        # 자막이 통째로 안 붙는다 (2026-08-29 에 실제로 겪었다).
        줄.append(r"Dialogue: 0,%s,%s,%s,,0,0,0,,{\an5\pos(%d,%d)%s}%s"
                  % (시각(a), 시각(b), st, x, y, 효과, txt))

    페이드 = r"\fad(700,700)"
    a, b = 제목띄움
    넣기(a, b, "제목", 960, 500, 제목, 페이드)
    넣기(a, b, "부제", 960, 566, 부제, 페이드)

    for g in 구간:
        넣기(g["시작"] + 0.4, g["시작"] + 0.4 + 도시띄움, "도시",
             360, 980, g["도시"], r"\fad(600,600)")

    # ── 세로 사진의 왼쪽 여백 ──────────────────────────
    #
    # **`\\an7` 로 왼쪽 위를 기준 삼는다.** `\\an5`(가운데)로 두면
    # x=96 을 한가운데로 잡아 **글자 절반이 화면 밖으로 나간다.**
    장소 = 장소읽기()
    global 캡션수
    캡션수 = 0
    for s2 in 장면들:
        경로 = s2["경로"]
        if not 세로인가(경로):
            continue
        캡션수 += 1
        a2 = s2["시작"] + 캡션여유
        b2 = max(a2 + 0.5, s2["끝"] - 0.3)
        한, 영 = 장소.get(경로, ("", ""))
        줄들 = [(도시(경로), "캡션1", 0)]
        if 한:
            줄들.append((한, "캡션2", 68))
            if 영:
                줄들.append((영, "캡션3", 112))
            줄들.append((날짜(경로), "캡션3", 150))
        else:
            줄들.append((날짜(경로), "캡션3", 68))
        for 글자, 스타일, dy in 줄들:
            줄.append(r"Dialogue: 0,%s,%s,%s,,0,0,0,,{\an7\pos(%d,%d)\fad(400,400)}%s"
                      % (시각(a2), 시각(b2), 스타일, 여백X, 여백Y + dy, 글자))

    넣기(총길이 - 8.0, 총길이, "맺음", 960, 700, 맺음말, 페이드)
    return 머리 + "\n".join(줄) + "\n"


def 자검사(글, 구간, 총길이):
    실패 = []
    if chr(7) in 글:
        실패.append("① 벨 문자(0x07) 가 들어갔다 — a 가 escape 됐다")
    표 = "{" + chr(92) + "an5" + chr(92) + "pos("
    기대 = 2 + len(구간) + 1
    if 글.count(표) != 기대:
        실패.append("② 가운데 자막이 %d개 (기대 %d)" % (글.count(표), 기대))
    # **★ 캡션이 정말 들어갔는지 센다.**
    # 「적어도 몇 개」로 느슨하게 뒀더니 **0개인데 통과**했다 (2026-08-30).
    왼표 = "{" + chr(92) + "an7" + chr(92) + "pos("
    if 캡션수 == 0:
        실패.append("⑤ 세로 사진 캡션이 하나도 없다")
    elif 글.count(왼표) < 캡션수 * 2:
        실패.append("⑤ 캡션 줄이 %d개 — 세로 사진 %d장이면 적어도 %d개"
                    % (글.count(왼표), 캡션수, 캡션수 * 2))
    for g in 구간:
        if g["도시"] not in 글:
            실패.append("③ %s 가 없다" % g["도시"])
    if 시각(총길이) not in 글:
        실패.append("④ 맺음말이 끝까지 안 간다")
    return 실패


if __name__ == "__main__":
    j = json.load(open(os.path.join(밑, "장면.json"), encoding="utf-8"))
    장면 = j["장면"]
    구간 = []
    for s in 장면:
        if not 구간 or 구간[-1]["도시"] != s["도시"]:
            구간.append({"도시": s["도시"], "시작": s["시작"]})
    총길이 = j["총길이"]

    글 = 만들기(구간, 총길이, 장면)
    실패 = 자검사(글, 구간, 총길이)
    print("자검사")
    if 실패:
        for x in 실패:
            print("   " + x)
        sys.exit("\n자검사 미달 — 자막을 안 쓴다.")
    print("   → 통과 4/4\n")

    p = os.path.join(HERE, "사진자막.ass")
    with open(p, "w", encoding="utf-8") as f:
        f.write(글)
    print("사진자막.ass")
    print("   제목    %.1f~%.1f초  %s" % (제목띄움[0], 제목띄움[1], 제목))
    for g in 구간:
        print("   도시    %7.2f초  %s" % (g["시작"], g["도시"]))
