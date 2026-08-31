# -*- coding: utf-8 -*-
"""**나갈 사진을 순서대로 늘어놓는다 — 검수자가 먼저 보시라고.**

2026-08-30. 검수자 — *"사진들 내가 먼저 보긴해야겠다."*

**흑백으로 만든다** — 실제로 화면에 나갈 모습 그대로여야 한다.
**구간별로 따로 내고, 순서와 시각을 붙인다.**

세 갈래를 낸다.

| 무엇 | 왜 |
|---|---|
| **쓸 것** — 구간별 | 실제로 나갈 것 |
| **안 쓴 것** | 추림에서 밀린 것. **되살릴지 보시라고** |
| **뺀 것** | 한 사람이 주제인 사진. **잘못 뺀 것이 있는지 보시라고** |
"""
import json
import os
import sys

from PIL import Image, ImageDraw

컬러 = set()

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
사진밑 = os.path.join(HERE, "..", "2005년 12월 스페인")
밑 = os.path.join(HERE, "..", "산출물", "20260830 - 사진 고르기")
낼 = os.path.join(밑, "검수용 연락표")

COL, TH, PAD, LBL = 5, 320, 10, 20


def 시각(t):
    return "%d:%05.2f" % (int(t // 60), t % 60)


def 만들기(항목들, 이름):
    """항목 = (경로, 밑에 적을 글)"""
    행 = (len(항목들) + COL - 1) // COL
    W = COL * (TH + PAD) + PAD
    H = 행 * (TH + PAD + LBL) + PAD
    c = Image.new("RGB", (W, H), (16, 17, 21))
    d = ImageDraw.Draw(c)
    for i, (p, 글) in enumerate(항목들):
        키 = p.replace("\\", "/").split("2005년 12월 스페인/")[-1]
        im = Image.open(p)
        im = im.convert("RGB") if 키 in 컬러 else im.convert("L").convert("RGB")
        im.thumbnail((TH, TH))
        x = PAD + (i % COL) * (TH + PAD)
        y = PAD + (i // COL) * (TH + PAD + LBL)
        c.paste(im, (x + (TH - im.width) // 2, y + (TH - im.height) // 2))
        d.text((x + 2, y + TH + 4), 글, fill=(190, 200, 214))
    f = os.path.join(낼, 이름)
    c.save(f)
    return f, W, H


if __name__ == "__main__":
    f = os.path.join(밑, "컬러로 낼 것.txt")
    if os.path.exists(f):
        for L in open(f, encoding="utf-8"):
            L = L.strip()
            if L and not L.startswith("#"):
                컬러.add(L.split(".JPG")[0] + ".JPG")
    os.makedirs(낼, exist_ok=True)
    장면 = json.load(open(os.path.join(밑, "장면.json"), encoding="utf-8"))["장면"]
    전부 = json.load(open(os.path.join(밑, "쓸 사진.json"), encoding="utf-8"))["쓸것"]

    # ── 쓸 것 — 구간별 ─────────────────────────────
    순서 = []
    구간들 = []
    for s in 장면:
        if not 구간들 or 구간들[-1][0] != s["도시"]:
            구간들.append([s["도시"], []])
        구간들[-1][1].append(s)
    for n, (도시, ss) in enumerate(구간들, 1):
        항목 = [(os.path.join(사진밑, s["경로"].replace("/", os.sep)),
                 "%02d  %s  %s" % (i + 1, 시각(s["시작"]),
                                   os.path.basename(s["경로"]).replace(".JPG", "")))
                for i, s in enumerate(ss)]
        f, W, H = 만들기(항목, "%d. 쓸 것 - %s (%d장).png" % (n, 도시.replace(" · ", "·"), len(ss)))
        print("%-24s %3d장  %s" % (도시, len(ss), os.path.basename(f)))
        순서 += [s["경로"] for s in ss]

    # ── 안 쓴 것 ────────────────────────────────
    안쓴 = [it for it in 전부 if it["경로"] not in set(순서)]
    안쓴 = sorted(안쓴, key=lambda x: -x["또렷"])
    항목 = [(os.path.join(사진밑, it["경로"].replace("/", os.sep)),
             "%s  %s  또렷 %.0f" % (it["도시"][:6], os.path.basename(it["경로"]).replace(".JPG", ""), it["또렷"]))
            for it in 안쓴]
    f, *_ = 만들기(항목, "7. 안 쓴 것 (%d장).png" % len(안쓴))
    print("%-24s %3d장  %s" % ("안 쓴 것", len(안쓴), os.path.basename(f)))

    # ── 뺀 것 ──────────────────────────────────
    뺀 = []
    for L in open(os.path.join(밑, "뺄 사람 사진.txt"), encoding="utf-8"):
        L = L.strip()
        if L and not L.startswith("#"):
            뺀.append(L.split(".JPG")[0] + ".JPG")
    항목 = [(os.path.join(사진밑, r.replace("/", os.sep)),
             os.path.basename(r).replace(".JPG", "")) for r in 뺀]
    f, *_ = 만들기(항목, "8. 뺀 것 - 한 사람이 주제 (%d장).png" % len(뺀))
    print("%-24s %3d장  %s" % ("뺀 것", len(뺀), os.path.basename(f)))
    print("\n→ %s" % 낼)
