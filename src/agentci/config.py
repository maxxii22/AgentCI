"""Minimal config loading for the AgentCI Day 3-5 refocus.

Why this file exists:
It keeps config parsing separate from the CLI and avoids a YAML dependency
until the config format becomes complex enough to justify one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when the repo config is missing or malformed."""


@dataclass(slots=True)
class AdapterConfig:
    type: str
    command: str


@dataclass(slots=True)
class TestsConfig:
    glob: str


@dataclass(slots=True)
class AgentCIConfig:
    version: int
    adapter: AdapterConfig
    tests: TestsConfig
    output_dir: Path
    config_path: Path
    root_dir: Path


def load_config(path: str | Path = "agentci.yaml") -> AgentCIConfig:
    """Load the narrow config format used by the Day 3-5 refocus."""

    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    raw = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))

    try:
        version = int(raw["version"])
        adapter_raw = raw["adapter"]
        tests_raw = raw["tests"]
        output_dir = raw["output_dir"]
    except KeyError as error:
        raise ConfigError(f"Missing required config key: {error}") from error

    if version != 1:
        raise ConfigError(f"Unsupported config version: {version}")

    if not isinstance(adapter_raw, dict):
        raise ConfigError("`adapter` must be a mapping.")
    if not isinstance(tests_raw, dict):
        raise ConfigError("`tests` must be a mapping.")

    adapter = AdapterConfig(
        type=str(adapter_raw.get("type", "")).strip(),
        command=str(adapter_raw.get("command", "")).strip(),
    )
    tests = TestsConfig(glob=str(tests_raw.get("glob", "")).strip())

    if adapter.type != "command":
        raise ConfigError("Only `adapter.type: command` is supported in this scaffold.")
    if not adapter.command:
        raise ConfigError("`adapter.command` is required.")
    if not tests.glob:
        raise ConfigError("`tests.glob` is required.")
    if not str(output_dir).strip():
        raise ConfigError("`output_dir` is required.")

    root_dir = config_path.parent
    resolved_output_dir = (root_dir / str(output_dir)).resolve()

    return AgentCIConfig(
        version=version,
        adapter=adapter,
        tests=tests,
        output_dir=resolved_output_dir,
        config_path=config_path,
        root_dir=root_dir,
    )


def _parse_simple_yaml(text: str) -> dict[str, object]:
    """Parse the tiny subset of YAML needed by the current config.

    TODO:
    Replace this with a real YAML parser if config complexity grows.
    """

    data: dict[str, object] = {}
    current_section: dict[str, object] | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            key, value = _split_mapping_line(line)
            if value == "":
                section: dict[str, object] = {}
                data[key] = section
                current_section = section
            else:
                data[key] = _parse_scalar(value)
                current_section = None
            continue

        if indent != 2 or current_section is None:
            raise ConfigError(f"Unsupported YAML structure: {raw_line}")

        key, value = _split_mapping_line(line)
        current_section[key] = _parse_scalar(value)

    return data


def _split_mapping_line(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ConfigError(f"Invalid config line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> object:
    if not value:
        return ""
    if value.isdigit():
        return int(value)
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    return value
