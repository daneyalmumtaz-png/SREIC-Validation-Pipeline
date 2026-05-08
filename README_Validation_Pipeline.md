# SREIC Validation Pipeline

This is the validation pipeline I built to expand the empirical validation of the SREIC framework from n = 7 telemetry events to a larger sample. SREIC is the Speed Restriction Economic Impact Calculator I developed during my MSc thesis at Tampere University in collaboration with FTIA (Finnish Transport Infrastructure Agency).

The pipeline does one thing: it takes Pendolino Sm3 telemetry from Digitraffic, cross-references each speed dip against speed-restriction notifications, runs my SREIC kinematic model on the matched events, and produces an Excel dataset of validation cases with bootstrapped confidence intervals.

## Why I built this

When I was preparing the SREIC paper for submission to the Journal of Rail Transport Planning and Management, I went through a strict pre-submission review of the manuscript. The dominant weakness was Section 4.1 — the empirical validation rested on only n = 7 telemetry events from a single two-day window. I knew a reviewer would attack this, and they would be right to. With n = 7 the bootstrap confidence interval on the correlation is too wide to support the precision the paper implies.

So instead of waiting for that to come back as a major revision, I decided to address it pre-emptively. I wrote this pipeline over the course of two weeks. The idea is simple: pull as many real Pendolino runs as I can from the Digitraffic open-data API, cross-reference them against actual speed-restriction records, and use the matched events to validate the model.

## How it works

The pipeline runs in two stages.

**Stage 1** (`fetch_validation_data.py`) does the data work:
- Pulls speed-restriction notifications from either the live Jeti API or an offline CSV (RAIDE export)
- Pulls Pendolino Sm3 historical telemetry from Digitraffic GraphQL, one train at a time (the bulk-query approach times out the database — I learned that one the hard way)
- Identifies dip episodes in each train's speed trace
- Filters out station dwells using the train's commercial-stop timetable
- Matches each remaining dip to a TSR within configurable spatial and temporal tolerances
- Writes the matched events to an Excel file

**Stage 2** (`compute_validation_metrics.py`) does the statistics:
- Loads the Excel from Stage 1
- Runs my SREIC kinematic model (`Model.py`) on each event
- Computes Pearson r, mean residual, MAE, and MAPE — each with a 95% non-parametric bootstrap CI from B = 10 000 resamples
- Runs a sign test for systematic bias
- Writes the results back into the Excel and produces a markdown report with a paragraph ready to drop into the paper

## Two operating modes

There are two ways to run this, and which one you use depends on what data you have access to.

**Online mode** uses the live Digitraffic Jeti API. It works, but you should know what to expect. Jeti is a real-time operational endpoint, not a historical archive. It retains roughly 30 most recent restriction notifications, mostly in `FINISHED` or `SENT` state, with very few `ACTIVE`. When I ran the pipeline against the live API in May 2026 I consistently got 0 to 5 matched events — not because the pipeline fails, but because the data simply isn't there. This is the mode you use to verify the pipeline runs and the matching logic works.

**Offline mode** reads TSRs from a local CSV file. This is the mode you use when you have a historical export from FTIA's RAIDE system, which is what I ultimately need to actually generate the n = 50–100 sample for the paper. The CSV schema is documented further down. Set `OFFLINE_TSR_PATH` in `config.py` and the pipeline switches over automatically.

## Running it

```bash
# put these four files alongside Model.py and your acceleration table:
#   config.py
#   fetch_validation_data.py
#   compute_validation_metrics.py
#   Model.py                          
#   sm3_acceleration_table.csv        

pip install requests openpyxl

# edit config.py — at minimum set DATE_RANGE_START / END

python fetch_validation_data.py
python compute_validation_metrics.py
```

Outputs:
- `sreic_validation_dataset.xlsx` — one row per matched event, plus a summary sheet
- `validation_diagnostics.json` — selection-criteria audit trail
- `validation_run.log` — full run log
- `validation_report.md` — a paragraph in the right format to paste into Section 4.1

## What's in the config

`config.py` has every knob in one place. The settings you most likely want to touch:

| Parameter | What it controls |
|---|---|
| `DATE_RANGE_START / END` | Window to scan |
| `TARGET_SAMPLE_SIZE` | Pipeline stops at this N |
| `OFFLINE_TSR_PATH` | Empty for online, CSV path for offline |
| `ALLOWED_TSR_STATES` | Permissive: ACTIVE, SENT, FINISHED. Strict: ACTIVE only |
| `MIN_SPEED_REDUCTION_KMH` | v0 − vr threshold (default 30) |
| `DIP_SPEED_THRESHOLD_KMH` | What counts as a "dip" (default 90) |
| `SPATIAL_MATCH_TOLERANCE_M` | Trace-to-TSR distance budget (default 200) |

## How the four design problems are addressed

When I started building this, I sat down and listed the four mechanical problems any validation expansion would face. Each one is solved explicitly.

**Are dips really TSRs, or station approaches / signals?** I use the Jeti or RAIDE record as independent ground truth. A speed dip is only counted as a validation event if a restriction notification with non-trivial length is active at that location and time. Both spatial (within 200 m of TSR centroid) and temporal (within 5 minutes of validity window) match are required. Pure signal slowdowns and station approaches don't have ground-truth records and are discarded.

**Are vr and L circular?** No — they come from the ground-truth record, not from the speed trace. The trace is only used to obtain v0, vt, and the observed traversal time. This is what makes it a real validation rather than a self-consistency check.

**How are station dwells handled?** Each candidate dip is checked against the train's commercial stops in its timetable. If a dip is within 500 m of a scheduled commercial-stop station, it's excluded.

**What does "observed delay" mean?** SREIC predicts τ = t_with_TSR − t_baseline. The "observed" version I compute is τ_obs = observed_traversal − model_baseline. I don't have a counterfactual real baseline (a parallel-universe run with no restriction); the model baseline is the only consistent reference. The paper states this explicitly. The suggested wording for Section 3.6 is:

> *"Observed delay is computed as the difference between the actual in-zone traversal time recorded in the telemetry and a kinematically modelled baseline traversal of the same zone at line speed. We do not claim a counterfactual real baseline; the modelled baseline is the reference used consistently for both the predicted and observed delay sides of the comparison."*

## Sample size — what I'm aiming for and why

| n | Bootstrap CI half-width on r | Sign-test power vs systematic bias |
|---|---|---|
| 7 | ±0.45 (essentially uninformative) | <0.10 |
| 30 | ±0.20 | 0.55 |
| 50 | ±0.16 | 0.75 |
| 100 | ±0.11 | 0.95 |

n = 50 is the minimum that lets me make a quantitative claim about correlation strength with confidence intervals tight enough to be reportable. n = 100 is what I want — it gives the sign test enough power to rule out a "no systematic bias" null at α = 0.05 even when the true bias is small.

## Offline RAIDE schema

If you're preparing a CSV export from RAIDE for me, the columns I need are:

```
id, version, valid_from, valid_to, restricted_speed_kmh, length_m, centroid_lat, centroid_lon, state
```

- `id` — notification identifier (string)
- `version` — integer
- `valid_from` / `valid_to` — ISO 8601 UTC timestamps. `valid_to` may be empty for still-in-force records
- `restricted_speed_kmh` — float, the in-zone limit
- `length_m` — float, length of the restricted zone
- `centroid_lat` / `centroid_lon` — WGS84 decimal degrees, midpoint of the zone
- `state` — text label (ACTIVE, FINISHED, etc.)

If your export uses different column names or a different format, let me know and I'll adjust `load_offline_tsrs()` in `fetch_validation_data.py` — it's a small function, all the parsing happens in one place.

For the SREIC paper, the most useful window is **June to November 2025** because it covers the seasonal frost-heave thaw period. That's the operationally most relevant period for the bridge and frost-heave archetypes that drive the headline results in the paper.

## Troubleshooting

**`Unknown type 'LocalDate'`** — the GraphQL schema changed at some point. The current pipeline uses `Date!`, which matched the schema when I last checked (May 2026). If this comes back, run a schema introspection to see what the right type is now.

**`Field 'trainStations' is undefined`** — the query is `stations`, not `trainStations`. Already fixed in this version.

**`NullValueInNonNullableField` on `trainLocations`** — database timeout from a too-broad query. The pipeline uses two-stage fetching now (metadata first, telemetry per-train) precisely to avoid this. If you still hit it, lower the rate limit and retry.

**Console crashes with `UnicodeEncodeError`** — Windows cp1252 encoding hitting a unicode arrow character. The pipeline forces UTF-8 on stdout/stderr at import time. If it still happens, set the console to UTF-8 first (`chcp 65001` in PowerShell).

**`No TSRs found`** — for online mode, this means the public Jeti snapshot has no records matching your state filter and date range. Try `ALLOWED_TSR_STATES = ("ACTIVE", "SENT", "FINISHED")` and bring the date window closer to today. For offline mode, check the CSV path and dates.

**`Resolved 0 station coordinates`** — the location field came back in a format my parser doesn't know about. Pipeline continues but station-dwell filtering is disabled. Open `extract_lat_lon()` and add the missing pattern.

## File map

```
sreic_validation_pipeline/
├── README.md                          ← you are here
├── config.py                          ← edit this
├── fetch_validation_data.py            ← Stage 1
├── compute_validation_metrics.py       ← Stage 2
│
├── Model.py                            ← my kinematic model (yours)
├── sm3_acceleration_table.csv          ← Pendolino Sm3 acceleration data
│
├── (optional) raide_export.csv         ← offline mode data source
│
├── sreic_validation_dataset.xlsx       ← output
├── validation_diagnostics.json         ← output
├── validation_report.md                ← output
└── validation_run.log                  ← output
```

## Data citations for the paper

When this work goes into the JRTPM submission, I cite the data sources as:

1. **Digitraffic** (operated by Fintraffic, Finland), railway traffic API, https://www.digitraffic.fi/en/railway-traffic/. CC BY 4.0. Data from Fintraffic's LIIKE, REAALI and LOKI operational systems.
2. **Jeti API** (Digitraffic), traffic restriction notifications endpoint *(used in online mode)*.
3. **RAIDE** (FTIA / Väylävirasto internal), historical TSR archive *(used in offline mode, by data-sharing arrangement)*.

## Acknowledgement of AI assistance

I used AI assistance (Anthropic Claude) during the development of this pipeline. The research problem, the methodology, the four-problem framing, the validation strategy, the choice of statistical tests, the iterative debugging against the live API, and all decisions about scope and design were mine. AI assistance was used for code drafting and refactoring — I would describe what I needed, run the result, identify the failures, and iterate. The final code is the product of that loop, which means I understand every line and have run every path against real data.

I'm flagging this here because I think transparency about how research code is produced is important, and because I'd rather state the situation honestly than have someone wonder. Anthropic Claude is a tool, like any other tool I might use to write code, but it's a non-trivial one and I think it deserves explicit acknowledgement.

---

*Daneyal Mumtaz, MSc Civil Engineering, Tampere University. Built in collaboration with FTIA (Finnish Transport Infrastructure Agency). For the SREIC manuscript prepared for submission to the Journal of Rail Transport Planning and Management.*
