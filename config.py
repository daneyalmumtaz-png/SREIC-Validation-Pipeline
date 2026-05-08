"""
SREIC validation pipeline — config

Edit this file before running. Most knobs are stable; the ones that
matter for a fresh run are DATE_RANGE_START/END, TARGET_SAMPLE_SIZE,
and OFFLINE_TSR_PATH if using a RAIDE export.
"""

from datetime import date

# -- date window --
# Public Jeti API only retains ~30 most recent records (live snapshot,
# not an archive), so for online runs keep this within the last few
# weeks. For offline RAIDE runs use whatever your archive covers.
DATE_RANGE_START = date(2026, 4, 1)
DATE_RANGE_END   = date(2026, 5, 31)

# Stop after this many matched events. Online realistically yields 0-5,
# offline yields whatever the archive contains.
TARGET_SAMPLE_SIZE = 100

# -- rolling stock filter --
OPERATOR_CODE = "vr"
PENDOLINO_TRAIN_TYPES = ["S"]   # S = Sm3-operated services
TRAIN_NUMBER_WHITELIST = None   # set to e.g. ["41","81"] to narrow further

# -- TSR filters --
# Jeti states observed in practice: DRAFT, SENT, ACTIVE, FINISHED.
# Keep this permissive; the time-overlap check downstream filters
# out records that weren't in force during the window.
ALLOWED_TSR_STATES = ("ACTIVE", "SENT", "FINISHED")

MIN_RESTRICTION_LENGTH_M = 50      # below this the model is too noisy
MAX_RESTRICTION_LENGTH_M = 5000    # above this single brake-plateau-accel breaks down
MIN_SPEED_REDUCTION_KMH  = 30      # v0 - vr must be at least this big

# -- dip detection --
DIP_SPEED_THRESHOLD_KMH = 90       # Pendolinos cruise 160-220, dip below 90 = candidate
MIN_DIP_DURATION_S      = 30       # filters one-sample anomalies
SPATIAL_MATCH_TOLERANCE_M    = 200
TEMPORAL_MATCH_TOLERANCE_MIN = 5

# Station-dwell exclusion radius. If a dip's centroid is within this
# distance of any commercial-stop station, it's a dwell, not a TSR.
STATION_DWELL_BUFFER_M = 500

# -- kinematic model (Sm3) --
SM3_DECEL_MS2 = 0.6
SM3_TRAIN_LENGTH_M = 160
KINEMATIC_DT = 0.1
SM3_ACCEL_TABLE_PATH = "sm3_acceleration_table.csv"

# -- API --
DIGITRAFFIC_BASE = "https://rata.digitraffic.fi"
GRAPHQL_URL = f"{DIGITRAFFIC_BASE}/api/v2/graphql/graphql"
JETI_RESTRICTIONS_URL = f"{DIGITRAFFIC_BASE}/api/v1/trafficrestriction-notifications.json"
TRACKWORK_URL = f"{DIGITRAFFIC_BASE}/api/v1/trackwork-notifications.json"

# Identifying header required by Digitraffic ToS
DIGITRAFFIC_USER_HEADER = "SREIC-Validation/Tampere-University 1.0"

RATE_LIMIT_REQUESTS_PER_MIN = 100   # Digitraffic allows 120, leave headroom

# -- offline mode --
# If this is a non-empty path, the pipeline reads TSRs from this CSV
# instead of hitting the live Jeti API. Use this once you have a
# RAIDE export from FTIA. See README for the expected CSV schema.
OFFLINE_TSR_PATH = ""   # e.g. "raide_export_2025.csv"

# -- output --
OUTPUT_EXCEL_PATH = "sreic_validation_dataset.xlsx"
OUTPUT_DIAGNOSTICS_PATH = "validation_diagnostics.json"
OUTPUT_LOG_PATH = "validation_run.log"

SAVE_RAW_TRACES = True
RAW_TRACES_DIR = "raw_traces"
