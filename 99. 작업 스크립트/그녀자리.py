# -*- coding: utf-8 -*-
"""**그녀(La Duende)가 나오는 자리를 음원에서 찾는다** — WBS 3.8.

## 왜 손으로 안 정하나

**`CLAUDE.md` V4 가 「AI 생성은 그녀에게만, 전곡에서 대여섯 곳」으로 못박았다.**
여섯 곳뿐이므로 **어디에 놓느냐가 전부**다. 그런데 그 자리 중 하나는
**「9:26 F♯→F 해소」**로 적혀 있고, **그것은 옛 9분 40초 판의 시각이다.**

**Suno 판(10:19.84)에서 그 순간이 언제인지는 재야 안다.** 손으로 옮겨 적으면
**옛 시각을 새 판에 붙이는 것**이 되고, 이 프로젝트가 여러 번 데인 자리다.

## 무엇을 재나

**F♯ 이 이 곡의 유일한 조성 밖 음이고 그녀의 색채다**(`CLAUDE.md` 6절).
9악장에서 **F♯ 이 F 로 내려앉으며** 주제 B 가 B♭장조로 편입된다 —
**상실이 아니라 편입.**

그래서 **9악장을 1초 창으로 썰어 F♯ 과 F 의 비중을 재고, F♯ 이 마지막으로
크게 울린 뒤 F 가 그것을 넘어서는 자리**를 찾는다.

## 자기검사 — 셋

**미달이면 멈춘다.** 자가 틀리면 그녀를 엉뚱한 자리에 세우게 된다.
"""
import io
import json
import os
import sys

import numpy as np
import scipy.signal as sg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성                                    # noqa: E402  read_wav

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

이름 = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]

# ── ★ **확정된 여섯 자리** (2026-08-24) ────────────────────────
#
# **자가 「언제」를 정하고, 사진이 「그 위에 설 수 있는가」를 정했다.**
# 둘은 F♯ 이 가장 큰 자리를 두고도 옮겼다 —
#
# | 옮긴 것 | 왜 |
# |---|---|
# | 7악장 7:37 → **6:56** | 7:37 의 컷이 **고양이 클로즈업**이다. 실루엣이 설 자리가 없다 |
# | 8악장 7:56 → **8:43** | 7:56 은 **사그라다 파밀리아 첨탑과 하늘**이다. 땅이 없다 |
#
# **V2(배경 변경 금지)가 여기서 실제로 작동한다** — 그녀를 넣을 수 있는 사진은
# **이미 사람이 설 만한 자리가 비어 있는 사진**뿐이다.
여섯 = [
    (3, 160.50, "씨앗 — 가장 약하다. 있는지 없는지 모를 만큼"),
    (5, 299.75, "★ 전곡에서 F♯ 이 가장 크다. 두 주제가 처음 겹치는 자리 — 따라온다"),
    (7, 416.08, "그라나다의 밤. 알함브라가 홀로 빛난다"),
    (7, 430.08, "★ 7악장 최대. 무그가 그녀의 목소리인 악장"),
    (8, 523.00, "주제 B 가 부서지는 악장. 몬세라트 광장"),
    (9, 595.98, "★★ 다음 1초에 F 가 0.5197 로 덮는다 — 사라지는 것이 아니라 편입"),
]
FS, F = 6, 5                                   # F♯ · F 의 반음 번호
창 = 1.0                                       # 1초


def 크로마(seg, sr):
    """반음 12개의 에너지 비중. `검증화성.py` 와 같은 방식이다."""
    n = 1 << 14
    if len(seg) < n:
        return np.zeros(12)
    f, t, Z = sg.stft(seg, sr, nperseg=n, noverlap=n // 2)
    P = (np.abs(Z) ** 2).mean(axis=1)
    ok = (f > 55) & (f < 4200)
    f, P = f[ok], P[ok]
    pc = np.rint(12 * np.log2(f / 440.0) + 69).astype(int) % 12
    c = np.array([P[pc == i].sum() for i in range(12)])
    s = c.sum()
    return c / s if s else c


def 자검사(sr):
    """**아는 소리를 넣어 본다.** 셋 다 맞아야 쓴다."""
    결과 = []
    t = np.arange(int(sr * 2.0)) / sr
    for 반음, 라벨 in ((FS, "F♯"), (F, "F")):
        hz = 440.0 * 2 ** ((반음 + 69 - 69 - 9) / 12.0)   # 옥타브는 상관없다
        c = 크로마(np.sin(2 * np.pi * hz * t).astype(np.float32), sr)
        이긴것 = int(np.argmax(c))
        결과.append(("%s 순음을 %s 로 읽는가" % (라벨, 라벨),
                     None if 이긴것 == 반음 else "%s 로 읽었다" % 이름[이긴것]))
    c = 크로마(np.zeros(int(sr * 2.0), dtype=np.float32), sr)
    결과.append(("무음이 0 인가", None if c.sum() == 0 else "0 이 아니다"))

    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-24s %s" % (이, "OK" if 틀 is None else "✗ " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자가 틀렸다. 재지 않는다.**")
    print("  → **셋 다 통과**\n")


def 전곡스캔(mono, sr, 뼈, 악장):
    """**전곡에서 F♯ 이 크게 울리는 자리를 찾는다 — 거기가 그녀다.**

    ## 왜 이것이 자리를 정하나

    **F♯ 은 이 곡의 유일한 조성 밖 음이고 그녀의 색채다**(`CLAUDE.md` 6절).
    **그러면 「어디에 그녀를 놓을까」는 취향이 아니라 측정이다** — 곡이 이미
    그녀를 어디에 두었는지 F♯ 이 말해 준다.

    ## 놓을 수 없는 곳

    | 악장 | 왜 |
    |---|---|
    | **1 마드리드** | 서사가 **「혼자」**다. F♯ 금지가 그 뜻이다 |
    | **4 세비야** | **V3** — 그녀의 유일한 실재는 **실제 기록물**이어야 한다 |
    | **0 Promenade 제시** | **여행 전.** 처음부터 있으면 「나중에 생겼다」가 안 된다 |
    """
    금지 = {0, 1, 4}
    print("=== 전곡에서 F♯ 이 가장 크게 울리는 자리 (악장마다 둘) ===")
    print("  **1악장(혼자) · 4악장(V3) · 0악장(여행 전)은 뺀다**\n")
    후보 = []
    for m in 뼈["악장"]:
        n = m["번호"]
        if n in 금지:
            continue
        행 = []
        t = m["시작"]
        while t + 창 <= m["끝"]:
            c = 크로마(mono[int(t * sr):int((t + 창) * sr)], sr)
            행.append((c[FS], t))
            t += 창
        행.sort(reverse=True)
        고른것, 쓴시각 = [], []
        for fs, t in 행:                      # 서로 6초 이상 떨어진 것만
            if all(abs(t - u) >= 6.0 for u in 쓴시각):
                고른것.append((t, fs)); 쓴시각.append(t)
            if len(고른것) == 2:
                break
        for t, fs in sorted(고른것):
            컷 = [c for c in 뼈["컷"] if c["시작"] <= t < c["시작"] + c["길이"]]
            c = 컷[0] if 컷 else None
            print("  %d %-16s %s  F♯ %.4f   컷 %s %s"
                  % (n, m["이름"], 분초(t), fs,
                     분초(c["시작"]) if c else "—",
                     (c["사진"][0].split("/")[-1] if c and c["사진"] else "제목")))
            후보.append((n, t, fs))
    print()
    return 후보


def main():
    P = os.path.join(ROOT, "산출물", "20260822 - 0악장을 다시 만든다", "이어붙인 것",
                     "전곡 E - 0악장 앞부분을 원본으로 되돌린 것.wav")
    sr, x = 화성.read_wav(P)
    mono = x.mean(axis=1) if x.ndim > 1 else x
    자검사(sr)

    뼈 = json.load(io.open(os.path.join(ROOT, "95. 영상 프로젝트", "src", "뼈대.json"),
                           encoding="utf-8"))
    악장 = {m["번호"]: m for m in 뼈["악장"]}
    전곡스캔(mono, sr, 뼈, 악장)
    a, b = 악장[9]["시작"], 악장[9]["끝"]

    print("=== 9악장 %s ~ %s — F♯ 과 F ===" % (분초(a), 분초(b)))
    행 = []
    t = a
    while t + 창 <= b:
        c = 크로마(mono[int(t * sr):int((t + 창) * sr)], sr)
        행.append((t, c[FS], c[F]))
        t += 창

    # **F♯ 이 마지막으로 크게 울린 뒤 F 가 넘어서는 자리**
    최고FS = max(r[1] for r in 행)
    문턱 = 최고FS * 0.5
    마지막FS = max((i for i, r in enumerate(행) if r[1] >= 문턱), default=0)
    해소 = None
    for i in range(마지막FS, len(행)):
        if 행[i][2] > 행[i][1] * 1.5:
            해소 = 행[i][0]
            break

    for i, (t, fs, f) in enumerate(행):
        표 = ""
        if i == 마지막FS:
            표 = "  ← F♯ 이 마지막으로 크게"
        if 해소 is not None and abs(t - 해소) < 0.01:
            표 = "  ★ **여기서 F 가 F♯ 을 넘어선다**"
        print("  %s  F♯ %.4f   F %.4f%s" % (분초(t), fs, f, 표))

    print()
    if 해소 is None:
        print("  **못 찾았다** — F 가 F♯ 을 뚜렷이 넘어서는 자리가 9악장에 없다.")
        print("  **「없다」가 아니라 「이 방법으로는 안 잡힌다」이다.** 창을 좁히거나")
        print("  9악장 밖도 봐야 한다.")
        return
    print("  **F♯ → F 해소: %s**  (옛 9분 40초 판에서는 9:26 이었다)" % 분초(해소))

    컷 = [c for c in 뼈["컷"] if c["시작"] <= 해소 < c["시작"] + c["길이"]]
    if 컷:
        c = 컷[0]
        print("  그 자리의 컷 — %s %s %.2f초 · %s"
              % (분초(c["시작"]), c["도시"], c["길이"],
                 c["사진"][0].split("/")[-1] if c["사진"] else "제목"))


def 분초(t):
    return "%d:%05.2f" % (t // 60, t % 60)


if __name__ == "__main__":
    main()
