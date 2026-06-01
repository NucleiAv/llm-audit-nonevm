# Securing Metaverse Blockchain Infrastructure: LLM-Assisted Vulnerability Detection on Solana and Algorand Smart Contracts

Companion repository for the paper submitted to **METAVERSE 2026** (Springer LNCS).

**Author:** Anmol Vats, NYU Tandon School of Engineering (`av3938@nyu.edu`)

**Reproducible capsule:** [Code Ocean DOI 10.24433/CO.0475286.v1](https://doi.org/10.24433/CO.0475286.v1)

---

## What this repo contains

Metaverse platforms rely on Solana and Algorand smart contracts for NFT ownership,
virtual economies, and cross-chain bridges — yet almost no LLM-based security tooling
exists for these chains. This repository provides the complete benchmark and pipeline
from the paper: 24 vulnerable/patched contract pairs across 8 vulnerability classes,
evaluated under 3 prompting strategies with 3 frontier LLMs (GPT-4o, Claude Sonnet 4,
Llama-3.3-70B), yielding 216 experimental runs.

---

## Repository Layout

| Path | Contents |
|------|----------|
| `contracts/solana/` | Rust/Anchor contracts for V1–V5 (vulnerable and patched) |
| `contracts/algorand/` | PyTEAL contracts for V6–V8 (vulnerable and patched) |
| `prompts/` | Prompt templates for zero-shot, CoT, and RAG strategies |
| `rag_corpus/` | Reference documents used for RAG retrieval |
| `scripts/` | Pipeline: RAG index builder, experiment runner, scorer, figure generator |
| `results/raw_outputs/` | Raw JSON outputs for all 216 experimental runs |
| `results/scores.csv` | Scored results (DR, FPR, EQS, RC) for all 216 runs |
| `figures/` | Generated figures (fig1–fig6) |
| `paper/main.tex` | LaTeX source (IEEEtran version) |
| `paper/metaverse_main.tex` | LaTeX source (LNCS version for METAVERSE 2026) |

---

## Vulnerability Classes

| ID | Chain | Class | Metaverse Impact |
|----|-------|-------|-----------------|
| V1 | Solana | Missing signer check | Unauthorized NFT minting, DAO takeover |
| V2 | Solana | Account confusion (type confusion) | Fake token mints in virtual marketplaces |
| V3 | Solana | Arithmetic overflow on u64 | Token vault exploits in play-to-earn economies |
| V4 | Solana | Bump seed canonicalization | PDA signature forgery for program-owned accounts |
| V5 | Solana | Stale account data after CPI | Double-withdrawal in DeFi/metaverse protocols |
| V6 | Algorand | Logic signature abuse | Unauthorized transfers in NFT bridges |
| V7 | Algorand | Group transaction manipulation | Fraudulent injection into atomic NFT settlements |
| V8 | Algorand | Unchecked asset receiver and fee fields | Fund redirection and account takeover |

---

## Key Results

| Strategy | DR (Solana) | DR (Algorand) | FPR (avg) |
|----------|------------|---------------|-----------|
| Zero-shot | 96.7% | 88.9% | 4.2% |
| Chain-of-thought (CoT) | **100%** | **100%** | **0.0%** |
| RAG | 100% | 88.9% | 11.1% |

CoT achieves 100% detection with 0% false positives across all three models.
GPT-4o zero-shot misses account confusion (V2) in 2 of 3 instances.
Llama-3.3-70B hallucinates EVM concepts (reentrancy, gas costs) in ~25% of Algorand zero-shot runs.

---

## Reproduction

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Set API keys:**
```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export TOGETHER_API_KEY=...
```

**Build the RAG index:**
```bash
python scripts/rag_index.py
```

**Dry-run a single contract to verify setup:**
```bash
python scripts/run_experiments.py \
  --contract contracts/solana/vulnerable/v1_missing_signer_inst1.rs \
  --strategy zero_shot \
  --model gpt-4o \
  --dry-run
```

**Run all 216 experiments:**
```bash
python scripts/run_experiments.py
```

**Check for any missing runs:**
```bash
python scripts/run_experiments.py --check-missing
```

**Score outputs:**
```bash
python scripts/score_outputs.py
```

**Generate all figures:**
```bash
python scripts/analyze.py
```

Estimated API cost: under **$20** for the full 216-run experiment.

---

## Models Evaluated

| Model | Provider | Version |
|-------|----------|---------|
| GPT-4o | OpenAI | `gpt-4o-2024-08-06` |
| Claude Sonnet 4 | Anthropic | `claude-sonnet-4-20250514` |
| Llama-3.3-70B-Instruct | Meta (via Together AI) | `Llama-3.3-70B-Instruct-Turbo` |

---

## Citation

```bibtex
@inproceedings{vats2026metaverse,
  author    = {Vats, Anmol},
  title     = {Securing Metaverse Blockchain Infrastructure: {LLM}-Assisted
               Vulnerability Detection on {Solana} and {Algorand} Smart Contracts},
  booktitle = {Proceedings of METAVERSE 2026 (Springer LNCS)},
  year      = {2026}
}
```

*(BibTeX will be updated with volume/pages after proceedings publication.)*
