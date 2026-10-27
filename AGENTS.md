# AGENTS.md - port_strategy_research

## 0. Highest-Priority Documentation Readability Rules

All work prioritizes readable results together with accuracy.

| Item | Rule |
|---|---|
| Default table | New standalone summary tables are written with two columns by default. |
| Recommended columns | Prefer `Item / Value`, `File / Role`, `Stage / Responsibility`, `Risk / Impact`. |
| Existing table | When adding a row to an existing table, preserve its existing column structure. |
| Long cell | Put only 1–2 key facts in a cell; if there are 3 or more, split into multiple rows or a detailed document. |
| Length limit | Do not exceed 300 characters per table cell or 500 characters per Markdown line. |
| No repetition | Do not repeat the same explanation at length across the README, CHANGELOG, and source catalog. |
| Fact distinction | Distinguish current implementation, design principles, external operational facts, and unverified assumptions. |
| Verbatim limit | Do not place raw logs, complete SQL, complete DB results, or verbatim secrets and operational identifiers in documentation. |
| Encoding | Save Korean Markdown as UTF-8 without BOM. |

Document roles are separated as follows.

| Document | Role |
|---|---|
| `AGENTS.md` | Kiro work scope, safety, data contracts, and validation rules |
| `README.md` | Current Research structure, flow, configuration, and operational AS-IS |
| `CHANGELOG.md` | Actual functional·structural·documentation change history |
| `docs/source-file-catalog.md` | Operationally important file responsibilities, input/output, and change impact |

## 1. Scope and Priority

- This file is the highest-priority working rule dedicated to `port_strategy_research`.
- When working in this repository, do not use another microservice's `AGENTS.md` as the working basis.
- For Workspace-common safety and work methods, follow the latest rules in `.kiro/AGENTS.md`.
- For Research responsibilities and data contracts, this file's Research-specific rules take precedence.
- The user's latest explicit request is the highest work instruction.
- If `.kiro/AGENTS.md` and this file directly conflict, apply the more restrictive and safer rule.
- Directly modify only the `port_strategy_research` root and its subordinate files.
- Files outside the root are allowed only as read-only reference for contract confirmation.
- If the user specifies a target file, modify only that file.
- A full workspace scan, sub-agent, orchestrator, and new scanner creation are prohibited.
- Keep changes small and verifiable in scope.
- In documentation work requests, do not modify Python, Dockerfile, requirements, or operational wrappers.

## 2. Service Responsibility

This repository is the Research layer that reads preprocessing features together with price and universe data to generate backtests, analysis, and reports.

Research is currently a `Versioned Backtest Platform` that selects and injects a per-Version Strategy Profile into a fixed
Common decision Engine. Common provides the decision functions and the base contract, and
Research selects a per-Version Strategy Profile and injects it explicitly into the entire Backtest Run.
Deploying the Research execution Artifact and promoting Strategy operational performance are separate procedures.

| Area | Research Responsibility |
|---|---|
| Strategy Profile | Per-Version Config selection and explicit Resolved Config injection |
| Backtest | Trading-day-level portfolio simulation |
| Market | Calls the Common market decision through a Research adapter |
| Buy Filter | Calls the Common buy candidate filter through a Research adapter |
| Sizing | Calls the Common position allocation through a Research adapter |
| Buy·Sell | Applies Guard, haircut, and the sell decision to the backtest flow |
| Position | Holding·liquidation·carry-over position processing |
| Persistence | Stores Run, Daily, Daily Position, and Trade Log |
| Analysis | Generates or updates the basic·extended analysis tables |
| Report | Generates Summary, Buy·Sell, Trade Detail, and Recommendation text |
| Research candidates | Studies Block Watch and Exception Buy scenarios |

The scope Research does not own directly is as follows.

| Area | Owning Layer |
|---|---|
| External data collection | Crawler |
| raw preprocessing and total feature generation | Preprocessor |
| Daily BUY and HOLD·SELL·SKIP operational decisions | StrategyDecision |
| Execution Plan and order request composition | StrategyExecution |
| Broker order·fill·balance·holding synchronization | MarketConnector |
| Status query and approval UI | View |
| Full Batch orchestration | Scheduler and Step Functions |
| Image build, ECR push, and infrastructure registration | Deployment pipeline |

Research results are research and validation artifacts. They are not expressed as an operational layer that generates Daily Signal, Execution Plan, or actual orders.

## 3. Core Execution Flow

### 3.1 Backtest Research

| File | Role |
|---|---|
| `backtest_research_run.py` | Full Backtest Run orchestration |
| `backtest_engine.py` | Trading-day-level main loop |
| `backtest_loader.py` | Query Feature, price, and universe |
| `research_backtest_market_adapter.py` | Common market adapter |
| `research_backtest_filter_adapter.py` | Common buy filter adapter |
| `research_backtest_sizing_adapter.py` | Common sizing adapter |
| `backtest_buy_logic.py` | New entry, guard, and haircut processing |
| `backtest_sell_logic.py` | Common sell decision wrapper |
| `backtest_position_manager.py` | Holding, liquidation, and carry-over processing |
| `backtest_trade_log.py` | Completed trade storage |
| `backtest_run_store.py` | Run, Daily, and Daily Position storage |
| `backtest_metrics.py` | Performance calculation such as MDD and Sharpe |

### 3.2 Analysis

| File | Role |
|---|---|
| `backtest_analysis_basic.py` | Basic analysis row generation·storage |
| `analysis_extended.py` | Run-based extended analysis table regeneration |
| `run_extended_analysis.py` | Extended analysis execution entrypoint |

### 3.3 Report

| File | Role |
|---|---|
| `backtest_report_run.py` | Full report generation orchestration |
| `report_data_loader.py` | Query stored Run·Daily·Position·Trade·Analysis |
| `report_formatter.py` | Format Label, ratios, inputs, and reasons |
| `report_summary.py` | Summary report |
| `report_buy_sell.py` | Per-date Buy·Sell report |
| `report_trade_detail.py` | Trade detail report |
| `report_recommendation.py` | Recommendation·diagnostics report |
| `aws_batch_backtest_report_wrapper.py` | AWS Batch environment variable mapping, report execution, and optional S3 upload |

### 3.4 Block·Watch·Exception Buy Research

| File | Handling Principle |
|---|---|
| `block_watch_analysis_run.py` | Research entrypoint that may analyze·update Watch candidates |
| `block_watch_backtest_run.py` | BLOCK Watch backtest candidate |
| `block_exception_buy_engine_run.py` | Exception Buy research engine candidate |
| `block_exception_buy_backtest_run.py` | Exception Buy backtest candidate |

The files above are treated as research·on-hold, not a formal stage of the daily operational pipeline. They are not confirmed as operational features before evidence of actual imports, DB writes, and calls is confirmed.

## 4. Relationship with Common and Decision

Research calls `port_strategy_common` directly through internal adapters.

| Area | Research Call |
|---|---|
| Market | `common_decide_market` |
| Buy Filter | `common_filter_buy_candidates` |
| Sizing | `common_allocate_positions` |
| Buy Guard | Common buy guard |
| Haircut | Common backtest buy size haircut |
| Sell | `common_evaluate_backtest_sell` |
| Metrics settings | Risk-free rate and annual trading days settings |

- `port_strategy_decision` is not a runtime import target of Research.
- Research and StrategyDecision are separate consumers sharing the same `port_strategy_common` contract.
- Decision is not a Research Runtime dependency but a separate consumer of the same Common contract.
- Do not merge the Research adapter with the Decision adapter into the same file or the same runtime dependency.
- Do not change Common function names, import paths, dataclass fields, enums, config keys, or reason strings without an explicit request.
- A Common mapping change can affect the compatibility of Research results and Daily Decision, so treat it as a functional change.

### 4.1 Common Wheel Version Pin and Runtime Version Validation

- The Research Image does not copy the Common Source Directory directly; it pins and installs `port_strategy_common` Wheel `1.0.0`.
- The actually installed Distribution Version is used as the Runtime Version Source.
- Block execution if the Profile-declared Common Package Version differs from the actually installed Version.
- The Common Strategy Version must also match between the Runtime value and the Profile-declared value.
- Do not confuse the responsibilities of the Common Package and the Research Source.

## 4A. Versioned Backtest Platform Contract

### 4A.1 Strategy Profile Schema

- Strategy Profiles are managed in `strategy_profiles/`, and `strategy_config_version` is the Profile Identity.
- The Profile filename must match the declared Version.
- Allow only required Categories, required Metadata Keys, and permitted Config Keys.
- Block Unknown Keys, Type errors, and missing Keys in a Category·Metadata.
- Merge Common Default and Profile Override into a complete Resolved Config.
- Block a nonexistent Version before the DB connection and Run creation.
- The Profile Status and the operational Promotion state are not the same thing.

### 4A.2 Explicit Resolved Config Injection

- Load the selected Profile to generate a Resolved Config and inject it explicitly into the entire execution path.
- Pass the actual Config into the Market, Filter, Sizing, Buy Guard, Buy Haircut, and Sell flows.
- The Engine and Adapters do not depend on Module Global Config or hidden defaults.
- The BUY Guard uses the actual Resolved `buy_guard` Config. Do not create an empty wiring such as `config={}`.
- Use only the CLI syntax that actually exists in the Source (e.g., `--strategy-config-version`).

### 4A.3 Config Snapshot·Hash Canonical Source

- Generate Canonical JSON and a SHA-256 Config Hash from the full Resolved Config that merges Common Default with Profile Override.
- Store the Strategy Config Version, Config Snapshot, and Flatten Config KV on the Run.
- The Trade Log references the same Snapshot by Run ID and Config Identity.
- The actual execution Config, not a Global Common Config Snapshot, is the Canonical Source.
- Secrets are not included in the Config Snapshot or the Hash input.

### 4A.4 Version Identity Separation

- Manage Common Package Version, Common Strategy Version, Research Engine Version, Strategy Config Version,
  Metrics Config Version, Run Identity, Source SHA, and Image Digest separately.
- Strategy Config Version and Research Engine Version are not the same value.
- Common Package Version and Common Strategy Version are also different values.
- Metrics Config Version is recorded separately from the Strategy Config Identity.
- Store the above Identities per Run to ensure reproducibility.
- Use only constant names and storage fields confirmed in the Source and SQL.

### 4A.5 Run Mode Separation

- Distinguish the `BACKTEST` and `CANDIDATE` Run Modes.
- Separate the query basis for operational Run and Candidate Run by Run Mode and Identity.
- Do not automatically connect Candidate execution to the operational Scheduler.
- Candidate is not automatically promoted.
- A failed Candidate Run also stores the failure status and Artifact Identity.
- A Candidate is a validation path for the deployment Artifact and execution contract, not an automatic approver of strategy performance.
- Do not confuse Strategy performance judgment with DevOps Artifact promotion.

### 4A.6 Artifact Identity and Input Snapshot Separation

- Artifact Identity consists of Source SHA, Image Digest, and Artifact Identity Status.
- Both Candidate·operational Runs use the same Artifact Identity structure and Digest-pinned Image.
- Input Snapshot consists of the execution input range, Manifest, Input Snapshot Hash, and Snapshot Status.
- Do not describe Config Identity and Input Data Identity as the same thing.
- Even for the same period, the Input Snapshot Hash may differ if source data is updated.

### 4A.7 Reproducibility Comparison Targets and Exclusions

- In reproducibility comparison, confirm an exact match for Config and Artifact Identity, Backtest results, and Trade Log.
- Distinguish the Input Snapshot Manifest (match) from the Input Snapshot Hash (may change due to source data updates).
- Exclude Run ID and creation·start·end timestamps from comparison.
- Do not incorrectly record that "an exactly identical Input Snapshot Hash was validated."

### 4A.8 Strategy Config Version and Challenger Separation

- Treat `strategy_config_version` as the Strategy Logic Release Identity.
- A new Strategy Logic experiment does not directly overwrite the existing Baseline Profile.
- Split the Challenger into a new `RSCFG` Version and keep the existing Version as a separate Config Identity.
- Currently `RSCFG-0001` is the Baseline (`status=BASELINE`) and `RSCFG-0002` is the Challenger (`status=CANDIDATE`).
- The Profile Status `CANDIDATE` does not mean the operational Champion.
- Per-Version Research results can each be queried, and performance comparison and Champion selection are judged by the Research owner.
- View is the Interface for Version query and Champion·Challenger selection and does not automatically judge which strategy is superior.
- A Research change does not arbitrarily change the `port_strategy_common` or StrategyDecision contract.

## 5. Input Data Contract

| Input | Role |
|---|---|
| `pre_total_market_daily_feature` | Market decision input |
| `pre_total_stock_daily_feature` | Stock Filter·Sizing and Sell decision input |
| `interest_price_raw` | Price, return, and fill assumption input |
| `stock_universe` | Backtest target universe |
| Config Snapshot | Reproduces the strategy and decision criteria |
| Run Input | Period, initial capital, and execution options |

Input-related rules:

- Do not conflate the relationship among the trading day, feature reference date, and next-trading-day price.
- Do not use a future price or future feature in the current decision.
- Confirm duplicate rows and cardinality for the same ticker·trade date combination.
- Distinguish a missing feature from an actual 0 value.
- Do not arbitrarily treat `NULL`, `0`, negatives, empty strings, and not-collected states as the same value.
- Do not infer price adjustment, trading halt, and universe active conditions without a basis in code.
- Document input tables and columns only after confirming the loader SQL directly.

## 6. Backtest Execution Contract

- Do not arbitrarily change the existing-position processing and new-buy order.
- Confirm the calculation order of same-day return, cumulative return, and portfolio valuation.
- Distinguish the buy·sell price basis and whether the next-trading-day price is used.
- Changing the sorting, tie handling, and max holding count of simultaneous buy candidates can change the results.
- Preserve the priority of Guard, haircut, stop, holding period, and sell reason.
- Do not conclude that trading cost, slippage, and tax are included without confirming they are implemented.
- Do not mark a Run successful after a partial-date store.
- If the Backtest fails, ensure the analysis and report do not proceed as if they were normal results.
- On re-running the same input, distinguish whether a new Run is created or an existing Run is updated.
- To reproduce results, preserve the strategy name, engine version, config, and input snapshot contract.

## 7. Output and Storage Contract

| Output | Meaning |
|---|---|
| `strategy_backtest_run` | Backtest execution metadata and status |
| `strategy_backtest_daily` | Per-trading-day performance and portfolio results |
| `strategy_backtest_daily_position` | Per-trading-day held position snapshot |
| `strategy_trade_log` | Completed trade detail |
| `strategy_backtest_*_analysis` | Run-based basic·extended analysis |
| Report TXT | Human-readable reports based on the stored Run |

Do not change the following contracts without an explicit request.

- schema, table, and column names
- run id and foreign references
- unique key and conflict target
- insert, update, delete, and upsert scope
- run status and analysis status
- trade reason and metadata structure
- strategy, engine, and evaluator version
- config, threshold, and input snapshot format
- report filename, section, and meaning

Storage handling principles:

- Do not infer whether DDL runs from the function name; confirm the actual SQL.
- For delete-then-insert analysis, always confirm the run id delete scope.
- Confirm the commit and rollback locations.
- Confirm whether the Daily row and Daily Position snapshot are stored in the same transaction.
- Confirm how a Trade Log insert failure is reflected in the overall Run status.
- Do not overwrite with a success status after catching a failure.
- Do not record a state where only some analysis tables were updated as an overall analysis completion.

## 8. Analysis Rules

- Do not treat Basic and Extended Analysis as the same execution.
- Confirm the analysis input against the stored Run, Daily, Position, and Trade Log.
- Confirm in code whether the latest Run is auto-selected without a Run id.
- Do not expand the analysis table delete·regenerate scope to other Runs.
- Do not arbitrarily change the meaning of Threshold, intervals, Bucket, and Label.
- Distinguish a Run with 0 trades from missing analysis input.
- Confirm handling of empty DataFrame, `NULL`, infinity, and zero denominators.
- Inspect the transaction boundary for whether existing rows may remain deleted after an analysis failure.
- Do not express analysis results as actual operational performance or a guarantee of future performance.

## 9. Report Rules

- Report is the presentation layer that reads stored Backtest results and generates text files.
- Distinguish the roles of Summary, Buy·Sell, Trade Detail, and Recommendation.
- Treat the Report Formatter's label, percentage, and reason mapping as a common contract.
- Distinguish latest-Run auto-selection from specified-Run-id execution.
- Confirm the output directory default and override against the actual code.
- Confirm whether the same filename is overwritten and whether existing files are deleted.
- Do not include sensitive information, DB connection values, secrets, or AWS identifiers in a report.
- Recommendation is a research diagnostic and is not expressed as actual investment advice or an order instruction.
- Distinguish Report generation success from S3 upload success as separate states.

## 10. AWS Batch and S3 Rules

`aws_batch_backtest_report_wrapper.py` is treated as a wrapper with operational impact.

| Item | Confirmation Criterion |
|---|---|
| Secret input | `RESEARCH_APP_SECRET_JSON` mapping |
| DB environment variables | Converted to `INTEREST_DB_*` |
| Output path | `REPORT_OUTPUT_DIR` |
| S3 condition | Whether `REPORT_S3_BUCKET` is set |
| Prefix | Combination of `REPORT_S3_PREFIX` with date·Job ID |
| Execution | `runpy.run_module` target |
| Upload | Confirm whether only generated report files are targeted |

- Do not output the actual secret JSON value or record it in documentation.
- Do not leave verbatim Secret ARN, Job Definition ARN, Queue ARN, Bucket, Prefix, and Job ID.
- The S3 upload is a separate external write from Report generation.
- Do not treat a partial file upload failure as a full success.
- The repository's wrapper is not evidence of a completed AWS Batch deployment.
- Do not run AWS CLI, SDK, Batch, ECS, Step Functions, or S3 work without explicit approval.

## 10A. Research CI·Candidate·Operational Promotion Rules

### 10A.1 Build Role and Runtime Role Permission Separation

- GitHub Actions handles only OIDC authentication and CodeBuild execution·status check.
- CodeBuild handles Compile, Test, Config·Version Contract, Container Build, Smoke, and conditional Publish.
- Limit the CodeBuild Role to the Build, Logs, and Research ECR scope.
- Limit the GitHub OIDC Role to the Research CodeBuild start·query scope.
- Do not include Batch, Step Functions, and DB permissions in the Build Role.

### 10A.2 Deployment Path and Image Contract

- `main` Push is a Build/Test validation path. Do not express `main` Push as always automatically running the Candidate.
- Depending on whether Strategy Logic changed, the Candidate or Operating Release path may be split.
- Candidate and Operating are separate deployment paths.
- Candidate is not an automatic Champion Promotion.
- Block ECR Push on a Build failure.
- Use Git SHA-based Image Tag and Digest as evidence and do not create a Mutable `latest` dependency.
- Both operational·Candidate use a Digest-pinned Image.
- OIDC Trust, detailed GitHub Actions branching, IAM Policy, and AWS deployment procedures are the responsibility of the `port-devops` document and are not duplicated in this file.

### 10A.3 Candidate and Operating Path Separation

- Separate the Candidate Job Definition Family from the operational Job Definition Family.
- The Candidate Revision uses a Digest Image and Source SHA·Image Digest environment variables.
- The Candidate runs with `--run-mode CANDIDATE`, the selected `--strategy-config-version`, and `--require-artifact-identity`.
- The Candidate Release path validates the Challenger `RSCFG` Version on the `-candidate` Family.
- The Operating Release path replaces only the validated Artifact while preserving the Strategy Config Version.
- Align the Candidate Runtime to Fargate VCPU 1, Memory 4096 MiB.
- Candidate validation includes confirming Job Status, Container Exit Code, and the storage contract.
- Candidate execution does not change the operational Step Functions or Scheduler.
- Candidate success means Challenger validation is complete and is not an automatic Champion Promotion.
- Do not configure automatic Candidate promotion.

### 10A.3.1 DevOps Automation Scope and Champion Responsibility

- The DevOps automation scope is up to Candidate generation·execution·validation and Challenger confirmation.
- After Candidate success, do not automatically change the Operating Job Definition, Step Functions reference, or Champion.
- Comparing multiple Challenger results and deciding Champion selection is the responsibility of the Research owner.
- View is the Interface for Challenger·Champion status query and selection·switching and does not judge the strategy.
- Separate Strategy performance judgment from Artifact deployment validation.
- The internal implementation details of Champion switching are not finalized or expanded in this document.

### 10A.4 Operational Promotion·Rollback and Resource Validation

- Operational promotion distinguishes Revision registration from the operational State Machine Champion Pointer change.
- For a long-running Backtest, do not judge that operational Resources are sufficient based on Candidate success alone.
- Perform standalone Step 4 validation with the actual operational period and input scale.
- Distinguish Exit Code 137 and OOM from an application logic failure.
- Identify Timeout and Memory failures separately.
- Register an AWS Resource change as a new Job Definition Revision.
- After a Resource change, run standalone before promoting the operational Pointer.
- On failure, immediately Rollback to the previous ACTIVE Champion Revision.
- Do not record verbatim ARN, Account ID, Job ID, and Digest in documentation; use only Family·Revision·status.

## 11. Database Rules

- Confirm the DB configuration based on the actual implementation of `db_config.py`.
- Do not assume environment variable names, defaults, and required values.
- Do not create a new default for the password.
- Changing the `search_path` order affects unqualified SQL resolution, so treat it as a contract change.
- Confirm the target schema of schema-qualified SQL and search-path-based SQL.
- Do not assume columns, unique keys, and conflict targets without a basis in SQL or DDL.
- Even in read-only work, confirm whether a DB connection occurs on import.
- Before a DB write change, confirm the DDL, insert, update, delete, upsert, and transaction scope.
- When only a static check without an actual DB connection was performed, do not express it as completed data-consistency validation.

## 12. Execution and Operational Safety

Unless the user specifies otherwise, the following work is prohibited.

| Prohibited Work | Reason |
|---|---|
| Running `backtest_research_run.py` | May change Run, Daily, Position, Trade, and Analysis |
| Running `backtest_engine.py` | Per-trading-day store and commit possible |
| Running `backtest_run_store.py` functions | DDL·DML and status change possible |
| Running `backtest_trade_log.py` | Trade Log insert possible |
| Running Analysis entrypoints | Analysis table delete·insert possible |
| Running Report entrypoints | DB query and local file generation possible |
| Running the AWS Batch wrapper | Secret mapping, Report, and S3 upload possible |
| Running Block·Watch research | DB update or backtest-like processing possible |
| Actual DB DDL·DML | Operational·research data change |
| External API·S3 calls | External system and storage change |
| Running AWS CLI·SDK | Impact on Batch, ECS, Step Functions, and operational resources |
| Running Crawler·Preprocessor | Upstream data change |
| Running Daily Decision·Execution | Impact on operational Signal and order candidates |
| Broker order·cancel | Actual order impact |
| Slack send | Risk of misdelivered operational notifications |

For documentation work, do not even perform a Python module import before confirming there is no import-time DB·file·AWS action.

## 13. Code Modification Rules

- Do not modify Python, Dockerfile, requirements, or wrappers without the user's explicit request.
- Preserve existing function signatures, CLI options, and module entrypoints.
- Do not break the `python -m port_strategy_research.<module>` execution structure.
- Avoid large-scale string replacement of the original Python files; make localized changes.
- Do not revert user changes.
- Do not assume test, debug, output, and report dump files are operational sources.
- Even if a file appears unused, confirm evidence of import, Docker CMD, Batch wrapper, and external command.
- Do not delete files without an explicit approval.
- Do not create a flow that unconditionally outputs SUCCESS after a failure.
- After a code change, do not perform validation that requires operational execution; leave it as a limitation.

## 14. Testing and Validation

If tests exist, prioritize unit validation that isolates the DB, filesystem, and AWS.

| Area | Priority Validation |
|---|---|
| Loader | Period, trading day, reference date, missing, and join cardinality |
| Adapter | Common input·output mapping and reason |
| Buy | Guard, haircut, sizing, and candidate order |
| Sell | Stop, hold period, and Common sell mapping |
| Position | Liquidation, carry-over, and same-day return |
| Run Store | Run status, unique key, rollback, and re-run |
| Trade Log | Completed trade fields and metadata |
| Metrics | Empty values, zero denominators, MDD and Sharpe boundaries |
| Analysis | Run scope, delete·insert, and empty trades |
| Report | Run selection, section, file path, and overwrite |
| AWS Wrapper | Environment variable mapping, module call, and S3 mock |

Validation principles:

- For tests that require the DB, replace the connection and cursor with a mock or fixture.
- Use a temporary directory for file generation.
- Mock boto3 and S3.
- Do not use the actual operational DB, secrets, bucket, or AWS resources.
- First confirm whether a test import performs a DB, file generation, or external call.
- Do not record a test that could not be run as passed.
- When only documentation is modified, validate only the document format and change scope.

## 15. Docker and Dependency Rules

- Confirm the `Dockerfile` base image, copy paths, work directory, and CMD against the actual file.
- Distinguish whether the default CMD is a compile check or an actual Research run.
- Separate the actual Backtest·Report command override from the external Batch or ECS configuration.
- Maintain that `port_strategy_common` is a pinned Wheel `1.0.0` install structure, not Source vendoring.
- Do not confuse a Common Source Directory copy with a Wheel Package install.
- The requirements pinned versions are managed in the file itself.
- Confirm whether code imports and requirements match, but do not modify them arbitrarily in documentation work.
- The presence of a Dockerfile is not evidence of a completed image build, push, and deployment.

## 16. Security and Sensitive Information

- Do not output or document passwords, tokens, API keys, accounts, webhook URLs, or DB connection information.
- For Secret JSON and environment variable values, confirm only the key name and do not quote the value.
- For discovered sensitive information, report only its existence and location, not the value itself.
- For examples, use `[REDACTED]` or an obvious placeholder.
- Do not record the full value of AWS Batch Job ID, ARN, image URI, bucket, prefix, and command id.
- If a report or dump contains per-stock trades, holdings, or account information, summarize only the minimum necessary facts.

## 17. Documentation Update Rules

### 17.1 README.md

Update only the necessary parts when the following change.

- Research responsibilities and boundaries with other MS
- Backtest, Analysis, and Report execution flow
- Input·output table contracts
- Common and Research adapter structure
- Block·Watch·Exception Buy classification
- DB configuration and search path
- Docker CMD, AWS Batch wrapper, and S3 path
- External dependencies or execution risk

### 17.2 CHANGELOG.md

- Record only actual changes by date.
- Distinguish documentation restructuring from Python functional changes.
- Preserve past worklog-creation and file-cleanup records as facts at the time.
- Do not record Backtest, DB, Report, or AWS validation that was not executed as complete.
- Do not record one-time Run ID, Job ID, paths, and execution logs.

### 17.3 docs/source-file-catalog.md

When the following changes are confirmed, update the related rows or sections together.

| Change | Update Content |
|---|---|
| File creation·deletion·rename | File list and responsibilities |
| Entrypoint change | Execution flow and risk |
| Loader·Store responsibility change | Input·output and DB impact |
| Common adapter change | Functions, mapping, and independence |
| Analysis change | Input, table, and regeneration scope |
| Report change | Data loader, formatter, and output files |
| AWS wrapper change | Secret, output, and S3 impact |
| Docker·dependency change | Runtime and execution structure |
| Research candidate status change | Block·Watch family classification and risk |
| Document creation·deletion | Documents list and roles |

If only the internal implementation changes and the file responsibility and change impact are the same, do not modify the catalog.
The catalog is maintained as a responsibility document for operationally and maintenance-important items, not a full inventory.

### 17.4 Worklog

- Do not create `docs/worklog` and date-specific worklogs anew.
- Past worklog-creation history remaining in the CHANGELOG is a fact at the time and is not deleted.
- Leave only the necessary key changes for the current work history in the CHANGELOG.

## 18. Documentation Consistency

The four documents must use the same terminology and responsibility boundaries.

| Term | Basis |
|---|---|
| Service name | `port_strategy_research` |
| Layer name | Research |
| Platform nature | Versioned Backtest Platform |
| Upstream | Preprocessor |
| Operational decision | StrategyDecision |
| Downstream execution | StrategyExecution |
| Core execution | Backtest Research |
| Strategy configuration | Strategy Profile and Strategy Config Version |
| Execution Config | Resolved Config, Config Snapshot, and Config Hash |
| Version | Common Package·Common Strategy·Research Engine·Metrics Config Version |
| Execution distinction | Run Mode (`BACKTEST`, `CANDIDATE`) |
| Reproducibility | Artifact Identity and Input Snapshot |
| Strategy Version | `RSCFG-0001` Baseline, `RSCFG-0002` Challenger |
| Deployment path | `main` Push Build/Test, Candidate·Operating split depending on Strategy Logic change |
| Champion responsibility | Research owner selection judgment, View query·selection Interface |
| Promotion | Candidate·Operating separate paths and past manual Promotion·Rollback history |
| DevOps detail | IAM·AWS deployment procedures are the responsibility of the `port-devops` document |
| Analysis | Basic Analysis and Extended Analysis |
| Report | Summary, Buy·Sell, Trade Detail, and Recommendation |
| Common contract | `port_strategy_common` Wheel `1.0.0` |
| Adapter | Research internal adapter |
| Storage unit | Run ID |
| Date basis | Trade Date |
| AWS execution | Step 4 Research and Step 5 Report |
| External operations | Separate Batch, ECS, and Step Functions from repository facts |

Do not add tables, columns, states, algorithms, or AWS resources not confirmed in code for documentation convenience.

## 19. Git Rules

- Preserve user changes before and after work.
- Use `git status --short` and `git diff --stat` only to confirm the change scope.
- Where possible, confirm whitespace errors with `git diff --check`.
- Do not run `git add`, `commit`, `push`, `reset`, `restore`, or `checkout` without an explicit request.
- For attached-file work without a repository, do not report as if Git validation was performed.

## 20. Completion Conditions

Confirm the following before completing work.

- Were only the target files modified?
- Were the Research responsibilities and boundaries with other MS preserved?
- Was it not incorrectly expressed as a `port_strategy_decision` runtime dependency?
- Were the Common and Research adapter contracts preserved?
- Were the Backtest input and storage table contracts preserved?
- Were the meanings of Run, Daily, Position, Trade, and Analysis not confused?
- Were Basic and Extended Analysis distinguished?
- Were Report generation and S3 upload distinguished?
- Were the Block·Watch research files not asserted to be an operational pipeline?
- Were the DB DDL·DML, file generation, and re-run risks confirmed?
- Was it confirmed whether the source catalog update conditions apply?
- Was no new worklog created?
- Was no verbatim sensitive information or operational identifier newly recorded?
- Are the document roles and terminology consistent across the four documents?
- Were UTF-8 No BOM, the 300-character cell, and the 500-character line standards met?
- Was validation that was not executed not reported as successful?

## 21. Completion Report

Write the completion report concisely, centered on two-column tables.

| Item | Report Content |
|---|---|
| Changed files | Actually modified files |
| Change summary | Key changes to responsibilities, contracts, and document structure |
| Validation result | Static checks and safe validation performed |
| Not performed | Unexecuted items related to Backtest, DB, Report, AWS, S3, and orders |
| Remaining risk | Items requiring code comparison or operational confirmation |
| Sensitive information | Whether verbatim was newly recorded |

Actual Research or operational execution beyond documentation changes is performed only when the user explicitly requests and approves it.
