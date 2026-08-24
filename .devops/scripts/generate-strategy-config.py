from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


VERSION_RE = re.compile(r"^RSCFG-(\d{4})$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profiles-dir",
        default="strategy_profiles",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    profiles_dir = Path(args.profiles_dir)

    if not profiles_dir.is_dir():
        raise SystemExit(
            f"STRATEGY_PROFILES_DIR_NOT_FOUND={profiles_dir}"
        )

    versions: list[tuple[int, Path]] = []

    for path in profiles_dir.glob("RSCFG-*.json"):
        match = VERSION_RE.fullmatch(path.stem)

        if match is None:
            continue

        versions.append((int(match.group(1)), path))

    if not versions:
        raise SystemExit("STRATEGY_CONFIG_BASELINE_NOT_FOUND")

    versions.sort(key=lambda item: item[0])

    current_number, source_path = versions[-1]
    next_number = current_number + 1

    if next_number > 9999:
        raise SystemExit("STRATEGY_CONFIG_VERSION_EXHAUSTED")

    current_version = f"RSCFG-{current_number:04d}"
    next_version = f"RSCFG-{next_number:04d}"

    target_path = profiles_dir / f"{next_version}.json"

    if target_path.exists():
        raise SystemExit(
            f"STRATEGY_CONFIG_TARGET_ALREADY_EXISTS={target_path}"
        )

    with source_path.open(
        "r",
        encoding="utf-8-sig",
    ) as fp:
        profile = json.load(fp)

    metadata = profile.get("metadata")

    if not isinstance(metadata, dict):
        raise SystemExit("STRATEGY_CONFIG_METADATA_MISSING")

    actual_version = metadata.get(
        "strategy_config_version"
    )

    if actual_version != current_version:
        raise SystemExit(
            "STRATEGY_CONFIG_FILENAME_METADATA_MISMATCH="
            f"{current_version}:{actual_version}"
        )

    metadata["strategy_config_version"] = next_version
    metadata["status"] = "CANDIDATE"
    metadata["created_at"] = date.today().isoformat()

    with target_path.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as fp:
        json.dump(
            profile,
            fp,
            ensure_ascii=False,
            indent=2,
        )
        fp.write("\n")

    with target_path.open(
        "r",
        encoding="utf-8",
    ) as fp:
        verify = json.load(fp)

    verify_version = (
        verify
        .get("metadata", {})
        .get("strategy_config_version")
    )

    if verify_version != next_version:
        raise SystemExit(
            "STRATEGY_CONFIG_GENERATION_VERIFY_FAILED"
        )

    print(f"BASE_CONFIG_VERSION={current_version}")
    print(f"NEW_CONFIG_VERSION={next_version}")
    print(f"NEW_CONFIG_PATH={target_path.as_posix()}")
    print("STRATEGY_CONFIG_GENERATION=SUCCESS")


if __name__ == "__main__":
    main()