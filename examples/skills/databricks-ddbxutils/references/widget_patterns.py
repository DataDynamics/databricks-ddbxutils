# =============================================================================
# databricks-ddbxutils — ddbxutils.widgets usage patterns
# =============================================================================
# IMPORTANT: the `add_days` function available inside a widget default value is
# DIFFERENT from the one in conf/settings.yml (EnvConfig).
#
#   widget  : add_days(value: str, fmt: str, default: str, days: int)   # 4 args
#   yaml    : add_days(value, n: int)                                   # 2 args
#
# Confusing the two is the #1 source of widget rendering errors.
# =============================================================================


# -----------------------------------------------------------------------------
# 1. Basic — derive next_day from another widget
# -----------------------------------------------------------------------------
dbutils.widgets.text("rawdate",  "2025-05-24", "Raw Date")
dbutils.widgets.text("next_day",
                     '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}',
                     "Next Day")

import ddbxutils
ddbxutils.widgets.get("next_day")   # -> "2025-05-25"


# -----------------------------------------------------------------------------
# 2. Subtract N days (use negative int)
# -----------------------------------------------------------------------------
dbutils.widgets.text("seven_days_ago",
                     '{{add_days(rawdate, "%Y-%m-%d", "", -7)}}',
                     "7 Days Ago")

ddbxutils.widgets.get("seven_days_ago")


# -----------------------------------------------------------------------------
# 3. Default value when the source widget is empty
# -----------------------------------------------------------------------------
# 3rd arg is the fallback used if `rawdate` can't be parsed.
dbutils.widgets.text("safe_next",
                     '{{add_days(rawdate, "%Y-%m-%d", "2025-01-01", 1)}}',
                     "Safe Next")


# -----------------------------------------------------------------------------
# 4. Non-dash date format
# -----------------------------------------------------------------------------
dbutils.widgets.text("yyyymmdd",       "20250524",        "YYYYMMDD")
dbutils.widgets.text("yyyymmdd_next",
                     '{{add_days(yyyymmdd, "%Y%m%d", "", 1)}}',
                     "Next YYYYMMDD")


# -----------------------------------------------------------------------------
# 5. add_datetime — same shape, datetime granularity
# -----------------------------------------------------------------------------
dbutils.widgets.text("run_ts",   "2025-05-24 10:00:00", "Run Timestamp")
dbutils.widgets.text("next_hour",
                     '{{add_datetime(run_ts, "%Y-%m-%d %H:%M:%S", "", 3600)}}',
                     "Next Hour")


# -----------------------------------------------------------------------------
# 6. Refresh — force re-read of widget values (e.g. after user edits them)
# -----------------------------------------------------------------------------
ddbxutils.widgets.refresh()
ddbxutils.widgets.get("next_day")


# -----------------------------------------------------------------------------
# 7. Env switch from a dropdown widget (pairs with EnvConfig)
# -----------------------------------------------------------------------------
import os
dbutils.widgets.dropdown("env", "dev", ["dev", "stg", "prd"], "Environment")
os.environ["ENV"] = dbutils.widgets.get("env")

from ddbxutils import EnvConfig
cfg = EnvConfig()
cfg.print_summary()
