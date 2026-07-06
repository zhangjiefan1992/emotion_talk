#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${IOS_DIR}/../.." && pwd)"

PORT="${EMOTION_TALK_API_PORT:-8000}"
BASE_URL="${EMOTION_TALK_API_BASE_URL:-http://127.0.0.1:${PORT}}"
LOG_DIR="${ROOT_DIR}/outputs/ios-smoke"
LOG_FILE="${LOG_DIR}/backend-smoke.log"

mkdir -p "${LOG_DIR}"

if ! command -v swift >/dev/null 2>&1; then
  echo "swift is required" >&2
  exit 1
fi

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing project virtualenv: ${ROOT_DIR}/.venv" >&2
  exit 1
fi

if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Stop that process or set EMOTION_TALK_API_PORT." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

(
  cd "${ROOT_DIR}"
  PYTHONPATH=services/api/src \
  EMOTION_TALK_LLM_PROVIDER="${EMOTION_TALK_LLM_PROVIDER:-deepseek}" \
  .venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port "${PORT}"
) >"${LOG_FILE}" 2>&1 &
SERVER_PID="$!"

"${ROOT_DIR}/.venv/bin/python" - "${BASE_URL}" <<'PY'
import sys
import time
import urllib.request

base_url = sys.argv[1].rstrip("/")
deadline = time.time() + 20
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=1) as response:
            if response.status == 200:
                print("backend_ready")
                raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(0.25)
print(f"backend_not_ready: {last_error}", file=sys.stderr)
raise SystemExit(1)
PY

(
  cd "${IOS_DIR}"
  EMOTION_TALK_API_BASE_URL="${BASE_URL}" swift run EmotionTalkAPISmoke
)

echo "backend_log=${LOG_FILE}"
