# -*- coding: utf-8 -*-
"""**Suno 판 검토 영상의 자막(ASS).**

2026-08-22 신설.

## `자막생성.py` 를 왜 못 쓰나

그 도구는 **`chordlog.npy`** 를 읽는다 — **`전곡화성.py` 가 악보를 소리로 구우면서
「지금 무슨 화음을 울리고 있다」를 함께 적어둔 파일**이다. 그래서 화면에 뜨는 화음
심볼과 네 성부의 음이름이 **틀릴 수가 없다. 연주한 쪽이 직접 적은 것**이기 때문이다.

**Suno 판에는 그 파일이 없다. 악보가 없고 소리만 있다.**

**그런데 그대로 돌리면 자막이 나오기는 한다** — 우리 악보의 화음이. **길이도 비슷하고
악장 이름도 그럴듯해서 얼핏 맞아 보인다.** 그것이 위험한 이유다.

> **「도구가 성공했다」와 「그 결과가 이 음원에 맞다」는 다른 말이다.**
> 같은 날 `납품.py` 가 우리 구간표를 Suno 음원 옆에 붙일 뻔했고, 거기서도 막았다.

## 그래서 무엇을 띄우나

**소리에서 나온 것만.** 화음 심볼과 성부 음이름을 뺀 자리에 —

* **악장 이름과 구간** — 경계는 우리가 쟀다
* **★ 그 경계를 어떻게 알았나** — 확실 / 강함 / 약함을 **화면에 적는다.**
  추정을 사실처럼 보이게 하지 않는 것이 이 자막의 요지다
* 청취 지점

**CQT 스펙트럼은 그대로 쓴다** — 그것은 소리에서 직접 계산되므로 악보가 필요 없다.
F♯ 붉은 건반도 의미가 살아 있다.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

TOTAL = 619.84
W, H = 1920, 1080
OUT = "자막Suno.ass"

# ── 악장 — 전곡 E 실측 (`구간표 - 전곡 E 10m20s.md` 가 정본) ──────────
#
# 넷째 칸이 **경계를 어떻게 알았나**다. 이 자막의 핵심이고, 다른 어떤 검토
# 영상에도 없던 칸이다. **우리 곡이 아니라 남이 연주한 것을 재고 있기 때문**이다.
MOV = [
 (0.00,  70.53, "0악장  Promenade 제시", "★ 오늘 고쳤다 — 맺고 4.3초에 걸쳐 사그라든다", None),
 (70.53, 128.50, "1악장  마드리드", "B♭ 이오니안 · 이 곡에서 유일하게 기능화성이 또렷하다", "확실 — 조각 경계"),
 (128.50, 155.50, "2악장  Promenade 변주 I", "나일론 기타 캐논 · 두 번째 발소리", "약함 — 자로만 쟀다"),
 (155.50, 184.62, "3악장  세고비아", "★ 오늘 고쳤다 — 3.1초에 걸쳐 사그라든다", "약함 — 자로만 쟀다"),
 (184.62, 280.75, "4악장  세비야", "D 프리지안 · 12박 컴파스 · 주제 B 탄생 · 베이스가 멈춘다", "확실 — 조각 경계"),
 (280.75, 315.75, "5악장  Promenade 변주 II", "두 주제 첫 겹침 · 불협을 해소하지 않는다", "강함 — 자와 A판이 일치"),
 (315.75, 350.08, "6악장  론다", "E♭ 리디안 · ★ 곡의 바닥이어야 하는데 지금은 가장 크다", "강함 — 자와 A판이 일치"),
 (350.08, 468.00, "7악장  그라나다", "D 프리지안 · 무그가 그녀의 목소리 · 주제 A는 침묵", "확실 — 조각 경계"),
 (468.00, 549.98, "8악장  바르셀로나", "7/8 (2+2+3) · 주제 B 파편화 · 가장 격렬하다", "강함 — 귀와 자가 따로 일치했다"),
 (549.98, 619.84, "9악장  The Great Gate", "플라갈 · 두 주제 총주 · 종결부는 Suno 가 만들어 붙였다", "확실 — 조각 경계"),
]

# ── 청취 지점 ────────────────────────────────────────
CUE = [
 (2.0,  30.0, "여기가 「잡음」이던 자리 — 이제 원본과 같은 소리다"),
 (37.0, 42.0, "0:39.0 — 원본에서 Suno 가 만든 종결로 넘어간다"),
 (63.0, 75.0, "★ 오늘 고친 첫 자리 — 한 마디를 끝내고 잦아든 뒤 드럼이 들어온다"),
 (178.0, 190.0, "★ 오늘 고친 둘째 자리 — 오르간이 사라진 빈자리 뒤에 손뼉이 들어온다"),
 (342.0, 350.0, "★ 론다가 가장 커지는 자리 — 여기가 곡에서 제일 조용해야 한다"),
 (464.0, 472.0, "그라나다 → 바르셀로나. 검수자가 귀로 짚었고 자가 따로 같은 곳을 가리켰다"),
 (605.0, 619.8, "곡이 사그라들며 끝난다 — 4부 Suno-03 이 스스로 만든 종결부"),
]

HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: %d
PlayResY: %d
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Noto Sans CJK KR,40,&H00E8E4DC,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,7,64,64,44,1
Style: Sub,Noto Sans CJK KR,25,&H00808A96,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,7,64,64,96,1
Style: Mov,Noto Sans CJK KR,64,&H00F2EFE6,&H00FFFFFF,&H96000000,&H00000000,1,0,0,0,100,100,2,0,1,3,0,7,64,64,160,1
Style: MovSub,Noto Sans CJK KR,30,&H009AA7B4,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,7,68,64,246,1
Style: Src,Noto Sans CJK KR,26,&H0078C8A0,&H00FFFFFF,&H96000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,7,68,64,246,1
Style: Span,DejaVu Sans Mono,44,&H00A8D8F0,&H00FFFFFF,&H96000000,&H00000000,1,0,0,0,100,100,3,0,1,3,0,2,64,64,118,1
Style: Legend,Noto Sans CJK KR,23,&H00707C8A,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,9,64,64,44,1
Style: Cue,Noto Sans CJK KR,32,&H0090C8E8,&H00FFFFFF,&H96000000,&H00000000,0,0,0,0,100,100,1,0,1,3,0,2,64,64,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (W, H)

# **`\\pos()` 로 자리를 못박는다.** libass 는 같은 시각에 겹치는 자막을
# 충돌 회피로 위아래로 밀어내는데, 그러면 순서가 뒤집힌다.
POS = {"Title": "{\\an4\\pos(64,60)}", "Sub": "{\\an4\\pos(64,112)}",
       "Mov": "{\\an4\\pos(64,224)}", "MovSub": "{\\an4\\pos(68,282)}",
       "Src": "{\\an6\\pos(1856,282)}", "Span": "{\\an5\\pos(960,880)}",
       "Legend": "{\\an6\\pos(1856,60)}", "Cue": "{\\an5\\pos(960,1026)}"}


def ts(t):
    t = max(0.0, min(t, TOTAL))
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def ev(a, b, style, text):
    return "Dialogue: 0,%s,%s,%s,,0,0,0,,%s%s" % (ts(a), ts(b), style, POS[style], text)


def 분초(t):
    return "%d:%05.2f" % (int(t) // 60, t % 60)


def main():
    L = [HEAD.rstrip("\n")]
    L.append(ev(0, TOTAL, "Title", "스페인 전람회의 그림 — Suno 판 전곡 E · 10:19.84"))
    L.append(ev(0, TOTAL, "Sub",
                "48 kHz · float32 · 전체 −16.7 dB · 피크 −1.6 dBFS   |   "
                "조각 다섯을 이은 것 — 0악장 · 1부b · 2부 · 3부 · 4부"))
    L.append(ev(0, TOTAL, "Legend",
                "밝은 건반 = 이 곡의 음집합 B♭ C D E♭ F G A   ·   "
                "붉은 건반 = F♯ (유일한 조성 밖 음 · 그녀의 색채)"))
    for a, b, 이름, 설명, 근거 in MOV:
        L.append(ev(a, b, "Mov", 이름))
        L.append(ev(a, b, "MovSub", 설명))
        L.append(ev(a, b, "Span", "%s ~ %s   (%.1f초)" % (분초(a), 분초(b), b - a)))
        if 근거:
            L.append(ev(a, b, "Src", "경계 " + 근거))
    for a, b, 글 in CUE:
        L.append(ev(a, b, "Cue", 글))
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("%s — 악장 %d · 청취 지점 %d · %.2f초" % (OUT, len(MOV), len(CUE), TOTAL))
    print("\n[경계 근거]")
    for _, _, 이름, _, 근거 in MOV:
        if 근거:
            print("  %-24s %s" % (이름, 근거))


if __name__ == "__main__":
    main()
