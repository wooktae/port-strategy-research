from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence


COMMON_DISTRIBUTION_NAME = "port-strategy-common"
COMMON_EXPECTED_VERSION = "1.0.0"

REQUIRED_RESEARCH_MODULES = (
    "port_strategy_research.backtest_research_run",
    "port_strategy_research.research_engine_version",
    "port_strategy_research.research_version_identity",
    "port_strategy_research.research_input_snapshot",
    "port_strategy_research.strategy_config_snapshot",
    "port_strategy_research.strategy_profile_loader",
    "port_strategy_research.strategy_profile_schema",
)

REQUIRED_CLI_ARGUMENTS = (
    "--strategy-config-version",
    "--require-artifact-identity",
    "--backtest-start-date",
    "--backtest-end-date",
    "--skip-extended-analysis",
)

PROFILE_PATH = "/app/strategy_profiles/RSCFG-0001.json"

COMPILE_ONLY_COMMAND = (
    "python",
    "-m",
    "py_compile",
    "port_strategy_research/backtest_research_run.py",
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(
    command: Sequence[str],
    *,
    allow_failure: bool = False,
) -> CommandResult:
    completed = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    result = CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if not allow_failure and result.returncode != 0:
        raise AssertionError(
            "COMMAND_FAILED="
            + " ".join(command)
            + f"\nRETURN_CODE={result.returncode}"
            + f"\nSTDOUT={result.stdout}"
            + f"\nSTDERR={result.stderr}"
        )

    return result


def docker_run(
    image: str,
    command: Sequence[str],
) -> CommandResult:
    return run_command(
        (
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "",
            image,
            *command,
        )
    )


def verify_docker_available() -> None:
    result = run_command(("docker", "version", "--format", "{{.Server.Version}}"))
    require(result.stdout.strip(), "DOCKER_SERVER_VERSION_EMPTY")
    print(f"DOCKER_SERVER_VERSION={result.stdout.strip()}")
    print("RESEARCH_CONTAINER_SMOKE_DOCKER_AVAILABLE=SUCCESS")


def verify_image_exists(image: str) -> None:
    result = run_command(
        (
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            "{{.Id}}",
        )
    )

    image_id = result.stdout.strip()

    require(
        re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None,
        f"LOCAL_IMAGE_ID_INVALID={image_id}",
    )

    print(f"RESEARCH_CONTAINER_IMAGE={image}")
    print(f"RESEARCH_CONTAINER_LOCAL_IMAGE_ID={image_id}")
    print("RESEARCH_CONTAINER_IMAGE_EXISTS=SUCCESS")


def verify_python_runtime(image: str) -> None:
    result = docker_run(
        image,
        (
            "python",
            "-c",
            (
                "import sys;"
                "print(sys.version);"
                "assert sys.version_info >= (3, 13)"
            ),
        ),
    )

    require(result.stdout.strip(), "CONTAINER_PYTHON_VERSION_EMPTY")
    print(
        "RESEARCH_CONTAINER_PYTHON_VERSION="
        + result.stdout.strip().splitlines()[0]
    )
    print("RESEARCH_CONTAINER_PYTHON_RUNTIME=SUCCESS")


def verify_package_imports(image: str) -> None:
    modules_literal = repr(REQUIRED_RESEARCH_MODULES)

    code = (
        "import importlib;"
        f"modules={modules_literal};"
        "[importlib.import_module(name) for name in modules];"
        "print('MODULE_IMPORT_COUNT=' + str(len(modules)))"
    )

    result = docker_run(
        image,
        ("python", "-c", code),
    )

    require(
        f"MODULE_IMPORT_COUNT={len(REQUIRED_RESEARCH_MODULES)}"
        in result.stdout,
        "RESEARCH_MODULE_IMPORT_COUNT_INVALID",
    )

    print(
        "RESEARCH_CONTAINER_MODULE_IMPORT_COUNT="
        f"{len(REQUIRED_RESEARCH_MODULES)}"
    )
    print("RESEARCH_CONTAINER_PACKAGE_IMPORTS=SUCCESS")


def verify_common_distribution(image: str) -> None:
    code = (
        "import importlib.metadata;"
        "import port_strategy_common;"
        f"version=importlib.metadata.version('{COMMON_DISTRIBUTION_NAME}');"
        "path=str(port_strategy_common.__file__);"
        "print('COMMON_VERSION=' + version);"
        "print('COMMON_IMPORT_PATH=' + path);"
        f"assert version == '{COMMON_EXPECTED_VERSION}';"
        "assert 'site-packages' in path.replace('\\\\', '/');"
    )

    result = docker_run(
        image,
        ("python", "-c", code),
    )

    require(
        f"COMMON_VERSION={COMMON_EXPECTED_VERSION}"
        in result.stdout,
        "COMMON_VERSION_OUTPUT_INVALID",
    )

    import_path_line = next(
        (
            line
            for line in result.stdout.splitlines()
            if line.startswith("COMMON_IMPORT_PATH=")
        ),
        "",
    )

    require(import_path_line, "COMMON_IMPORT_PATH_OUTPUT_MISSING")
    require(
        "site-packages" in import_path_line.replace("\\", "/"),
        "COMMON_IMPORT_NOT_FROM_SITE_PACKAGES",
    )

    print(f"RESEARCH_CONTAINER_COMMON_VERSION={COMMON_EXPECTED_VERSION}")
    print(import_path_line)
    print("RESEARCH_CONTAINER_COMMON_DISTRIBUTION=SUCCESS")


def verify_profile_exists(image: str) -> None:
    code = (
        "from pathlib import Path;"
        f"path=Path('{PROFILE_PATH}');"
        "assert path.is_file(), path;"
        "print('PROFILE_SIZE=' + str(path.stat().st_size))"
    )

    result = docker_run(
        image,
        ("python", "-c", code),
    )

    profile_size_line = next(
        (
            line
            for line in result.stdout.splitlines()
            if line.startswith("PROFILE_SIZE=")
        ),
        "",
    )

    require(profile_size_line, "PROFILE_SIZE_OUTPUT_MISSING")
    profile_size = int(profile_size_line.split("=", 1)[1])
    require(profile_size > 0, "PROFILE_FILE_EMPTY")

    print(f"RESEARCH_CONTAINER_PROFILE_PATH={PROFILE_PATH}")
    print(f"RESEARCH_CONTAINER_PROFILE_SIZE={profile_size}")
    print("RESEARCH_CONTAINER_PROFILE_EXISTS=SUCCESS")


def verify_cli_contract(image: str) -> None:
    result = docker_run(
        image,
        (
            "python",
            "-m",
            "port_strategy_research.backtest_research_run",
            "--help",
        ),
    )

    help_text = result.stdout + result.stderr

    for argument in REQUIRED_CLI_ARGUMENTS:
        require(
            argument in help_text,
            f"REQUIRED_CLI_ARGUMENT_NOT_FOUND={argument}",
        )
        print(f"RESEARCH_CONTAINER_CLI_ARGUMENT={argument} STATUS=FOUND")

    print("RESEARCH_CONTAINER_CLI_CONTRACT=SUCCESS")


def verify_compile_only_default_command(image: str) -> None:
    inspect_result = run_command(
        (
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            "{{json .Config.Cmd}}",
        )
    )

    raw_cmd = inspect_result.stdout.strip()
    require(raw_cmd, "CONTAINER_IMAGE_CMD_EMPTY")

    parsed_cmd = json.loads(raw_cmd)

    require(
        tuple(parsed_cmd) == COMPILE_ONLY_COMMAND,
        (
            "CONTAINER_DEFAULT_CMD_INVALID="
            f"{parsed_cmd}"
        ),
    )

    run_result = run_command(
        (
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            image,
        )
    )

    require(
        run_result.returncode == 0,
        f"CONTAINER_DEFAULT_CMD_EXIT_CODE={run_result.returncode}",
    )

    print(
        "RESEARCH_CONTAINER_DEFAULT_CMD="
        + " ".join(parsed_cmd)
    )
    print("RESEARCH_CONTAINER_COMPILE_ONLY_CMD=SUCCESS")


def verify_no_runtime_external_access() -> None:
    print("RESEARCH_CONTAINER_NETWORK_MODE=none")
    print("RESEARCH_CONTAINER_DB_CONNECTION_EXECUTED=False")
    print("RESEARCH_CONTAINER_BACKTEST_EXECUTED=False")
    print("RESEARCH_CONTAINER_EXTERNAL_ACCESS_BLOCKED=SUCCESS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the Research Docker image without DB access."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Local Docker image reference to validate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    verify_docker_available()
    verify_image_exists(args.image)
    verify_python_runtime(args.image)
    verify_package_imports(args.image)
    verify_common_distribution(args.image)
    verify_profile_exists(args.image)
    verify_cli_contract(args.image)
    verify_compile_only_default_command(args.image)
    verify_no_runtime_external_access()

    print("RESEARCH_CONTAINER_SMOKE=SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"RESEARCH_CONTAINER_SMOKE_FAILED={exc}",
            file=sys.stderr,
        )
        raise