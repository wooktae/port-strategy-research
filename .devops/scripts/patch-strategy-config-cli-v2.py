from pathlib import Path

repository = Path(r"C:\Workspaces\port_strategy_research")
entrypoint = repository / "backtest_research_run.py"

text = entrypoint.read_text(encoding="utf-8-sig")

if "--strategy-config-version" in text:
    raise RuntimeError("STRATEGY_CONFIG_CLI_ALREADY_PRESENT")

old_imports = "import warnings\nimport json\n"
new_imports = "import argparse\nimport warnings\nimport json\n"

if old_imports not in text:
    raise RuntimeError("IMPORT_ANCHOR_NOT_FOUND")

text = text.replace(old_imports, new_imports, 1)

db_import = "from port_strategy_research.db_config import get_db_config\n"
loader_import = (
    "from port_strategy_research.strategy_profile_loader import (\n"
    "    DEFAULT_STRATEGY_CONFIG_VERSION,\n"
    "    load_strategy_profile,\n"
    ")\n"
)

if db_import not in text:
    raise RuntimeError("DB_IMPORT_ANCHOR_NOT_FOUND")

text = text.replace(db_import, db_import + loader_import, 1)

main_marker = 'if __name__ == "__main__":'

prefix, original_main = text.split(main_marker, 1)
original_lines = original_main.lstrip("\r\n").splitlines()

if not original_lines:
    raise RuntimeError("ORIGINAL_MAIN_BODY_EMPTY")

if original_lines[0].strip() != "conn = get_conn()":
    raise RuntimeError(
        f"UNEXPECTED_ORIGINAL_MAIN_START={original_lines[0]!r}"
    )

main_body = []
main_body.extend([
    "def parse_args():",
    "    parser = argparse.ArgumentParser(",
    "        description=\"Run the versioned Research backtest.\",",
    "    )",
    "    parser.add_argument(",
    "        \"--strategy-config-version\",",
    "        default=DEFAULT_STRATEGY_CONFIG_VERSION,",
    "        help=(",
    "            \"Strategy Profile Version. \"",
    "            f\"Default: {DEFAULT_STRATEGY_CONFIG_VERSION}\"",
    "        ),",
    "    )",
    "    return parser.parse_args()",
    "",
    "",
    "def main() -> None:",
    "    args = parse_args()",
    "    strategy_profile, strategy_profile_path = load_strategy_profile(",
    "        args.strategy_config_version",
    "    )",
    "",
    "    selected_version = strategy_profile[\"metadata\"][",
    "        \"strategy_config_version\"",
    "    ]",
    "    print(f\"STRATEGY_CONFIG_VERSION={selected_version}\")",
    "    print(f\"STRATEGY_PROFILE_PATH={strategy_profile_path}\")",
    "",
])

for line in original_lines:
    if line:
        main_body.append("    " + line)
    else:
        main_body.append("")

main_body.extend([
    "",
    "",
    'if __name__ == "__main__":',
    "    main()",
    "",
])

new_text = prefix.rstrip() + "\n\n\n" + "\n".join(main_body)
entrypoint.write_text(new_text, encoding="utf-8")

print(f"PATCHED_ENTRYPOINT={entrypoint}")
print("STRATEGY_CONFIG_CLI_PATCH_V2=SUCCESS")
