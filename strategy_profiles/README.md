# Research Strategy Profiles

This directory manages the Research Strategy Profiles that are injected into the fixed Common Engine.

## Responsibilities

- Manage the Market, Filter, Sizing, BUY Guard, BUY, and SELL settings per Version.
- Track the Backtest Policy and Metrics settings together with the strategy execution settings.
- Record the Common Package Version and Common Strategy Version in the Metadata.
- At actual execution time, use the Resolved Config that merges the Profile Override with the Common Default.

## Out of Scope

- The Backtest start date and the Decision reference date are managed as Run Input.
- REPORT_CONFIG is an analysis and presentation setting rather than a trading result, so it is not included.
- The Profile status does not imply automatic operational Promotion or Champion designation.

## Baseline

- RSCFG-0001 is the Baseline Profile against Common Package 1.0.0.
- It expands the Config declared in Common and the hidden defaults inside the BUY Guard functions.
- Decimal-based values are stored as JSON strings to preserve precision.
- Schema and Unknown Key enforcement is performed by the subsequent Profile Validator.
