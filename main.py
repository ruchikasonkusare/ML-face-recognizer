# main.py

from cors.pipeline import run_pipeline

# ── Settings ──────────────────────────────
DRIVE_LINK  = "https://drive.google.com/drive/folders/13D7dwveo_OU3odIe44Ql8CP7JkG7xTfe?usp=sharing"
OUTPUT_DIR  = "output"
BATCH_SIZE  = 10        # process 50 photos at a time
# ──────────────────────────────────────────

run_pipeline(
    drive_link  = DRIVE_LINK,
    output_dir  = OUTPUT_DIR,
    batch_size  = BATCH_SIZE,
)