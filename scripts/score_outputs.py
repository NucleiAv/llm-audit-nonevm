"""
Manual-assist scoring script for the 216 experimental runs.

DR  (detection rate): 1 if model correctly names the vulnerability class
    AND points to the correct code location; 0 otherwise.
FPR (false positive rate): for patched contracts, 1 if model incorrectly
    claims a vulnerability is present; measured separately by reading the
    patched contract and checking model output.
EQS (explanation quality score): 1-5 rubric (see proposal Section 5.3).
RC  (reasoning coherence): 1 if model response contains no factually wrong
    statements about the language/runtime (e.g., claiming Solana has
    Ethereum-style reentrancy); 0 otherwise.

Usage:
  python scripts/score_outputs.py            # scores all unscored runs
  python scripts/score_outputs.py --file <json_path>  # score single file
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).parent.parent
RESULTS_DIR = REPO_ROOT / "results"
RAW_DIR = RESULTS_DIR / "raw_outputs"
SCORES_CSV = RESULTS_DIR / "scores.csv"

CSV_HEADERS = [
    "filename", "chain", "vuln_class", "instance", "strategy", "model",
    "DR", "FPR", "EQS", "RC", "notes",
]

VULN_CLASS_KEYWORDS = {
    "v1_missing_signer": ["missing signer", "signer check", "AccountInfo", "Signer<'info>", "has_one"],
    "v2_account_confusion": ["account confusion", "type confusion", "owner check", "account validation", "collateral"],
    "v3_arithmetic_overflow": ["overflow", "integer overflow", "checked_mul", "wrapping", "arithmetic"],
    "v4_bump_seed": ["bump seed", "canonical bump", "create_program_address", "find_program_address", "PDA"],
    "v5_stale_cpi": ["stale", "CPI", "reload", "cross-program invocation", "stale account"],
    "v6_logsig_abuse": ["logic signature", "LogicSig", "reuse", "replay", "logsig"],
    "v7_group_tx": ["group transaction", "group index", "group_size", "atomic group", "Gtxn"],
    "v8_unchecked_fields": ["unchecked", "receiver", "fee", "close_remainder_to", "asset_receiver", "rekey_to"],
}

EVM_HALLUCINATIONS = [
    "reentrancy",
    "gas limit",
    "solidity",
    "evm",
    "ethereum virtual machine",
    "msg.sender",
    "fallback function",
    "storage slot",
    "wei",
    "gwei",
    "opcode",
]


def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem
    parts = stem.split("_")
    chain = parts[0]
    if chain == "solana":
        vuln_class = "_".join(parts[1:3])
        instance = parts[3]
        strategy = parts[4]
        model = "_".join(parts[5:])
    else:
        vuln_class = "_".join(parts[1:3])
        instance = parts[3]
        strategy = parts[4]
        model = "_".join(parts[5:])
    return {
        "chain": chain,
        "vuln_class": vuln_class,
        "instance": instance,
        "strategy": strategy,
        "model": model,
    }


def auto_score_dr(response: str, vuln_class: str) -> int:
    response_lower = response.lower()
    keywords = VULN_CLASS_KEYWORDS.get(vuln_class, [])
    return int(any(kw.lower() in response_lower for kw in keywords))


def auto_score_rc(response: str, chain: str) -> int:
    response_lower = response.lower()
    for hallucination in EVM_HALLUCINATIONS:
        if hallucination in response_lower:
            return 0
    return 1


def auto_score_eqs(response: str, vuln_class: str, dr: int) -> int:
    if dr == 0:
        return 1
    response_lower = response.lower()
    has_location = bool(re.search(r"line\s+\d+|fn\s+\w+|pub\s+\w+|Gtxn\[\d+\]|Txn\.", response_lower))
    has_attack = any(w in response_lower for w in ["attacker", "exploit", "bypass", "attack scenario"])
    has_fix = any(w in response_lower for w in ["fix", "recommend", "should", "replace", "use signer", "checked_"])
    score = 2
    if has_location:
        score = 3
    if has_location and has_attack:
        score = 4
    if has_location and has_attack and has_fix:
        score = 5
    return score


def score_single_file(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    meta = parse_filename(json_path.name)
    response = data.get("response", "")

    dr = auto_score_dr(response, meta["vuln_class"])
    rc = auto_score_rc(response, meta["chain"])
    eqs = auto_score_eqs(response, meta["vuln_class"], dr)

    return {
        "filename": json_path.name,
        "chain": meta["chain"],
        "vuln_class": meta["vuln_class"],
        "instance": meta["instance"],
        "strategy": meta["strategy"],
        "model": meta["model"],
        "DR": dr,
        "FPR": "",
        "EQS": eqs,
        "RC": rc,
        "notes": "",
    }


def load_existing_scores() -> dict:
    if not SCORES_CSV.exists():
        return {}
    with open(SCORES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["filename"]: row for row in reader}


def save_scores(scores: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(SCORES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(scores)
    logging.info("wrote %d rows to %s", len(scores), SCORES_CSV)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score raw model outputs")
    parser.add_argument("--file", help="Score a single JSON file")
    args = parser.parse_args()

    if args.file:
        row = score_single_file(Path(args.file))
        print(json.dumps(row, indent=2))
        return

    existing = load_existing_scores()
    all_json = sorted(RAW_DIR.glob("*.json"))
    if not all_json:
        raise FileNotFoundError(f"No JSON files found in {RAW_DIR}. Run run_experiments.py first.")

    rows = []
    for json_path in all_json:
        if json_path.name in existing:
            rows.append(existing[json_path.name])
            continue
        try:
            row = score_single_file(json_path)
            rows.append(row)
            logging.info("scored %s (DR=%s, EQS=%s, RC=%s)", json_path.name, row["DR"], row["EQS"], row["RC"])
        except Exception as exc:
            logging.error("failed to score %s: %s", json_path.name, exc)

    save_scores(rows)
    logging.info("scoring complete: %d / 216 rows", len(rows))


if __name__ == "__main__":
    main()
