# satnogs-telemetry

Command-line tool to download telemetry from the SatNOGS database, store the raw frames locally, decode them with Kaitai-based decoders, inspect parsed packets, export CSV files, and plot decoded fields.

## What the project does

For a given satellite NORAD ID, this project can:

- download telemetry frames from the SatNOGS DB API
- store the original SatNOGS packet JSON in a local SQLite database
- parse AX.25 and CCSDS headers from each frame
- decode mission-specific payloads using a Kaitai `.ksy` schema
- cache the generated Python decoder locally so recompilation is only done when needed
- optionally convert raw decoded values to engineering units using a CSV-based conversion table
- export parsed packets to CSV
- plot decoded numeric fields to PNG

## Main folders created/used at runtime

These folders are created in the project root when needed:

- `data/` - one SQLite database per satellite, for example `data/98386.sqlite3`
- `decoders/` - compiled decoder cache and optional conversion lookup files, for example `decoders/98386/`
- `csv/` - CSV exports when you use `export-csv`
- any plot output folder you choose when using `plot`

The project also expects decoder `.ksy` files to exist under the repo, typically in:

- `tools/satnogs-decoders/ksy/`

## Requirements

You need:

- Python 3.11 to 3.13
- Poetry `pip install poetry`
- Java SDK 26.0.1 https://www.oracle.com/java/technologies/downloads/ (make sure to add location of Java SDK bin to PATH)
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

### 3. Install Kaitai Struct Compiler

This project uses the Python Kaitai runtime through Poetry, but it also needs the external compiler executable to generate decoders from `.ksy` files. The compiler is available at: https://kaitai.io/

After installing it. Verify that the compiler is available in your terminal:

```bash
kaitai-struct-compiler --version
```

On Windows, you can also check:

```bat
where kaitai-struct-compiler
where kaitai-struct-compiler.bat
```

If this command is not found, install Kaitai Struct Compiler and make sure it is on your `PATH`.

### 4. Create a `.env` file with your SatNOGS token

Create a file named `.env` in the project root with the following contents:

```text
SATNOGS_API_TOKEN=your_token_here
```

This is required by the app to be able to download data from SatNOGS.

## First-time setup checklist

Before your first real run, confirm these work:

```bash
poetry run satnogs-telemetry --help
kaitai-struct-compiler --version
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
- compiles the configured decoder if needed
- parses raw frames that do not yet have parsed rows
- stores parsed output in the database

This looks for any available data in SatNOGS for the specific NORAD ID, and the download process could take a while. For quick analysis. The commands detailed below might be more useful:

## Command reference

### Run the normal incremental workflow

```bash
poetry run satnogs-telemetry --norad 98386
```

Use this for day-to-day operation.

If you also want engineering conversions applied during parsing:

```bash
poetry run satnogs-telemetry --norad 98386 --conv_to_eng
```

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

With engineering conversion enabled:

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98386 --conv_to_eng
```

### Rebuild all parsed rows from the stored raw data

```bash
poetry run satnogs-telemetry reparse-all --norad 98386
```

Use this after changing:

- parser logic
- the `.ksy` decoder
- engineering conversion definitions

With engineering conversion enabled:

```bash
poetry run satnogs-telemetry reparse-all --norad 98386 --conv_to_eng
```

### Load engineering conversions from a CSV definition

```bash
poetry run satnogs-telemetry load-conversions --norad 98386 --input beacon_definition.csv
```

This builds a lookup table from a CSV and saves it under:

```text
decoders/98386/98386_conversions.json
```

Then you can parse with `--conv_to_eng` to store converted values instead of raw decoded values where matching conversion rules exist.

#### Expected CSV fields

The conversion loader looks for columns such as:

- `ItemName`
- `Units`
- `Conversion`

Supported conversion styles include:

- simple linear expressions like `C0=... C1=...`
- enum mappings like `0/OFF 1/ON`

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
csv/98386/apid_201.csv
csv/98386/apid_202.csv
```

Note: This CSV exporter currently organizes columns alphabetically rather than following the parameter order defined in the frame decoder. This will be fixed in future iterations.

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

## Decoder compilation and caching

The first time a satellite is parsed, the tool compiles the configured `.ksy` file into Python and stores the generated decoder under:

```text
decoders/<norad>/
```

Example:

```text
decoders/98386/cosmo.py
decoders/98386/.buildinfo.json
```

The compiled decoder is reused until the `.ksy` file changes.

## Engineering conversion workflow

If your decoder returns raw values and you want engineering values:

1. prepare a CSV definition file
2. load it with `load-conversions`
3. parse using `--conv_to_eng`

Example:

```bash
poetry run satnogs-telemetry load-conversions --norad 98386 --input beacon.csv
poetry run satnogs-telemetry reparse-all --norad 98386 --conv_to_eng
```

Important:

- loading conversions alone does not change existing parsed rows
- you must parse or reparse with `--conv_to_eng` for conversions to be applied
- conversions are applied by matching CSV `ItemName` entries to decoded JSON leaf field names

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

### Example 3: Load conversions and regenerate parsed products

```bash
poetry run satnogs-telemetry load-conversions --norad 98386 --input beacon_definition.csv
poetry run satnogs-telemetry reparse-all --norad 98386 --conv_to_eng
poetry run satnogs-telemetry export-csv --norad 98386 --outdir csv
```

## Troubleshooting

### `kaitai-struct-compiler` not found

The external Kaitai compiler is not installed or not on your `PATH`.

Check:

```bash
kaitai-struct-compiler --version
```

### `KSY file not found`

The `ksy_path` in `config.toml` is wrong, or the file does not exist in the repo.

### The tool asks me to choose a decoder interactively

That means no decoder mapping was found for that NORAD ID in `config.toml`.

You can either:

- choose one interactively once, or
- add the mapping manually to `config.toml`

### Frames download but parsing fails

Possible causes:

- wrong `.ksy` selected for that satellite
- incorrect `root_class` in `config.toml`
- malformed frames in the downloaded data
- mission payload structure changed relative to the schema

### `--conv_to_eng` does not seem to do anything

Check that:

- you already ran `load-conversions`
- the conversion JSON exists under `decoders/<norad>/`
- the CSV `ItemName` values match the decoded field names
- you reparsed after loading conversions

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
