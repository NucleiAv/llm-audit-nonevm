# Beyond Solidity: LLM Vulnerability Detection on Non-EVM Smart Contracts

Companion repository for:
"Beyond Solidity: A Benchmarking Study of LLM-Assisted Vulnerability Detection on Solana and Algorand Smart Contracts"
Author: Anmol Vats, NYU Tandon School of Engineering

## Contents

- `contracts/solana/` — Rust/Anchor contracts for V1-V5 (vulnerable and patched)
- `contracts/algorand/` — PyTEAL contracts for V6-V8 (vulnerable and patched)
- `prompts/` — Prompt templates for zero-shot, chain-of-thought, and RAG strategies
- `rag_corpus/` — Reference documents used for RAG retrieval
- `scripts/` — Pipeline scripts: RAG index, experiment runner, scorer, figure generator
- `results/raw_outputs/` — Raw JSON outputs for all 216 experimental runs
- `results/scores.csv` — Scored results (DR, FPR, EQS, RC) for all runs
- `figures/` — Generated figures (fig1-fig6)
- `paper/` — LaTeX source for the paper

## Vulnerability Classes

| ID | Chain | Class |
|----|-------|-------|
| V1 | Solana | Missing signer check |
| V2 | Solana | Account confusion (type confusion) |
| V3 | Solana | Arithmetic overflow on u64 |
| V4 | Solana | Bump seed canonicalization |
| V5 | Solana | Stale account data after CPI |
| V6 | Algorand | Logic signature abuse |
| V7 | Algorand | Group transaction manipulation |
| V8 | Algorand | Unchecked asset receiver and fee fields |

## Reproduction

Install dependencies:
```
pip install -r requirements.txt
```

Set API keys:
```
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export TOGETHER_API_KEY=...
```

Build RAG index:
```
python scripts/rag_index.py
```

Run a single dry-run to verify the pipeline:
```
python scripts/run_experiments.py \
  --contract contracts/solana/vulnerable/v1_missing_signer_inst1.rs \
  --strategy zero_shot \
  --model gpt-4o \
  --dry-run
```

Run all 216 experiments:
```
python scripts/run_experiments.py
```

Check for missing runs:
```
python scripts/run_experiments.py --check-missing
```

Score outputs:
```
python scripts/score_outputs.py
```

Generate all figures:
```
python scripts/analyze.py
```

Estimated API cost: under $20 for the full experimental run.

## Citation

[BibTeX entry added after paper acceptance]
