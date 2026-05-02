#!/usr/bin/env bash
# HF Spaces entrypoint — ensure data dir + model + DB ready before Streamlit starts.
set -e

DATA_DIR="${WUSHU_DATA_DIR:-/data}"
mkdir -p "$DATA_DIR/models" "$DATA_DIR/videos/references" "$DATA_DIR/videos/tests" \
         "$DATA_DIR/poses/references" "$DATA_DIR/poses/tests" \
         "$DATA_DIR/renders/references" "$DATA_DIR/renders/tests" \
         "$DATA_DIR/references"

# Download MediaPipe pose landmarker model if missing
MODEL_PATH="$DATA_DIR/models/pose_landmarker_full.task"
if [ ! -f "$MODEL_PATH" ]; then
    echo "[entrypoint] Downloading MediaPipe pose model..."
    curl -L --fail --show-error \
        -o "$MODEL_PATH" \
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
    echo "[entrypoint] Model downloaded: $(du -h "$MODEL_PATH" | cut -f1)"
fi

# Pose model env var so core/pose_extractor.py picks it up
export WUSHU_POSE_MODEL="$MODEL_PATH"

# Initialize / migrate DB and seed forms catalog
echo "[entrypoint] Initializing database..."
python /home/user/app/scripts/init_db.py

# Storage backend self-check (verifies R2 reachability from container)
echo "[entrypoint] Checking storage backend..."
python -c "
import sys
sys.path.insert(0, '/home/user/app')
from core.storage import get_storage
try:
    s = get_storage()
    print(f'[storage] backend = {s.backend_name}')
    if s.backend_name == 'r2':
        s.client.head_bucket(Bucket=s.bucket)
        print(f'[storage] R2 bucket {s.bucket!r} reachable from container ✓')
    else:
        print(f'[storage] LocalStorage at {s.root}')
except Exception as e:
    print(f'[storage] WARN: {type(e).__name__}: {e}', file=sys.stderr)
" || echo "[entrypoint] Storage check failed (container will still start; first upload will retry)"

# Launch Streamlit
echo "[entrypoint] Starting Streamlit on :${STREAMLIT_SERVER_PORT}..."
exec streamlit run /home/user/app/apps/workbench/app.py
