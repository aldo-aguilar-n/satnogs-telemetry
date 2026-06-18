# satnogs-telemetry

Command-line tool for downloading telemetry from the SatNOGS database, storing raw frames in a local SQLite3 database, parsing them with decoders generated from telemetry dictionaries, exporting the results to CSV files, and generating plots from the data.

## What the project does

For a given satellite NORAD ID, this project can:

- download telemetry frames from the SatNOGS DB API
- store the raw SatNOGS packets in a local SQLite database
- generate and cache a Python decoder under `decoders/<norad>/decoder.py` based on a user-selected telemetry dictionary
- decode and parse AX.25 frames into mission-specific CCSDS packets following the telemetry dictionary
- export parsed packets to CSV
- plot decoded numeric fields to PNG

## Main folders created/used at runtime

These folders are created in the project root when needed:

- `data/` - one SQLite database per satellite, for example `data/68635.sqlite3`
- `ctdb/` - telemetry dictionaries available for selection. Copy any telemetry dictionaries you want to use into this folder for convenience.
- `decoders/` - generated decoder cache, for example `decoders/68635/decoder.py`
- `csv/` - CSV exports when you use `export-csv`
- any plot output folder you choose when using `plot`

## Requirements

You need:

- Python 3.11 to 3.13
- Poetry `pip install poetry`
- a SatNOGS API token if the API requires authentication for your usage
- An SSH key for GitHub to make cloning easier

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:aldo-aguilar-n/satnogs-telemetry.git
cd satnogs-telemetry
```

### 2. Install dependencies with Poetry

```bash
poetry install
```

### 3. Create a `.env` file with your SatNOGS token

Create a file named `.env` in the project root with the following contents:

```text
SATNOGS_API_TOKEN=your_token_here
```

This is required by the app to be able to download data from SatNOGS.

## First-time setup checklist

Before your first real run, confirm these work:

```bash
poetry run satnogs-telemetry --help
```

And confirm these files exist:

- `.env`

## Typical workflow

The most common workflow is:

1. download new raw frames from SatNOGS
2. parse any raw frames that have not been parsed yet
3. inspect, export, or plot the parsed results

The default command does steps 1 and 2 together:

```bash
poetry run satnogs-telemetry --norad <norad_id>
```

What this does:

- opens or creates `data/<norad_id>.sqlite3`
- downloads only new raw frames not already stored
- prompts for a decoder database if one is not configured
- generates `decoders/<norad>/decoder.py` if needed
- parses raw frames that do not yet have parsed rows
- stores parsed output in the database

This looks for any available data in SatNOGS for the specific NORAD ID, and the download process could take a while. For quick analysis. The commands detailed below might be more useful:

## Command reference

### Run the normal incremental workflow

```bash
poetry run satnogs-telemetry --norad 98386
```

Use this for day-to-day operation.

### Download only new raw frames

```bash
poetry run satnogs-telemetry sync-raw-latest --norad 98386
```

Use this when you only want to refresh the raw database without parsing yet.

### Download raw frames for a specific time range

```bash
poetry run satnogs-telemetry sync-raw-range \
  --norad 98386 \
  --start 2026-04-11T00:00:00Z \
  --end 2026-04-12T00:00:00Z
```

This is useful for backfilling or re-downloading a known period. Some SatNOGS users upload data frames post-mortem (i.e., not in real time during a pass), and these data frames are typically tagged with the wrong timestamp (SatNOGS tags frames at upload). So this command is useful for backfilling any gaps in the data caused by these incorrect timestamps.

### Parse only rows that are not parsed yet

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98386
```

### Rebuild all parsed rows from the stored raw data

```bash
poetry run satnogs-telemetry reparse-all --norad 98386
```

Use this after changing parser logic or the telemetry dictionary.

### Reparse rows within range

```bash
poetry run satnogs-telemetry reparse-range \
  --norad 98386 \
  --start 2026-04-11T00:00:00Z \
  --end 2026-04-12T00:00:00Z
```

### Engineering conversions

Engineering conversions are read from the telemetry dictionary and written to `parsed_json_eng` when conversion definitions exist.

### Show recent raw rows

```bash
poetry run satnogs-telemetry show-recent-raw --norad 98386 --limit 5
```

Useful for checking what was downloaded before decoding.

### Show recent parsed rows

```bash
poetry run satnogs-telemetry show-recent-parsed --norad 98386 --limit 5
```

Useful for verifying header extraction and decoder output.

### List numeric fields available for plotting

```bash
poetry run satnogs-telemetry list-fields --norad 98386
```

To restrict the list to a single APID:

```bash
poetry run satnogs-telemetry list-fields --norad 98386 --apid 201
```

### Dump parsed frames into compact JSON file

```bash
poetry run satnogs-telemetry dump-parsed-json \
  --norad 98386 \
  --output data_dump.json \
  --start 2026-04-11T00:00:00Z \
  --end 2026-04-12T00:00:00Z
```

### Plot one decoded field

```bash
poetry run satnogs-telemetry plot \
  --norad 98386 \
  --field beacon_t.battery_voltage \
  --output plots/battery_voltage.png
```

You can also filter by APID:

```bash
poetry run satnogs-telemetry plot \
  --norad 98386 \
  --apid 201 \
  --field beacon_t.battery_voltage \
  --output plots/battery_voltage.png
```

The plot uses:

- x-axis: packet timestamp in UTC
- y-axis: numeric field value from the parsed JSON

### Export one CSV per APID

```bash
poetry run satnogs-telemetry export-csv --norad 98386 --outdir csv
```

This writes files under:

```text
csv/98386/
```

For example:

```text
csv/98386/apid_201_raw.csv
csv/98386/apid_201_eng.csv
csv/98386/apid_202_raw.csv
csv/98386/apid_202_eng.csv
```

## How parsed data is organized

The tool stores two layers of data:

### Raw frames

The `raw_frames` table contains the original SatNOGS JSON packet exactly as received.

### Parsed frames

The `parsed_frames` table contains:

- metadata timestamp
- observer/station
- AX.25 destination and source callsigns
- raw AX.25 frame as hex
- CCSDS APID
- CCSDS sequence count
- raw CCSDS packet as hex
- decoded JSON payload when decoding succeeds

This split allows you to reparse packets later without downloading them again.

## Decoder generation and caching

The first time a satellite is parsed, the tool generates a Python decoder from the configured spreadsheet database and stores it under:

```text
decoders/<norad>/decoder.py
decoders/<norad>/.buildinfo.json
```

The generated decoder is reused until the source spreadsheet changes. `parsed_json` keeps the same decoded-payload structure as before, and `parsed_json_eng` is populated when the spreadsheet defines engineering conversions.

## Common examples

### Example 1: New user, first data pull

```bash
poetry install
poetry run satnogs-telemetry --norad 98386
```

### Example 2: Backfill one day and inspect parsed packets

```bash
poetry run satnogs-telemetry sync-raw-range \
  --norad 98386 \
  --start 2026-04-11T00:00:00Z \
  --end 2026-04-12T00:00:00Z

poetry run satnogs-telemetry parse-unparsed --norad 98386
poetry run satnogs-telemetry show-recent-parsed --norad 98386 --limit 10
```

### Example 3: Regenerate parsed products after decoder database changes

```bash
poetry run satnogs-telemetry reparse-all --norad 98386
poetry run satnogs-telemetry export-csv --norad 98386 --outdir csv
```

## Troubleshooting

### Decoder source file not found

The `source_path` in `config.toml` is wrong, or the spreadsheet database file does not exist in the repo.

### The tool asks me to choose a decoder interactively

That means no decoder mapping was found for that NORAD ID in `config.toml`.

You can either:

- choose one interactively once, or
- add the mapping manually to `config.toml`

### Frames download but parsing fails

Possible causes:

- wrong telemetry dictionary selected for that satellite
- incorrect `source_path` in `config.toml`
- malformed frames in the downloaded data
- mission payload structure changed relative to the schema

## Notes for maintainers

A few behavior details that are useful to know:

- one SQLite database is created per NORAD ID
- parsed rows are rebuilt from stored raw rows during `reparse-all`
- malformed raw rows with deterministic framing errors may be deleted during parse so they are not retried forever
- CSV export preserves field order based on first-seen parsed rows rather than alphabetically sorting every column

## Help

To see the CLI help:

```bash
poetry run satnogs-telemetry --help
```
