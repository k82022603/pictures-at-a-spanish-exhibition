"""
악보 채보 파이프라인 — 오선 검출 · 음표 머리 인식 · 음정 매핑
높은음자리표 최상성부(주선율)만 뽑는다.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

DIA = ['E', 'F', 'G', 'A', 'B', 'C', 'D']          # 높은음자리표 아래줄 E4 기준
SEMI = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def load(path, dpi_scale=1.0):
    im = Image.open(path).convert('L')
    return np.array(im), im


def find_staves(a, min_frac=0.28):
    """페이지에서 오선(5줄 묶음)을 모두 찾는다."""
    h, w = a.shape
    D = a < 130
    x0, x1 = int(w * 0.08), int(w * 0.95)
    rows = D[:, x0:x1].sum(1) / float(x1 - x0)
    cand = np.where(rows > min_frac)[0]
    if len(cand) == 0:
        return []
    # 인접 행 묶기 → 선 하나
    lines, cur = [], [cand[0]]
    for i in cand[1:]:
        if i - cur[-1] <= 4:
            cur.append(i)
        else:
            lines.append(float(np.mean(cur)))
            cur = [i]
    lines.append(float(np.mean(cur)))
    # 5줄씩 묶기 — 간격이 균일한 연속 5개
    staves = []
    i = 0
    while i + 4 < len(lines):
        g = lines[i:i + 5]
        d = np.diff(g)
        if d.max() < d.min() * 1.5 and d.mean() < 0.03 * h:
            staves.append(g)
            i += 5
        else:
            i += 1
    return staves


def note_heads(a, staff, x_lo=None, x_hi=None, pad=3.2):
    """오선 주변에서 음표 머리 중심 (x, y) 목록."""
    h, w = a.shape
    step = (staff[4] - staff[0]) / 8.0
    y0 = max(0, int(staff[0] - pad * step * 2))
    y1 = min(h, int(staff[4] + pad * step * 2))
    xa = 0 if x_lo is None else x_lo
    xb = w if x_hi is None else x_hi
    band = (a[y0:y1, xa:xb] < 130)

    thick = np.zeros_like(band, bool)
    minrun = max(8, int(step * 0.78))
    for x in range(band.shape[1]):
        col = band[:, x]
        i = 0
        while i < len(col):
            if col[i]:
                j = i
                while j < len(col) and col[j]:
                    j += 1
                if j - i >= minrun:
                    thick[i:j, x] = True
                i = j
            else:
                i += 1

    lab, n = ndi.label(thick)
    heads = []
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        if len(ys) < step * 12:
            continue
        rows = {}
        for yy, xx in zip(ys, xs):
            rows.setdefault(yy, []).append(xx)
        wid = {y: (max(v) - min(v) + 1) for y, v in rows.items()}
        mx = max(wid.values())
        if mx < step * 0.95:
            continue
        good = sorted([y for y, v in wid.items() if v >= 0.78 * mx])
        segs, cur = [], [good[0]]
        for y in good[1:]:
            if y - cur[-1] <= 2:
                cur.append(y)
            else:
                segs.append(cur)
                cur = [y]
        segs.append(cur)
        for s in segs:
            if len(s) < step * 0.42:
                continue
            cy = float(np.mean(s)) + y0
            cx = float(np.mean([np.mean(rows[y]) for y in s])) + xa
            heads.append((cx, cy))
    heads.sort()
    return heads


def to_pitch(cy, staff, key_acc):
    """오선 위치 → (음명, 옥타브, MIDI, 계단값, 신뢰도)"""
    step = (staff[4] - staff[0]) / 8.0
    p = (staff[4] - cy) / step
    k = int(round(p))
    name = DIA[k % 7]
    octv = 4 + (k + 2) // 7
    midi = 12 * (octv + 1) + SEMI[name] + key_acc.get(name, 0)
    return name, octv, midi, p, abs(p - k)


def calib(ps):
    """음표는 줄이나 칸의 중앙에 놓인다. 잔차가 정수에 가장 가까워지는
    보정값 δ를 찾아 오선 검출의 계통 편차를 스스로 없앤다."""
    best, bd = -1, 0.0
    for d in np.arange(-0.5, 0.5, 0.01):
        r = np.abs((np.array(ps) + d) - np.round(np.array(ps) + d))
        score = float((r < 0.18).sum()) - r.sum()
        if score > best:
            best, bd = score, float(d)
    return bd


def melody(a, staff, key_acc, x_lo=None, x_hi=None, cluster=None, delta=None):
    """같은 x에 여러 음이 있으면 가장 높은 음(주선율)만."""
    step = (staff[4] - staff[0]) / 8.0
    cl = cluster if cluster else step * 1.2
    hs = note_heads(a, staff, x_lo, x_hi)
    out, group = [], []
    for cx, cy in hs:
        if group and cx - group[-1][0] > cl:
            out.append(min(group, key=lambda t: t[1]))
            group = []
        group.append((cx, cy))
    if group:
        out.append(min(group, key=lambda t: t[1]))

    raw = [(staff[4] - cy) / step for _, cy in out]
    if not raw:
        return []
    d = calib(raw) if delta is None else delta
    res = []
    for (cx, cy), p0 in zip(out, raw):
        p = p0 + d
        k = int(round(p))
        nm = DIA[k % 7]
        oc = 4 + (k + 2) // 7
        midi = 12 * (oc + 1) + SEMI[nm] + key_acc.get(nm, 0)
        res.append((cx, cy, nm, oc, midi, p, abs(p - k)))
    return res


KEYS = {
    'Bb': {'B': -1, 'E': -1},
    'Ab': {'B': -1, 'E': -1, 'A': -1, 'D': -1},
    'B':  {'F': 1, 'C': 1, 'G': 1, 'D': 1, 'A': 1},
    'Dm': {'B': -1},
    'F':  {'B': -1},
    'C':  {},
}


def overlay(im, staff, notes, path, key='Bb'):
    """검증용 — 오선 눈금과 판독 결과를 그림에 겹쳐 저장."""
    rgb = im.convert('RGB')
    d = ImageDraw.Draw(rgb)
    step = (staff[4] - staff[0]) / 8.0
    for k in range(-4, 12):
        y = staff[4] - k * step
        d.line([(0, y), (rgb.size[0], y)], fill=(255, 190, 190), width=1)
    for cx, cy, nm, oc, midi, p, err in notes:
        col = (0, 160, 0) if err < 0.3 else (255, 0, 0)
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=col, width=3)
        d.text((cx - 12, cy - 34), '%s%d' % (nm, oc), fill=col)
    rgb.save(path)
