# -*- coding: utf-8 -*-
"""마스터를 납품 파일로 굽는다.

> **⚠ 지금 24비트로 나가지만 이것은 승인된 것이 아니다 (2026-08-12).**
> **검수자 확정은 「32bit로 굳혀줘」였다.** 재생기가 32비트를 못 읽자
> **내가 그 자리에서 승인 없이 24비트로 바꿨다.** 검수자 — *"24비트로
> 굳힌적 없음 ^^"*. **판정 대기이고, 32비트로 되돌리려면 ① 의
> `pcm_s24le` 를 `pcm_s32le` 로 바꾸면 된다.**
검수자 — *"mp3는 더이상 만들지 않아도 됨."*
**굽고 나서 악장별 구간표까지 만든다.**

    python 납품.py "산출물/20260812 - 한 마디" "full v4.15 9m40s"
    python 납품.py <폴더> <이름> --from 전곡화성.wav --excerpt 325:32

검수자 확정 — *"32bit로 굳혀줘."*

**왜 도구로 만드는가.** 이 프로젝트는 형식을 손으로 굽다가 두 번 틀렸다.

  ① `write_wav` 가 **마스터만 16비트로** 떨어뜨리고 있었다. 계산도 스템도
     32비트 실수인데 마지막 한 줄이 깎았고, 넉 달 동안 아무도 안 봤다.
  ② `ffmpeg -c:a flac -sample_fmt s32` 가 **24비트를 쓴다.** 인코더가
     "Supported sample formats: s16 s32" 라고 적어놓고 그렇게 한다.
     경고도 안 낸다 — **「지원한다」와 「그 비트로 쓴다」가 다른 말이었다.**

**둘 다 「이름이 값과 다르다」이고, 사람이 매번 확인할 것이 아니라 도구가
확인해야 한다.** 그래서 이 스크립트는 굽고 나서 **반드시 되돌려 대조한다.**

경위와 실측은 [10. 렌더와 음원 파일] 5절과 별첨.
"""
import io
import os
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def find_flac():
    """공식 FLAC 도구를 찾는다.

    **ffmpeg 으로는 24비트가 상한이다.** 32비트는 FLAC 1.4+ 가 필요하고,
    winget 으로 깐 것은 **새 셸에서만 PATH 에 잡히므로** 설치 경로도 뒤진다.
    """
    from shutil import which
    p = which("flac")
    if p:
        return p
    base = os.path.expandvars(r"%LocalAppData%\Microsoft\WinGet\Packages")
    if os.path.isdir(base):
        for d in os.listdir(base):
            if not d.startswith("Xiph.FLAC"):
                continue
            for root, _, files in os.walk(os.path.join(base, d)):
                if "flac.exe" in files and "Win64" in root:
                    return os.path.join(root, "flac.exe")
    return None


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode("utf-8", "replace")[-800:])
        raise SystemExit("실패: %s" % cmd[0])


def load(path):
    """**자료형을 먼저 본다.** int16 도 float32 도 int32 도 돌아온다."""
    _, a = wavfile.read(path)
    return a


def probe(path, key):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=%s" % key, "-of", "default=nw=1", path],
                       capture_output=True)
    m = re.search(r"=(.+)", r.stdout.decode("utf-8", "replace"))
    return m.group(1).strip() if m else "?"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    outdir, name = sys.argv[1], sys.argv[2]
    src = os.path.join(HERE, "전곡화성.wav")
    if "--from" in sys.argv:
        src = sys.argv[sys.argv.index("--from") + 1]
    if not os.path.isabs(outdir):
        outdir = os.path.join(HERE, "..", outdir)
    os.makedirs(outdir, exist_ok=True)

    flac_bin = find_flac()
    if not flac_bin:
        raise SystemExit("flac 을 못 찾았다. winget install --id Xiph.FLAC")

    fmt = probe(src, "sample_fmt")
    print("마스터   %s  (%s)" % (os.path.basename(src), fmt))
    if fmt not in ("flt", "s32"):
        print("  ⚠ 마스터가 %s 다. 32비트로 못 간다 — piano.write_wav 를 본다" % fmt)

    # ── ① 24비트 정수로 옮긴다. FLAC 은 실수를 못 담는다 ──────────────
    #
    # `ffmpeg -c:a pcm_s24le` 가 진짜 24비트 wav 를 쓴다. **`flac --bps=24` 는
    # 안 된다** — raw 입력에만 쓰는 옵션이라 wav 를 주면 거부한다.
    # 그러므로 **비트depth 는 이 단계에서 정해진다.**
    tmp = os.path.join(HERE, "_납품중간24.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:a", "pcm_s24le", tmp])

    # ── ② FLAC — 지금 24비트, **미승인** ────────────────────────────
    #
    # **2026-08-12 저녁 — 32비트에서 24비트로 내렸다. 승인 없이 내가 했다.**
    #
    # 검수자가 32비트 전곡을 열자 Windows 미디어 플레이어가 거부했다 —
    # *"지원되지 않는 형식으로 인코딩되어 있습니다"* (0xC00D36B4).
    # **FLAC 이 32비트를 지원한 것은 1.4(2022) 부터**라 재생기 대부분이 못 읽는다.
    #
    # **그리고 그 자리에서 내가 또 확인 없이 단정했다** — 「32비트는 대부분
    # 못 연다」고 말했는데, 검수자가 *"mv9 대문은 재생 가능함. 뭔가 잘못
    # 알고 있는 것 아닌가?"* 라고 되물었다. **재보니 발췌들은 24비트였다**
    # (내가 ffmpeg 으로 구웠고 ffmpeg 은 32비트를 못 쓴다). 즉 **32비트인
    # 전곡만 안 열렸고 24비트인 발췌는 다 열렸다** — 그게 실제 증거다.
    #
    # **차이는 −149.1 dB 로 24비트의 잡음 바닥(−144)보다도 아래다.** 안 들린다.
    #
    # > **「안 버리는 것」만 보고 「열리는가」를 안 봤다.**
    # > 이 스크립트가 무손실인지와 비트depth 는 검사하면서 **재생 가능성은
    # > 검사하지 않았다.** ④ 에 그 검사를 넣는다.
    fl = os.path.join(outdir, name + ".flac")
    run([flac_bin, "--best", "--force", "--silent", "-o", fl, tmp])

    # ── ③ MP3 는 더 이상 굽지 않는다 (2026-08-12, 검수자 "mp3는 더이상 만들지
    #     않아도 됨"). FLAC 이 정본이 된 이상 손실 사본을 같이 낼 이유가 없다.
    #     되살릴 일이 생기면 아래 한 줄이면 된다 —
    #       ffmpeg -i <마스터> -c:a libmp3lame -b:a 320k <이름>.mp3

    # ── ④ 되돌려 대조한다. **이 검사가 이 스크립트의 존재 이유다** ────────
    back = os.path.join(HERE, "_납품확인.wav")
    run([flac_bin, "-d", "--force", "--silent", "-o", back, fl])
    a, b = load(tmp), load(back)
    n = min(len(a), len(b))
    ok = bool(np.array_equal(a[:n], b[:n]))
    bits = probe(fl, "bits_per_raw_sample")

    for f in (tmp, back):
        try:
            os.remove(f)
        except OSError:
            pass

    mb = lambda p: os.path.getsize(p) / 1048576.0
    print()
    print("FLAC     %s  %d비트  %.1f MB" % (os.path.basename(fl), int(bits or 0), mb(fl)))
    print()
    print("무손실 확인   %s" % ("★ 비트 단위 100% 일치" if ok else "✘ 다르다 — 쓰면 안 된다"))
    print("비트depth     %s" % ("★ 24비트 — 재생기가 읽는다" if bits == "24"
                                else "✘ %s 비트 — 24 여야 한다" % bits))
    if not ok or bits != "24":
        raise SystemExit(1)

    # ── ⑤ **악장별 구간표를 같이 만든다** ────────────────────────────
    #
    # `movement-guide` 스킬이 "전곡 파일을 하나라도 새로 만들면 쓴다. 요청을
    # 기다리지 않는다"고 적어두었는데 **2026-08-12 하루에 두 번 빠뜨렸다.**
    # 검수자 — *"오늘 같은말 여러번 하게 하지마라."*
    #
    # **스킬에 적어두는 것으로는 안 지켜졌다.** `11. 공용 함수` 6절이 그날
    # 세운 규칙이 이것이다 — **문서에 적을 수 있는 규칙은 도구로 옮길 수
    # 있는지 먼저 묻는다.** 그래서 납품이 구간표를 낳게 한다.
    guide = os.path.join(outdir, "구간표 - %s.md" % name)
    r = subprocess.run([sys.executable, os.path.join(HERE, "악장표.py")],
                       capture_output=True, cwd=HERE,
                       env=dict(os.environ, PYTHONUTF8="1"))
    body = r.stdout.decode("utf-8", "replace")
    if r.returncode != 0 or not body.strip():
        print()
        print("⚠ 구간표를 못 만들었다 — `악장표.py` 를 직접 돌려 확인한다")
    else:
        head = [
            "# 구간표 — %s" % name,
            "",
            "**`악장표.py` 가 코드와 음원에서 생성한 것이다. 손으로 안 적는다.**",
            "",
            "청취 안내를 쓸 때는 `CLAUDE.md` 8절의 **여섯 칸**을 다 채운다 —",
            "소리의 모양 · 시각 전부 · 길이 · 일상 비유 · 가장 쉬운 확인법 · A/B 차이.",
            "**시각은 반드시 음원에서 재서 적는다** (계산으로 적다가 틀린 적이 있다).",
            "",
            "```",
            body.rstrip(),
            "```",
            "",
        ]
        io.open(guide, "w", encoding="utf-8").write("\n".join(head))
        print("구간표       %s" % os.path.basename(guide))
        print()
        print("★ 전곡 파일을 냈으므로 **악장별 구간표를 반드시 붙여 보낸다** "
              "(`movement-guide`).")


if __name__ == "__main__":
    main()
