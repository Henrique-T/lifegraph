import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent


def test_execution_config_hash_and_non_sampling_semantics():
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    path = HERE / "execution_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == protocol["execution_config_sha256"]
    assert config["system_a"]["entity_confidence_threshold"] == 0.5
    assert config["system_a"]["stage_2_model_calls"] == 0
    assert config["system_b"]["aggregation_strategy"] == "simple"
    assert config["system_b"]["tokenizer"]["truncation"] is False
    assert config["system_c"]["decoding"] == "GREEDY"
    assert config["system_c"]["do_sample"] is False
    assert config["system_c"]["temperature"] == "NOT_APPLICABLE"
    assert config["quality_run_policy"]["semantic_quality_retries"] == 0
