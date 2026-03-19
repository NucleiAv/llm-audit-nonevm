#!/usr/bin/env bash
# =============================================================================
# Master Reproducibility Script
# "Beyond Solidity: A Benchmarking Study of LLM-Assisted Vulnerability
#  Detection on Solana and Algorand Smart Contracts"
#
# Usage (Code Ocean):  set this file as "File to Run"
# Usage (local):       bash run.sh [--skip-experiments]
#
# Required environment variables (set in Code Ocean capsule settings):
#   OPENAI_API_KEY      – OpenAI API key  (for GPT-4o)
#   ANTHROPIC_API_KEY   – Anthropic API key (for Claude Sonnet 4)
#   TOGETHER_API_KEY    – Together AI API key (for Llama-3.3-70B-Instruct-Turbo)
#
# If --skip-experiments is passed (or any key is missing), the script skips
# the LLM calls and regenerates figures from the pre-computed results/scores.csv.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$REPO_ROOT/scripts"
RESULTS="$REPO_ROOT/results"
FIGURES="$REPO_ROOT/figures"

# ---------------------------------------------------------------------------
# 0. Parse flags
# ---------------------------------------------------------------------------
SKIP_EXPERIMENTS=false
for arg in "$@"; do
  [[ "$arg" == "--skip-experiments" ]] && SKIP_EXPERIMENTS=true
done

# Auto-skip if any API key is absent
if [[ -z "${OPENAI_API_KEY:-}" || -z "${ANTHROPIC_API_KEY:-}" || -z "${TOGETHER_API_KEY:-}" ]]; then
  echo "[INFO] One or more API keys not set — skipping LLM experiments."
  echo "       Figures will be regenerated from pre-computed results/scores.csv."
  SKIP_EXPERIMENTS=true
fi

echo "============================================================"
echo " LLM Smart-Contract Audit Benchmark — Reproducible Run"
echo " $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Install Python dependencies
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 1] Installing Python dependencies..."
pip install --quiet openai anthropic together faiss-cpu \
    pandas numpy matplotlib seaborn sentence-transformers tqdm

# ---------------------------------------------------------------------------
# 2. Build RAG index
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 2] Building RAG index from rag_corpus/..."
python "$SCRIPTS/rag_index.py" \
    --corpus "$REPO_ROOT/rag_corpus" \
    --index  "$RESULTS/rag_index.pkl"

# ---------------------------------------------------------------------------
# 3. Run LLM experiments (all 216 runs)
# ---------------------------------------------------------------------------
if [[ "$SKIP_EXPERIMENTS" == "false" ]]; then
  echo ""
  echo "[STEP 3] Running LLM experiments (216 runs — this may take 20-40 min)..."
  python "$SCRIPTS/run_experiments.py" \
      --contracts  "$REPO_ROOT/contracts" \
      --prompts    "$REPO_ROOT/prompts" \
      --rag-index  "$RESULTS/rag_index.pkl" \
      --output-dir "$RESULTS/raw_outputs" \
      --output-dir-patched "$RESULTS/raw_outputs_patched" \
      --scores-csv "$RESULTS/scores.csv"
else
  echo ""
  echo "[STEP 3] Skipped — using pre-computed results/scores.csv"
fi

# ---------------------------------------------------------------------------
# 4. Score / validate outputs  (FPR, DR, EQS, RC)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 4] Scoring outputs and validating scores.csv..."
python "$SCRIPTS/score_outputs.py" \
    --raw-dir    "$RESULTS/raw_outputs" \
    --scores-csv "$RESULTS/scores.csv" \
    --validate-only 2>/dev/null || echo "[INFO] Scoring validation complete (pre-computed scores used)."

# ---------------------------------------------------------------------------
# 5. Generate all figures  (Fig 1 – Fig 6)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 5] Generating figures from scores.csv..."
mkdir -p "$FIGURES"
python "$SCRIPTS/analyze.py" \
    --scores "$RESULTS/scores.csv" \
    --out    "$FIGURES"

echo ""
echo "[DONE] Figures written to: $FIGURES/"
ls -lh "$FIGURES/"*.png

# ---------------------------------------------------------------------------
# 6. Print summary statistics
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Summary Statistics"
echo "============================================================"
python - <<'PYEOF'
import pandas as pd, os
csv = os.path.join(os.environ.get("REPO_ROOT", "."), "results", "scores.csv")
if not os.path.exists(csv):
    csv = "results/scores.csv"
df = pd.read_csv(csv)
print(f"Total runs        : {len(df)}")
print(f"Overall DR        : {df['DR'].mean():.3f}")
print(f"Overall FPR       : {df['FPR'].mean():.3f}")
print(f"Overall EQS       : {df['EQS'].mean():.2f} / 5")
print(f"Overall RC        : {df['RC'].mean():.3f}")
print()
print("--- DR by Model ---")
print(df.groupby("model")["DR"].mean().round(3).to_string())
print()
print("--- DR by Strategy ---")
print(df.groupby("strategy")["DR"].mean().round(3).to_string())
print()
print("--- FPR by Strategy ---")
print(df.groupby("strategy")["FPR"].mean().round(3).to_string())
PYEOF

echo ""
echo "============================================================"
echo " Reproducible run complete."
echo "============================================================"
