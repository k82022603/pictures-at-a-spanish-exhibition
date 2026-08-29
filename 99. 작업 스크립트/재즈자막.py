# -*- coding: utf-8 -*-
"""**재즈판 검토 영상의 자막을 만든다 — 아는 것만 적는다.**

2026-08-29. 검수자 — *"mp4인데 적어도 곡 제목과 코드 등 기본적인 정보는 나와줘야 하는것 아닌가?"*

## 무엇을 적고 무엇을 안 적나

| | |
|---|---|
| **적는다** | 곡 제목 · **도시와 구간**(`도시 구간.json` 에서 읽는다) · **어느 재즈인가** · 흐른 시각 |
| **안 적는다** | **화음 이름.** 우리 악보에서 나온 음원이 아니라 **`chordlog.npy` 가 없다.** 소리에서 화음을 추정하는 자를 아직 안 만들었고, **틀린 화음을 화면에 박느니 안 적는 게 낫다** |

**`자막생성.py` 는 못 쓴다** — 그 도구는 `전곡화성.py` 의 악보를 읽는다.

## 자검사 — 답을 아는 문제 셋

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 구간 여섯 | **자막 줄이 여섯 + 제목 하나** |
| 각 구간의 시각 | **json 의 시작·끝과 같다** (±0.01초) |
| 역슬래시 | `{\an5}` 가 **하나**로 나온다 — 둘이면 글자로 찍힌다 |
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

밑 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "..", "산출물", "20260829 - 재즈 2판")

제목 = "스페인 전람회의 그림 — 재즈판"
부제 = "Suno 로 다시 지은 별도 실험 · 승인된 곡과 영상은 안 건드렸다"

재즈 = {
    "프롬나드": "피아노 솔로 → 트리오",
    "마드리드 · 세고비아": "비밥 → 재즈 기타 · 노래",
    "세비야": "라틴",
    "론다": "더블베이스 듀오",
    "그라나다 · 바르셀로나": "마일즈 → 콜트레인",
    "위대한 문": "총주 + 목소리",
}


def 시각(t):
    return "%d:%02d:%05.2f" % (int(t // 3600), int(t % 3600 // 60), t % 60)


def 만들기(구간, 총길이):
    머리 = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: 제목,Malgun Gothic,46,&H00E8EEF6,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: 부제,Malgun Gothic,22,&H0090A0B8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: 도시,Malgun Gothic,40,&H0066C8FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: 갈래,Malgun Gothic,26,&H00C8D4E4,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: 구간,Malgun Gothic,22,&H007890A8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    줄 = []

    def 넣기(a, b, st, x, y, txt):
        # **r"..." 로 쓴다.** 그냥 쓰면 파이썬이 \\a 를 벨 문자(0x07)로 바꿔
        # {\\an5} 가 {<BEL>n5} 로 나가고 **자막이 통째로 안 붙는다** (2026-08-29).
        줄.append(r"Dialogue: 0,%s,%s,%s,,0,0,0,,{\an5\pos(%d,%d)}%s"
                  % (시각(a), 시각(b), st, x, y, txt))

    # 제목은 처음부터 끝까지
    넣기(0, 총길이, "제목", 960, 70, 제목)
    넣기(0, 총길이, "부제", 960, 110, 부제)

    for g in 구간:
        도시 = g["도시"]
        a, b = g["시작"], g["끝"]
        넣기(a, b, "도시", 960, 190, 도시)
        넣기(a, b, "갈래", 960, 235, 재즈.get(도시, ""))
        넣기(a, b, "구간", 960, 900,
             "%d:%05.2f ~ %d:%05.2f   ·   %.0f초"
             % (int(a // 60), a % 60, int(b // 60), b % 60, b - a))
    return 머리 + "\n".join(줄) + "\n"


def 자검사(구간, 총길이, 글):
    실패 = []
    if 글.count("Dialogue:") != 2 + len(구간) * 3:
        실패.append("① 자막 줄이 %d개 (기대 %d)"
                    % (글.count("Dialogue:"), 2 + len(구간) * 3))
    for g in 구간:
        if 시각(g["시작"]) not in 글 or 시각(g["끝"]) not in 글:
            실패.append("② %s 의 시각이 안 들어갔다" % g["도시"])
    # **바이트를 본다.** 「글자로 보인다」가 아니라 실제로 무엇이 들어갔는가다.
    if chr(7) in 글:
        실패.append("③ 벨 문자(0x07) 가 들어갔다 — a 가 escape 됐다")
    표 = "{" + chr(92) + "an5" + chr(92) + "pos("
    if 글.count(표) != 2 + len(구간) * 3:
        실패.append("③ 위치 지정이 줄 수만큼 없다 — %d개" % 글.count(표))
    return 실패


if __name__ == "__main__":
    with open(os.path.join(밑, "도시 구간.json"), encoding="utf-8") as f:
        j = json.load(f)
    구간, 총길이 = j["구간"], j["총길이"]
    글 = 만들기(구간, 총길이)

    실패 = 자검사(구간, 총길이, 글)
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 자막을 안 쓴다.")
    print("   → 통과 3/3\n")

    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "재즈자막.ass")
    with open(p, "w", encoding="utf-8") as f:
        f.write(글)
    print("재즈자막.ass  구간 %d개 · 총 %.2f초" % (len(구간), 총길이))
    for g in 구간:
        print("   %-22s %6.2f ~ %7.2f   %s"
              % (g["도시"], g["시작"], g["끝"], 재즈.get(g["도시"], "")))
