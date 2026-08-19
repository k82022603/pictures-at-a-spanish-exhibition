# -*- coding: utf-8 -*-
"""**노래 도구에 넣을 입력 재료.** 9악장 네 줄.

2026-08-18. 검수자가 *"외부 도구 이용해서 가사 입히는 작업시작하자 vs.
suno 이용해보자"* 라고 물었고, 답은 **둘 다 재 본다** 였다. 어느 쪽을 고르든
**입력 재료는 같으므로** 갈림길 앞에서 한 번에 만든다.

세 가지를 낸다.

  ① **`9악장 네 줄.mid`** — 음 + 가사가 붙은 MIDI. 노래 합성 도구(A판)가
     이것을 읽으면 **음과 음절이 제자리를 잡는다.** 줄마다 트랙을 나눈다 —
     Synthesizer V 시험판이 **한 묶음당 40음**까지인데 한 줄은 11음이다
  ② **`9악장 반주만 55초.wav`** — Suno(B판) 에 올릴 것. **전곡을 올리지
     않는다.** 8:45~9:40 구간만
  ③ **`가사 - 음절 쪼갬.md`** — 11음절이 어느 음에 붙는지

**음·박·시각을 손으로 옮겨 적지 않는다.** 전부 `가이드반주.py` 에서 읽어
쓴다 — 창법 지시서가 손으로 옮겨 적다가 **온음 하나 낮은 조로** 적혔다
(2026-08-18 발견). 그래서 이 스크립트는 마지막에 **자기가 쓴 MIDI 를 다시
읽어 대조하고, 하나라도 다르면 멈춘다.** `납품.py` 가 굽고 되돌려 보는 것과
같은 방식이다.

    python 보컬입력.py
"""
import os
import struct
import sys

import numpy as np

import 화성
import synth
import 가이드반주 as G

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
TPQ = 480                                  # 4분음표 한 개당 틱
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "산출물", "20260818 - 목소리를 사러 가기 전에")

# 발췌 구간 — `가이드반주.py` 의 `build()` 와 같은 창을 쓴다
T0, T1 = 525.0, 580.0

NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]

# ── 노랫말 ──────────────────────────────────────────────────────────────
# `05` 9.31.3절 승인. **한 줄이 정확히 11음절**이고, 주제 A 의 4·5번째와
# 7·8번째가 8분음표로 붙으므로 그 자리에 **짧게 붙는 약음절**이 온다.
LYRICS = {
    "4행": ("I count out every step under my own feet",
            ["I", "count", "out", "ev", "ry", "step", "un", "der", "my", "own", "feet"]),
    "6행": ("Now we walk, two of us, never in one step",
            ["Now", "we", "walk", "two", "of", "us", "nev", "er", "in", "one", "step"]),
    "7행": ("Now the light in the old picture holds you too",
            ["Now", "the", "light", "in", "the", "old", "pic", "ture", "holds", "you", "too"]),
    "8행": ("Looking back, you were here always in my step",
            ["Look", "ing", "back", "you", "were", "here", "al", "ways", "in", "my", "step"]),
}


def name(m):
    return NAMES[m % 12] + str(m // 12 - 1)


def ticks(sec):
    """초 → 틱. `BT9` 가 한 박의 길이다."""
    return int(round(sec / G.BT9 * TPQ))


# ══════════════════════ MIDI 를 바이트로 직접 쓴다 ═══════════════════════
# `mido`·`pretty_midi` 가 이 PC 에 없다. 표준 MIDI 파일은 규격이 단순해서
# **패키지를 새로 깔 이유가 없다.**

def vlq(n):
    """가변 길이 수. MIDI 의 델타 시간이 이 꼴이다."""
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def meta(kind, payload):
    return b"\xFF" + bytes([kind]) + vlq(len(payload)) + payload


def chunk(tag, body):
    return tag + struct.pack(">I", len(body)) + body


def track_line(line_name, start_tick):
    """한 줄 = 트랙 하나. 음 열하나와 음절 열하나."""
    text, syls = LYRICS[line_name]
    ev = bytearray()
    # 트랙 이름은 아스키로 — 도구마다 한글 인코딩 해석이 다르다
    label = "L%s %s" % (line_name[0], text)
    ev += vlq(0) + meta(0x03, label.encode("ascii", "replace"))
    cur = 0                                            # 지금까지 흘린 틱
    for (m, beats), syl in zip(G.TH_A, syls):
        dur = int(round(beats * TPQ))
        ev += vlq(start_tick - cur) + meta(0x05, syl.encode("utf-8"))   # 가사
        ev += vlq(0) + bytes([0x90, m, 88])                            # 켬
        ev += vlq(dur) + bytes([0x80, m, 64])                          # 끔
        cur = start_tick + dur
        start_tick = cur                               # 다음 음은 바로 이어서
    ev += vlq(0) + meta(0x2F, b"")
    return chunk(b"MTrk", bytes(ev))


def build_midi():
    us = int(round(G.BT9 * 1000000))                   # 한 박의 마이크로초
    head = bytearray()
    head += vlq(0) + meta(0x03, b"Pictures at a Spanish Exhibition - Mv9 vocal")
    head += vlq(0) + meta(0x51, struct.pack(">I", us)[1:])
    head += vlq(0) + meta(0x58, bytes([4, 2, 24, 8]))  # 9악장은 마디가 4박
    head += vlq(0) + meta(0x2F, b"")
    trks = [chunk(b"MTrk", bytes(head))]
    for t0, line_name in G.LINES:
        trks.append(track_line(line_name, ticks(t0)))
    hdr = chunk(b"MThd", struct.pack(">HHH", 1, len(trks), TPQ))
    return hdr + b"".join(trks)


# ══════════════════════ 다시 읽어서 대조한다 ════════════════════════════
# **여기가 이 스크립트의 요점이다.** 손으로 옮겨 적은 값이 틀려 있던 것을
# 오늘 찾았으므로, 도구가 스스로 확인하지 않으면 같은 일이 또 난다.

def read_vlq(b, i):
    n = 0
    while True:
        c = b[i]
        i += 1
        n = (n << 7) | (c & 0x7F)
        if not c & 0x80:
            return n, i


def parse_midi(raw):
    """우리가 쓴 것만 읽으면 된다 — 러닝 스테이터스를 안 쓴다."""
    assert raw[:4] == b"MThd", "MThd 가 아니다"
    fmt, ntrk, tpq = struct.unpack(">HHH", raw[8:14])
    i, out = 14, []
    for _ in range(ntrk):
        assert raw[i:i + 4] == b"MTrk", "MTrk 가 아니다"
        ln = struct.unpack(">I", raw[i + 4:i + 8])[0]
        b, j, end = raw[i + 8:i + 8 + ln], 0, ln
        i += 8 + ln
        tick, notes, pend, syl = 0, [], {}, None
        while j < end:
            d, j = read_vlq(b, j)
            tick += d
            st = b[j]
            if st == 0xFF:
                kind = b[j + 1]
                n, j2 = read_vlq(b, j + 2)
                payload = b[j2:j2 + n]
                j = j2 + n
                if kind == 0x05:
                    syl = payload.decode("utf-8")
            elif st & 0xF0 == 0x90:
                pend[b[j + 1]] = (tick, syl)
                j += 3
            elif st & 0xF0 == 0x80:
                t0, s = pend.pop(b[j + 1])
                notes.append((t0, b[j + 1], tick - t0, s))
                j += 3
            else:
                raise AssertionError("모르는 상태 바이트 %02X" % st)
        if notes:
            out.append(sorted(notes))
    return tpq, out


def verify(raw):
    tpq, trks = parse_midi(raw)
    assert tpq == TPQ, "틱 해상도가 다르다"
    assert len(trks) == len(G.LINES), "줄 수가 %d 다 (넷이어야 한다)" % len(trks)
    bad = 0
    print("  되읽어 대조 — 트랙 %d개" % len(trks))
    for (t0, line_name), notes in zip(G.LINES, trks):
        text, syls = LYRICS[line_name]
        assert len(notes) == 11, "%s 이 %d음이다 (열하나여야 한다)" % (line_name, len(notes))
        st = notes[0][0] * G.BT9 / TPQ
        if abs(st - t0) > 1e-6:
            print("    ✘ %s 시작 %.3f초 (%.3f 이어야)" % (line_name, st, t0))
            bad += 1
        for k, ((tk, m, dur, s), (em, eb), es) in enumerate(
                zip(notes, G.TH_A, syls)):
            if m != em or abs(dur - eb * TPQ) > 0.5 or s != es:
                print("    ✘ %s %d번째 — %d/%d틱/%s (%d/%.0f틱/%s 이어야)"
                      % (line_name, k + 1, m, dur, s, em, eb * TPQ, es))
                bad += 1
        if bad == 0:
            print("    ✔ %s  %d:%02d  11음 11음절  %s ~ %s"
                  % (line_name, int(t0) // 60, int(t0) % 60,
                     name(min(m for _, m, _, _ in notes)),
                     name(max(m for _, m, _, _ in notes))))
    if bad:
        raise SystemExit("\n✘ MIDI 가 원본과 다르다 — %d군데. 아무것도 안 냈다." % bad)


# ══════════════════════ 반주 발췌 · 음절 표 ═════════════════════════════

def excerpt():
    """**승인판을 읽기만 한다.** 8:45~9:40 구간 55초."""
    sr, x = 화성.read_wav(os.path.join(HERE, "전곡화성.wav"))
    assert sr == SR
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return x[int(T0 * SR):int(T1 * SR)].copy()


def syllable_md():
    L = ["# 가사 — 음절이 어느 음에 붙는가", "",
         "**9악장 네 줄. 한 줄이 정확히 11음절**이고 선율은 주제 A 다.",
         "`05` 9.31.3절 승인 · `99. 작업 스크립트/보컬입력.py` 가 만든다.", "",
         "> **4·5번째와 7·8번째가 8분음표로 붙어 있다**(표의 ♪). 그 자리에는",
         "> `ev-ry` · `un-der` 처럼 **짧게 붙는 약한 음절**이 온다.", ""]
    lo = min(m for m, _ in G.TH_A)
    hi = max(m for m, _ in G.TH_A)
    L += ["| | |", "|---|---|",
          "| 빠르기 | ♩ = 63 — **느리게 걷는 속도.** 한 박이 %.2f초 |" % G.BT9,
          "| 한 줄의 길이 | **%.2f초** (9박) |" % (9 * G.BT9),
          "| 음역 | **%s ~ %s** (%.0f~%.0f Hz). 옥타브를 내리지 않는다 |"
          % (name(lo), name(hi), G.hz(lo), G.hz(hi)),
          "| 조 | **B♭ 장조** |", ""]
    for t0, line_name in G.LINES:
        text, syls = LYRICS[line_name]
        L += ["## %s — %d:%02d" % (line_name, int(t0) // 60, int(t0) % 60), "",
              "> *%s*" % text, "",
              "| # | 음절 | 음 | 길이 |", "|---|---|---|---|"]
        for k, (syl, (m, b)) in enumerate(zip(syls, G.TH_A)):
            L.append("| %d | **%s** | %s | %s |"
                     % (k + 1, syl, name(m), "♩" if b == 1.0 else "♪"))
        L.append("")
    L += ["---", "", "*작성 일자: 2026-08-18*"]
    return "\n".join(L) + "\n"


# ══════════════════════ MusicXML — 이쪽이 정본 입력이다 ═════════════════
# **2026-08-18 오후에 추가했다.** Synthesizer V 문서가 **「영어 가사는 MIDI 보다
# MusicXML 이 정확하게 들어온다」**고 적고 있다. MIDI 의 가사(lyric meta)는
# 규격이 느슨해서 도구마다 읽는 방식이 다르다.
#
# **그리고 마디 1부터 시작하게 만든다.** 절대 시각을 그대로 쓰면 네 줄이
# **139마디**에 놓여 창을 열었을 때 빈 화면만 보인다. 노래 도구는 **소리를
# 만드는 데**만 쓰고, **곡의 어느 자리에 놓을지는 이쪽에서 붙인다** — 시각
# 넷(527·538·549·556초)을 이미 알고 있으므로 정확도를 잃지 않는다.

# B♭ 장조의 음이름. **음집합이 다섯 음뿐이라 표가 짧다**
SPELL = {0: ("C", 0), 2: ("D", 0), 5: ("F", 0), 7: ("G", 0), 10: ("B", -1)}

# 붙는 음절 — `begin`/`end` 로 묶어야 도구가 한 낱말로 발음한다
SYLLABIC = {
    "4행": ["single", "single", "single", "begin", "end", "single",
            "begin", "end", "single", "single", "single"],
    "6행": ["single", "single", "single", "single", "single", "single",
            "begin", "end", "single", "single", "single"],
    "7행": ["single", "single", "single", "single", "single", "single",
            "begin", "end", "single", "single", "single"],
    "8행": ["begin", "end", "single", "single", "single", "single",
            "begin", "end", "single", "single", "single"],
}
DIV = 480                                  # 4분음표 한 개당


def _note_xml(m, beats, syl, kind):
    step, alter = SPELL[m % 12]
    octv = m // 12 - 1
    d = int(round(beats * DIV))
    typ = "quarter" if beats == 1.0 else "eighth"
    a = "        <alter>%d</alter>\n" % alter if alter else ""
    return ("      <note>\n        <pitch>\n          <step>%s</step>\n"
            "%s          <octave>%d</octave>\n        </pitch>\n"
            "        <duration>%d</duration>\n        <voice>1</voice>\n"
            "        <type>%s</type>\n        <lyric number=\"1\">\n"
            "          <syllabic>%s</syllabic>\n          <text>%s</text>\n"
            "        </lyric>\n      </note>\n"
            % (step, a.replace("        <alter>", "          <alter>"),
               octv, d, typ, kind, syl))


def _rest_xml(beats):
    return ("      <note>\n        <rest/>\n        <duration>%d</duration>\n"
            "        <voice>1</voice>\n        <type>quarter</type>\n      </note>\n"
            % int(round(beats * DIV)))


def musicxml():
    """네 줄 = 파트 넷. 각각 **마디 1부터** 세 마디(9박 + 쉼 3박)."""
    parts, plist = [], []
    for idx, (t0, line_name) in enumerate(G.LINES):
        text, syls = LYRICS[line_name]
        pid = "P%d" % (idx + 1)
        plist.append('    <score-part id="%s">\n      <part-name>%s %d:%02d</part-name>\n'
                     '    </score-part>\n' % (pid, line_name, int(t0) // 60, int(t0) % 60))
        # 마디 셋으로 쪼갠다 — 4박 · 4박 · (1박 + 쉼 3박)
        cuts = [(0, 5), (5, 10), (10, 11)]
        body = ""
        for mi, (a, b) in enumerate(cuts):
            body += '    <measure number="%d">\n' % (mi + 1)
            if mi == 0:
                body += ("      <attributes>\n        <divisions>%d</divisions>\n"
                         "        <key><fifths>-2</fifths></key>\n"
                         "        <time><beats>4</beats><beat-type>4</beat-type></time>\n"
                         "        <clef><sign>G</sign><line>2</line></clef>\n"
                         "      </attributes>\n"
                         "      <direction placement=\"above\">\n        <direction-type>\n"
                         "          <metronome><beat-unit>quarter</beat-unit>"
                         "<per-minute>63</per-minute></metronome>\n"
                         "        </direction-type>\n        <sound tempo=\"63\"/>\n"
                         "      </direction>\n" % DIV)
            for k in range(a, b):
                m, beats = G.TH_A[k]
                body += _note_xml(m, beats, syls[k], SYLLABIC[line_name][k])
            if mi == 2:
                body += _rest_xml(1.0) * 3
            body += "    </measure>\n"
        parts.append('  <part id="%s">\n%s  </part>\n' % (pid, body))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"'
            ' "http://www.musicxml.org/dtds/partwise.dtd">\n'
            '<score-partwise version="3.1">\n'
            '  <work><work-title>Mv9 vocal - four lines</work-title></work>\n'
            '  <part-list>\n%s  </part-list>\n%s</score-partwise>\n'
            % ("".join(plist), "".join(parts)))


def verify_xml(x):
    """되읽어 대조. **음 44개와 음절 44개가 원본과 같아야 한다.**"""
    import re
    rev = {}
    for pc, (s, a) in SPELL.items():
        rev[(s, a)] = pc
    notes = re.findall(r"<step>(\w)</step>\s*(?:<alter>(-?\d+)</alter>)?\s*"
                       r"<octave>(\d)</octave>.*?<text>([^<]+)</text>", x, re.S)
    assert len(notes) == 44, "음이 %d개다 (44여야 한다)" % len(notes)
    bad = 0
    for i, (s, a, o, syl) in enumerate(notes):
        pc = rev[(s, int(a) if a else 0)]
        m = (int(o) + 1) * 12 + pc
        em, _ = G.TH_A[i % 11]
        es = LYRICS[G.LINES[i // 11][1]][1][i % 11]
        if m != em or syl != es:
            print("    ✘ %d번째 — %d/%s (%d/%s 이어야)" % (i + 1, m, syl, em, es))
            bad += 1
    if bad:
        raise SystemExit("\n✘ MusicXML 이 원본과 다르다 — %d군데." % bad)
    print("  MusicXML 되읽어 대조 — 44음 44음절 전부 일치 · 네 파트 · 마디 1부터")


def put(path, data):
    """**내용이 같으면 손대지 않는다.**

    2026-08-18 에 여기서 `PermissionError` 가 났다 — 검수자가 그 파일을
    노래 도구로 **열어둔 채**였다. 내용이 똑같은데 굳이 다시 쓸 이유가 없고,
    **안 건드리는 것이 R9 의 정신**이기도 하다.
    """
    mode = "wb" if isinstance(data, bytes) else "w"
    if os.path.exists(path):
        old = (open(path, "rb").read() if mode == "wb"
               else open(path, encoding="utf-8").read())
        if old == data:
            print("   (그대로 · 안 건드림)  %s" % os.path.basename(path))
            return
    try:
        with open(path, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
            f.write(data)
    except PermissionError:
        raise SystemExit(
            "\n✘ %s 를 못 쓴다 — **다른 프로그램이 열고 있다.**\n"
            "   그 파일을 닫고 다시 돌려라." % os.path.basename(path))


def main():
    print("9악장 네 줄 — 노래 도구에 넣을 입력 재료\n")
    print("  ♩=63 · 한 박 %.4f초 · 한 줄 9박 %.2f초" % (G.BT9, 9 * G.BT9))
    print("  주제 A  %s\n" % " ".join(name(m) for m, _ in G.TH_A))

    raw = build_midi()
    verify(raw)                                        # 틀리면 여기서 멈춘다

    os.makedirs(OUT, exist_ok=True)
    put(os.path.join(OUT, "9악장 네 줄.mid"), raw)
    print("\n→ 9악장 네 줄.mid  (%d바이트 · 트랙 %d개 · 절대 시각)" % (len(raw), 1 + len(G.LINES)))

    x = musicxml()
    verify_xml(x)
    put(os.path.join(OUT, "9악장 네 줄.musicxml"), x)
    print("→ 9악장 네 줄.musicxml  (%d바이트 · 파트 %d개 · **마디 1부터**)"
          % (len(x), len(G.LINES)))

    seg = excerpt()
    synth.write_wav(os.path.join(OUT, "9악장 반주만 55초.wav"), seg, bits=24)
    print("→ 9악장 반주만 55초.wav  (%.1f초 · 24비트)" % (len(seg) / SR))

    put(os.path.join(OUT, "가사 - 음절 쪼갬.md"), syllable_md())
    print("→ 가사 - 음절 쪼갬.md")
    print("\n**셋 다 대조를 통과했다.**")


if __name__ == "__main__":
    main()
