# port_strategy_research

`port_strategy_research` is a Research microservice that reads preprocessing features together with price and universe data, runs portfolio backtests, and analyzes the stored results to generate text reports.

Research is currently not a single fixed-Config backtest runner but a `Versioned Backtest Platform` that selects and injects a per-Version Strategy Profile into a fixed Common decision Engine.
Common provides the decision functions and the base contract, and Research selects a per-Version `Strategy Profile` and injects it explicitly into the entire Backtest Run.

Research uses the market, filter, sizing, guard, and sell contracts of `port_strategy_common` directly through internal adapters.
It does not import `port_strategy_decision` at runtime; the two services are separate consumers of the same Common contract.

Research results remain research and validation artifacts.
Daily Signal, Execution Plan, and actual orders are not Research responsibilities.
Deploying the Research execution Artifact and promoting Strategy operational performance are separate procedures.

This document is written based on the current repository's file structure, imports, entrypoints, and actual source.
No actual Backtest, Analysis, Report, DB write, AWS, S3, or order execution was performed during documentation cleanup.

## 1. Service Summary

| Item | Value |
|---|---|
| Service | `port_strategy_research` |
| Layer | Research |
| Nature | Versioned Backtest Platform |
| Common logic | `port_strategy_common` Wheel `1.0.0`, pinned install |
| Strategy configuration | Per-Version Strategy Profile (`strategy_profiles/`) |
| Default Baseline | `RSCFG-0001` (`status=BASELINE`) |
| Challenger | `RSCFG-0002` (`status=CANDIDATE`) |
| Core execution | Backtest Research |
| Run Mode | `BACKTEST`, `CANDIDATE` |
| Primary persistence | Run, Daily, Daily Position, Trade Log, and Analysis |
| Operational entrypoints | `backtest_research_run.py`, `backtest_report_run.py` |
| AWS location | Paper Daily Step 4, Step 5 |
| Detailed file document | `docs/source-file-catalog.md` |

## 2. Responsibility Boundary

Research simulates past periods and analyzes and presents those results.
External data collection, Daily operational decisions, and actual orders are the responsibility of other layers.

### 2.1 Scope Research Owns

| Area | Responsibility |
|---|---|
| Strategy Profile | Per-Version Config selection and Resolved Config injection |
| Backtest | Trading-day-level portfolio simulation |
| Market | Calls the Common Market decision through a Research adapter |
| Buy Filter | Calls the Common Buy Candidate Filter |
| Sizing | Computes per-candidate Position Allocation |
| Buy·Sell | Applies Guard, Haircut, and the Common Sell decision |
| Position | Holding, liquidation, and next-trading-day carry-over |
| Persistence | Stores Run, Daily, Daily Position, Trade Log, and Config·Identity |
| Analysis | Generates or updates Basic·Extended Analysis |
| Report | Generates Summary, Buy·Sell, Trade Detail, and Recommendation |
| Research candidates | Studies Block Watch and Exception Buy scenarios |

### 2.2 Scope Other Layers Own

| Area | Owning Layer |
|---|---|
| External data collection | Crawler |
| Raw preprocessing and Total Feature generation | Preprocessor |
| Daily BUY and HOLD·SELL·SKIP decisions | StrategyDecision |
| Execution Plan and order request composition | StrategyExecution |
| Broker order·fill·balance·holding synchronization | MarketConnector |
| Status query and approval UI | View |
| Full Batch orchestration | Scheduler and Step Functions |
| Image build, ECR push, and infrastructure registration | Deployment pipeline |

Research results are research and validation artifacts.
They are not expressed as a Daily Signal, an Execution Plan, or an actual order.

## 3. Versioned Backtest Platform

Research injects a per-Version Strategy Profile into a fixed Common decision Engine.
The strategy configuration is finalized as a Resolved Config that merges the Common Default with the Profile Override.

### 3.1 Config Data Flow

```text
Strategy Profile (RSCFG-0001.json)
  → Load       Load the profile JSON
  → Resolve    Merge Common Default + Profile Override
  → Validate   Validate schema, allowed Category·Key, Type, and Metadata
  → Hash       Generate Canonical JSON and SHA-256 Config Hash
  → Inject     Explicitly inject the Resolved Config into the Engine and Adapters
  → Persist    Store Config Snapshot·Hash·Version Identity on the Run
```

| Stage | File |
|---|---|
| Load·Resolve·Snapshot | `strategy_profile_loader.py` |
| Schema·merge validation | `strategy_profile_schema.py` |
| Canonical JSON·Hash | `strategy_config_snapshot.py` |
| Version Identity | `research_version_identity.py` |
| Engine injection | `backtest_engine.py` |
| Run·Config store | `backtest_run_store.py` |

### 3.2 Common Wheel Consumption Structure

| Item | Current Structure |
|---|---|
| Common inclusion method | Wheel Package install, not a Common Source Directory copy |
| Install target | `port_strategy_common-1.0.0-py3-none-any.whl` |
| Runtime Version Source | The actually installed Distribution Metadata Version |
| Package Version validation | Block execution if the Profile-declared Version differs from the installed Version |
| Strategy Version validation | Block execution if the Runtime value differs from the Profile-declared value |
| Consumer relationship | Decision and Research consume the same Common Package contract |

Do not confuse the responsibilities of the Common Package and the Research Source.
Common provides the decision contract, and Research handles per-Version Profile selection and injection.

### 3.3 Strategy Profile

`strategy_profiles/` manages per-Version Strategy Profiles.
`strategy_config_version` is the Profile Identity, and each Version is a separate Strategy Config Identity.

| Version | Nature |
|---|---|
| `RSCFG-0001` | Baseline Strategy Profile (`status=BASELINE`) |
| `RSCFG-0002` | Challenger Strategy Profile (`status=CANDIDATE`) |

`RSCFG-0002` is a Challenger split into a new Version rather than overwriting `RSCFG-0001`.
The only value difference between the two Profiles is `market.aggressive_max_positions`, which is `4` for `RSCFG-0001` and `6` for `RSCFG-0002`.
The remaining Category values are identical.

| Config Category | Nature |
|---|---|
| `metadata` | Profile·Version Metadata |
| `market` | Market Regime and Exposure criteria |
| `filter` | Buy Filter criteria |
| `sizing` | Position Sizing criteria |
| `buy_guard` | Buy Guard and Haircut criteria |
| `buy` | Buy execution-related values |
| `sell` | Sell decision criteria |
| `backtest_policy` | Re-entry, Return Floor, and Risk-off policy |
| `metrics` | Risk-free Rate and annual trading days |

Profile validation contract:

| Item | Criterion |
|---|---|
| Filename·Version | The Profile filename matches the declared `strategy_config_version` |
| Metadata | Validate that required Metadata Keys exist and have non-empty values |
| Category | Allow only permitted Categories and permitted Keys |
| Unknown Key | Block Unknown Keys in a Category or in Metadata |
| Type·missing | Block Type errors and missing Resolved Config Keys |
| Merge | Merge Common Default and Profile Override into a complete Config |
| Nonexistent Version | Block before the DB connection and Run creation |

The Profile Status and the operational Promotion state are not the same thing.
`status=CANDIDATE` for `RSCFG-0002` does not imply an operational Champion designation or automatic Promotion.
`status=BASELINE` for `RSCFG-0001` likewise does not mean the same thing as the operational Champion state.

### 3.4 Config Selection CLI and Explicit Injection

`backtest_research_run.py` selects the Profile and injects the Resolved Config explicitly into the entire execution path.

| CLI Option | Role |
|---|---|
| `--strategy-config-version` | Strategy Profile Version to run, default `RSCFG-0001` |
| `--run-mode` | `BACKTEST` or `CANDIDATE`, default `BACKTEST` |
| `--require-artifact-identity` | Block execution if Source SHA·Image Digest are not injected |
| `--backtest-start-date` | Backtest start date |
| `--backtest-end-date` | Backtest end date; the latest trading day if omitted |
| `--skip-extended-analysis` | Skip Extended Analysis in local short validation |

Injection contract:

- Load the selected Profile and generate a Resolved Config.
- Pass the actual Config into the Market, Filter, Sizing, Buy Guard, Buy Haircut, and Sell flows.
- The Engine and Adapters do not depend on Module Global Config or hidden defaults.
- The BUY Guard passes the actual Resolved `buy_guard` Config instead of the previous `config={}` wiring.

### 3.5 Version Identity

Each Run stores the following Version Identities separately to ensure reproducibility.

| Identity | Basis |
|---|---|
| Common Package Version | Installed `port-strategy-common` Distribution Version |
| Common Strategy Version | Strategy Version constant provided by the installed Common Wheel |
| Research Engine Version | Research repository constant (`research_engine_version.py`) |
| Strategy Config Version | The running Profile's `RSCFG-` Version |
| Metrics Config Version | The `RMETRICS-` Version in the Resolved Config Metadata |
| Run Identity | Run ID |
| Source SHA | Deployment Source environment variable |
| Image Digest | Deployment Image environment variable |

Distinctions:

- Strategy Config Version and Research Engine Version are not the same value.
- Common Package Version and Common Strategy Version are also different values.
- Metrics Config Version is recorded separately from the Strategy Config Identity.
- Source SHA and Image Digest are different identifiers.

### 3.6 Config Snapshot·Hash and Input Snapshot

Config Identity and Input Data Identity are different concepts.

| Item | Config Snapshot·Hash | Input Snapshot |
|---|---|---|
| Target | The Resolved Config used for execution | The input data actually consumed |
| Canonical | Config Canonical JSON | Input Canonical JSON |
| Hash | SHA-256 Config Hash | SHA-256 Input Snapshot Hash |
| Run store | `config_snapshot`, `config_hash` | `input_snapshot_hash`, `input_snapshot_manifest` |
| Volatility | The same Profile yields the same Config Hash | The Hash may change when source data is updated |

Config Snapshot flow:

- Generate the full Resolved Config that merges the Common Default with the Profile Override.
- Generate Canonical JSON and a SHA-256 Config Hash.
- Store the Strategy Config Version, Config Snapshot, and Flatten Config KV (`strategy_run_input`) on the Run.
- The Trade Log references the same Snapshot by Run ID and Config Identity (Version·Hash).
- The actual execution Config, not a Global Common Config Snapshot, is the Canonical Source.
- Secrets are not included in the Config Snapshot or the Hash input.

Input Snapshot flow:

- Store the execution input range and Manifest.
- Store the Input Snapshot Hash and Snapshot Status.
- Link the execution period with the input Data Identity.
- Even for the same period, the Input Snapshot Hash may differ if source data is updated.

### 3.7 Run Mode and Candidate

Research execution distinguishes the `BACKTEST` and `CANDIDATE` Run Modes.

| Item | Criterion |
|---|---|
| Operational Run | `BACKTEST` Run Mode |
| Candidate Run | `CANDIDATE` Run Mode |
| Query separation | Distinguish operational Run from Candidate Run by Run Mode and Identity |
| Scheduler linkage | Do not automatically connect Candidate execution to the operational Scheduler |
| Automatic Promotion | Candidate is not automatically promoted |
| Failure storage | A failed Candidate Run also stores the failure status and Artifact Identity |
| RDS sharing | The same RDS may be used, but the two are distinguished by Run Mode and Identity |

A Candidate is a validation path for the deployment Artifact and execution contract, not an automatic approver of strategy performance.
A Candidate is executed with `--run-mode CANDIDATE` and the selected `--strategy-config-version`.
A Candidate Run is stored in `strategy_backtest_run` together with its Run Mode·Version Identity.
Candidate success means Challenger validation is complete; it does not mean automatic Champion Promotion.

The `RSCFG-0002` Challenger was executed and validated through the Candidate path, and its Candidate Run is stored in the DB.
`RSCFG-0001` and `RSCFG-0002` can each be queried as per-Version Research results.

Champion–Challenger responsibilities are separated as follows.

| Actor | Responsibility |
|---|---|
| DevOps automation | Up to Candidate generation·execution·validation (Challenger confirmation) |
| Research owner | Comparing multiple Challenger results and deciding Champion selection |
| View | The Interface for Version query and Champion·Challenger comparison·selection |

View does not automatically judge which strategy is superior.
The actor that decides Champion selection is the Research owner, and View is the Interface that carries out that decision.
Implementing the actual View operational Promotion feature is out of scope for this document work.

### 3.8 Artifact Identity

| Item | Criterion |
|---|---|
| Source SHA | Validated as a 40-character hex format |
| Image Digest | Validated as `sha256:` plus a 64-character hex format |
| Artifact Identity Status | Block `UNRESOLVED`, `COMPLETE`, or a format error |
| Digest pinning | Both operational and Candidate use a Digest-based pinned Image |
| Required validation | `--require-artifact-identity` enforces a complete Identity |
| Structure sharing | Both Candidate and operational Runs use the same Artifact Identity structure |

Distinguish an incomplete deployment Artifact Identity (`UNRESOLVED`) from a complete one (`COMPLETE`).

### 3.9 Reproducibility Validation Criteria

On re-running the same Version, validate the following with a clear distinction.

| Target | Criterion |
|---|---|
| Config and Artifact Identity | Exact match |
| Backtest results and Trade Log | Exact match |
| Input Snapshot Manifest | Match |
| Input Snapshot Hash | May change due to source data updates |
| Excluded from comparison | Run ID and creation·start·end timestamps |
| Numeric tolerance | `0.000000000001` |

The case where the Manifest and results are identical and the Hash difference is explained by source data updates is accepted as an exception.

## 4. End-to-End Execution Flow

```text
Strategy Profile + Common Wheel + Preprocessor Feature + Price + Universe
  → Backtest Research
  → Run · Daily · Daily Position · Trade Log · Config·Input Snapshot
  → Basic / Extended Analysis
  → Summary / Buy·Sell / Trade Detail / Recommendation Report
  → Optional S3 upload
```

| Stage | Primary Entrypoint |
|---|---|
| Backtest | `backtest_research_run.py` |
| Basic Analysis | `backtest_analysis_basic.py` |
| Extended Analysis | `run_extended_analysis.py` |
| Report | `backtest_report_run.py` |
| AWS Batch Report | `aws_batch_backtest_report_wrapper.py` |

## 5. Backtest Research

### 5.1 Execution Flow

```text
Profile Load · Resolve · Hash · Artifact Identity
  → Create Run and store Config·Version Identity
  → Query trading day·Feature·price·Universe and collect Input Snapshot
  → Market Decision
  → Process existing Positions
  → Buy Candidate Filter
  → Guard and Sizing
  → Create new Positions
  → Store Daily Result and Daily Position
  → Store Trade Log
  → Finalize Input Snapshot
  → Finalize Metrics and Run status
```

| Stage | Primary File |
|---|---|
| Full orchestration | `backtest_research_run.py` |
| Trading-day main loop | `backtest_engine.py` |
| Input query | `backtest_loader.py` |
| Market adapter | `research_backtest_market_adapter.py` |
| Filter adapter | `research_backtest_filter_adapter.py` |
| Sizing adapter | `research_backtest_sizing_adapter.py` |
| New entry | `backtest_buy_logic.py` |
| Sell decision | `backtest_sell_logic.py` |
| Position processing | `backtest_position_manager.py` |
| Trade store | `backtest_trade_log.py` |
| Run·Daily·Config store | `backtest_run_store.py` |
| Input Snapshot | `research_input_snapshot.py` |
| Performance calculation | `backtest_metrics.py` |

### 5.2 Engine

`backtest_engine.py` orchestrates the trading-day-level main loop.
`run_backtest` receives the Resolved Config, Strategy Config Version, and Config Hash as arguments and injects them into the entire path.

| Item | Role |
|---|---|
| Input | Trading day, Market·Stock Feature, price, and Universe |
| Config validation | Confirm required Config Categories exist and the Config Hash format |
| Market | Passes `market_config` to the Research Market Adapter |
| Position | Processes existing Positions before new buys |
| Buy | Passes the actual Config into Filter, Guard, Haircut, and Sizing |
| Input Snapshot | Records the consumed trading day·Feature·price·Universe in the Builder |
| Store | Daily Result and Daily Position Snapshot |

The price basis, trading-day ordering, existing-Position processing order, and new-buy timing are core contracts that change the backtest results.

### 5.3 Loader

`backtest_loader.py` is the SQL helper that reads Backtest inputs.

| Input | Purpose |
|---|---|
| `pre_total_market_daily_feature` | Market decision |
| `pre_total_stock_daily_feature` | Filter, Sizing, and Sell decision |
| `interest_price_raw` | Price and return calculation |
| `stock_universe` | Backtest target Universe |

The trading day, Feature reference date, and next-trading-day price must be distinguished.
If a future price or future Feature is included in the current decision, Look-ahead Bias occurs.

### 5.4 Research Adapter

The Research internal adapters connect the `port_strategy_common` contract to the Backtest flow and receive the Resolved Config explicitly.

| File | Common Call |
|---|---|
| `research_backtest_market_adapter.py` | `common_decide_market` |
| `research_backtest_filter_adapter.py` | `common_filter_buy_candidates` |
| `research_backtest_sizing_adapter.py` | `common_allocate_positions` |

The adapters do not perform their own DB access or external API calls.
They are the boundary that converts Common results into Research row and object formats.

### 5.5 Buy Logic

`backtest_buy_logic.py` handles new Position entry.

| Item | Processing |
|---|---|
| Candidates | Stocks that passed the Filter |
| Allocation | Passes `sizing_config` to the Research Sizing Adapter |
| Guard | Passes `buy_guard_config` to the Common Buy Guard |
| Haircut | Passes `buy_guard_config` to the Common Backtest Buy Size Haircut |
| Metadata | Entry Reason and information for later analysis |
| Same-day Stop | May generate a Trade Log depending on conditions |

Available Cash, Exposure, Max Positions, minimum quantity, and rounding criteria directly affect the results.
The BUY Guard and Haircut use the actual Resolved `buy_guard` Config.

### 5.6 Sell Logic and Position Manager

`backtest_sell_logic.py` is a wrapper around the Common Sell decision.

`backtest_position_manager.py` processes existing Positions and receives `sell_config` and `backtest_policy`.

| Processing | Meaning |
|---|---|
| Daily return | Computes the same-day change of held Positions |
| Intraday Stop | Emergency liquidation conditions for existing Positions |
| Regular Sell | Common Sell Decision |
| Liquidation | Generates a Trade Log |
| Carry-over | Passes surviving Positions to the next trading day |

Stop, holding period, and Sell Reason priority are affected by the Common contract shared with the Daily Decision.

### 5.7 Metrics

`backtest_metrics.py` provides DataFrame-based performance calculation and receives the Resolved `metrics` Config as an argument.

| Metric | Meaning |
|---|---|
| MDD | Maximum Drawdown |
| Sharpe Ratio | Return relative to risk |

The Risk-free Rate and annual trading days are passed from the Profile `metrics` Config.
Handling of empty data, zero denominators, and insufficient samples must be confirmed against the actual code.

## 6. Input Data

| Input | Role |
|---|---|
| Market Total Feature | Judges market state and allowed exposure |
| Stock Total Feature | Stock Filter, Sizing, and Sell decision |
| Price Raw | Price, return, and fill assumptions |
| Stock Universe | Target stocks and active conditions |
| Strategy Profile | Reproduces the per-Version Resolved Config |
| Run Input | Period, initial capital, and execution options |

For input data, distinguish the following.

| Category | Content to Confirm |
|---|---|
| Trade Date | Trading-day order and basis |
| Feature Date | Market·Stock Feature reference date |
| Price Date | Price date used for entry·exit |
| Missing | Not collected or join failure |
| Zero | A state where the actual value is 0 |
| Duplicate | Duplicate rows for the same Ticker·Date |
| Universe | Active stocks and exclusion conditions |

## 7. Output Data

### 7.1 Backtest Storage

| Output | Meaning |
|---|---|
| `strategy_backtest_run` | Run metadata, Config Snapshot, Version Identity, and status |
| `strategy_backtest_daily` | Per-trading-day portfolio performance |
| `strategy_backtest_daily_position` | Per-trading-day held Position Snapshot |
| `strategy_trade_log` | Completed trade detail, referencing Run ID and Config Identity |
| `strategy_run_input` | Run input values and Flatten Config KV |

`strategy_backtest_run` stores, together with the Config Snapshot, the Strategy Config Version, Metrics Config Version,
Source SHA, Image Digest, Artifact Identity Status, Config Hash, and Input Snapshot Hash·Status·Manifest.

### 7.2 Analysis Storage

| Output | Meaning |
|---|---|
| Basic Analysis | Basic aggregation results of the Run |
| Extended Analysis | Threshold, Bucket, and diagnostic-purpose extended results |
| `strategy_backtest_*_analysis` | The family of analysis tables keyed by Run ID |

### 7.3 Report Files

| Report | Meaning |
|---|---|
| Summary | Summary of Run performance and key metrics |
| Buy·Sell | Per-date buy·sell activity |
| Trade Detail | Per-trade detailed information |
| Recommendation | Research-perspective recommendation·diagnostics |

Recommendation is a research diagnostic.
It is not interpreted as actual investment advice, an order instruction, or a guarantee of future performance.

## 8. Storage and Re-run

| Consideration | Content to Confirm |
|---|---|
| Run creation | Whether the same input is a new Run or an update to an existing Run |
| Config storage | Config Snapshot once per Run; the Trade Log references the Identity |
| Daily storage | Per-trading-day Unique Key and Upsert |
| Position storage | Keyed by Run·Trade Date·Ticker |
| Trade Log | Completed trade and Metadata contract |
| Status transition | Started, Completed, and Failed handling |
| Input Snapshot | The point at which Manifest·Hash·Status is finalized |
| Transaction | Storage boundary for Run, Daily, Position, and Trade |
| Partial Success | Whether only the Run is marked successful after partial storage |
| Re-run | Linkage with existing Analysis·Report |
| Snapshot | Reproducibility of Config and Input |

The actual Unique Key and Conflict Target must be confirmed directly in the SQL or DDL.
Do not infer them from documentation alone.

## 9. Analysis

### 9.1 Basic Analysis

`backtest_analysis_basic.py` converts stored Run results into a basic aggregation form and stores it.
In the standard Backtest Run entrypoint, this Basic Analysis call is commented out and does not run automatically.

| Item | Meaning |
|---|---|
| Basis | Run ID |
| Input | Run, Daily, Position, and Trade Log |
| Output | Basic Analysis Rows |
| Risk | DB Insert possible |

### 9.2 Extended Analysis

`analysis_extended.py` regenerates the extended analysis keyed by Run ID.
The standard Backtest Run entrypoint (`backtest_research_run.py`) calls Extended Analysis automatically.

| Item | Meaning |
|---|---|
| Execution entrypoint | `run_extended_analysis.py` |
| Input | Stored Backtest results |
| Processing | May delete rows for the existing Run and recompute |
| Output | Multiple Extended Analysis Tables |
| Risk | Delete-then-Insert and Commit |

It deletes 12 analysis Tables, recomputes them, and commits once at the end.
On a mid-run failure, the Delete and Insert are rolled back together so that no partial results remain.

### 9.3 Analysis Interpretation

| State | Distinction |
|---|---|
| 0 trades | May be a normal Run but with no trades |
| Missing input | Stored data required for analysis is absent |
| Empty DataFrame | There is nothing to compute |
| Zero denominator | Ratio calculation not possible |
| `NULL` | Not computed or missing |
| Infinity | Possible denominator or numeric-stability issue |

Analysis results are not expressed as identical to actual operational performance.

## 10. Report

### 10.1 Report Composition

| File | Role |
|---|---|
| `report_data_loader.py` | Query Run·Daily·Position·Trade·Analysis |
| `report_formatter.py` | Format Label, Percentage, and Reason |
| `report_summary.py` | Generate Summary |
| `report_buy_sell.py` | Generate per-date Buy·Sell |
| `report_trade_detail.py` | Generate trade detail |
| `report_recommendation.py` | Generate recommendation·diagnostics |
| `backtest_report_run.py` | Full Report orchestration |

Report is the presentation layer that reads stored Backtest results and generates Text Files.

### 10.2 Run Selection

| Method | Meaning |
|---|---|
| Latest Run auto-select | `get_latest_run_id` selects the latest Run by `started_at DESC` |
| Specified Run ID | Each report function takes a run_id argument, but the entrypoint has no CLI option |
| No Run | Report generation not possible |

The latest Run is selected by `started_at` regardless of completion status.

### 10.3 Output Files

| Item | Current Documentation Basis |
|---|---|
| Default output | Current working directory |
| AWS Batch output | `/tmp/portfolio-reports` |
| Format | Text File |
| Overwrite | Filename generation rule needs confirmation |
| S3 | Optional upload when the Wrapper environment variables are set |

Report generation success and S3 upload success are separate states.

## 11. Block·Watch·Exception Buy Research

| File | Current Classification |
|---|---|
| `block_watch_analysis_run.py` | Watch Candidate analysis |
| `block_watch_backtest_run.py` | BLOCK Watch Backtest |
| `block_exception_buy_engine_run.py` | Exception Buy Engine research |
| `block_exception_buy_backtest_run.py` | Exception Buy Backtest |

This family is managed as research·on-hold candidates rather than a formal stage of the Daily operational pipeline.
They are not deleted merely because usage traces and operational linkage have not been confirmed.

## 12. Relationship with `port_strategy_common`

Research reuses core decision logic from Common.

| Area | Common Contract |
|---|---|
| Config | Strategy, Engine, and decision setting defaults |
| Market | Market Context and Decision |
| Filter | Buy Candidate Filter |
| Sizing | Position Allocation |
| Guard | Buy Guard |
| Haircut | Backtest Buy Size Haircut |
| Sell | Backtest Sell Decision |
| Metrics | Risk-free Rate and Trading Days defaults |

Public function names, dataclass fields, enums, config keys, and reason strings may be linked to other services.

### 12.1 Relationship with StrategyDecision

| Item | Relationship |
|---|---|
| Runtime Import | None |
| Shared target | `port_strategy_common` contract |
| Research Adapter | Internal to the Research repository |
| Decision Adapter | Internal to the StrategyDecision repository |
| Daily operational decision | StrategyDecision responsibility |
| Backtest decision | Research responsibility |

Decision is not a Research runtime dependency but a separate consumer of the same Common contract.
Research changes alone do not arbitrarily change the Common or Decision contract.

## 13. AWS Paper Daily Location

Research is invoked in AWS Paper Daily as Backtest and Report execution units.

| Daily Stage | Research Role |
|---|---|
| Step 4 · Backtest Research | Reads Features and generates Backtest and analysis results |
| Step 5 · Backtest Report | Generates Text Reports from the stored Run |

### 13.1 Step 4

| Item | Value |
|---|---|
| Entrypoint | `backtest_research_run.py` |
| Input | Feature, Price, Universe, Strategy Profile, and period |
| Output | Run, Daily, Position, Trade, and Analysis |
| DB impact | DDL·DML and Commit possible |
| Does not do directly | Daily Signal, Execution Plan, and Broker orders |

### 13.2 Step 5

| Item | Value |
|---|---|
| Entrypoint | `backtest_report_run.py` |
| Input | Latest or specified Run ID |
| Output | Summary, Buy·Sell, Trade Detail, and Recommendation |
| File impact | Local Text File generation |
| Optional impact | S3 upload through the AWS Batch Wrapper |

Scheduler and Step Functions handle execution orchestration.
The presence of an entrypoint in the Research repository is not evidence of the current AWS execution state or of a completed deployment.

## 14. Research CI and Deployment Path Contract

Research-specific DevOps is based on GitHub Actions·OIDC and CodeBuild,
and separates the Build/Test/Artifact responsibility from the Release Control responsibility.
The following is the execution-contract level Research needs to know; detailed GitHub Actions branching, IAM Policy,
AWS CLI, Job Definition Revision change procedures, and Step Functions update procedures are the responsibility of the `port-devops` document.

### 14.1 Current Deployment Path AS-IS

| Item | Current Contract |
|---|---|
| `main` Push | Build/Test validation path (no Image Publish·Candidate·Operating) |
| Release path split | Split into Candidate or Operating Release depending on whether Strategy Logic changed |
| Candidate path | Validates a new Challenger `RSCFG` Version on the `-candidate` Family |
| Operating path | Deploys the validated Artifact to the operational Family (Strategy Config Version preserved) |
| Common | Candidate and Operating are separate deployment paths |

- `main` Push performs Build/Test validation only.
- Candidate and Operating Release are separate paths and are not bundled into the same execution.
- Candidate is not an automatic Champion Promotion.
- Deploying the Research execution Artifact and promoting Strategy performance are separate procedures.

### 14.2 Responsibility Separation

| Actor | Responsibility |
|---|---|
| GitHub Actions | OIDC authentication, CodeBuild execution·status check, and Release Control |
| CodeBuild | Compile, Test, Config·Version Contract, Container Build·Smoke, and conditional ECR Artifact generation |
| CodeBuild Role | Build, Logs, and Research ECR scope |
| GitHub OIDC Role | Research CodeBuild start·query and Release Control scope |

Do not grant the Build Role operational Batch deployment, Step Functions, or operational DB permissions.
Candidate·Operating Release use a validated Digest-pinned Image and do not create a Mutable `latest` dependency.
Detailed permissions and deployment procedures are managed in the `port-devops` document and are not duplicated here.

## 15. Candidate and Operating Path Contract

The Candidate-specific Job Definition Family is separated from the operational Family.

| Item | Contract |
|---|---|
| Operating Family | The operational Backtest Job Definition Family |
| Candidate Family | The `-candidate` Family, separated from operational |
| Artifact | Both Candidate·operational use a validated Digest-pinned Image with Source SHA·Image Digest injected |
| Candidate execution | `--run-mode CANDIDATE`, selected `--strategy-config-version`, `--require-artifact-identity` |
| Candidate Runtime | Fargate, VCPU 1, Memory 4096 MiB |
| Operating Release | Replaces only the validated Artifact while preserving the Strategy Config Version |

Candidate validation confirms Job Status·Container Exit Code, storage of Run·Config Hash·Metrics·Input Snapshot,
and the failure-storage contract of an intentionally failed Candidate.

Even after Candidate success, the Operating Job Definition, Step Functions reference, and Champion are not changed automatically.
The actual procedure for Job Definition Revision registration and Step Functions reference switching is the responsibility of the `port-devops` document.

## 16. Operational Promotion·Rollback Historical Record

The following documents past manual promotion·validation results performed by the operator in AWS; these are operational facts,
not values determined by the Research repository code alone.
This record is preserved as a past manual-validation fact and is distinguished from the current automation AS-IS (14.1).

| Item | Value |
|---|---|
| Operational Champion at the time | Research Job Definition Revision 7 |
| Operational Resource at the time | VCPU 1, Memory 4096MiB |
| Rollback target at the time | Revision 5 (kept ACTIVE) |
| Revision 6 | OOM-failed Revision, preserved as evidence |
| Operational Run Mode at the time | `BACKTEST` |
| Operational Strategy Config Version at the time | `RSCFG-0001` |

Past promotion·Rollback summary:

- Registered Revision 6 with the Artifact validated on Champion Revision 5, and promoted the operational Step 4 reference from 5→6.
- Revision 6 failed with an Exit Code 137 Fargate OutOfMemoryError at VCPU 1·Memory 2048MiB (a memory shortage, not a logic·Config error).
- After rolling back to Revision 5, Revision 7 (with memory expanded to 4096MiB only) was validated standalone and finally promoted to operational Step 4.

This record is a past manual-validation fact; the current `main` Push does not perform such operational Champion changes automatically.
Strategy performance evaluation and DevOps Artifact promotion responsibilities are separated.

## 17. Container and Key DevOps Files

### 17.1 Dockerfile

| Item | Current Source Basis |
|---|---|
| Base Image | `python:3.13-slim` |
| Dependency | `requirements.txt` |
| Common | Installs `.devops/packages/port_strategy_common-1.0.0-py3-none-any.whl` with `--no-deps` |
| Version validation | Asserts `1.0.0` after install |
| Included | Root `*.py` and `strategy_profiles/` |
| Default CMD | `backtest_research_run.py` Compile check |
| Actual Research execution | External Command Override |

The default CMD is a Compile check, not an actual Backtest run.
It installs the Wheel Package rather than copying the Common Source Directory directly.

### 17.2 Key New DevOps Files

| File | Role |
|---|---|
| `Dockerfile` | Common Wheel install and Compile default CMD |
| `.dockerignore` | Excludes docs·DevOps Script·non-runtime files from the Build Context |
| `.devops/codebuild/buildspec.yml` | Build/Test/Container/ECR Artifact generation (no Job Definition registration responsibility) |
| `.devops/scripts/verify-candidate-contract.py` | Candidate static contract validation |
| `.devops/scripts/container-smoke.py` | Network-blocked Container Smoke Test |
| `.devops/scripts/generate-strategy-config.py` | Generates the next `RSCFG` Challenger (`status=CANDIDATE`) from the latest Profile |
| `.devops/scripts/deploy-candidate.sh` | Registers a new Candidate Family Revision and runs·validates the AWS Batch Candidate |
| `.devops/scripts/deploy-operating.sh` | Registers an operational Family Revision and switches the operational Step 4 reference |
| `.github/workflows/research-codebuild.yml` | `main` Push Build/Test and Candidate·Operating Release path branching |
| `strategy_profiles/README.md` | Strategy Profile management criteria |
| `strategy_profiles/RSCFG-0001.json` | Baseline Strategy Profile (`status=BASELINE`) |
| `strategy_profiles/RSCFG-0002.json` | Challenger Strategy Profile (`status=CANDIDATE`) |

The IAM, ARN, Job Definition Revision, and Step Functions operational procedure details of the above DevOps files are the responsibility of the `port-devops` document.

### 17.3 AWS Batch Report Wrapper

`aws_batch_backtest_report_wrapper.py` is the Report Wrapper for AWS Batch.

| Item | Role |
|---|---|
| `RESEARCH_APP_SECRET_JSON` | DB Secret JSON input |
| `INTEREST_DB_*` | Mapped to Research DB environment variables |
| `REPORT_OUTPUT_DIR` | Report output path |
| `runpy.run_module` | Runs the Report Entrypoint |
| `REPORT_S3_BUCKET` | Activation condition for S3 upload |
| `REPORT_S3_PREFIX` | S3 Key Prefix |
| `AWS_BATCH_JOB_ID` | Distinguishes per-Job output paths |

Secret values and the actual Bucket, Prefix, Job ID, and ARN are not recorded in documentation.

## 18. How to Run

Internal imports are based on the `port_strategy_research` package path.
When execution is needed, use the `python -m` form rather than running a file path directly.

The commands below are format examples for illustration.
Because they may trigger actual DB writes, file generation, and S3 uploads, do not run them during documentation work.

```powershell
python -m port_strategy_research.backtest_research_run --strategy-config-version RSCFG-0001

python -m port_strategy_research.run_extended_analysis

python -m port_strategy_research.backtest_report_run

python -m port_strategy_research.aws_batch_backtest_report_wrapper
```

The actual CLI options and required environment variables must be confirmed in each Entrypoint source.

| Entrypoint | Execution Impact |
|---|---|
| `backtest_research_run` | May store a Backtest Run and results |
| `run_extended_analysis` | May Delete·Insert Analysis Tables |
| `backtest_report_run` | DB Read and local Report generation |
| AWS Batch Wrapper | May map Secrets, generate Reports, and upload to S3 |
| Block·Watch Entrypoint | May Update the DB or run a Simulation |

## 19. DB Configuration

DB connection uses `get_db_config()` in `db_config.py`.

### 19.1 Environment Variables

| Environment Variable | Current Documentation Basis |
|---|---|
| `INTEREST_DB_HOST` | Default `localhost` |
| `INTEREST_DB_PORT` | Default `5433` |
| `INTEREST_DB_NAME` | Default `portfolio` |
| `INTEREST_DB_USER` | Default `postgres` |
| `INTEREST_DB_PASSWORD` | No default; missing value causes an execution error |

```powershell
$env:INTEREST_DB_HOST="localhost"
$env:INTEREST_DB_PORT="5433"
$env:INTEREST_DB_NAME="portfolio"
$env:INTEREST_DB_USER="postgres"
$env:INTEREST_DB_PASSWORD="[REDACTED]"
```

The example values are for local documentation and are not actual operational connection information.
The Artifact Identity environment variables `RESEARCH_SOURCE_SHA` and `RESEARCH_IMAGE_DIGEST` are injected by the deployment Runtime.

### 19.2 Search Path

The Search Path per current documentation is in the following order.

```text
research, preprocessor, interest, reference, legacy, public
```

| Schema | Primary Role |
|---|---|
| `research` | Backtest, Analysis, and Research artifacts |
| `preprocessor` | Total Feature |
| `interest` | Price Raw |
| `reference` | Stock Universe |
| `legacy`, `public` | Compatibility for existing Unqualified SQL |

Changing the Search Path order can change the Table that Unqualified SQL references.

## 20. External Dependencies

| Dependency | Purpose |
|---|---|
| Python | Runtime |
| PostgreSQL | Feature query and Research result storage |
| `pandas` | Table and performance calculation |
| `numpy` | Numeric calculation |
| `psycopg2` | PostgreSQL connection |
| `psycopg2-binary` | Install Package |
| `boto3` | S3 upload in the AWS Batch Wrapper |
| `port_strategy_common` | Wheel `1.0.0` pinned install, common decision and configuration |

Pinned Versions are managed in `requirements.txt`.
Version values are not duplicated in the README.

## 21. State and Calculation Considerations

| Consideration | Content to Confirm |
|---|---|
| Look-ahead | Do not use future Feature·Price |
| Trade Order | Existing-Position processing and new-Buy order |
| Missing | Distinguish missing values from actual 0 |
| Duplicate | Ticker·Date Join Cardinality |
| Cash | Available Cash and Position Allocation |
| Cost | Whether Fee, Tax, and Slippage are implemented |
| Stop | Same-day Stop and regular Sell priority |
| Config Inject | Use the Resolved Config, not Module Global |
| Run Status | Whether Completed is set after a Partial Save |
| Analysis | Possibility of Insert failure after Delete |
| Report | Latest Run selection and file overwrite |
| S3 | Distinguish partial upload failure from full success |
| Reproducibility | Preserve Config·Input Snapshot and Artifact Identity |

Do not conclude from the README alone that the current implementation automatically handles all failures and numeric boundaries.
For code changes or incident analysis, confirm the EntryPoint, Store, and Transaction directly.

## 22. Document Structure

| Document | Role |
|---|---|
| `AGENTS.md` | Kiro work scope, safety, data contracts, and validation rules |
| `README.md` | Current Research structure, execution·configuration, and operational AS-IS |
| `CHANGELOG.md` | Key change history and facts at the time |
| `docs/source-file-catalog.md` | File responsibilities, input/output, and change impact |

When file responsibilities, Entrypoints, DB access, Analysis, Report, the AWS Wrapper, or Dependencies change,
check the README and `docs/source-file-catalog.md` together.

Do not create date-specific `docs/worklog/*.md` files.
Past creation facts are preserved only as historical entries in the CHANGELOG.

## 23. Safe Validation Scope

When only documentation is modified, confirm only the changed files and Diff scope.

```powershell
git status --short
git diff --stat
git diff --check
```

Even for code changes, prioritize validation without actual Backtest, Analysis, Report, DB write, AWS, S3, or order execution.

| Validation | Safe Method |
|---|---|
| Profile·Schema | Resolved Config merge and Unknown Key unit validation |
| Config Snapshot | Canonical JSON and Hash unit validation |
| Adapter | Unit input·output comparison |
| Metrics | Small DataFrame Fixture |
| Loader | DB Mock |
| Run Store | Connection·Cursor Mock |
| Report | Temporary directory |
| AWS Wrapper | Environment variable and boto3 Mock |

Validation that requires operational execution is not performed automatically and is reported as remaining validation.
