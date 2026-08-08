# -*- coding: utf-8 -*-
"""
화성 검토용 자막(ASS) 생성 — 유튜브 업로드용 영상에 번인한다.
chordlog.npy 에서 화음 심볼과 실제 보이싱을 읽어, 지금 울리는 화음과
네 성부의 음이름을 화면에 띄운다. 성부 진행이 눈으로 확인된다.
"""
import numpy as np

TOTAL = 580.0
W, H = 1920, 1080

# ── 표기 변환 : 프로그램 내부 표기 → 악보 표기
FLAT = {"Bb": "B♭", "Eb": "E♭", "Ab": "A♭", "Db": "D♭", "Gb": "G♭"}
NOTE = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]


def sym_fmt(s):
    """'Ebmaj7/G' → 'E♭maj7/G',  'Dphr' → 'D(F♯·♭9)'"""
    def root(r):
        return FLAT.get(r, r)
    if "/" in s:
        a, b = s.split("/")
        return sym_fmt(a) + "/" + root(b)
    i = 2 if len(s) > 1 and s[1] in "#b" else 1
    r, q = s[:i], s[i:]
    q = {"phr": "(F♯ ♭9)", "7b9": "7♭9", "maj7": "maj7", "maj9": "maj9",
         "7sus4": "7sus4", "sus4": "sus4", "m7": "m7", "m9": "m9",
         "m11": "m11", "6": "6", "7": "7", "m": "m", "": ""}.get(q, q)
    return root(r) + q


def notes_fmt(v):
    """(53,58,62,65) → 'F3  B♭3  D4  F4'"""
    out = []
    for m in v:
        out.append("%s%d" % (NOTE[m % 12], m // 12 - 1))
    return "   ".join(out)


def tc(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


# ── 악장 마커 (전곡화성.py 의 MARK 출력과 동일) ────────────────
MOV = [
    (0.0, 50.0, "0악장  Promenade 제시", "B♭ 이오니안 · ♩=100 · 주제 A"),
    (50.0, 90.0, "1악장  마드리드", "B♭ 이오니안 · ♩=138 · ii–V–I · 그녀는 없다"),
    (90.0, 105.0, "2악장  Promenade 변주 I", "나일론 기타 둘 · 두 번째 발소리"),
    (105.0, 160.0, "3악장  세고비아", "G 에올리안 · ♩=72 · 코랄 · 하강 4음 G–F–E♭–D"),
    (160.0, 260.0, "4악장  세비야", "D 프리지안 · 12박 컴파스 · 주제 B 탄생 · 베이스가 멈춘다"),
    (260.0, 275.0, "5악장  Promenade 변주 II", "두 주제 겹침 · D7♭9 · 불협 미해소"),
    (275.0, 325.0, "6악장  론다", "E♭ 리디안 · ♩=56 · 비움으로 만드는 광활함"),
    (325.0, 425.0, "7악장  그라나다", "D 프리지안 · 6/8 · ♭II–i 종지 · 무그 = 그녀의 목소리"),
    (425.0, 525.0, "8악장  바르셀로나", "7/8 (2+2+3) · ♩=176 · 주제 B 파편화"),
    (525.0, 580.0, "9악장  The Great Gate", "B♭ 이오니안 · ♩=63 · 플라갈 · 두 주제 총주"),
]

# ── 청취 지점 주석 ───────────────────────────────────────────
CUE = [
    (11.5, 16.0, "베이스가 현악·오르간보다 먼저 들어온다 — 첫 화음의 조성을 선포"),
    (105.0, 111.0, "하강 4음 G–F–E♭–D — 4악장 안달루시아 종지와 같은 진행 (씨앗)"),
    (167.1, 173.0, "주제 B 첫 등장 — 나일론 기타 독주, 반주는 팔마스뿐"),
    (173.8, 180.0, "컴파스 3단계로 쌓인다 · 베이스는 강세 자리에만 — 걷기를 멈췄다"),
    (275.0, 282.0, "E♭ 리디안 — E♭maj9 ↔ F 가 어디로도 해결되지 않는다"),
    (325.0, 332.0, "E♭maj7 → Dm 프리지안 종지 · 주제 A는 이 악장에서 침묵한다"),
    (566.0, 569.0, "D–F♯–A   그녀의 색채 (F♯)"),
    (569.0, 572.0, "D–F–A    F♯이 F로 내려앉는다"),
    (572.0, 579.5, "B♭–D–F–A   B♭장조로 편입 — 상실이 아니라 편입이다"),
]

TITLE = "《스페인 전람회의 그림》   전곡 코드 진행  v1.4"
SUB = "화성 검토용 · 성부 진행 자동 최적화 · 병행 5·8도 0건 · 평균 이동 3.93반음"

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
Style: Chord,DejaVu Sans Mono,100,&H00A8D8F0,&H00FFFFFF,&H96000000,&H00000000,1,0,0,0,100,100,4,0,1,4,0,2,64,64,118,1
Style: Voice,DejaVu Sans Mono,40,&H00929CAA,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,7,0,1,3,0,2,64,64,72,1
Style: Legend,Noto Sans CJK KR,23,&H00707C8A,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,9,64,64,44,1
Style: Cue,Noto Sans CJK KR,32,&H0090C8E8,&H00FFFFFF,&H96000000,&H00000000,0,0,0,0,100,100,1,0,1,3,0,2,64,64,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (W, H)


POS = {"Chord": "{\\an5\\pos(960,872)}", "Voice": "{\\an5\\pos(960,952)}",
       "Cue": "{\\an5\\pos(960,1026)}", "Mov": "{\\an4\\pos(64,224)}",
       "MovSub": "{\\an4\\pos(68,282)}", "Title": "{\\an4\\pos(64,60)}",
       "Sub": "{\\an4\\pos(64,110)}", "Legend": "{\\an6\\pos(1856,60)}",
       "Legend2": "{\\an6\\pos(1856,106)}"}


def ev(style, a, b, text, layer=0):
    st = "Legend" if style.startswith("Legend") else style
    return "Dialogue: %d,%s,%s,%s,,0,0,0,,%s%s\n" % (
        layer, tc(a), tc(b), st, POS.get(style, ""), text)


lines = [HEAD]
lines.append(ev("Title", 0.0, TOTAL, TITLE))
lines.append(ev("Sub", 0.0, TOTAL, SUB))
lines.append(ev("Legend", 0.0, TOTAL, "음정축 — 밝은 건반 = 이 곡의 음집합  B♭ C D E♭ F G A"))
lines.append(ev("Legend2", 0.0, TOTAL, "붉은 건반 = F♯  ·  이 곡의 유일한 조성 밖 음"))

for a, b, name, desc in MOV:
    lines.append(ev("Mov", a, b, name))
    lines.append(ev("MovSub", a, b, desc))

log = np.load("chordlog.npy", allow_pickle=True)
log = sorted([(float(r[0]), str(r[1]), tuple(r[2])) for r in log], key=lambda r: r[0])
n = 0
for i, (t, sym, v) in enumerate(log):
    end = log[i + 1][0] if i + 1 < len(log) else TOTAL
    if end - t < 0.25:                      # 너무 짧으면 건너뛴다 (읽을 수 없다)
        continue
    end = min(end, TOTAL)
    lines.append(ev("Chord", t, end, sym_fmt(sym)))
    lines.append(ev("Voice", t, end, notes_fmt(v)))
    n += 1

for a, b, txt in CUE:
    lines.append(ev("Cue", a, b, txt, layer=1))

open("자막.ass", "w", encoding="utf-8").write("".join(lines))
print("자막.ass 생성 — 화음 %d개 · 악장 %d개 · 청취 지점 %d개" % (n, len(MOV), len(CUE)))
print("첫 화음 %s   마지막 화음 %.1fs %s" %
      (sym_fmt(log[0][1]), log[-1][0], sym_fmt(log[-1][1])))
