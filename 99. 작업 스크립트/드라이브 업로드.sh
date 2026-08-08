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
