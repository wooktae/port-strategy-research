"""Report presentation locale helper (Phase 3, Task 3.1).

Selects the report presentation language via the ``REPORT_LOCALE`` environment
variable. English is the default; Korean is available as an alternate locale.

The locale affects presentation only: report labels, section titles and
explanatory narrative. It must never change report data, metrics, run IDs,
strategy/engine versions, RSCFG identifiers, tickers, raw company names,
reason codes, bucket/status contract values, persisted analysis values, or
report filenames.
"""

import os

SUPPORTED_LOCALES = ("en", "ko")
DEFAULT_LOCALE = "en"


def get_report_locale() -> str:
    """Return the active report locale.

    Reads ``REPORT_LOCALE`` on each call so tests and runtime can switch the
    locale by setting the environment variable. Any unsupported or unset value
    falls back to the English default.
    """
    raw = (os.environ.get("REPORT_LOCALE") or "").strip().lower()
    return raw if raw in SUPPORTED_LOCALES else DEFAULT_LOCALE


def t(en: str, ko: str) -> str:
    """Return the presentation string for the active report locale.

    ``en`` is returned for the English default locale, ``ko`` for the Korean
    locale. Both arguments must carry the same interpolated data so that only
    the presentation language differs.
    """
    return ko if get_report_locale() == "ko" else en
