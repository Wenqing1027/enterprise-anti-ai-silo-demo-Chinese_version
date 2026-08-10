#!/usr/bin/env bash
# 构建时从「私有」仓库拉取讲解视频，避免出现在公开 GitHub 仓库中。
# Render 环境变量：GH_MEDIA_TOKEN = 有 private repo 读权限的 GitHub PAT
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/apps/ui/media/demo-walkthrough.mp4"
REPO="${DEMO_VIDEO_REPO:-Wenqing1027/qingshu-demo-media-private}"
PATH_IN_REPO="${DEMO_VIDEO_PATH:-demo-walkthrough.mp4}"

mkdir -p "$(dirname "$DEST")"

if [[ -f "$DEST" && -s "$DEST" ]]; then
  echo "[fetch_demo_video] already present: $DEST ($(wc -c <"$DEST") bytes)"
  exit 0
fi

TOKEN="${GH_MEDIA_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "${TOKEN}" ]]; then
  echo "[fetch_demo_video] WARN: GH_MEDIA_TOKEN not set; skipping (page will show download/missing)."
  exit 0
fi

URL="https://api.github.com/repos/${REPO}/contents/${PATH_IN_REPO}"
echo "[fetch_demo_video] downloading from private repo ${REPO}:${PATH_IN_REPO}"
curl -fsSL \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/vnd.github.raw" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -o "$DEST" \
  "$URL"

echo "[fetch_demo_video] saved $(wc -c <"$DEST") bytes -> $DEST"
