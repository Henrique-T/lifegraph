"""Generate frozen final-evaluation predictions without scoring or tuning.

This runner implements the already frozen execution contract for systems A, B,
and C.  It deliberately does not import the metric implementation and never
changes the held-out dataset, prompt, or execution configuration.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GLINER_APP = ROOT / "gliner-service"
PROTOCOL_PATH = HERE / "protocol.json"
CONFIG_PATH = HERE / "execution_config.json"
PROMPT_PATH = HERE / "gemma_prompt.txt"
WARMUP_TEXT = "Nasci em 2000."


def digest(path: Path) -> str:
    """Return an uppercase SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    """Read one UTF-8 JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def verify_frozen_inputs(dataset_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify all hashes and authorization before loading a model."""
    protocol = load_json(PROTOCOL_PATH)
    config = load_json(CONFIG_PATH)
    dataset = load_json(dataset_path)
    recorded_protocol_hash = (HERE / "protocol.sha256").read_text(encoding="ascii").split()[0]
    if digest(PROTOCOL_PATH) != recorded_protocol_hash:
        raise RuntimeError("FROZEN_PROTOCOL_HASH_MISMATCH")
    if digest(CONFIG_PATH) != protocol["execution_config_sha256"]:
        raise RuntimeError("FROZEN_EXECUTION_CONFIG_HASH_MISMATCH")
    if digest(PROMPT_PATH) != protocol["systems"]["C"]["prompt_sha256"]:
        raise RuntimeError("FROZEN_PROMPT_HASH_MISMATCH")
    if digest(dataset_path) != protocol["data"]["held_out_sha256"]:
        raise RuntimeError("FROZEN_DATASET_HASH_MISMATCH")
    review_path = ROOT / protocol["data"]["human_review_record"]
    if digest(review_path) != protocol["data"]["human_review_sha256"]:
        raise RuntimeError("HUMAN_REVIEW_HASH_MISMATCH")
    if not protocol["data"]["human_ground_truth_review"]:
        raise RuntimeError("HUMAN_REVIEW_NOT_COMPLETE")
    if not protocol["final_model_comparison_authorized"]:
        raise RuntimeError("FINAL_MODEL_COMPARISON_NOT_AUTHORIZED")
    return protocol, config, dataset


def package_version(name: str) -> str | None:
    """Return an installed distribution version without failing provenance."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def runtime_provenance(system: str, config: dict[str, Any]) -> dict[str, Any]:
    """Capture non-sensitive execution provenance."""
    return {
        "system": system,
        "model_id": config[f"system_{system.lower()}"]["model_id"],
        "model_revision": config[f"system_{system.lower()}"]["model_revision"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "packages": {
            "gliner2": package_version("gliner2"),
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
            "tokenizers": package_version("tokenizers"),
            "numpy": package_version("numpy"),
        },
    }


def iso_utc(value: Any) -> str | None:
    """Serialize a UTC datetime using the frozen ground-truth representation."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def next_exact_span(text: str, value: str | None, used: set[tuple[int, int]]) -> dict[str, Any] | None:
    """Locate an exact substring left-to-right, without fuzzy repair."""
    if not value:
        return None
    start = 0
    while True:
        index = text.find(value, start)
        if index < 0:
            return None
        span = (index, index + len(value))
        if span not in used:
            used.add(span)
            return {"text": value, "start": span[0], "end": span[1]}
        start = index + 1


def approved_result_to_events(text: str, result: Any) -> list[dict[str, Any]]:
    """Map the production result to the frozen canonical prediction schema."""
    used_dates: set[tuple[int, int]] = set()
    events = []
    for candidate in result.candidates:
        subject_text = candidate.subject_text
        if candidate.subject_resolution == "UNRESOLVED":
            subject_role = "UNRESOLVED"
            subject_text = None
        elif subject_text == "__NARRATOR__":
            subject_role = "NARRATOR"
        else:
            subject_role = "THIRD_PARTY"
        normalized = candidate.normalized_time_candidate
        normalized_time = {
            "start": iso_utc(normalized.start) if normalized else None,
            "end": iso_utc(normalized.end) if normalized else None,
            "precision": normalized.temporal_precision if normalized else "UNSUPPORTED",
            # The frozen production pipeline does not claim uncertainty detection.
            "uncertainty": False,
        }
        date_expression = next_exact_span(text, candidate.date_expression, used_dates)
        events.append({
            "event_type": candidate.event_type,
            "trigger": {
                "text": candidate.trigger_text,
                "start": candidate.trigger_start,
                "end": candidate.trigger_end,
            },
            "subject_text": subject_text,
            "subject_role": subject_role,
            "participant_texts": list(candidate.participant_texts),
            "date_expression": date_expression,
            "normalized_time": normalized_time,
        })
    return events


async def load_system_a(config: dict[str, Any], cache_dir: str | None, offline: bool) -> Any:
    """Load the approved production GLiNER pipeline at its pinned revision."""
    del cache_dir
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    if str(GLINER_APP) not in sys.path:
        sys.path.insert(0, str(GLINER_APP))
    from app.model import GLiNERModel, MODEL_ID, MODEL_REVISION

    frozen = config["system_a"]
    if MODEL_ID != frozen["model_id"] or MODEL_REVISION != frozen["model_revision"]:
        raise RuntimeError("SYSTEM_A_IDENTITY_MISMATCH")
    model = GLiNERModel()
    await model.load()
    if not model.ready:
        raise RuntimeError("SYSTEM_A_MODEL_LOAD_FAILED")
    return model


def load_system_b(config: dict[str, Any], cache_dir: str | None, offline: bool) -> Any:
    """Load the frozen Portuguese NER baseline."""
    from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

    frozen = config["system_b"]
    common = {
        "revision": frozen["model_revision"],
        "cache_dir": cache_dir,
        "local_files_only": offline,
    }
    tokenizer = AutoTokenizer.from_pretrained(frozen["model_id"], use_fast=True, **common)
    model = AutoModelForTokenClassification.from_pretrained(frozen["model_id"], **common)
    model.eval()
    return pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy=frozen["aggregation_strategy"],
        device=-1,
    )


def load_system_c(config: dict[str, Any], cache_dir: str | None, offline: bool) -> tuple[Any, Any]:
    """Load the frozen structured generative baseline."""
    import torch
    from transformers import AutoProcessor, Gemma3ForConditionalGeneration

    frozen = config["system_c"]
    common = {
        "revision": frozen["model_revision"],
        "cache_dir": cache_dir,
        "local_files_only": offline,
    }
    processor = AutoProcessor.from_pretrained(frozen["model_id"], **common)
    model = Gemma3ForConditionalGeneration.from_pretrained(
        frozen["model_id"], dtype=torch.bfloat16, **common
    )
    model.to("cpu")
    model.eval()
    return model, processor


def classify_failure(exc: Exception) -> str:
    """Map runtime exceptions to the frozen technical failure classes."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "MODEL_TIMEOUT"
    return "MODEL_SERVICE_FAILURE"


async def infer_a(model: Any, text: str) -> list[dict[str, Any]]:
    """Run one approved LifeGraph inference."""
    return approved_result_to_events(text, await model.extract(text))


def infer_b(model: Any, text: str, config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Run one frozen shared-NER inference and retain exact offsets."""
    label_map = config["system_b"]["evaluation_label_map"]
    result = {"person_spans": [], "date_spans": []}
    retained: dict[tuple[str, int, int], dict[str, Any]] = {}
    for item in model(text):
        group = item.get("entity_group")
        mapped = label_map.get(group)
        if mapped not in {"PERSON", "DATE"}:
            continue
        start, end = int(item["start"]), int(item["end"])
        if not text[start:end]:
            continue
        key = (mapped, start, end)
        candidate = {"text": text[start:end], "start": start, "end": end, "score": float(item["score"])}
        if key not in retained or candidate["score"] > retained[key]["score"]:
            retained[key] = candidate
    for (kind, _, _), item in retained.items():
        result["person_spans" if kind == "PERSON" else "date_spans"].append(item)
    result["person_spans"].sort(key=lambda item: (item["start"], item["end"]))
    result["date_spans"].sort(key=lambda item: (item["start"], item["end"]))
    return result


def infer_c(model: Any, processor: Any, text: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Run one frozen greedy Gemma generation and parse its complete JSON output."""
    import torch

    prompt = PROMPT_PATH.read_text(encoding="utf-8").replace("{{NARRATIVE}}", text, 1)
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    if int(inputs["input_ids"].shape[-1]) > config["system_c"]["input_token_limit"]:
        raise RuntimeError("MODEL_SERVICE_FAILURE_INPUT_OVERFLOW")
    inputs = {key: value.to("cpu") if hasattr(value, "to") else value for key, value in inputs.items()}
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=config["system_c"]["max_new_tokens"],
            num_return_sequences=1,
        )
    continuation = generated[0, inputs["input_ids"].shape[-1]:]
    raw = processor.decode(continuation, skip_special_tokens=True).strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("events"), list):
        raise ValueError("MODEL_OUTPUT_INVALID")
    return parsed["events"]


def percentile_95(values: list[float]) -> float | None:
    """Return the nearest-rank p95 used for descriptive runtime reporting."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return ordered[index]


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a result atomically to avoid a plausible-looking partial run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def run(args: argparse.Namespace) -> None:
    """Execute exactly one frozen system over the authorized dataset."""
    dataset_path = Path(args.dataset).resolve()
    protocol, config, dataset = verify_frozen_inputs(dataset_path)
    system = args.system.upper()
    cache_dir = str(Path(args.cache_dir).resolve()) if args.cache_dir else None
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    failures = {"MODEL_OUTPUT_INVALID": 0, "MODEL_TIMEOUT": 0, "MODEL_SERVICE_FAILURE": 0}

    if system == "A":
        loaded = await load_system_a(config, cache_dir, args.offline)
        if args.preflight:
            print(json.dumps(runtime_provenance(system, config), indent=2))
            return
        await infer_a(loaded, WARMUP_TEXT)
    elif system == "B":
        loaded = load_system_b(config, cache_dir, args.offline)
        if args.preflight:
            print(json.dumps(runtime_provenance(system, config), indent=2))
            return
        infer_b(loaded, WARMUP_TEXT, config)
    else:
        loaded = load_system_c(config, cache_dir, args.offline)
        if args.preflight:
            print(json.dumps(runtime_provenance(system, config), indent=2))
            return
        infer_c(*loaded, WARMUP_TEXT, config)

    for narrative in dataset["narratives"]:
        narrative_id, text = narrative["narrative_id"], narrative["text"]
        retries = 0
        while True:
            started = perf_counter()
            try:
                if system == "A":
                    value = await infer_a(loaded, text)
                    row = {"narrative_id": narrative_id, "events": value}
                elif system == "B":
                    row = {"narrative_id": narrative_id, **infer_b(loaded, text, config)}
                else:
                    value = infer_c(*loaded, text, config)
                    row = {"narrative_id": narrative_id, "events": value}
                latency = (perf_counter() - started) * 1000
                row.update({"latency_ms": latency, "technical_retries": retries})
                rows.append(row)
                latencies.append(latency)
                break
            except (json.JSONDecodeError, ValueError) as exc:
                del exc
                failures["MODEL_OUTPUT_INVALID"] += 1
                empty = {"narrative_id": narrative_id, "failure": "MODEL_OUTPUT_INVALID", "technical_retries": retries}
                rows.append(empty)
                break
            except Exception as exc:  # technical failures follow the frozen single-retry rule
                failure = classify_failure(exc)
                if retries == 0:
                    retries = 1
                    continue
                failures[failure] += 1
                rows.append({"narrative_id": narrative_id, "failure": failure, "technical_retries": retries})
                break

    output = {
        "run_id": f"LIFEGRAPH_FINAL_{system}",
        "system": system,
        "protocol_sha256": digest(PROTOCOL_PATH),
        "dataset_sha256": digest(dataset_path),
        "execution_config_sha256": digest(CONFIG_PATH),
        "prompt_sha256": digest(PROMPT_PATH) if system == "C" else None,
        "runtime": runtime_provenance(system, config),
        "model_failures": failures,
        "latency": {
            "unit": "ms",
            "measured_narratives": len(latencies),
            "median": statistics.median(latencies) if latencies else None,
            "p95": percentile_95(latencies),
        },
        "narratives": rows,
    }
    atomic_write_json(Path(args.output), output)


def parse_args() -> argparse.Namespace:
    """Parse a deliberately narrow final-run command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True, choices=("A", "B", "C"))
    parser.add_argument("--dataset", default=str(HERE / "heldout_v1.json"))
    parser.add_argument("--output")
    parser.add_argument("--cache-dir")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if not args.preflight and not args.output:
        parser.error("--output is required unless --preflight is used")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
