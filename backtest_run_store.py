"""백테스트 Run 메타데이터와 일별 산출물을 DB에 저장한다.

전체 Resolved Config의 유일한 기준 Source는
`strategy_backtest_run.config_snapshot`이다.
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


def ensure_run_tables(conn) -> None:
    """Run·Trade Config 식별 컬럼과 필요한 인덱스를 생성 또는 보강한다."""
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
    """새 Run과 Config·Version·Artifact Identity를 함께 저장한다.

    기존 Local·단위 테스트 호출은 Artifact Identity를 생략할 수 있으며,
    이 경우 UNRESOLVED 상태로 저장한다. Candidate 실행은 Entrypoint의
    ``--require-artifact-identity`` Gate에서 COMPLETE Identity를 강제한다.
    """
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
                run_mode,
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
    """실제 소비한 입력 Snapshot Hash와 Manifest를 Run에 확정 저장한다."""
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
    """run_id와 date 기준으로 일별 수익률 Row를 Upsert한다."""
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
    """특정 일자의 보유 포지션 Snapshot을 Upsert한다."""
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
    """백테스트 종료 시 Run Row에 성과 지표와 종료 시각을 반영한다."""
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
