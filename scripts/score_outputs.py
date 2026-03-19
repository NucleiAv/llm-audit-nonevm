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
PATCHED_DIR = RESULTS_DIR / "raw_outputs_patched"
SCORES_CSV = RESULTS_DIR / "scores.csv"

CSV_HEADERS = [
    "filename",
    "chain",
    "vuln_class",
    "instance",
    "strategy",
    "model",
    "DR",
    "FPR",
    "EQS",
    "RC",
    "notes",
]

VULN_CLASS_KEYWORDS = {
    "v1_missing_signer": [
        "missing signer",
        "signer check",
        "AccountInfo",
        "Signer<'info>",
        "has_one",
    ],
    "v2_account_confusion": [
        "account confusion",
        "type confusion",
        "owner check",
        "account validation",
        "collateral",
    ],
    "v3_arithmetic_overflow": [
        "overflow",
        "integer overflow",
        "checked_mul",
        "wrapping",
        "arithmetic",
    ],
    "v4_bump_seed": [
        "bump seed",
        "canonical bump",
        "create_program_address",
        "find_program_address",
        "PDA",
    ],
    "v5_stale_cpi": [
        "stale",
        "CPI",
        "reload",
        "cross-program invocation",
        "stale account",
    ],
    "v6_logsig_abuse": ["logic signature", "LogicSig", "reuse", "replay", "logsig"],
    "v7_group_tx": [
        "group transaction",
        "group index",
        "group_size",
        "atomic group",
        "Gtxn",
    ],
    "v8_unchecked_fields": [
        "unchecked",
        "receiver",
        "fee",
        "close_remainder_to",
        "asset_receiver",
        "rekey_to",
    ],
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


_KNOWN_VULN_CLASSES = [
    "v1_missing_signer",
    "v2_account_confusion",
    "v3_arithmetic_overflow",
    "v4_bump_seed",
    "v5_stale_cpi",
    "v6_logsig_abuse",
    "v7_group_tx",
    "v8_unchecked_fields",
]
_KNOWN_STRATEGIES = ["zero_shot", "cot", "rag"]
_KNOWN_MODELS = ["gpt-4o", "claude-3-7", "codellama"]


def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem
    chain = stem.split("_")[0]
    vuln_class = next((vc for vc in _KNOWN_VULN_CLASSES if f"_{vc}_" in stem), None)
    if vuln_class is None:
        raise ValueError(f"Could not parse vuln_class from filename: {filename}")
    remainder = stem[len(chain) + 1 + len(vuln_class) + 1 :]
    # remainder is now: {instance}_{strategy}_{model}
    instance = remainder.split("_")[0]
    after_instance = remainder[len(instance) + 1 :]
    strategy = next(
        (s for s in _KNOWN_STRATEGIES if after_instance.startswith(s)), None
    )
    if strategy is None:
        raise ValueError(f"Could not parse strategy from filename: {filename}")
    model = after_instance[len(strategy) + 1 :]
    if model not in _KNOWN_MODELS:
        raise ValueError(f"Unknown model '{model}' in filename: {filename}")
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
    has_location = bool(
        re.search(r"line\s+\d+|fn\s+\w+|pub\s+\w+|Gtxn\[\d+\]|Txn\.", response_lower)
    )
    has_attack = any(
        w in response_lower
        for w in ["attacker", "exploit", "bypass", "attack scenario"]
    )
    has_fix = any(
        w in response_lower
        for w in ["fix", "recommend", "should", "replace", "use signer", "checked_"]
    )
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


def fill_fpr_from_patched() -> None:
    """Score FPR column by checking model responses on patched contracts.

    A false positive (FPR=1) means the model claimed a vulnerability exists
    on a contract where the bug has been fixed.
    """
    patched_files = sorted(PATCHED_DIR.glob("*.json"))
    if not patched_files:
        raise FileNotFoundError(
            f"No patched JSON files in {PATCHED_DIR}. "
            "Run: python scripts/run_experiments.py --patched"
        )

    existing = load_existing_scores()
    if not existing:
        raise FileNotFoundError(
            "No scores.csv found. Run score_outputs.py (without --fill-fpr) first."
        )

    updated = 0
    for json_path in patched_files:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        response = data.get("response", "")
        try:
            meta = parse_filename(json_path.name)
        except ValueError as exc:
            logging.error("skip %s: %s", json_path.name, exc)
            continue

        # FPR=1 if model mentions vulnerability keywords on patched contract
        fpr = auto_score_dr(response, meta["vuln_class"])

        vuln_filename = json_path.name  # same name as vulnerable counterpart
        if vuln_filename in existing:
            existing[vuln_filename]["FPR"] = fpr
            updated += 1
            logging.info("FPR=%d for %s", fpr, vuln_filename)
        else:
            logging.warning("no matching row for %s in scores.csv", vuln_filename)

    rows = list(existing.values())
    save_scores(rows)
    logging.info("filled FPR for %d rows", updated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score raw model outputs")
    parser.add_argument("--file", help="Score a single JSON file")
    parser.add_argument(
        "--fill-fpr",
        action="store_true",
        help="Fill FPR column from patched contract runs in raw_outputs_patched/",
    )
    args = parser.parse_args()

    if args.fill_fpr:
        fill_fpr_from_patched()
        return

    if args.file:
        row = score_single_file(Path(args.file))
        print(json.dumps(row, indent=2))
        return

    existing = load_existing_scores()
    all_json = sorted(RAW_DIR.glob("*.json"))
    if not all_json:
        raise FileNotFoundError(
            f"No JSON files found in {RAW_DIR}. Run run_experiments.py first."
        )

    rows = []
    for json_path in all_json:
        if json_path.name in existing:
            rows.append(existing[json_path.name])
            continue
        try:
            row = score_single_file(json_path)
            rows.append(row)
            logging.info(
                "scored %s (DR=%s, EQS=%s, RC=%s)",
                json_path.name,
                row["DR"],
                row["EQS"],
                row["RC"],
            )
        except Exception as exc:
            logging.error("failed to score %s: %s", json_path.name, exc)

    save_scores(rows)
    logging.info("scoring complete: %d / 216 rows", len(rows))


if __name__ == "__main__":
    main()
