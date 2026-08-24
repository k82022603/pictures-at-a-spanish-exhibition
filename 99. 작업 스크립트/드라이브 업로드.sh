#!/usr/bin/env bash
# 산출물을 Google Drive 로 올린다.
#
#   bash "99. 작업 스크립트/드라이브 업로드.sh"          실제로 올린다
#   bash "99. 작업 스크립트/드라이브 업로드.sh" --dry     무엇이 올라갈지만 본다
#
# 왜 --config 로 프로젝트 안의 열쇠를 쓰는가
#   Claude 의 도구는 프로젝트 폴더 밖(%AppData% 등)에서 검수자와 다른 파일을 본다.
#   2026-08-08 에 그것 때문에 rclone 이 토큰을 못 찾았다. 프로젝트 안에 두면 둘이
#   같은 것을 보므로 Claude 가 직접 실행할 수 있다.
#   .rclone.conf 는 .gitignore 대상이다 — 절대 커밋되지 않는다.
#
# 왜 sync 가 아니라 copy 인가
#   sync 는 Drive 쪽에만 있는 파일을 지운다. 산출물은 판정의 물증이므로 지우면 안 된다.
#
# README.md 도 함께 올린다
#   Drive 만 열었을 때 그 음원들이 무엇인지 알아야 하기 때문이다. 설명 없는
#   mp3 열 개는 쓸모가 없다. 정본은 git 이고 Drive 쪽은 읽기 전용 사본이다 —
#   copy 가 git 에서 Drive 로 한 방향이라 마감 때마다 자동으로 갱신된다.
#   **Drive 의 README 를 손으로 고치지 않는다.** 고치면 다음 마감에 덮인다.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONF="$ROOT/.rclone.conf"
OUT="$ROOT/산출물"

RCLONE=$(command -v rclone || true)
if [ -z "$RCLONE" ]; then
    RCLONE=$(ls "/c/Users/$USERNAME/AppData/Local/Microsoft/WinGet/Packages/"*Rclone*/*/rclone.exe 2>/dev/null | head -1 || true)
fi
[ -n "$RCLONE" ] || { echo "rclone 을 찾지 못했습니다.  winget install --id Rclone.Rclone"; exit 1; }

if [ ! -f "$CONF" ]; then
    cat <<MSG
열쇠가 없습니다: $CONF

아래를 한 번 실행하면 만들어집니다 (브라우저 인증).
Out-Null 은 토큰이 화면에 찍히는 것을 막습니다.

  rclone config create drive drive scope=drive \\
    root_folder_id=1VKkKWI5kTLqeCjlnBL5GTZsc6JbDQHmu \\
    --config "$(cygpath -w "$CONF" 2>/dev/null || echo "$CONF")" | Out-Null
MSG
    exit 1
fi

# 토큰이 실수로 커밋되지 않는지 매번 확인한다. 공개 저장소다.
if git -C "$ROOT" check-ignore -q .rclone.conf 2>/dev/null; then :; else
    echo "위험: .rclone.conf 가 .gitignore 에 걸리지 않습니다. 중단합니다."; exit 1
fi

FLAGS=(--progress --config "$CONF")
[ "${1:-}" = "--dry" ] && FLAGS+=(--dry-run)

echo "▶ 올릴 것"
find "$OUT" -type f ! -name "README.md" -printf "   %10s  %P\n" 2>/dev/null | sort -k2
echo

"$RCLONE" copy "$OUT" "drive:" "${FLAGS[@]}"

echo
echo "▶ Drive 현황"
"$RCLONE" ls "drive:" --max-depth 2 --config "$CONF" 2>/dev/null | sed 's/^/   /'

# ── ★ 올라갔는지 스스로 확인한다 (2026-08-24 신설) ─────────────────
#
# **`copy` 의 진행률은 「끝났다」의 증거가 아니다.**
# 2026-08-24 에 로그가 `Transferred: 77 / 81, 95%` 에서 멈춰 있었고
# **큰 mp4 넷이 전송 중에 끊겨 있었다.** 그중 하나가 **승인판**이었고
# 하나가 **그날의 최종본**이었다 — **둘 다 로컬에만 있었다.**
#
# 그 상태로 마감을 닫으면 `96. 운영` 가이드가 못박은
# *"산출물은 Drive 가 갖는다"* 를 어긴 채로 하루가 끝나고, **아무도 모른다.**
#
# **그래서 사람이 기억하는 대신 스크립트가 잰다.**
# 규칙을 문서에만 적으면 안 지켜진다 — 이 프로젝트가 여러 번 겪은 일이다.
if [ "${1:-}" != "--dry" ]; then
    echo
    echo "▶ 대조 — 빠진 것이 있는가"
    # **변수 이름은 아스키로.** bash 는 한글 변수명을 못 받는다 — 2026-08-24 실측
    #
    # **`--combined` 의 접두사를 짐작하지 않는다.** 처음에 `-` 로 알고 걸렀는데
    # **빠진 파일은 `+` 로 나온다** — 시험 파일을 하나 만들어 보고서야 알았다.
    # **`--missing-on-dst` 는 접두사 없이 경로만 준다.** 짐작할 것이 없다.
    missing=$("$RCLONE" check "$OUT" "drive:" --config "$CONF" --one-way               --missing-on-dst - 2>/dev/null || true)
    if [ -n "$missing" ]; then
        echo "   ✘ 안 올라간 것이 있습니다 —"
        echo "$missing" | sed 's/^/     /'
        echo
        echo "   **끊긴 것입니다. 이 스크립트를 다시 돌리십시오.**"
        echo "   copy 라서 이미 올라간 것은 건너뜁니다."
        exit 1
    fi
    echo "   ✔ 빠진 것 없음 — Drive 가 로컬을 전부 갖고 있습니다"
fi
