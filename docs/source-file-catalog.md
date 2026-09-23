# Source File Catalog

Organizes the primary file responsibilities, input/output, change impact, and execution risk of `port_strategy_research`.

This document is not a full repository inventory.
It manages only the files needed to understand and maintain the Research flow.

## 1. Document Purpose

| Item | Value |
|---|---|
| Target | The `port_strategy_research` root and `docs/source-file-catalog.md` |
| Basis | The currently documented file structure, imports, entrypoints, and data contracts |
| Excluded | Build artifacts, Cache, IDE files, `__pycache__`, and one-time Dump·Report artifacts |
| Primary perspective | File responsibility, input, output, DB·file·AWS impact, and change linkage |
| Actual execution | Not performed during documentation cleanup |
| Unconfirmed items | Content requiring a final comparison against the actual code is not inferred |

## 2. Service Flow

| Stage | Responsibility |
|---|---|
| Config Resolve | Strategy Profile Load, Common Default merge, and Config Snapshot·Hash generation |
| Input Load | Query Market·Stock Feature, Price, and Universe |
| Market Decision | Calls the Common Market decision |
| Position Process | Holding·liquidation·carry-over processing of existing Positions |
| Buy Filter | Selects new buy candidates |
| Sizing·Guard | Applies Allocation, Guard, and Haircut |
| Daily Store | Stores per-trading-day performance and Position Snapshot |
| Trade Store | Stores completed trades and Metadata |
| Analysis | Generates Basic·Extended Analysis |
| Report | Generates Summary·Buy·Sell·Trade·Recommendation |
| Delivery | Optional S3 upload by the AWS Batch Wrapper |

## 3. Root and Configuration Files

| File | Role |
|---|---|
| `__init__.py` | `port_strategy_research` Package Import reference point |
| `db_config.py` | Manages `INTEREST_DB_*` and Research DB connection settings |
| `requirements.txt` | Research Runtime Dependency list |
| `Dockerfile` | Defines the Research Container Image and default CMD |

### 3.1 `__init__.py`

| Item | Value |
|---|---|
| Responsibility | Package initialization |
| Feature logic | None |
| Change impact | The `python -m port_strategy_research.<module>` Import structure |
| Caution | Do not delete arbitrarily even if it appears to have no functionality |

### 3.2 `db_config.py`

| Item | Value |
|---|---|
| Responsibility | Centralizes PostgreSQL connection settings |
| Primary input | `INTEREST_DB_HOST`, `PORT`, `NAME`, `USER`, `PASSWORD` |
| Password | External injection with no default |
| Search Path | `research, preprocessor, interest, reference, legacy, public` |
| Call impact | A DB connection may occur when creating a Connection |
| Change risk | The default DB, Schema order, and Credential handling contract |
| Caution | Do not record actual connection values in documentation·logs |

### 3.3 `requirements.txt`

| Item | Value |
|---|---|
| Primary Dependency | `psycopg2-binary`, `pandas`, `numpy`, `boto3` |
| Common handling | `port_strategy_common` is included separately as a pinned Wheel `1.0.0` install |
| Change impact | Container Build and Runtime Import |
| Caution | Pinned Versions are managed in the file itself and not repeated in documentation |

### 3.4 `Dockerfile`

| Item | Value |
|---|---|
| Base image | `python:3.13-slim` |
| Common install | Installs `.devops/packages/port_strategy_common-1.0.0-py3-none-any.whl` with `--no-deps` |
| Version validation | Asserts `1.0.0` after install |
| Included | Root `*.py` and `strategy_profiles/` |
| Default CMD | `backtest_research_run.py` Compile check |
| Actual execution | Batch·ECS or Local Command Override |
| Change impact | Common Source Copy removal and Wheel Pin contract |
| Repository boundary | Image Push and Job·Task registration are the deployment domain |
| Caution | Do not record URI, ARN, Queue, and Registry verbatim in documentation |

## 4. Backtest Research Entrypoint

### 4.1 `backtest_research_run.py`

| Item | Value |
|---|---|
| Responsibility | Full orchestration of the standard Backtest Research |
| CLI | `--strategy-config-version`, `--run-mode`, `--require-artifact-identity`, `--backtest-start-date`, `--backtest-end-date`, `--skip-extended-analysis` |
| Primary input | Strategy Profile, period, Run Mode, and DB Feature |
| Primary processing | Profile Load·Hash, Artifact Identity resolution, Run creation, Engine injection, and Analysis |
| Primary output | Run, Daily, Daily Position, Trade, Analysis, and Input Snapshot |
| DB impact | DDL·DML and Commit possible |
| Status impact | May change Run started·completed·failed status |
| Re-run risk | May create a new Run or link existing results for the same input |
| Execution risk | Actual Research data creation·change |
| Other-file contract | Passes Config·Identity to the Loader, Config Snapshot, Version Identity, and Run Store |
| Caution | Do not run during documentation·static analysis |

## 5. Backtest Core

The Backtest Core processes existing Positions in trading-day order and computes new entries.

| Order | File |
|---|---|
| 1 | `backtest_engine.py` |
| 2 | `backtest_loader.py` |
| 3 | 3 Research Adapters |
| 4 | `backtest_position_manager.py`, `backtest_sell_logic.py` |
| 5 | `backtest_buy_logic.py` |
| 6 | `backtest_run_store.py`, `backtest_trade_log.py` |
| 7 | `backtest_metrics.py` |

### 5.1 `backtest_engine.py`

| Item | Value |
|---|---|
| Responsibility | Trading-day-level Backtest main loop |
| Primary input | Resolved Config, Strategy Config Version, Config Hash, trading day, and Feature |
| Config injection | Passes Market·Filter·Sizing·Buy Guard·Buy·Sell·Backtest Policy Config to each stage |
| Primary processing | Config validation, Market, Position, Filter, Buy, and performance aggregation |
| Processing order | Processes existing Positions before new buys |
| Input Snapshot | Records the consumed trading day·Feature·price·Universe in the Builder |
| Primary output | Daily Result and Daily Position Snapshot |
| DB impact | Write and Commit possible through the Store Helper |
| Change risk | Trading-day order, price basis, Position processing order, and Config passing |
| Caution | Use explicit Config rather than Module Global, and confirm Partial Save |

### 5.2 `backtest_loader.py`

| Item | Value |
|---|---|
| Responsibility | Backtest input DB query |
| Market input | `pre_total_market_daily_feature` |
| Stock input | `pre_total_stock_daily_feature` |
| Price input | `interest_price_raw` |
| Universe input | `stock_universe` |
| DB impact | Query |
| Change risk | Date basis, Join Cardinality, sorting, and Row Shape |
| Caution | Distinguish missing Feature, actual 0, and future data |

### 5.3 `backtest_buy_logic.py`

| Item | Value |
|---|---|
| Responsibility | New Position entry processing |
| Primary input | Filter candidates, Market Decision, Cash, and Resolved Config |
| Sizing | Passes `sizing_config` to the Research Sizing Adapter |
| Guard | Passes `buy_guard_config` to the Common Buy Guard |
| Haircut | Passes `buy_guard_config` to the Common Backtest Buy Size Haircut |
| Primary output | New Position and Entry Metadata |
| DB direct write | May store same-day Stop trades through the Trade Log Helper |
| Change risk | Candidate order, Allocation, Reason, and Position Shape |
| Change impact | Fixed the BUY Guard `config={}` wiring to pass the actual Resolved Config |
| Caution | Do not express it as an operational Daily BUY Signal generation flow |

### 5.4 `backtest_sell_logic.py`

| Item | Value |
|---|---|
| Responsibility | Common Sell decision Wrapper |
| Common function | `common_evaluate_backtest_sell` |
| Primary input | Position, Market·Stock Feature, and Config |
| Primary output | Sell Decision and Reason |
| DB direct access | None |
| Change risk | Common Input Mapping, priority, and Reason |
| Caution | Do not treat it as the same Runtime implementation as the Daily Position Evaluator |

### 5.5 `backtest_position_manager.py`

| Item | Value |
|---|---|
| Responsibility | Holding·liquidation·carry-over processing of existing Positions |
| Primary processing | Same-day return, intraday Stop, regular Sell, and Carry |
| Primary output | Surviving Positions, liquidation trades, and daily performance |
| DB impact | Write possible through the Trade Log Helper |
| Change risk | Stop priority, holding days, price, and Position Dict |
| Caution | Confirm liquidation-trade storage failure together with Position State |

### 5.6 `backtest_trade_log.py`

| Item | Value |
|---|---|
| Responsibility | Completed trade Persistence |
| Primary Table | `strategy_trade_log` |
| Primary input | Run, stock, Buy·Sell dates, price, Reason, and Snapshot |
| DB impact | Insert |
| Change risk | Meaning of Column, JSON Metadata, Return, and Hold Period |
| Caution | Confirm the same-trade duplication and Transaction participation scope |

### 5.7 `backtest_metrics.py`

| Item | Value |
|---|---|
| Responsibility | Backtest performance metric calculation |
| Primary input | Daily Return DataFrame |
| Primary output | MDD and Sharpe Ratio |
| Settings | Common Risk-free Rate and Trading Days |
| DB access | None |
| Change risk | Column, Annualization, empty-value, and zero-denominator handling |
| Caution | Do not turn insufficient samples or non-computable cases into normal numbers |

### 5.8 `backtest_run_store.py`

| Item | Value |
|---|---|
| Responsibility | Backtest Run, daily results, and Config·Identity Persistence |
| Primary Table | `strategy_backtest_run`, `strategy_backtest_daily`, `strategy_backtest_daily_position` |
| Run storage columns | Config Snapshot·Hash, Strategy·Metrics Config Version, Source SHA, Image Digest, Artifact·Input Snapshot Status |
| Run Mode | Validates `BACKTEST`·`CANDIDATE` via `ALLOWED_RUN_MODES` |
| Trade Log reference | Adds Run ID·Config Version·Config Hash columns to `strategy_trade_log` |
| Primary processing | Table check, Run creation, Daily·Position storage, Input Snapshot finalization, and Finalize |
| DB impact | DDL, Insert, Update, Upsert, and Commit possible |
| Re-run risk | Duplicate on Run·Date·Ticker basis or update of existing Rows |
| Change risk | Unique Key, Conflict Target, Status, Config columns, and Transaction |
| Caution | Confirm the Run-status finalization order after Daily and Position storage |

## 6. Research Adapter

The Research Adapters call `port_strategy_common` directly and do not Runtime Import `port_strategy_decision`.

### 6.1 `research_backtest_market_adapter.py`

| Item | Value |
|---|---|
| Responsibility | Converts Market Feature into a Common Context |
| Common function | `common_decide_market` |
| Primary output | The Market Decision that Research uses |
| DB access | None |
| Change risk | Context Field, Config, and Reason Mapping |
| Caution | Do not arbitrarily reinterpret the Common result meaning in Research |

### 6.2 `research_backtest_filter_adapter.py`

| Item | Value |
|---|---|
| Responsibility | Connects Stock Feature to the Common Buy Filter |
| Common function | `common_filter_buy_candidates` |
| Primary output | Passed·excluded candidates and Reason |
| DB access | None |
| Change risk | Candidate Row, Filter Config, and sorting |
| Caution | Distinguish Filter rejection from missing Feature |

### 6.3 `research_backtest_sizing_adapter.py`

| Item | Value |
|---|---|
| Responsibility | Connects Filter candidates to the Common Allocation |
| Common function | `common_allocate_positions` |
| Primary output | Per-candidate Position Allocation |
| DB access | None |
| Change risk | Cash, Exposure, quantity·weight, and Rounding |
| Caution | Do not arbitrarily change the Position size meaning as Research-only |

## 7. Analysis

### 7.1 `backtest_analysis_basic.py`

| Item | Value |
|---|---|
| Responsibility | Generates Run-based basic aggregation Analysis |
| Primary input | Trade Log and stored Backtest results |
| Primary output | Buy Reason, Hold Period, and Market Signal analysis |
| DB impact | Insert into 3 Analysis Tables (no Delete·Upsert) |
| Execution location | Commented out in `backtest_research_run.py`; not auto-run in the standard Run |
| Change risk | Meaning of Run ID scope, Bucket, and Label |
| Caution | Distinguish 0 trades from missing input |

### 7.2 `analysis_extended.py`

| Item | Value |
|---|---|
| Responsibility | Regenerates Run-based extended Analysis |
| Execution location | Auto-called by `backtest_research_run.py` + standalone run via `run_extended_analysis.py` |
| Primary areas | Signal·Holding, Ticker, Entry·Exit, Sector, and MB Weak |
| Primary output | The `strategy_backtest_*_analysis` family |
| DB impact | Delete-then-Insert of 12 Tables |
| Re-run risk | Single commit at the end; rolled back together on a mid-run failure |
| Change risk | Run scope, Threshold, Bucket, and Transaction |
| Caution | Do not expand the 12-Table delete scope to other Runs |

### 7.3 `run_extended_analysis.py`

| Item | Value |
|---|---|
| Responsibility | Extended Analysis execution Entrypoint |
| Run selection | Latest or the Run ID that the code determines |
| Call target | `analysis_extended.run_analysis_extended` |
| DB impact | Analysis Table update |
| Execution risk | Delete·Insert and Commit possible |
| Caution | Do not run during documentation work |

## 8. Report

### 8.1 `backtest_report_run.py`

| Item | Value |
|---|---|
| Responsibility | Full Text Report generation Orchestration |
| Run selection | Auto-selects the latest Run by `started_at DESC` (no entrypoint-specified option) |
| Call target | Summary, Buy·Sell, Trade Detail, and Recommendation |
| DB impact | Query |
| File impact | Local TXT generation |
| Change risk | Run selection, call order, filename, and overwrite |
| Caution | Distinguish Report generation success from S3 upload success |

### 8.2 `report_data_loader.py`

| Item | Value |
|---|---|
| Responsibility | Report common data query |
| Primary input | Run, Daily, Daily Position, Trade, and Analysis |
| Snapshot input | Threshold and Config-related stored data |
| DB impact | Query |
| Change risk | Latest Run, Join, Sort, and Missing handling |
| Caution | Do not confuse the Daily Position Snapshot with the Trade Event meaning |

### 8.3 `report_formatter.py`

| Item | Value |
|---|---|
| Responsibility | Human-readable string formatting |
| Primary processing | Label, Percentage, Run Input, and Buy·Sell Reason |
| DB access | None |
| File write | None |
| Change risk | Reason Mapping, units, and display meaning |
| Caution | Record a display change as a Report interpretation change too |

### 8.4 `report_summary.py`

| Item | Value |
|---|---|
| Responsibility | Summary Report generation |
| Primary input | Run, Metrics, and key Analysis |
| Output | Summary TXT |
| DB impact | Query |
| File impact | Write |
| Caution | Do not display a non-computed metric as 0 |

### 8.5 `report_buy_sell.py`

| Item | Value |
|---|---|
| Responsibility | Per-trading-day Buy·Sell Report generation |
| Primary input | Daily, Daily Position, and Trade Event |
| Output | Buy·Sell TXT |
| DB impact | Query |
| File impact | Write |
| Caution | Distinguish held Positions from new Buys on a Snapshot basis |

### 8.6 `report_trade_detail.py`

| Item | Value |
|---|---|
| Responsibility | Completed trade detail Report generation |
| Primary input | `strategy_trade_log` |
| Output | Trade Detail TXT |
| DB impact | Query |
| Change risk | Meaning of Trade Column, Reason, and Return |
| Caution | Do not express it as an actual order·fill Report |

### 8.7 `report_recommendation.py`

| Item | Value |
|---|---|
| Responsibility | Research recommendation·diagnostics Report generation |
| Primary input | Analysis and Threshold Snapshot |
| Output | Recommendation TXT |
| DB impact | Query |
| File impact | Write |
| Change risk | Threshold interpretation, Label, and diagnostic wording |
| Caution | Do not express it as actual investment advice or an order instruction |

## 9. AWS Batch Report Wrapper

### 9.1 `aws_batch_backtest_report_wrapper.py`

| Item | Value |
|---|---|
| Responsibility | AWS Batch Report execution and optional S3 upload |
| Secret input | `RESEARCH_APP_SECRET_JSON` |
| DB Mapping | `INTEREST_DB_*` environment variables |
| Output | `REPORT_OUTPUT_DIR` |
| Execution target | `port_strategy_research.backtest_report_run` |
| S3 condition | `REPORT_S3_BUCKET` set |
| Key composition | Prefix, date, Job ID, and filename |
| External impact | DB query, Local File, and S3 write |
| Caution | Do not leave Secret, Bucket, Prefix, and Job ID verbatim |

## 10. Block·Watch·Exception Buy Research

This family is managed as research·on-hold files rather than a formal stage of the Daily operational pipeline.

### 10.1 `block_watch_analysis_run.py`

| Item | Value |
|---|---|
| Responsibility | Post-hoc performance analysis of Watch Candidates |
| Primary processing | N-day forward Return calculation |
| DB impact | Candidate Return Update possible |
| Classification | Research |
| Caution | Not run and not a deletion target |

### 10.2 `block_watch_backtest_run.py`

| Item | Value |
|---|---|
| Responsibility | Quality validation of Watch Candidates after BLOCK |
| Primary processing | Candidate and Forward Return calculation |
| DB impact | Query |
| Output | Console Summary possible |
| Classification | Backtest-natured Research |
| Caution | Do not express it as an operational BLOCK Watch run |

### 10.3 `block_exception_buy_engine_run.py`

| Item | Value |
|---|---|
| Responsibility | Backtest Engine-based Exception Buy validation |
| Primary processing | Run creation, Daily storage, and Finalize (no Analysis call) |
| DB impact | Write and Commit possible |
| Classification | Research·on-hold |
| Caution | Do not run without an explicit approval |

### 10.4 `block_exception_buy_backtest_run.py`

| Item | Value |
|---|---|
| Responsibility | Threshold-based Exception Buy candidate validation |
| Primary output | Candidate, Trade, and monthly Summary |
| DB impact | Query possible |
| Classification | Backtest-natured Research |
| Caution | Do not assert it is an actual Daily BUY exception-allow feature |

## 10A. Strategy Profile and Config·Version Identity

### 10A.1 `strategy_profiles/README.md`

| Item | Value |
|---|---|
| Responsibility | Document of per-Version Strategy Profile management criteria |
| Content | Category management scope, exclusion scope, and Baseline description |
| DB·AWS impact | None |
| Change impact | Profile management rules |
| Caution | Report Config and Run Input are excluded from the Profile scope |

### 10A.2 `strategy_profiles/RSCFG-0001.json`

| Item | Value |
|---|---|
| Responsibility | Baseline Strategy Profile |
| Primary input | None (declaration data) |
| Primary output | The per-Version Config Override that the Loader reads |
| Category | metadata, market, filter, sizing, buy_guard, buy, sell, backtest_policy, metrics |
| Identity | `strategy_config_version=RSCFG-0001`, `metrics_config_version=RMETRICS-0001` |
| Status | `BASELINE` |
| Change impact | Strategy decision results and Config Hash |
| Caution | Do not copy the full detailed Config values into documentation |

### 10A.2b `strategy_profiles/RSCFG-0002.json`

| Item | Value |
|---|---|
| Responsibility | Challenger Strategy Profile |
| Status | `CANDIDATE` |
| Primary difference | `market.aggressive_max_positions=6` (RSCFG-0001 is 4) |
| Baseline relationship | A separate Config Identity that does not overwrite `RSCFG-0001` |
| Change impact | Challenger strategy decision results and Config Hash |
| Caution | `CANDIDATE` is not an operational Champion designation |

### 10A.3 `strategy_profile_loader.py`

| Item | Value |
|---|---|
| Responsibility | Profile selection, path resolution, validation, and Snapshot generation |
| Primary input | `strategy_config_version` string |
| Primary output | Profile, Resolved Config, and Config Snapshot |
| Default | `DEFAULT_STRATEGY_CONFIG_VERSION=RSCFG-0001` |
| DB·AWS impact | None (file read) |
| Change risk | Version pattern, path lookup, and Snapshot generation contract |
| Caution | Block a nonexistent Version before the DB connection·Run creation |

### 10A.4 `strategy_profile_schema.py`

| Item | Value |
|---|---|
| Responsibility | Profile Schema validation and Common Default merge |
| Primary input | Profile Dict and requested Version |
| Primary output | Resolved Config Dict |
| Validation | Required Category·Metadata, permitted Keys, Type, and Unknown Key blocking |
| Common dependency | `port_strategy_common.config` and `COMMON_STRATEGY_VERSION` |
| Change risk | Permitted Key set, Type rules, and merge result |
| Caution | Block Common Package·Strategy Version declaration mismatches |

### 10A.5 `strategy_config_snapshot.py`

| Item | Value |
|---|---|
| Responsibility | Resolved Config Canonical JSON and SHA-256 Hash generation |
| Primary input | Resolved Config and Profile Path |
| Primary output | `StrategyConfigSnapshot` (Version, Config, Canonical JSON, Hash) |
| Secret | Blocks execution if a Secret candidate is found in the Config |
| DB·AWS impact | None |
| Change risk | Canonical rules, Hash input, and Secret detection |
| Caution | The actual execution Config is the Canonical Source; Secrets are excluded from the Hash input |

### 10A.6 `research_version_identity.py`

| Item | Value |
|---|---|
| Responsibility | Version Identity separation and Artifact Identity resolution |
| Primary input | Resolved Config, install Metadata, and environment variables |
| Primary output | Common Package·Strategy, Research Engine, Strategy·Metrics Config, Artifact Identity |
| Environment variables | `RESEARCH_SOURCE_SHA`, `RESEARCH_IMAGE_DIGEST` |
| Validation | Package·Strategy Version match, Source SHA·Image Digest format |
| Change risk | Identity separation rules and required validation options |
| Caution | Distinguish the `UNRESOLVED`·`COMPLETE`·format-error states |

### 10A.7 `research_engine_version.py`

| Item | Value |
|---|---|
| Responsibility | The single source of truth for the Research Engine Version |
| Primary output | The `RESEARCH_ENGINE_VERSION` constant |
| DB·AWS impact | None |
| Change risk | Run-stored Engine Version and reproducibility |
| Caution | Keep it as a different value from the Strategy Config Version |

### 10A.8 `research_input_snapshot.py`

| Item | Value |
|---|---|
| Responsibility | Deterministic Snapshot Hash and Manifest generation of consumed input data |
| Primary input | Trading day, Universe, Market·Stock Feature, and price |
| Primary output | `InputSnapshotEvidence` (Hash, Manifest, Status) |
| DB·AWS impact | None (In-memory aggregation) |
| Change risk | Canonical rules, special-value handling, and Manifest format |
| Caution | An Input Data Identity different from the Config Hash; may change on source update |

## 10B. Research DevOps Files

### 10B.1 `.devops/codebuild/buildspec.yml`

| Item | Value |
|---|---|
| Responsibility | Build/Test/Container/ECR Artifact generation and conditional ECR Publish |
| Primary steps | Compile, Contract Test, Common Wheel validation, Docker Build, and Container Smoke |
| Publish control | `PUSH_IMAGE` and `RELEASE_STAGE=BUILD_ONLY` |
| Image basis | Git SHA-based Tag; Digest lookup on Push |
| Candidate responsibility | No Candidate Job Definition registration responsibility (`REGISTRATION=DISABLED`) |
| AWS impact | ECR lookup and conditional Push |
| Change risk | Build·Publish separation; block Push on failure |
| Caution | Do not leave actual ARN, Account ID, and Digest verbatim in documentation |

### 10B.2 `.devops/scripts/verify-candidate-contract.py`

| Item | Value |
|---|---|
| Responsibility | Candidate static contract validation |
| Validation | Dockerfile Wheel Pin, Entrypoint CLI, Artifact Identity format, Job Definition separation |
| Confirmation | Operational·Candidate Family separation and absence of Scheduler·Step Functions Wiring |
| AWS impact | None (static file inspection) |
| Change risk | Contract constants and prohibited Token list |
| Caution | Maintain the Mutable Tag and automatic-Wiring prohibition contract |

### 10B.3 `.devops/scripts/container-smoke.py`

| Item | Value |
|---|---|
| Responsibility | Network-blocked Container Smoke Test |
| Validation | Python Runtime, module Import, Common install location, Profile existence, and CLI contract |
| Execution | `docker run --network none`, confirm the default Compile CMD |
| DB·external access | Blocked (no DB connection·Backtest execution) |
| Change risk | Required module·CLI list and default CMD contract |
| Caution | Import·structure validation, not an actual Research run |

### 10B.4 `.github/workflows/research-codebuild.yml`

| Item | Value |
|---|---|
| Responsibility | OIDC authentication, CodeBuild execution·status validation, and Release Control |
| Trigger | `main` Push and `workflow_dispatch` |
| `main` Push | Build/Test validation path (not automatic Candidate execution) |
| Path branching | Split into Candidate or Operating Release depending on whether Strategy Logic changed |
| Candidate path | Calls `deploy-candidate.sh` |
| Operating path | Calls `deploy-operating.sh` |
| AWS impact | CodeBuild start·status query and Release Control |
| Caution | Detailed branching·OIDC·IAM·ARN details are the responsibility of the `port-devops` document |

### 10B.5 `.devops/scripts/deploy-candidate.sh`

| Item | Value |
|---|---|
| Responsibility | Registers a new Candidate Family Revision and runs·validates the AWS Batch Candidate |
| Execution path | Candidate Release path |
| Validation | Confirm Artifact Identity, Container Exit Code, and Job Definition Identity |
| Boundary | No change to Operating·Step Functions·Champion |
| AWS impact | Batch Job Definition registration and Candidate execution |
| Caution | Shell implementation details, AWS CLI, ARN, and IAM Policy are the responsibility of `port-devops` |

### 10B.5b `.devops/scripts/deploy-operating.sh`

| Item | Value |
|---|---|
| Responsibility | Registers an operational Family Revision and switches the operational Step 4 reference |
| Execution path | Operating Release path |
| Config preservation | Preserves the operational Strategy Config Version and fails on change |
| Boundary | An operational deployment path separated from the Candidate path |
| AWS impact | Batch Job Definition registration and Step Functions reference switching |
| Caution | State Machine·ARN·IAM operational procedure details are the responsibility of `port-devops` |

### 10B.5c `.devops/scripts/generate-strategy-config.py`

| Item | Value |
|---|---|
| Responsibility | Generates the next Challenger Version from the latest `RSCFG` Profile |
| Processing | Creates the next Version file and sets `status=CANDIDATE` |
| Baseline | Creates only a new file without overwriting the existing Profile |
| DB·AWS impact | None (file creation) |
| Caution | The generated Version is a Challenger and not an automatic Champion |

### 10B.6 `.dockerignore`

| Item | Value |
|---|---|
| Responsibility | Excludes docs·DevOps Script·non-runtime files from the Build Context |
| Primary exclusions | docs, `.devops/scripts`, `.github`, Cache, and logs |
| Change impact | Image size and Build Context content |
| Caution | Do not confuse Runtime-required files with exclusion targets |

## 11. Data Contract

### 11.1 Primary Inputs

| Data | Role |
|---|---|
| `pre_total_market_daily_feature` | Market decision |
| `pre_total_stock_daily_feature` | Filter, Sizing, and Sell decision |
| `interest_price_raw` | Price, return, and fill assumptions |
| `stock_universe` | Backtest target Universe |
| Config Snapshot | Strategy criteria reproduction |
| Run Input | Period, initial capital, and execution options |

### 11.2 Primary Outputs

| Data | Role |
|---|---|
| `strategy_backtest_run` | Execution metadata, Config Snapshot, and Version·Artifact·Input Identity |
| `strategy_backtest_daily` | Per-trading-day performance |
| `strategy_backtest_daily_position` | Per-trading-day Position Snapshot |
| `strategy_trade_log` | Completed trade detail, referencing Run ID·Config Version·Config Hash |
| `strategy_run_input` | Run input values and Flatten Config KV |
| `strategy_backtest_*_analysis` | Run-based analysis results |
| Report TXT | Human-readable Research results |

### 11.3 Contracts to Confirm on Change

| Item | Content to Confirm |
|---|---|
| Table | Schema, Table Name, and Search Path |
| Column | Type, NULL allowance, and meaning |
| Key | Run ID, Unique Key, and Conflict Target |
| Date | Trade Date, Feature Date, and Price Date |
| Status | Run and Analysis status values |
| Reason | Strings consumed by Common·Report |
| Snapshot | Config, Input, Threshold, and Metadata Shape |
| Transaction | DDL·DML, Partial Save, and Rollback |
| Re-run | New Run, Delete·Insert, and Upsert behavior |
| File | Report name, path, and overwrite |
| S3 | Upload condition, target files, and partial failure |

## 12. Execution Risk Classification

| Grade | Meaning |
|---|---|
| Read | DB query and operational·research data output possible |
| Write | Research Table Insert·Update·Upsert possible |
| Delete | Run ID-targeted Analysis Row deletion possible |
| File | Local TXT generation·overwrite possible |
| External write | S3 upload possible |
| Downstream impact | Analysis and Report consume the stored results |

### 12.1 Per-file Risk

| File | Risk |
|---|---|
| `backtest_research_run.py` | DB DDL·DML, Backtest, and Analysis |
| `backtest_engine.py` | Daily·Position storage and Commit possible |
| `backtest_run_store.py` | DDL, Insert, Update, and Finalize |
| `backtest_trade_log.py` | Trade Log Insert |
| `analysis_extended.py` | Analysis Delete·Insert |
| `run_extended_analysis.py` | DB connection and Extended Analysis execution |
| `backtest_report_run.py` | DB Read and Local TXT generation |
| `report_*.py` | DB Read or Local File write |
| AWS Batch Wrapper | Secret mapping, Report, and S3 upload |
| `block_watch_analysis_run.py` | DB Update possible |
| Exception Buy family | DB connection and Backtest-like execution |
| Loader | DB Read |
| Adapter·Formatter·Metrics | No direct DB write, but affects the result contract |

### 12.2 Targets Not Run During Documentation Work

| Target | Reason |
|---|---|
| Backtest Entrypoint | May change the Run and result Tables |
| Engine·Store functions | DDL·DML and Commit possible |
| Analysis Entrypoint | Delete·Insert possible |
| Report Entrypoint | DB Read and Local File generation |
| AWS Batch Wrapper | Secret, File, and S3 impact |
| Block·Watch research | DB Update or Simulation possible |
| Container Command Override | Actual Research execution possible |
| AWS Batch·ECS | Leads to external operational execution |

## 13. AWS and Operational Location

| Item | Value |
|---|---|
| Paper Daily Step 4 | `backtest_research_run.py` |
| Paper Daily Step 5 | `backtest_report_run.py` |
| Orchestration | Scheduler and Step Functions responsibility |
| Report Wrapper | Usable in the AWS Batch environment |
| Container default CMD | Compile check |
| Actual execution | Job·Task Command Override |
| Repository evidence | Dockerfile, Wrapper, and Python Entrypoint |
| External operational facts | Queue, Definition, Schedule, and State Machine managed in documentation |

Do not confuse the structure confirmed by Repository files with the current actual AWS state.

## 14. Documentation Files

| File | Role |
|---|---|
| `AGENTS.md` | Work scope, safety, data contracts, and completion criteria |
| `README.md` | Research structure, flow, configuration, and operational AS-IS |
| `CHANGELOG.md` | Functional·structural·documentation change history |
| `docs/source-file-catalog.md` | File responsibilities, input/output, and change impact |

### Per-Document Update Criteria

| Document | Update Condition |
|---|---|
| `AGENTS.md` | Work rules, safety criteria, and required contracts change |
| `README.md` | Responsibilities, flow, configuration, Entrypoints, and operational location change |
| `CHANGELOG.md` | Actual features, structure, or documentation criteria change |
| `docs/source-file-catalog.md` | Files, responsibilities, input/output, and execution risk change |

Do not create date-specific `docs/worklog/*.md` files.
Past creation facts are preserved only as historical entries in the CHANGELOG.

## 15. Cleanup Candidates

| File | Current Judgment |
|---|---|
| Block Watch family | Preserved as research·validation files |
| Exception Buy family | Preserved as research·on-hold files |
| Report modules | Kept as operational Report generation components |
| Other Tracked Source | No confirmed deletion targets currently |

Do not delete files before meeting the following conditions.

| Confirmation | Criterion |
|---|---|
| Import | Not referenced by any other file |
| Entrypoint | Not called by Local, Docker, Batch, or ECS Command |
| DB contract | Not used in operational validation or manual Research |
| Output | Not required for Report or Analysis generation |
| Documentation | Responsibility organized in the README, CHANGELOG, and Catalog |
| Approval | The user's explicit deletion request |

## 16. Catalog Update Conditions

When the following changes occur, update this document in the same task.

| Change | Reflected Content |
|---|---|
| File addition | Add role, input, output, and risk |
| File deletion | Confirm reference removal and deletion history |
| File move | Fix path and Import·Entrypoint impact |
| Entrypoint change | Reflect Step 4·5 and execution risk |
| Loader change | Fix input Table, Date, and Join contract |
| Store change | Fix Output Table, Key, and Transaction |
| Adapter change | Fix Common function and Mapping |
| Analysis change | Fix Table, Run scope, and Delete·Insert |
| Report change | Fix Data Loader, Formatter, and Output File |
| AWS Wrapper change | Fix Secret, Environment, Output, and S3 impact |
| Strategy Profile change | Fix Profile Category, Version, and validation rules |
| Config·Version change | Fix Config Snapshot, Version Identity, and Artifact Identity |
| DevOps change | Fix Buildspec, Workflow, Candidate·Smoke Script, and Publish contract |
| Docker change | Fix Common Wheel Pin, Copy, and Command |
| Dependency change | Fix Runtime Import and install structure |
| Research candidate change | Fix Block·Watch family classification and risk |
| Document system change | Fix AGENTS, README, and CHANGELOG role consistency |

Record only confirmed current responsibilities in the catalog.
Do not add nonexistent files, inferred AWS Resources, or unconfirmed behavior.
