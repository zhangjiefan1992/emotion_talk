#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${IOS_DIR}/../.." && pwd)"

PORT="${EMOTION_TALK_API_PORT:-8000}"
BASE_URL="${EMOTION_TALK_API_BASE_URL:-http://127.0.0.1:${PORT}}"
SIM_NAME="${SIM_NAME:-iPhone 16}"
BUNDLE_ID="${BUNDLE_ID:-com.jeff.emotiontalk}"
DERIVED_DATA="${DERIVED_DATA:-${ROOT_DIR}/.tmp/EmotionTalkDerivedData}"
OUTPUT_DIR="${ROOT_DIR}/outputs/ios-simulator-smoke"
BACKEND_LOG="${OUTPUT_DIR}/backend.log"
SCREENSHOT_PATH="${OUTPUT_DIR}/first-screen.png"
UI_TEST_LOG="${OUTPUT_DIR}/ui-test.log"
RUN_UI_TESTS="${RUN_UI_TESTS:-1}"

mkdir -p "${OUTPUT_DIR}" "${ROOT_DIR}/.tmp"

require_full_xcode() {
  local developer_dir
  developer_dir="$(xcode-select -p 2>/dev/null || true)"
  if [[ "${developer_dir}" == "/Library/Developer/CommandLineTools" || -z "${developer_dir}" ]]; then
    cat >&2 <<EOF
Full Xcode is required for Simulator verification.
Current developer directory: ${developer_dir:-<none>}

Run after installing Xcode:
  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
EOF
    exit 2
  fi
  xcodebuild -version >/dev/null
  xcrun simctl help >/dev/null
}

boot_or_find_simulator() {
  if [[ -n "${SIM_UDID:-}" ]]; then
    echo "${SIM_UDID}"
    return
  fi

  local booted
  booted="$(xcrun simctl list devices booted -j | /usr/bin/python3 - <<'PY'
import json
import sys

data = json.load(sys.stdin)
for devices in data.get("devices", {}).values():
    for device in devices:
        if device.get("isAvailable") and device.get("state") == "Booted":
            print(device["udid"])
            raise SystemExit(0)
raise SystemExit(1)
PY
)" || true
  if [[ -n "${booted}" ]]; then
    echo "${booted}"
    return
  fi

  local candidate
  candidate="$(xcrun simctl list devices available -j | SIM_NAME="${SIM_NAME}" /usr/bin/python3 - <<'PY'
import json
import os
import sys

name = os.environ["SIM_NAME"]
data = json.load(sys.stdin)
fallback = None
for devices in data.get("devices", {}).values():
    for device in devices:
        if not device.get("isAvailable"):
            continue
        fallback = fallback or device
        if device.get("name") == name:
            print(device["udid"])
            raise SystemExit(0)
if fallback:
    print(fallback["udid"])
    raise SystemExit(0)
raise SystemExit(1)
PY
)"
  xcrun simctl boot "${candidate}" >/dev/null 2>&1 || true
  xcrun simctl bootstatus "${candidate}" -b
  echo "${candidate}"
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

require_full_xcode

if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Stop that process or set EMOTION_TALK_API_PORT." >&2
  exit 1
fi

(
  cd "${ROOT_DIR}"
  PYTHONPATH=services/api/src \
  EMOTION_TALK_LLM_PROVIDER="${EMOTION_TALK_LLM_PROVIDER:-heuristic}" \
  .venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port "${PORT}"
) >"${BACKEND_LOG}" 2>&1 &
SERVER_PID="$!"

"${ROOT_DIR}/.venv/bin/python" - "${BASE_URL}" <<'PY'
import sys
import time
import urllib.request

base_url = sys.argv[1].rstrip("/")
deadline = time.time() + 20
while time.time() < deadline:
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=1) as response:
            if response.status == 200:
                print("backend_ready")
                raise SystemExit(0)
    except Exception:
        time.sleep(0.25)
print("backend_not_ready", file=sys.stderr)
raise SystemExit(1)
PY

SIM_UDID="$(boot_or_find_simulator)"

xcodebuild \
  -project "${IOS_DIR}/EmotionTalk.xcodeproj" \
  -scheme EmotionTalk \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=${SIM_UDID}" \
  -derivedDataPath "${DERIVED_DATA}" \
  build

APP_PATH="$(find "${DERIVED_DATA}" -path '*Build/Products/Debug-iphonesimulator/EmotionTalk.app' -print -quit)"
if [[ -z "${APP_PATH}" ]]; then
  echo "Built app not found in ${DERIVED_DATA}" >&2
  exit 1
fi

xcrun simctl install "${SIM_UDID}" "${APP_PATH}"
xcrun simctl launch "${SIM_UDID}" "${BUNDLE_ID}"
sleep 3
xcrun simctl io "${SIM_UDID}" screenshot "${SCREENSHOT_PATH}"

if [[ "${RUN_UI_TESTS}" == "1" ]]; then
  EMOTION_TALK_API_BASE_URL="${BASE_URL}" \
  xcodebuild \
    -project "${IOS_DIR}/EmotionTalk.xcodeproj" \
    -scheme EmotionTalk \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=${SIM_UDID}" \
    -derivedDataPath "${DERIVED_DATA}" \
    -only-testing:EmotionTalkUITests/EmotionTalkUITests/testRecordingSummaryAndExpertAdviceFlow \
    test | tee "${UI_TEST_LOG}"
fi

echo "simulator_udid=${SIM_UDID}"
echo "app_path=${APP_PATH}"
echo "screenshot=${SCREENSHOT_PATH}"
echo "backend_log=${BACKEND_LOG}"
if [[ "${RUN_UI_TESTS}" == "1" ]]; then
  echo "ui_test_log=${UI_TEST_LOG}"
fi
