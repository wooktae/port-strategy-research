# CHANGELOG

Records the change history of `port_strategy_research` features, data contracts, execution structure, and documentation criteria.

- Place the latest change at the top.
- Distinguish functional changes from documentation cleanup.
- Do not record sensitive information or one-time operational values.
- Do not create date-specific worklogs anew; leave major changes in this document.

## 2026-08-24

### Research Strategy Version and Champion–Challenger Path Enhancement

This change places the Strategy Config Version as the Strategy Logic Release Identity and reflects a
Challenger Version that does not overwrite the Baseline, plus the split of the Candidate·Operating deployment paths.
This work is documentation cleanup of 4 documents; code·AWS·DB·Backtest were not executed.

#### Functional·Structural AS-IS

| Item | Value |
|---|---|
| Challenger addition | Added the `RSCFG-0002` Challenger Profile (`status=CANDIDATE`) |
| Value difference | `market.aggressive_max_positions` `4` → `6` (RSCFG-0001 preserved) |
| Baseline preservation | Split into a separate Version without overwriting the `RSCFG-0001` Baseline |
| Candidate execution | `RSCFG-0002` Candidate execution succeeded (operator-validated fact) |
| Candidate storage | The Candidate Run is stored in `strategy_backtest_run` |
| Version query | Per-Version results for `RSCFG-0001`·`RSCFG-0002` can be queried |

#### Deployment Path AS-IS

| Item | Value |
|---|---|
| `main` Push | Build/Test validation path (not automatic Candidate execution) |
| Path split | Split into Candidate or Operating Release depending on whether Strategy Logic changed |
| Candidate·Operating | Separate deployment paths |
| Champion Promotion | Candidate success is not an automatic Champion Promotion |
| Champion judgment | Research owner judgment; View is the query·selection Interface |

#### Documentation Boundary

| Item | Value |
|---|---|
| Past-expression correction | Corrected the "main Push → automatic Candidate execution" wording to the current AS-IS |
| Past history preservation | Revision 5·6·7 promotion·Rollback kept as past manual-validation history |
| DevOps detail | IAM·AWS CLI·Job Definition·Step Functions procedures are the responsibility of `port-devops` |
| Change scope | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| One-time identifiers | Full SHA, Digest, ARN, Job ID, and GitHub Run ID are not recorded |

## 2026-08-12

### Research main Push Candidate Automation Complete

This is a DevOps AS-IS change that automated up to ECR Publish and Candidate validation in the `main` Push-based CI.
It is a documentation-criteria change; code·AWS·DB were not executed in this work.

#### DevOps AS-IS

| Item | Change Content |
|---|---|
| main Push CI | Automatic Research CodeBuild execution via GitHub Actions·OIDC |
| ECR Publish | Automatic Git SHA-based Image Publish and Image Digest Artifact confirmation |
| Candidate registration | Automatic registration of a new Candidate Job Definition Revision |
| Candidate execution | Automatic AWS Batch Candidate execution and Artifact Identity validation |
| Candidate validation | Confirm Batch SUCCEEDED and Container Exit Code 0 |
| Automation scope confirmed | Confirmed the DevOps automation completion scope as up to Challenger validation |

#### Candidate Runtime

| Item | Value |
|---|---|
| Candidate Revision 4 | VCPU 1, Memory 2048 MiB, Exit Code 137 Fargate OOM |
| Candidate Memory alignment | Aligned to 4096 MiB |
| Candidate Revision 5 | VCPU 1, Memory 4096 MiB, full-period execution succeeded |

#### Operational Boundary

| Item | Value |
|---|---|
| Operating Job Definition change | None |
| Step Functions change | None |
| Automatic Champion Promotion | Not performed |
| Champion selection judgment | Research owner responsibility |
| Champion selection·switching Interface | View operational UI |

#### Work Scope

| Item | Value |
|---|---|
| This document change scope | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| Code·config change | None in this documentation work |
| Backtest·DB·AWS·S3 execution | None in this documentation work |
| One-time identifiers | Full SHA, Digest, ARN, Job ID, and GitHub Run ID are not recorded |
| Past history | 2026-08-05~06 manual Candidate·Promotion·Rollback validation kept as history at the time |

## 2026-08-06

### 2026-08-05~2026-08-06 Research Versioned Backtest Platform and DevOps Adoption

This is a change set that converts Research from a fixed-Config runner to a Versioned Backtest Platform and
adopts a Research-specific CI·Container·Candidate·operational-promotion structure.

#### Features

| Item | Change Content |
|---|---|
| Common Wheel Pin | Removed the Common Source Copy and switched to a pinned `port_strategy_common` Wheel `1.0.0` install |
| Config CLI | Added execution options such as `--strategy-config-version` (default `RSCFG-0001`) and `--run-mode` |
| Explicit Config injection | Explicit Resolved Config passing to Engine·Adapter·Buy·Sell·Position |
| BUY Guard fix | Fixed the BUY Guard `config={}` wiring to pass the actual Resolved `buy_guard` Config |
| Config Snapshot·Hash | Generate Resolved Config Canonical JSON and a SHA-256 Config Hash |

#### Structure

| Item | Change Content |
|---|---|
| Strategy Profile | Introduced `strategy_profiles/` and the `RSCFG-0001` Baseline Profile |
| Schema validation | Added validation for required Category·Metadata, permitted Keys, and Unknown Key blocking |
| Version Identity separation | Separated Common Package·Common Strategy·Research Engine·Strategy Config·Metrics Config Version |
| Run·Trade Config Persistence | Store Config Snapshot once per Run; the Trade Log references Run ID·Config Identity |
| Artifact Identity | Added Source SHA·Image Digest·Status storage and format validation |
| Input Snapshot | Added an input Manifest·Hash·Status storage structure |
| Run Mode separation | Distinguished the `BACKTEST` and `CANDIDATE` Run Modes |

#### DevOps

| Item | Change Content |
|---|---|
| GitHub Actions·OIDC | Added a Workflow that starts·checks Research CodeBuild with OIDC authentication |
| CodeBuild | Runs Compile, Contract Test, Config·Version validation, Docker Build, and Smoke |
| Build-only and Publish | Split Build-only default from conditional ECR Publish; block Push on failure |
| Image Identity | Git SHA-based Image Tag and Digest evidence; removed the Mutable `latest` dependency |
| Candidate Job Definition | Static contract validation of the `-candidate` Family, separated from the operational Family |
| OIDC Trust fix | Confirmed the initial Workflow's `AssumeRoleWithWebIdentity` failure cause as an actual Subject mismatch and fixed it |

#### Validation

| Item | Result |
|---|---|
| OIDC initial failure | The initial Workflow failed at the OIDC step; CodeBuild did not start and no ECR Push occurred |
| OIDC resolution | After restricting the Trust Policy to the Repository and `main` Branch based on the actual Token Subject, Build-only succeeded, and the subsequent Image Publish Workflow succeeded |
| Candidate execution | Manual run with `--run-mode CANDIDATE`·`RSCFG-0001`·`--require-artifact-identity`; confirmed Job Status·Exit Code·CloudWatch Log and storage of Run·Config Hash·Metrics·Input Snapshot |
| Candidate failure contract | Confirmed failure status and Artifact Identity storage in an intentionally failed Candidate run |
| Candidate isolation | Confirmed no change to operational Step Functions·Scheduler and no automatic-promotion configuration |
| Reproducibility – match | Exact match of Config Hash, Config Snapshot·KV, Daily Result·Position, Trade Log, Run Input, and Total Return·MDD·Sharpe·Trade Count for the same Candidate Revision·Digest·Source SHA·`RSCFG-0001` (tolerance `0.000000000001`) |
| Reproducibility – exclusion | Run ID and creation·start·end timestamps excluded from comparison |
| Reproducibility – Input Snapshot | The Manifest matches, but the Input Snapshot Hash may change due to source data updates; not recorded as an exactly identical Hash |
| Operational promotion | Registered Revision 6 with the Candidate Artifact validated on Champion Revision 5, then promoted the operational State Machine Step 4 reference from 5→6; no change to definition·Role·Type other than Step 4 |
| Rollback | Restored the operational State Machine Step 4 reference from 6→5 (Champion Pointer change); confirmed Revision 5 kept ACTIVE |
| Revision 6 OOM | Exit Code 137 Fargate OutOfMemoryError in the VCPU 1·Memory 2048MiB Step 4 standalone run; confirmed as a memory shortage, not a logic·Config error, then rolled back to Revision 5 |
| Revision 7 resolution | Kept the Revision 6 Image·Command·Config·Role·Secret·Environment, expanded Memory to 4096MiB only, and kept VCPU 1 |
| Revision 7 promotion | Standalone validation on a Step 4-dedicated State Machine (Step Functions·AWS Batch success, Exit Code 0), then final promotion of operational Step 4 to Revision 7 |
| Revision 5 Rollback retention | Kept Revision 5 as the Rollback-target ACTIVE Revision; Revision 6 preserved as failure evidence |

#### Operational AS-IS

| Item | Value |
|---|---|
| Operational Champion | Revision 7 |
| Operational Step 4 | Revision 7 |
| Operational Resource | VCPU 1, Memory 4096MiB, Attempt Timeout 600 seconds |
| Previous Rollback Revision | Revision 5 |
| Operational Run Mode | `BACKTEST` |
| Operational Strategy Config Version | `RSCFG-0001` |

#### Work Scope

| Item | Value |
|---|---|
| This document change scope | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| Code·config change | None in this documentation work |
| Backtest·DB·AWS·S3 execution | None in this documentation work |
| One-time identifiers | Full SHA, Digest, ARN, and Job ID are not recorded |

## 2026-07-22

### Research Documentation Criteria Reorganization

| Item | Value |
|---|---|
| Change scope | Documentation cleanup of `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| Functional change | None |
| Code·config change | None |
| DB·AWS·S3 execution | None |
| Backtest·Analysis·Report execution | None |
| Operational data change | None |

### AGENTS.md

| Item | Change Content |
|---|---|
| Highest-priority rules | Placed readability, 2-column tables, long-cell splitting, and duplication-prevention criteria at the front of the document |
| Work scope | Clarified the principle of `port_strategy_research` internal work and other-MS read-only |
| Responsibility boundary | Separated the responsibilities of Research and Crawler, Preprocessor, StrategyDecision, StrategyExecution, MarketConnector, View |
| Backtest | Distinguished the Entrypoint, Engine, Loader, Adapter, Buy·Sell, Position, Store, and Metrics flow |
| Analysis | Separated the input, storage, and regeneration risk of Basic and Extended Analysis |
| Report | Distinguished the responsibilities of Loader, Formatter, Summary, Buy·Sell, Trade Detail, and Recommendation |
| Common relationship | Clarified that Research calls `port_strategy_common` directly through internal adapters |
| Decision relationship | Removed the `port_strategy_decision` runtime dependency expression and clarified it as a separate Common consumer |
| Data contract | Organized the Feature, Price, Universe inputs and the Run, Daily, Position, Trade, Analysis, Report outputs |
| Backtest safety | Added Look-ahead, trading-day·price basis, candidate order, partial success, and reproducibility criteria |
| DB safety | Added DDL·DML, delete·insert, transaction, rollback, and re-run impact criteria |
| AWS Batch | Separately distinguished Secret mapping, Report generation, and S3 upload risk |
| Research candidates | Classified the Block Watch and Exception Buy family as research·on-hold files |
| Document linkage | Specified updating `docs/source-file-catalog.md` together when file responsibilities change |
| Worklog | Changed the current document operation criterion by prohibiting new date-specific worklog creation |

### README.md

| Item | Change Content |
|---|---|
| Document purpose | Restructured to focus on the current Research structure and operational AS-IS rather than work rules |
| Service summary | Placed input, core execution, storage, common logic, entrypoints, and AWS location in the first table |
| End-to-end flow | Organized as Feature → Backtest → storage → Analysis → Report → optional S3 upload |
| Backtest | Separated Engine, Loader, Adapter, Buy, Sell, Position, Store, and Metrics by role |
| Common relationship | Clarified the Research internal adapter and `port_strategy_common` direct-call structure |
| Decision relationship | Organized the runtime-independent, Common-contract-sharing relationship with StrategyDecision in a separate table |
| Input contract | Distinguished Market·Stock Feature, Price Raw, Universe, Config Snapshot, and Run Input |
| Output contract | Distinguished Run, Daily, Daily Position, Trade Log, Analysis, and Report |
| Re-run | Added considerations for Run creation, partial storage, transaction, snapshot, and idempotency |
| Analysis | Separated Basic and Extended Analysis into distinct execution and storage flows |
| Report | Distinguished Run selection, output files, overwrite, and S3 success status |
| Recommendation | Specified that it is a research diagnostic, not actual investment advice |
| Research candidates | Separated Block Watch and Exception Buy from Daily operations |
| AWS location | Organized the Research responsibilities in Paper Daily Step 4 and Step 5 |
| Docker | Distinguished the Compile default CMD from the actual execution command override |
| AWS Batch Wrapper | Organized Secret mapping, output directory, module execution, and S3 upload |
| DB configuration | Organized `INTEREST_DB_*`, the default DB, and the search path explanation centered on tables |
| Calculation safety | Reinforced Look-ahead, duplicate join, fee·tax·slippage, and numeric boundaries |
| Document system | Distinguished the roles of AGENTS, README, CHANGELOG, and source catalog |

### docs/source-file-catalog.md

| Item | Change Content |
|---|---|
| Per-file tables | Restructured centered on flow, input/output, and DB·file·AWS impact |
| Update conditions | Added change criteria for Entrypoint, Loader, Store, Adapter, Analysis, Report, Wrapper, and Docker |
| Code comparison | Confirmed the Entrypoint, Loader, Adapter, Store, Analysis, Report, and Wrapper against the actual source |

### CHANGELOG.md

| Item | Change Content |
|---|---|
| Change scope | Specified this documentation cleanup scope as 4 documents |
| Worklog | Kept non-restoration of deleted date-specific Worklog entries and the prohibition on new creation |

### Document Operation Decisions

| Item | Value |
|---|---|
| New worklog | Not created |
| Past worklog records | Preserved in the CHANGELOG as change facts at the time |
| Detailed file responsibilities | Managed in `docs/source-file-catalog.md` |
| Actual code comparison | Performed separately in the source catalog cleanup and final review step |
| Sensitive information | Verbatim recording prohibited |
| One-time Run·Job values | Excluded from CHANGELOG recording |

## 2026-07-01

### Documenting the AWS Operational Location and Research Responsibility Boundary

| Item | Change Content |
|---|---|
| Responsibility boundary | Distinguished Backtest·Analysis·Report from other-MS responsibilities in the README |
| Step 4 | Organized `backtest_research_run.py` as the Backtest Research entrypoint |
| Step 5 | Organized `backtest_report_run.py` as the Backtest Report entrypoint |
| Container | Added the Dockerfile, requirements, and AWS Batch Report Wrapper roles |
| Wrapper settings | Explained the Report output, Secret JSON, S3 Bucket·Prefix, and Job ID usage path |
| Research candidates | Separated the Block Watch and Exception Buy family from Daily operations |
| Adapter | Reflected the 3 Research internal Market·Filter·Sizing Adapters |
| Source catalog | Added the Adapter and Container·AWS Batch Wrapper file responsibilities |
| Worklog | Created `docs/worklog/2026-07-01.md` per the document operation criteria at the time |

### Structural Corrections

| Item | Change Content |
|---|---|
| Research·Decision relationship | Specified that Research calls `port_strategy_common` directly and does not import Decision at runtime |
| Engine | Updated the explanation to the Research Market·Filter Adapter call path |
| Buy Logic | Updated the explanation to the structure that goes through the Research Sizing Adapter |
| Dependency | Removed the `port_strategy_decision` runtime dependency |
| AWS Dependency | Reflected `boto3` on the S3 upload path |
| PostgreSQL Package | Marked the install basis as `psycopg2-binary` |

### Work Scope

| Item | Value |
|---|---|
| Functional change | None |
| Code·config change | None |
| Actual execution | No Backtest, Analysis, Report, DB, AWS, S3, Slack, or order execution |
| External MS records | Other-MS internals and full orchestration details are not reflected |
| Sensitive information | No verbatim recording of Secret, ARN, URI, Bucket, Command, or DB connection values |

## 2026-05-28

### File Catalog and Explanatory Comment Cleanup

| Item | Change Content |
|---|---|
| Source catalog | Added a document of per-file roles, key responsibilities, and execution considerations |
| Python explanation | Added module-level Korean docstrings |
| Function explanation | Added docstrings, limited to DB storage, analysis, Report, and core Backtest functions |
| Daily Position Snapshot | Documented the `strategy_backtest_daily_position` storage flow |
| Report query | Reflected the switch to per-day Position Snapshot-based queries |
| Worklog | Created `docs/worklog/2026-05-28.md` per the document operation criteria at the time |

### Work Scope

| Item | Value |
|---|---|
| Document·comment change | Yes |
| Functional change | Recorded as none |
| Actual Backtest·DB execution | None |
| Sensitive information | No verbatim recording |

## 2026-05-27

### DB Configuration and Schema Structure Cleanup

| Item | Change Content |
|---|---|
| DB configuration | Externalized connection settings via `get_db_config()` in `db_config.py` |
| Environment variables | Organized into `INTEREST_DB_*`-based settings |
| Password | Applied removal of hardcoding candidates and the external-injection principle |
| Default DB | Organized the local default DB name as `portfolio` |
| Schema structure | Documented the single-DB and per-Domain Schema structure |
| Search Path | Specified `research, preprocessor, interest, reference, legacy, public` |
| SQL compatibility | Kept the structure where existing SQL operates based on the Search Path |

### Work Scope

| Item | Value |
|---|---|
| Actual DB execution | None |
| Backtest·Report execution | None |
| External calls·orders | None |
| Sensitive information | No verbatim recording |

## 2026-05-26

### Initial Documentation and Cache Cleanup

| Item | Change Content |
|---|---|
| Initial documents | Added `AGENTS.md`, `README.md`, and a Worklog draft at the time |
| Cache cleanup | Cleaned up `__pycache__/` and internal `*.pyc` files |
| Authoring basis | The result of Read-only confirmation of the file structure and source at the time |

### Work Scope

| Item | Value |
|---|---|
| Actual execution | No Backtest, Research, Report, DB, external API, Crawler, or order execution |
| Sensitive information | No verbatim recording |
