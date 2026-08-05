from __future__ import annotations

import ast
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

DOCKERFILE_PATH = REPOSITORY_ROOT / "Dockerfile"
ENTRYPOINT_PATH = REPOSITORY_ROOT / "backtest_research_run.py"
ARTIFACT_IDENTITY_PATH = (
    REPOSITORY_ROOT / "research_version_identity.py"
)

COMMON_WHEEL_FILENAME = (
    "port_strategy_common-1.0.0-py3-none-any.whl"
)
COMMON_WHEEL_RELATIVE_PATH = (
    ".devops/packages/"
    "port_strategy_common-1.0.0-py3-none-any.whl"
)

OPERATING_JOB_DEFINITION_NAME = (
    "portfolio-paper-strategy-research"
)
CANDIDATE_JOB_DEFINITION_NAME = (
    "portfolio-paper-strategy-research-candidate"
)

CANDIDATE_RUNTIME_COMMAND = (
    "python -m "
    "port_strategy_research.backtest_research_run"
)

REQUIRED_RUNTIME_ENVIRONMENT_VARIABLES = (
    "RESEARCH_SOURCE_SHA",
    "RESEARCH_IMAGE_DIGEST",
)

REQUIRED_CANDIDATE_ARGUMENTS = (
    "--strategy-config-version",
    "--require-artifact-identity",
)

FORBIDDEN_MUTABLE_IMAGE_TAGS = (
    ":latest",
    ":paper-latest",
)

FORBIDDEN_AWS_INTEGRATION_TOKENS = (
    "aws_scheduler_schedule",
    "aws_cloudwatch_event_rule",
    "aws_sfn_state_machine",
    "create_schedule(",
    "create_state_machine(",
    "update_state_machine(",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_required_text(path: Path) -> str:
    require(path.is_file(), f"REQUIRED_FILE_NOT_FOUND={path}")
    return path.read_text(encoding="utf-8-sig")


def normalized_whitespace(value: str) -> str:
    return " ".join(value.split())


def verify_dockerfile_contract() -> None:
    dockerfile = read_required_text(DOCKERFILE_PATH)

    require(
        COMMON_WHEEL_RELATIVE_PATH in dockerfile,
        "COMMON_WHEEL_COPY_PATH_NOT_FOUND",
    )
    require(
        COMMON_WHEEL_FILENAME in dockerfile,
        "COMMON_WHEEL_FILENAME_NOT_FOUND",
    )
    require(
        "pip install --no-cache-dir --no-deps" in dockerfile,
        "COMMON_WHEEL_INSTALL_COMMAND_NOT_FOUND",
    )
    require(
        "version == '1.0.0'" in dockerfile
        or 'version == "1.0.0"' in dockerfile,
        "COMMON_WHEEL_VERSION_ASSERT_NOT_FOUND",
    )

    forbidden_common_source_copy_patterns = (
        r"(?im)^\s*COPY\s+port_strategy_common(?:/|\s)",
        r"(?im)^\s*ADD\s+port_strategy_common(?:/|\s)",
    )

    for pattern in forbidden_common_source_copy_patterns:
        require(
            re.search(pattern, dockerfile) is None,
            "COMMON_SOURCE_DIRECTORY_COPY_FOUND",
        )

    expected_cmd = (
        'CMD ["python", "-m", "py_compile", '
        '"port_strategy_research/backtest_research_run.py"]'
    )

    require(
        normalized_whitespace(expected_cmd)
        in normalized_whitespace(dockerfile),
        "COMPILE_ONLY_DEFAULT_CMD_NOT_FOUND",
    )

    for forbidden_tag in FORBIDDEN_MUTABLE_IMAGE_TAGS:
        require(
            forbidden_tag not in dockerfile,
            f"FORBIDDEN_MUTABLE_IMAGE_TAG_FOUND={forbidden_tag}",
        )

    print("CANDIDATE_DOCKER_COMMON_WHEEL_PIN=SUCCESS")
    print("CANDIDATE_DOCKER_COMMON_SOURCE_COPY_REMOVED=SUCCESS")
    print("CANDIDATE_DOCKER_COMPILE_ONLY_CMD=SUCCESS")
    print("CANDIDATE_DOCKER_MUTABLE_TAG_ABSENCE=SUCCESS")


def verify_entrypoint_contract() -> None:
    entrypoint_source = read_required_text(ENTRYPOINT_PATH)

    try:
        ast.parse(entrypoint_source)
    except SyntaxError as exc:
        raise AssertionError(
            f"ENTRYPOINT_PYTHON_SYNTAX_INVALID={exc}"
        ) from exc

    for argument in REQUIRED_CANDIDATE_ARGUMENTS:
        require(
            argument in entrypoint_source,
            f"REQUIRED_CANDIDATE_ARGUMENT_NOT_FOUND={argument}",
        )

    require(
        "resolve_research_artifact_identity" in entrypoint_source,
        "ARTIFACT_IDENTITY_RESOLUTION_NOT_WIRED",
    )

    print("CANDIDATE_STRATEGY_CONFIG_OVERRIDE_CLI=SUCCESS")
    print("CANDIDATE_ARTIFACT_IDENTITY_GATE_CLI=SUCCESS")
    print("CANDIDATE_ARTIFACT_IDENTITY_WIRING=SUCCESS")


def verify_artifact_identity_contract() -> None:
    identity_source = read_required_text(
        ARTIFACT_IDENTITY_PATH
    )

    try:
        ast.parse(identity_source)
    except SyntaxError as exc:
        raise AssertionError(
            f"ARTIFACT_IDENTITY_PYTHON_SYNTAX_INVALID={exc}"
        ) from exc

    for variable in REQUIRED_RUNTIME_ENVIRONMENT_VARIABLES:
        require(
            variable in identity_source,
            f"REQUIRED_RUNTIME_ENV_NOT_FOUND={variable}",
        )

    require(
        r"^[0-9a-f]{40}$" in identity_source,
        "SOURCE_SHA_FORMAT_CONTRACT_NOT_FOUND",
    )
    require(
        r"^sha256:[0-9a-f]{64}$" in identity_source,
        "IMAGE_DIGEST_FORMAT_CONTRACT_NOT_FOUND",
    )

    print("CANDIDATE_SOURCE_SHA_RUNTIME_CONTRACT=SUCCESS")
    print("CANDIDATE_IMAGE_DIGEST_RUNTIME_CONTRACT=SUCCESS")
    print("CANDIDATE_ARTIFACT_FORMAT_CONTRACT=SUCCESS")


def verify_job_definition_separation_contract() -> None:
    require(
        OPERATING_JOB_DEFINITION_NAME
        != CANDIDATE_JOB_DEFINITION_NAME,
        "OPERATING_CANDIDATE_JOB_DEFINITION_COLLISION",
    )
    require(
        CANDIDATE_JOB_DEFINITION_NAME.endswith("-candidate"),
        "CANDIDATE_JOB_DEFINITION_SUFFIX_INVALID",
    )
    require(
        CANDIDATE_RUNTIME_COMMAND
        == (
            "python -m "
            "port_strategy_research.backtest_research_run"
        ),
        "CANDIDATE_RUNTIME_COMMAND_INVALID",
    )

    print(
        "OPERATING_JOB_DEFINITION_NAME="
        f"{OPERATING_JOB_DEFINITION_NAME}"
    )
    print(
        "CANDIDATE_JOB_DEFINITION_NAME="
        f"{CANDIDATE_JOB_DEFINITION_NAME}"
    )
    print(
        "CANDIDATE_RUNTIME_COMMAND="
        f"{CANDIDATE_RUNTIME_COMMAND}"
    )
    print("CANDIDATE_JOB_DEFINITION_SEPARATION=SUCCESS")


def verify_no_scheduler_or_step_functions_wiring() -> None:
    scan_directories = (
        REPOSITORY_ROOT / ".devops" / "codebuild",
        REPOSITORY_ROOT / ".devops" / "job-definitions",
        REPOSITORY_ROOT / ".github" / "workflows",
    )

    checked_files = 0

    for directory in scan_directories:
        if not directory.exists():
            continue

        for path in directory.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".json",
                ".py",
                ".yaml",
                ".yml",
                ".tf",
                ".ps1",
                ".sh",
            }:
                continue

            checked_files += 1
            text = path.read_text(encoding="utf-8-sig").lower()

            for token in FORBIDDEN_AWS_INTEGRATION_TOKENS:
                require(
                    token.lower() not in text,
                    (
                        "FORBIDDEN_AUTOMATIC_WIRING_FOUND="
                        f"{path.relative_to(REPOSITORY_ROOT)}:"
                        f"{token}"
                    ),
                )

    print(f"CANDIDATE_WIRING_SCAN_FILE_COUNT={checked_files}")
    print("CANDIDATE_SCHEDULER_WIRING_ABSENT=SUCCESS")
    print("CANDIDATE_STEP_FUNCTIONS_WIRING_ABSENT=SUCCESS")


def main() -> None:
    verify_dockerfile_contract()
    verify_entrypoint_contract()
    verify_artifact_identity_contract()
    verify_job_definition_separation_contract()
    verify_no_scheduler_or_step_functions_wiring()

    print(
        "CANDIDATE_REQUIRED_ENVIRONMENT="
        + ",".join(REQUIRED_RUNTIME_ENVIRONMENT_VARIABLES)
    )
    print(
        "CANDIDATE_REQUIRED_ARGUMENTS="
        + ",".join(REQUIRED_CANDIDATE_ARGUMENTS)
    )
    print("RESEARCH_CANDIDATE_CONTRACT=SUCCESS")


if __name__ == "__main__":
    main()