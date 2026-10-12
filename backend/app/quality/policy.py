"""Every threshold used by the quality checks, in one place.

Health of a delivery = worst status among its checks (fail > warn > pass).
"""
MAX_EXAMPLES = 20                  # examples listed per check in a report

# Row-level checks (completeness, validity): share of rows affected.
#   0            -> pass
#   <= 5 %       -> warn   (a few bad rows; the rest of the delivery is usable)
#   >  5 %       -> fail   (the export itself looks broken)
ROW_FAIL_FRACTION = 0.05

# Coverage: share of the expected (campaign x day) cells that arrived with valid data.
#   100 % pass | >= 90 % warn | < 90 % fail
COVERAGE_WARN_MIN = 0.90

# Rows dated outside the window the filename promises: warn up to 5 %, fail above.
DATE_WINDOW_FAIL_FRACTION = 0.05

# Unit/scale detection: compare spend-per-1000-impressions with the platform's other deliveries.
SCALE_MIN_ROWS = 3                 # need this many rows in a delivery to judge it
SCALE_MIN_BASELINE_DELIVERIES = 2  # ...and this many *other* deliveries to compare against
SCALE_ANOMALY_LOW, SCALE_ANOMALY_HIGH = 0.2, 5.0     # ratio outside this range = anomaly
SCALE_FACTORS = (100, 1000)        # recognized unit errors we will auto-correct (cents, mills)
SCALE_FACTOR_TOLERANCE = 0.25      # ratio within +/-25 % of a factor counts as that factor
