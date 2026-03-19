#!/usr/bin/env bash
# =============================================================================
# Master Reproducibility Script
# "Beyond Solidity: A Benchmarking Study of LLM-Assisted Vulnerability
#  Detection on Solana and Algorand Smart Contracts"
#
# Code Ocean: set this file as "File to Run"
# Local:      bash run.sh
#
# Required env vars (set in Code Ocean capsule → Environment Variables):
#   OPENAI_API_KEY      – for GPT-4o
#   ANTHROPIC_API_KEY   – for Claude Sonnet 4
#   TOGETHER_API_KEY    – for Llama-3.3-70B-Instruct-Turbo
#
# Without API keys the script skips LLM experiments and regenerates
# all figures from the pre-computed results/scores.csv.
# =============================================================================

# Recursion guard — Code Ocean sets BASH_ENV to the "File to Run", which
# would re-execute this script inside every $(...) subshell.
unset BASH_ENV ENV
if [[ "${_RUN_SH_GUARD:-}" == "1" ]]; then exit 0; fi
export _RUN_SH_GUARD=1

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths — Code Ocean always mounts capsule files under /code
# ---------------------------------------------------------------------------
if [[ -d "/code" ]]; then
  REPO_ROOT="/code"
else
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
SCRIPTS="$REPO_ROOT/scripts"

# Code Ocean requires results to be written to /results to appear in the
# computation snapshot. Fall back to $REPO_ROOT/results locally.
if [[ -d "/results" ]]; then
  OUT="/results"
else
  OUT="$REPO_ROOT/results"
fi

echo "============================================================"
echo " LLM Smart-Contract Audit Benchmark — Reproducible Run"
echo " $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo " REPO_ROOT : $REPO_ROOT"
echo " OUTPUT    : $OUT"
echo "============================================================"

# ---------------------------------------------------------------------------
# 0. Check API keys
# ---------------------------------------------------------------------------
SKIP_EXPERIMENTS=false
if [[ -z "${OPENAI_API_KEY:-}"    ||
      -z "${ANTHROPIC_API_KEY:-}" ||
      -z "${TOGETHER_API_KEY:-}" ]]; then
  echo ""
  echo "[INFO] One or more API keys not set — skipping LLM experiments."
  echo "       Figures will be regenerated from pre-computed scores.csv."
  SKIP_EXPERIMENTS=true
fi

# ---------------------------------------------------------------------------
# 1. Install extra Python dependencies not already in the base image
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 1] Installing Python dependencies..."
pip install --quiet --root-user-action=ignore \
    sentence-transformers together tqdm

# ---------------------------------------------------------------------------
# 2. Build RAG index  (saves to rag_corpus/faiss_index/ relative to repo)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 2] Building RAG index..."
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  python "$SCRIPTS/rag_index.py"
else
  echo "         Skipped (OPENAI_API_KEY not set)."
fi

# ---------------------------------------------------------------------------
# 3. Run LLM experiments — 216 runs (skip if keys missing)
# ---------------------------------------------------------------------------
if [[ "$SKIP_EXPERIMENTS" == "false" ]]; then
  echo ""
  echo "[STEP 3] Running 216 LLM experiments (est. 20-40 min)..."
  python "$SCRIPTS/run_experiments.py"
  echo ""
  echo "[STEP 3b] Running 216 patched-contract runs for FPR scoring..."
  python "$SCRIPTS/run_experiments.py" --patched
else
  echo ""
  echo "[STEP 3] Skipped — using pre-computed scores.csv."
fi

# ---------------------------------------------------------------------------
# 4. Score outputs  (updates scores.csv in place)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 4] Scoring outputs..."
python "$SCRIPTS/score_outputs.py" || echo "[INFO] Scoring complete."

# ---------------------------------------------------------------------------
# 5. Generate all 6 figures
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 5] Generating figures..."
python "$SCRIPTS/analyze.py"

# ---------------------------------------------------------------------------
# 6. Copy outputs to /results  (Code Ocean snapshot requirement)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 6] Copying outputs to $OUT/..."
mkdir -p "$OUT/figures"

# scores.csv
if [[ -f "$REPO_ROOT/results/scores.csv" ]]; then
  cp "$REPO_ROOT/results/scores.csv" "$OUT/scores.csv"
fi

# figures
if ls "$REPO_ROOT/figures/"*.png 2>/dev/null | grep -q .; then
  cp "$REPO_ROOT/figures/"*.png "$OUT/figures/"
fi

# raw outputs (if experiments were run)
if [[ -d "$REPO_ROOT/results/raw_outputs" ]]; then
  cp -r "$REPO_ROOT/results/raw_outputs"         "$OUT/raw_outputs"        2>/dev/null || true
fi
if [[ -d "$REPO_ROOT/results/raw_outputs_patched" ]]; then
  cp -r "$REPO_ROOT/results/raw_outputs_patched" "$OUT/raw_outputs_patched" 2>/dev/null || true
fi

echo ""
echo "[DONE] Files in $OUT/:"
ls -lh "$OUT/"
echo ""
ls -lh "$OUT/figures/" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 7. Summary statistics
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Summary Statistics"
echo "============================================================"
SCORES_FILE="${OUT}/scores.csv"
if [[ ! -f "$SCORES_FILE" ]]; then
  SCORES_FILE="$REPO_ROOT/results/scores.csv"
fi

python - "$SCORES_FILE" <<'PYEOF'
import sys, pandas as pd
df = pd.read_csv(sys.argv[1])
print(f"Total runs   : {len(df)}")
print(f"Overall DR   : {df['DR'].mean():.3f}")
print(f"Overall FPR  : {df['FPR'].mean():.3f}")
print(f"Overall EQS  : {df['EQS'].mean():.2f} / 5")
print(f"Overall RC   : {df['RC'].mean():.3f}")
print()
print("DR by model:")
print(df.groupby("model")["DR"].mean().round(3).to_string())
print()
print("DR by strategy:")
print(df.groupby("strategy")["DR"].mean().round(3).to_string())
print()
print("FPR by strategy:")
print(df.groupby("strategy")["FPR"].mean().round(3).to_string())
PYEOF

echo ""
echo "============================================================"
echo " Reproducible run complete."
echo "============================================================"
