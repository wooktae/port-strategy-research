"""Entrypoint for running the standard backtest Research Run.

The Resolved Config Snapshot is saved once per Run in `strategy_backtest_run.config_snapshot`.
The Trade Log references the same Snapshot via run_id, Strategy Config Version, and Config Hash.
"""

from __future__ import annotations

import argparse
from datetime import date
import warnings

import pandas as pd
import psycopg2

from port_strategy_common.config import (
    BACKTEST_START_DATE,
    DECISION_RUN_DATE,
)
from port_strategy_research.backtest_engine import run_backtest
from port_strategy_research.backtest_metrics import (
    calculate_mdd,
    calculate_sharpe,
)
from port_strategy_research.backtest_run_store import (
    complete_input_snapshot,
    create_run,
    ensure_run_tables,
    fail_run,
    finalize_run,
)
from port_strategy_research.db_config import get_db_config
from port_strategy_research.research_input_snapshot import (
    InputSnapshotBuilder,
)
from port_strategy_research.research_version_identity import (
    resolve_research_artifact_identity,
)
from port_strategy_research.strategy_profile_loader import (
    DEFAULT_STRATEGY_CONFIG_VERSION,
    load_strategy_config_snapshot,
)

warnings.filterwarnings("ignore", category=UserWarning)


def parse_args() -> argparse.Namespace:
    """Parses the Research Backtest execution arguments."""
    parser = argparse.ArgumentParser(
        description="Run the versioned Research backtest.",
    )
    parser.add_argument(
        "--run-mode",
        choices=("BACKTEST", "CANDIDATE"),
        default="BACKTEST",
        type=str.upper,
        help=(
            "Run 저장 영역. 기본값은 운영 호환을 위한 BACKTEST이며, "
            "AWS Batch Candidate는 CANDIDATE를 명시한다."
        ),
    )
    parser.add_argument(
        "--strategy-config-version",
        default=DEFAULT_STRATEGY_CONFIG_VERSION,
        help=(
            "실행할 Strategy Profile Version. "
            f"기본값: {DEFAULT_STRATEGY_CONFIG_VERSION}"
        ),
    )
    parser.add_argument(
        "--require-artifact-identity",
        action="store_true",
        help=(
            "Source SHA와 Image Digest가 모두 주입되지 않으면 "
            "실행을 차단한다. Candidate AWS Batch에서 사용한다."
        ),
    )
    parser.add_argument(
        "--backtest-start-date",
        default=str(BACKTEST_START_DATE),
        help=(
            "백테스트 시작일(YYYY-MM-DD). "
            f"기본값: {BACKTEST_START_DATE}"
        ),
    )
    parser.add_argument(
        "--backtest-end-date",
        default=None,
        help=(
            "백테스트 종료일(YYYY-MM-DD). "
            "생략하면 Loader의 최신 거래일까지 실행한다."
        ),
    )
    parser.add_argument(
        "--skip-extended-analysis",
        action="store_true",
        help=(
            "로컬 단기 통합검증에서 Extended Analysis를 생략한다. "
            "Backtest Run 저장과 Metrics 확정은 수행한다."
        ),
    )
    return parser.parse_args()



def _parse_iso_date(value: str, *, argument_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{argument_name}_INVALID={value}"
        ) from exc


def _resolve_backtest_date_range(
    args: argparse.Namespace,
) -> tuple[date, date | None]:
    start_date = _parse_iso_date(
        args.backtest_start_date,
        argument_name="BACKTEST_START_DATE",
    )
    end_date = (
        _parse_iso_date(
            args.backtest_end_date,
            argument_name="BACKTEST_END_DATE",
        )
        if args.backtest_end_date
        else None
    )

    if end_date is not None and end_date <= start_date:
        raise ValueError(
            "BACKTEST_DATE_RANGE_INVALID="
            f"{start_date.isoformat()}..{end_date.isoformat()}"
        )

    return start_date, end_date

def get_conn():
    """Creates an environment-variable-based AWS RDS PostgreSQL Connection."""
    return psycopg2.connect(**get_db_config())


def save_run_inputs(conn, run_id, inputs: dict):
    """Saves the Run input values to a separate input-history table."""
    with conn.cursor() as cur:
        for key, value in inputs.items():
            cur.execute(
                """
                INSERT INTO strategy_run_input
                    (run_id, input_key, input_value)
                VALUES (%s, %s, %s)
                """,
                (
                    run_id,
                    key,
                    str(value),
                ),
            )

    conn.commit()


def main() -> None:
    """Wires the Resolved Config Snapshot and execution Identity through the full path."""
    args = parse_args()
    selected_run_mode = args.run_mode
    selected_start_date, selected_end_date = (
        _resolve_backtest_date_range(args)
    )

    config_snapshot = load_strategy_config_snapshot(
        args.strategy_config_version
    )
    resolved_config = config_snapshot.resolved_config
    selected_version = config_snapshot.strategy_config_version
    artifact_identity = resolve_research_artifact_identity(
        require_complete=args.require_artifact_identity
    )

    print(f"RUN_MODE={selected_run_mode}")
    print(f"STRATEGY_CONFIG_VERSION={selected_version}")
    print(f"STRATEGY_PROFILE_PATH={config_snapshot.profile_path}")
    print(f"STRATEGY_CONFIG_HASH={config_snapshot.config_hash}")
    print(f"BACKTEST_START_DATE={selected_start_date}")
    print(
        "BACKTEST_END_DATE="
        f"{selected_end_date or 'LATEST_AVAILABLE'}"
    )
    print(
        "EXTENDED_ANALYSIS="
        f"{'SKIP' if args.skip_extended_analysis else 'RUN'}"
    )
    print(
        "RESEARCH_ARTIFACT_IDENTITY_STATUS="
        f"{artifact_identity.status}"
    )
    print(
        "RESEARCH_SOURCE_SHA="
        f"{artifact_identity.source_sha or 'UNRESOLVED'}"
    )
    print(
        "RESEARCH_IMAGE_DIGEST="
        f"{artifact_identity.image_digest or 'UNRESOLVED'}"
    )

    conn = get_conn()
    run_id: str | None = None

    try:
        ensure_run_tables(conn)

        run_id = create_run(
            conn,
            run_mode=selected_run_mode,
            config_snapshot=config_snapshot,
            artifact_identity=artifact_identity,
            run_note=(
                "versioned resolved config persistence; "
                f"run_mode={selected_run_mode}; "
                f"strategy_config_version={selected_version}; "
                f"config_hash={config_snapshot.config_hash}; "
                f"artifact_identity_status={artifact_identity.status}"
            ),
        )

        inputs = {
            "run_mode": selected_run_mode,
            "decision_run_date": DECISION_RUN_DATE,
            "backtest_start_date": selected_start_date,
            "backtest_end_date": (
                selected_end_date or "LATEST_AVAILABLE"
            ),
            "strategy_config_version": selected_version,
            "strategy_config_hash": config_snapshot.config_hash,
            "strategy_profile_path": str(config_snapshot.profile_path),
            "source_sha": artifact_identity.source_sha or "UNRESOLVED",
            "image_digest": (
                artifact_identity.image_digest or "UNRESOLVED"
            ),
            "artifact_identity_status": artifact_identity.status,
            "flow_min": str(resolved_config["filter"]["flow_min"]),
            "vol_penalty_multiplier": str(
                resolved_config["sizing"]["vol_penalty_multiplier"]
            ),
        }
        save_run_inputs(
            conn,
            run_id,
            inputs,
        )

        input_snapshot_builder = InputSnapshotBuilder()

        history = run_backtest(
            conn=conn,
            run_id=run_id,
            resolved_config=resolved_config,
            backtest_start_date=selected_start_date,
            backtest_end_date=selected_end_date,
            strategy_config_version=selected_version,
            config_hash=config_snapshot.config_hash,
            input_snapshot_builder=input_snapshot_builder,
        )

        input_evidence = input_snapshot_builder.finalize()
        complete_input_snapshot(
            conn,
            run_id,
            input_snapshot_hash=input_evidence.snapshot_hash,
            input_snapshot_manifest=input_evidence.manifest_json,
        )

        print(
            "INPUT_SNAPSHOT_HASH="
            f"{input_evidence.snapshot_hash}"
        )
        print(
            "INPUT_SNAPSHOT_DATASET_COUNT="
            f"{input_evidence.dataset_count}"
        )
        print(
            "INPUT_SNAPSHOT_ITEM_COUNT="
            f"{input_evidence.item_count}"
        )
        print(
            "INPUT_SNAPSHOT_SPECIAL_VALUE_COUNT="
            f"{input_evidence.special_value_count}"
        )

        df = pd.DataFrame(history)

        if df.empty:
            raise RuntimeError(
                "Backtest history is empty. Check engine/date loading."
            )

        print(f"\nRUN ID: {run_id}")
        print("\n===== RESULT =====")
        print(df.tail())

        metrics_config = resolved_config["metrics"]
        total_return = float(df.iloc[-1]["cum_return"])
        mdd = float(
            calculate_mdd(
                df,
                metrics_config=metrics_config,
            )
        )
        sharpe = float(
            calculate_sharpe(
                df,
                metrics_config=metrics_config,
            )
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM strategy_trade_log
                WHERE run_id = %s
                """,
                (run_id,),
            )
            trade_count = cur.fetchone()[0]

        finalize_run(
            conn,
            run_id,
            backtest_start_date=selected_start_date,
            backtest_end_date=str(df.iloc[-1]["date"]),
            total_return=total_return,
            mdd=mdd,
            sharpe=sharpe,
            trade_count=trade_count,
        )

        if args.skip_extended_analysis:
            print("EXTENDED_ANALYSIS_SKIPPED=LOCAL_RUNTIME_OPTION")
        else:
            from port_strategy_research.analysis_extended import (
                run_analysis_extended,
            )

            run_analysis_extended(
                conn,
                run_id,
            )

        print(f"\nTOTAL RETURN: {total_return}")
        print(f"\nMDD: {mdd:.4f}")
        print(f"Sharpe Ratio: {sharpe:.2f}")

    except Exception as exc:
        if run_id is not None:
            try:
                conn.rollback()
                fail_run(
                    conn,
                    run_id,
                    backtest_start_date=selected_start_date,
                    backtest_end_date=selected_end_date,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                print(f"RUN_FAILED_ID={run_id}")
                print(
                    "RUN_FAILED_ERROR_TYPE="
                    f"{type(exc).__name__}"
                )
            except Exception as failure_record_error:
                print(
                    "RUN_FAILURE_RECORD_ERROR="
                    f"{type(failure_record_error).__name__}:"
                    f"{failure_record_error}"
                )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
