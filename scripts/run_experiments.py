import argparse
import json
import logging
import os
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import faiss
import numpy as np
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"
PROMPTS_DIR = REPO_ROOT / "prompts"
RAG_INDEX_DIR = REPO_ROOT / "rag_corpus" / "faiss_index"
RESULTS_DIR = REPO_ROOT / "results" / "raw_outputs"
PATCHED_DIR = REPO_ROOT / "results" / "raw_outputs_patched"
EMBEDDING_MODEL = "text-embedding-3-small"
RAG_TOP_K = 3

MODELS = {
    "gpt-4o": "gpt-4o-2024-08-06",
    # claude-3-7-sonnet-20250219 reached EOL 2026-02-19; claude-sonnet-4-20250514 is current
    "claude-3-7": "claude-sonnet-4-20250514",
    # CodeLlama 34B serverless not available; Llama-3.3-70B is the accessible open model
    "codellama": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
}

STRATEGIES = ["zero_shot", "cot", "rag"]

CHAIN_EXTENSIONS = {
    "solana": ".rs",
    "algorand": ".py",
}

VULN_CLASSES = {
    "solana": [
        "v1_missing_signer",
        "v2_account_confusion",
        "v3_arithmetic_overflow",
        "v4_bump_seed",
        "v5_stale_cpi",
    ],
    "algorand": ["v6_logsig_abuse", "v7_group_tx", "v8_unchecked_fields"],
}

INSTANCES = ["inst1", "inst2", "inst3"]


def load_contract(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt_template(strategy: str, chain: str) -> str:
    path = PROMPTS_DIR / f"{strategy}_{chain}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def retrieve_context(client: OpenAI, contract_code: str, top_k: int) -> str:
    index_path = RAG_INDEX_DIR / "index.faiss"
    chunks_path = RAG_INDEX_DIR / "chunks.pkl"
    if not index_path.exists() or not chunks_path.exists():
        raise FileNotFoundError(
            f"RAG index not found at {RAG_INDEX_DIR}. Run scripts/rag_index.py first."
        )
    index = faiss.read_index(str(index_path))
    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)

    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[contract_code])
    query_vec = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    distances, indices = index.search(query_vec, top_k)
    retrieved = [chunks[i]["text"] for i in indices[0] if i < len(chunks)]
    return "\n\n---\n\n".join(retrieved)


def build_prompt(
    strategy: str, chain: str, contract_code: str, openai_client: OpenAI
) -> str:
    template = load_prompt_template(strategy, chain)
    if strategy == "rag":
        context = retrieve_context(openai_client, contract_code, RAG_TOP_K)
        return template.replace("{retrieved_context}", context).replace(
            "{contract_code}", contract_code
        )
    return template.replace("{contract_code}", contract_code)


def call_gpt4o(client: OpenAI, prompt: str, model_version: str) -> str:
    response = client.chat.completions.create(
        model=model_version,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def call_claude(client: anthropic.Anthropic, prompt: str, model_version: str) -> str:
    response = client.messages.create(
        model=model_version,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_codellama(prompt: str, model_version: str, openrouter_api_key: str) -> str:
    # Open-source model (Llama-3.3-70B) routed through Together AI serverless endpoint
    from openai import OpenAI as TogetherClient

    client = TogetherClient(
        api_key=openrouter_api_key,
        base_url="https://api.together.xyz/v1",
    )
    response = client.chat.completions.create(
        model=model_version,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def run_single(
    chain: str,
    vuln_class: str,
    instance: str,
    strategy: str,
    model_key: str,
    openai_client: OpenAI,
    anthropic_client: anthropic.Anthropic,
    openrouter_api_key: str,
    dry_run: bool,
    patched: bool = False,
) -> dict:
    ext = CHAIN_EXTENSIONS[chain]
    variant = "patched" if patched else "vulnerable"
    contract_path = CONTRACTS_DIR / chain / variant / f"{vuln_class}_{instance}{ext}"
    contract_code = load_contract(contract_path)
    prompt = build_prompt(strategy, chain, contract_code, openai_client)

    output_filename = f"{chain}_{vuln_class}_{instance}_{strategy}_{model_key}.json"
    out_dir = PATCHED_DIR if patched else RESULTS_DIR
    output_path = out_dir / output_filename

    if dry_run:
        logging.info("[dry-run] would write to %s", output_path)
        result = {
            "contract_file": str(contract_path.relative_to(REPO_ROOT)),
            "strategy": strategy,
            "model": model_key,
            "model_version": MODELS[model_key],
            "prompt": prompt,
            "response": "[dry-run: no API call made]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    model_version = MODELS[model_key]
    if model_key == "gpt-4o":
        response_text = call_gpt4o(openai_client, prompt, model_version)
    elif model_key == "claude-3-7":
        response_text = call_claude(anthropic_client, prompt, model_version)
    elif model_key == "codellama":
        if not openrouter_api_key:
            raise ValueError(
                "TOGETHER_API_KEY environment variable is not set for open-source model"
            )
        response_text = call_codellama(prompt, model_version, openrouter_api_key)
    else:
        raise ValueError(f"Unknown model key: {model_key}")

    result = {
        "contract_file": str(contract_path.relative_to(REPO_ROOT)),
        "strategy": strategy,
        "model": model_key,
        "model_version": model_version,
        "prompt": prompt,
        "response": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logging.info("wrote %s", output_filename)
    return result


def enumerate_all_runs() -> list[dict]:
    runs = []
    for chain, classes in VULN_CLASSES.items():
        for vuln_class in classes:
            for instance in INSTANCES:
                for strategy in STRATEGIES:
                    for model_key in MODELS:
                        runs.append(
                            {
                                "chain": chain,
                                "vuln_class": vuln_class,
                                "instance": instance,
                                "strategy": strategy,
                                "model_key": model_key,
                            }
                        )
    return runs


def check_missing() -> None:
    all_runs = enumerate_all_runs()
    missing = []
    for run in all_runs:
        fname = (
            f"{run['chain']}_{run['vuln_class']}_{run['instance']}"
            f"_{run['strategy']}_{run['model_key']}.json"
        )
        if not (RESULTS_DIR / fname).exists():
            missing.append(fname)
    if missing:
        logging.info("%d missing runs:", len(missing))
        for m in missing:
            print(m)
    else:
        logging.info("all 216 runs present")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM vulnerability detection experiments"
    )
    parser.add_argument("--contract", help="Single contract file path for targeted run")
    parser.add_argument("--strategy", choices=STRATEGIES, help="Prompting strategy")
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Model key")
    parser.add_argument(
        "--dry-run", action="store_true", help="Build prompt but skip API call"
    )
    parser.add_argument(
        "--check-missing", action="store_true", help="List missing run outputs"
    )
    parser.add_argument(
        "--patched",
        action="store_true",
        help="Run patched contracts (for FPR scoring) instead of vulnerable",
    )
    args = parser.parse_args()

    if args.check_missing:
        check_missing()
        return

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    openrouter_key = os.environ.get("TOGETHER_API_KEY", "")

    openai_client = OpenAI(api_key=openai_key)
    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PATCHED_DIR.mkdir(parents=True, exist_ok=True)

    if args.contract:
        if not args.strategy or not args.model:
            parser.error("--contract requires --strategy and --model")
        contract_path = Path(args.contract)
        parts = contract_path.stem.split("_")
        chain = "solana" if contract_path.suffix == ".rs" else "algorand"
        # vuln_class is always 3 parts: v{n}_{word}_{word}
        vuln_class = "_".join(parts[:3])
        instance = parts[-1]
        run_single(
            chain,
            vuln_class,
            instance,
            args.strategy,
            args.model,
            openai_client,
            anthropic_client,
            openrouter_key,
            args.dry_run,
            patched=args.patched,
        )
        return

    all_runs = enumerate_all_runs()
    out_dir = PATCHED_DIR if args.patched else RESULTS_DIR
    label = "patched" if args.patched else "vulnerable"
    logging.info("running %d %s experiments", len(all_runs), label)
    for i, run in enumerate(all_runs, 1):
        output_fname = (
            f"{run['chain']}_{run['vuln_class']}_{run['instance']}"
            f"_{run['strategy']}_{run['model_key']}.json"
        )
        if (out_dir / output_fname).exists():
            logging.info("[%d/%d] skip (exists): %s", i, len(all_runs), output_fname)
            continue
        logging.info("[%d/%d] running: %s", i, len(all_runs), output_fname)
        try:
            run_single(
                run["chain"],
                run["vuln_class"],
                run["instance"],
                run["strategy"],
                run["model_key"],
                openai_client,
                anthropic_client,
                openrouter_key,
                args.dry_run,
                patched=args.patched,
            )
        except Exception as exc:
            logging.error("failed %s: %s", output_fname, exc)
            continue
        # Brief pause to respect API rate limits.
        time.sleep(0.5)

    logging.info("all experiments complete")


if __name__ == "__main__":
    main()
