"""Saves backtest Run metadata and daily outputs to the DB.

The single source of truth for the full Resolved Config is
`strategy_backtest_run.config_snapshot`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from port_strategy_common.config import STRATEGY_NAME
from port_strategy_research.research_engine_version import (
    RESEARCH_ENGINE_VERSION,
)
from port_strategy_research.research_version_identity import (
    ResearchArtifactIdentity,
    resolve_metrics_config_identity,
)
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


ALLOWED_RUN_MODES = frozenset({
    "BACKTEST",
    "CANDIDATE",
})


def ensure_run_tables(conn) -> None:
    """Creates or augments the Run / Trade Config identity columns and required indexes."""
    ddl = """
    CREATE TABLE IF NOT EXISTS strategy_backtest_run (
        run_id UUID PRIMARY KEY,
        strategy_name VARCHAR(100) NOT NULL,
        strategy_version VARCHAR(100) NOT NULL,
        strategy_config_version VARCHAR(100),
        metrics_config_version VARCHAR(100),
        source_sha CHAR(40),
        image_digest VARCHAR(80),
        artifact_identity_status VARCHAR(20) NOT NULL DEFAULT 'UNRESOLVED',
        input_snapshot_hash CHAR(64),
        input_snapshot_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        input_snapshot_manifest JSONB,
        config_hash CHAR(64),
        strategy_profile_path TEXT,
        run_mode VARCHAR(30) NOT NULL,
        run_note TEXT,
        run_date DATE,
        started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        finished_at TIMESTAMPTZ,
        backtest_start_date DATE,
        backtest_end_date DATE,
        total_return NUMERIC(20,8),
        mdd NUMERIC(20,8),
        sharpe NUMERIC(20,8),
        trade_count INT,
        config_snapshot JSONB NOT NULL
    );

    ALTER TABLE strategy_backtest_run
        ADD COLUMN IF NOT EXISTS strategy_config_version VARCHAR(100),
        ADD COLUMN IF NOT EXISTS metrics_config_version VARCHAR(100),
        ADD COLUMN IF NOT EXISTS source_sha CHAR(40),
        ADD COLUMN IF NOT EXISTS image_digest VARCHAR(80),
        ADD COLUMN IF NOT EXISTS artifact_identity_status
            VARCHAR(20) NOT NULL DEFAULT 'UNRESOLVED',
        ADD COLUMN IF NOT EXISTS input_snapshot_hash CHAR(64),
        ADD COLUMN IF NOT EXISTS input_snapshot_status
            VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        ADD COLUMN IF NOT EXISTS input_snapshot_manifest JSONB,
        ADD COLUMN IF NOT EXISTS config_hash CHAR(64),
        ADD COLUMN IF NOT EXISTS strategy_profile_path TEXT;

    CREATE TABLE IF NOT EXISTS strategy_backtest_daily (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        run_id UUID NOT NULL
            REFERENCES strategy_backtest_run(run_id)
            ON DELETE CASCADE,
        date DATE NOT NULL,
        market_signal VARCHAR(30),
        position_count INT,
        daily_return NUMERIC(20,8),
        cum_return NUMERIC(20,8),
        UNIQUE(run_id, date)
    );

    ALTER TABLE strategy_trade_log
        ADD COLUMN IF NOT EXISTS run_id UUID,
        ADD COLUMN IF NOT EXISTS strategy_config_version VARCHAR(100),
        ADD COLUMN IF NOT EXISTS config_hash CHAR(64),
        ADD COLUMN IF NOT EXISTS config_snapshot JSONB;

    CREATE INDEX IF NOT EXISTS idx_strategy_trade_log_run_id
        ON strategy_trade_log(run_id);

    CREATE INDEX IF NOT EXISTS idx_strategy_trade_log_config_hash
        ON strategy_trade_log(config_hash);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_started_at
        ON strategy_backtest_run(started_at DESC);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_config_hash
        ON strategy_backtest_run(config_hash);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_metrics_config_version
        ON strategy_backtest_run(metrics_config_version);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_source_sha
        ON strategy_backtest_run(source_sha);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_image_digest
        ON strategy_backtest_run(image_digest);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_input_snapshot_hash
        ON strategy_backtest_run(input_snapshot_hash);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_daily_run_id_date
        ON strategy_backtest_daily(run_id, date);
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def create_run(
    conn,
    run_mode: str,
    config_snapshot: StrategyConfigSnapshot,
    artifact_identity: ResearchArtifactIdentity | None = None,
    run_note: str | None = None,
    run_date: str | None = None,
) -> str:
    """Saves a new Run together with its Config, Version, and Artifact Identity.

    Existing Local / unit-test calls may omit the Artifact Identity, in which case
    it is saved with UNRESOLVED status. Candidate execution enforces a COMPLETE Identity
    via the Entrypoint's ``--require-artifact-identity`` Gate.
    """
    normalized_run_mode = str(run_mode).strip().upper()
    if normalized_run_mode not in ALLOWED_RUN_MODES:
        raise ValueError(
            "RUN_MODE_INVALID="
            f"{run_mode}; allowed={sorted(ALLOWED_RUN_MODES)}"
        )

    run_id = str(uuid.uuid4())
    metrics_identity = resolve_metrics_config_identity(
        config_snapshot
    )
    effective_artifact_identity = artifact_identity
    if effective_artifact_identity is None:
        effective_artifact_identity = ResearchArtifactIdentity(
            source_sha=None,
            image_digest=None,
            status="UNRESOLVED",
        )

    sql = """
    INSERT INTO strategy_backtest_run (
        run_id,
        strategy_name,
        strategy_version,
        strategy_config_version,
        metrics_config_version,
        source_sha,
        image_digest,
        artifact_identity_status,
        config_hash,
        strategy_profile_path,
        run_mode,
        run_note,
        run_date,
        config_snapshot
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s::jsonb
    )
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                STRATEGY_NAME,
                RESEARCH_ENGINE_VERSION,
                config_snapshot.strategy_config_version,
                metrics_identity.version,
                effective_artifact_identity.source_sha,
                effective_artifact_identity.image_digest,
                effective_artifact_identity.status,
                config_snapshot.config_hash,
                str(config_snapshot.profile_path),
                normalized_run_mode,
                run_note,
                run_date,
                config_snapshot.canonical_json,
            ),
        )

    conn.commit()
    return run_id



def complete_input_snapshot(
    conn,
    run_id: str,
    *,
    input_snapshot_hash: str,
    input_snapshot_manifest: str,
) -> None:
    """Finalizes and saves the actually consumed input Snapshot Hash and Manifest to the Run."""
    if len(input_snapshot_hash) != 64:
        raise ValueError("INPUT_SNAPSHOT_HASH_INVALID")

    sql = """
    UPDATE strategy_backtest_run
    SET input_snapshot_hash = %s,
        input_snapshot_status = 'COMPLETE',
        input_snapshot_manifest = %s::jsonb
    WHERE run_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                input_snapshot_hash,
                input_snapshot_manifest,
                run_id,
            ),
        )
    conn.commit()

def insert_daily_result(
    conn,
    run_id: str,
    row: dict[str, Any],
) -> None:
    """Upserts the daily return Row keyed by run_id and date."""
    sql = """
    INSERT INTO strategy_backtest_daily (
        run_id,
        date,
        market_signal,
        position_count,
        daily_return,
        cum_return
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (run_id, date) DO UPDATE SET
        market_signal = EXCLUDED.market_signal,
        position_count = EXCLUDED.position_count,
        daily_return = EXCLUDED.daily_return,
        cum_return = EXCLUDED.cum_return
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                row["date"],
                row.get("market_signal"),
                row.get("position_count"),
                row.get("daily_return"),
                row.get("cum_return"),
            ),
        )


def insert_daily_positions(
    conn,
    run_id: str,
    date: str,
    positions: dict[str, dict[str, Any]],
    company_map: dict | None = None,
) -> None:
    """Upserts the held-position Snapshot for a specific date."""
    sql = """
    INSERT INTO strategy_backtest_daily_position (
        run_id,
        date,
        ticker_code,
        company_name,
        buy_date,
        holding_days,
        cum_return,
        position_size,
        entry_open_price,
        entry_close_price,
        entry_low_price,
        prev_close,
        entry_buy_info
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s::jsonb
    )
    ON CONFLICT (run_id, date, ticker_code) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        buy_date = EXCLUDED.buy_date,
        holding_days = EXCLUDED.holding_days,
        cum_return = EXCLUDED.cum_return,
        position_size = EXCLUDED.position_size,
        entry_open_price = EXCLUDED.entry_open_price,
        entry_close_price = EXCLUDED.entry_close_price,
        entry_low_price = EXCLUDED.entry_low_price,
        prev_close = EXCLUDED.prev_close,
        entry_buy_info = EXCLUDED.entry_buy_info
    """

    with conn.cursor() as cur:
        for ticker_code, position in positions.items():
            company_name = None
            if company_map:
                company_name = company_map.get(ticker_code)

            cur.execute(
                sql,
                (
                    run_id,
                    date,
                    ticker_code,
                    company_name,
                    position.get("buy_date"),
                    position.get("holding_days"),
                    position.get("cum_return"),
                    position.get("size"),
                    position.get("entry_open_price"),
                    position.get("entry_close_price"),
                    position.get("entry_low_price"),
                    position.get("prev_close"),
                    json.dumps(
                        position.get("entry_buy_info") or {},
                        ensure_ascii=False,
                    ),
                ),
            )


def fail_run(
    conn,
    run_id: str,
    *,
    backtest_start_date: str | None,
    backtest_end_date: str | None,
    error_type: str,
    error_message: str,
) -> None:
    """Records the finish time, execution range, and failure reason on a failed Run."""
    normalized_error_type = str(error_type).strip() or "Exception"
    normalized_error_message = (
        str(error_message).strip() or "UNKNOWN_ERROR"
    )
    failure_note = (
        "run_status=FAILED; "
        f"error_type={normalized_error_type}; "
        f"error_message={normalized_error_message}"
    )

    sql = """
    UPDATE strategy_backtest_run
    SET finished_at = now(),
        backtest_start_date = COALESCE(
            backtest_start_date,
            %s
        ),
        backtest_end_date = COALESCE(
            backtest_end_date,
            %s
        ),
        run_note = concat_ws(
            '; ',
            NULLIF(run_note, ''),
            %s
        )
    WHERE run_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                backtest_start_date,
                backtest_end_date,
                failure_note,
                run_id,
            ),
        )
    conn.commit()


def finalize_run(
    conn,
    run_id: str,
    *,
    backtest_start_date: str | None,
    backtest_end_date: str | None,
    total_return: float,
    mdd: float,
    sharpe: float,
    trade_count: int,
) -> None:
    """On backtest completion, records the performance metrics and finish time on the Run Row."""
    sql = """
    UPDATE strategy_backtest_run
    SET finished_at = now(),
        backtest_start_date = %s,
        backtest_end_date = %s,
        total_return = %s,
        mdd = %s,
        sharpe = %s,
        trade_count = %s
    WHERE run_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                backtest_start_date,
                backtest_end_date,
                total_return,
                mdd,
                sharpe,
                trade_count,
                run_id,
            ),
        )
    conn.commit()
