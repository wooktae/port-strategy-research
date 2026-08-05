from pathlib import Path

repository = Path(r"C:\Workspaces\port_strategy_research")
entrypoint = repository / "backtest_research_run.py"
dockerfile = repository / "Dockerfile"

text = entrypoint.read_text(encoding="utf-8-sig")

if "--strategy-config-version" in text:
    raise RuntimeError("STRATEGY_CONFIG_CLI_ALREADY_PRESENT")

text = text.replace(
    "import warnings\nimport json\n",
    "import argparse\nimport warnings\nimport json\n",
    1,
)

loader_import = (
    "from port_strategy_research.strategy_profile_loader import (\n"
    "    DEFAULT_STRATEGY_CONFIG_VERSION,\n"
    "    load_strategy_profile,\n"
    ")\n"
)

anchor = "from port_strategy_research.db_config import get_db_config\n"

if anchor not in text:
    raise RuntimeError("DB_CONFIG_IMPORT_ANCHOR_NOT_FOUND")

text = text.replace(anchor, anchor + loader_import, 1)

marker = 'if __name__ == "__main__":'

if marker not in text:
    raise RuntimeError("MAIN_MARKER_NOT_FOUND")

prefix, body = text.split(marker, 1)
body_lines = body.lstrip("\r\n").splitlines()

if not body_lines or body_lines[0].strip() != "conn = get_conn()":
    raise RuntimeError("UNEXPECTED_MAIN_BODY_START")

nested_body = "\n".join(
    ("    " + line) if line else ""
    for line in body_lines
)

cli_block = r''
def parse_args():
    """Research Backtest 실행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Run the versioned Research backtest.",
    )
    parser.add_argument(
        "--strategy-config-version",
        default=DEFAULT_STRATEGY_CONFIG_VERSION,
        help=(
            "Strategy Profile Version. "
            f"Default: {DEFAULT_STRATEGY_CONFIG_VERSION}"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Profile을 먼저 선택한 뒤 기존 Backtest 실행 흐름을 시작한다."""
    args = parse_args()
    strategy_profile, strategy_profile_path = load_strategy_profile(
        args.strategy_config_version
    )

    print(
        "STRATEGY_CONFIG_VERSION="
        f"{strategy_profile['metadata']['strategy_config_version']}"
    )
    print(f"STRATEGY_PROFILE_PATH={strategy_profile_path}")

''

new_text = (
    prefix.rstrip()
    + "\n\n\n"
    + cli_block
    + nested_body
    + '\n\n\nif __name__ == "__main__":\n    main()\n'
)

entrypoint.write_text(new_text, encoding="utf-8")

docker_text = dockerfile.read_text(encoding="utf-8-sig")
source_copy = "COPY *.py ./port_strategy_research/"
profile_copy = "COPY strategy_profiles/ ./strategy_profiles/"

if source_copy not in docker_text:
    raise RuntimeError("DOCKER_SOURCE_COPY_ANCHOR_NOT_FOUND")

if profile_copy not in docker_text:
    docker_text = docker_text.replace(
        source_copy,
        source_copy + "\n" + profile_copy,
        1,
    )

dockerfile.write_text(docker_text, encoding="utf-8")

print(f"PATCHED_ENTRYPOINT={entrypoint}")
print(f"PATCHED_DOCKERFILE={dockerfile}")
print("STRATEGY_CONFIG_CLI_PATCH=SUCCESS")
