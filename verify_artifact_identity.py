"""Verifies the Research Source SHA / Image Digest Runtime Identity contract."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from unittest.mock import patch

from port_strategy_research import (
    backtest_research_run,
    backtest_run_store,
)
from port_strategy_research.research_version_identity import (
    RESEARCH_IMAGE_DIGEST_ENV,
    RESEARCH_SOURCE_SHA_ENV,
    ResearchArtifactIdentity,
    ResearchVersionIdentityError,
    resolve_research_artifact_identity,
)
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


SOURCE_SHA = "a" * 40
IMAGE_DIGEST = "sha256:" + ("b" * 64)


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None) -> None:
        self.calls.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def _snapshot() -> StrategyConfigSnapshot:
    return StrategyConfigSnapshot(
        strategy_config_version="RSCFG-0001",
        resolved_config={
            "metadata": {
                "strategy_config_version": "RSCFG-0001",
                "metrics_config_version": "RMETRICS-0001",
            },
        },
        canonical_json="{}",
        config_hash="0" * 64,
        profile_path=Path(
            "strategy_profiles/RSCFG-0001.json"
        ),
    )


def _expect_error(
    expected_marker: str,
    callback,
) -> None:
    try:
        callback()
    except ResearchVersionIdentityError as exc:
        assert expected_marker in str(exc), str(exc)
        return

    raise AssertionError(
        f"EXPECTED_RESEARCH_VERSION_IDENTITY_ERROR={expected_marker}"
    )


def main() -> None:
    with patch.dict(os.environ, {}, clear=True):
        unresolved = resolve_research_artifact_identity()

    assert unresolved == ResearchArtifactIdentity(
        source_sha=None,
        image_digest=None,
        status="UNRESOLVED",
    )

    print("ARTIFACT_IDENTITY_LOCAL_UNRESOLVED_ALLOWED=SUCCESS")

    with patch.dict(os.environ, {}, clear=True):
        _expect_error(
            "RESEARCH_ARTIFACT_IDENTITY_REQUIRED",
            lambda: resolve_research_artifact_identity(
                require_complete=True
            ),
        )

    print("ARTIFACT_IDENTITY_CANDIDATE_REQUIRED=SUCCESS")

    with patch.dict(
        os.environ,
        {
            RESEARCH_SOURCE_SHA_ENV: SOURCE_SHA,
            RESEARCH_IMAGE_DIGEST_ENV: IMAGE_DIGEST,
        },
        clear=True,
    ):
        complete = resolve_research_artifact_identity(
            require_complete=True
        )

    assert complete.source_sha == SOURCE_SHA
    assert complete.image_digest == IMAGE_DIGEST
    assert complete.status == "COMPLETE"
    assert complete.is_complete

    print("SOURCE_SHA_RUNTIME_ENV_SOURCE=SUCCESS")
    print("IMAGE_DIGEST_RUNTIME_ENV_SOURCE=SUCCESS")
    print("ARTIFACT_IDENTITY_COMPLETE_RESOLUTION=SUCCESS")

    with patch.dict(
        os.environ,
        {RESEARCH_SOURCE_SHA_ENV: SOURCE_SHA},
        clear=True,
    ):
        _expect_error(
            "RESEARCH_ARTIFACT_IDENTITY_PARTIAL",
            resolve_research_artifact_identity,
        )

    print("PARTIAL_ARTIFACT_IDENTITY_BLOCKED=SUCCESS")

    with patch.dict(
        os.environ,
        {
            RESEARCH_SOURCE_SHA_ENV: "invalid",
            RESEARCH_IMAGE_DIGEST_ENV: IMAGE_DIGEST,
        },
        clear=True,
    ):
        _expect_error(
            "RESEARCH_SOURCE_SHA_FORMAT_INVALID",
            resolve_research_artifact_identity,
        )

    with patch.dict(
        os.environ,
        {
            RESEARCH_SOURCE_SHA_ENV: SOURCE_SHA,
            RESEARCH_IMAGE_DIGEST_ENV: "sha256:invalid",
        },
        clear=True,
    ):
        _expect_error(
            "RESEARCH_IMAGE_DIGEST_FORMAT_INVALID",
            resolve_research_artifact_identity,
        )

    print("ARTIFACT_IDENTITY_FORMAT_VALIDATION=SUCCESS")

    conn = FakeConnection()
    run_id = backtest_run_store.create_run(
        conn,
        run_mode="BACKTEST",
        config_snapshot=_snapshot(),
        artifact_identity=complete,
    )

    assert run_id
    sql, params = conn.cursor_instance.calls[0]
    assert "source_sha" in sql
    assert "image_digest" in sql
    assert "artifact_identity_status" in sql
    assert params is not None
    assert SOURCE_SHA in params
    assert IMAGE_DIGEST in params
    assert "COMPLETE" in params

    print("RUN_SOURCE_SHA_PERSISTENCE=SUCCESS")
    print("RUN_IMAGE_DIGEST_PERSISTENCE=SUCCESS")
    print("RUN_ARTIFACT_IDENTITY_STATUS_PERSISTENCE=SUCCESS")

    ddl_source = inspect.getsource(
        backtest_run_store.ensure_run_tables
    )
    assert "ADD COLUMN IF NOT EXISTS source_sha" in ddl_source
    assert "ADD COLUMN IF NOT EXISTS image_digest" in ddl_source
    assert (
        "ADD COLUMN IF NOT EXISTS artifact_identity_status"
        in ddl_source
    )

    cli_source = inspect.getsource(
        backtest_research_run.parse_args
    )
    assert "--require-artifact-identity" in cli_source

    print("RUN_ARTIFACT_IDENTITY_DDL=SUCCESS")
    print("CANDIDATE_ARTIFACT_IDENTITY_CLI_GATE=SUCCESS")
    print(
        "SOURCE_SHA_CANONICAL_RUNTIME_SOURCE="
        "RESEARCH_SOURCE_SHA"
    )
    print(
        "IMAGE_DIGEST_CANONICAL_RUNTIME_SOURCE="
        "RESEARCH_IMAGE_DIGEST"
    )
    print("RESEARCH_ARTIFACT_IDENTITY_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
