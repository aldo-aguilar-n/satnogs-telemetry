# satnogs-telemetry

Headless SatNOGS telemetry downloader, decoder, SQLite store, plotter, and CSV exporter.

## Simplified project layout

```text
src/satnogs_telemetry/
  cli.py
  download.py
  decode.py
  database.py
  plotting.py
  csv_export.py
```

## What this project does

- Downloads raw telemetry packets from SatNOGS for a NORAD ID.
- Stores the **full raw SatNOGS packet unchanged** in SQLite.
- Uses **one SQLite database per satellite**.
- Parses each stored raw packet into:
  - metadata timestamp
  - observer
  - AX.25 destination and source callsigns
  - raw AX.25 frame
  - CCSDS APID and sequence count
  - raw CCSDS packet
  - decoded payload fields when a decoder succeeds
- Uses Kaitai `.ksy` decoders.
- Compiles the selected `.ksy` decoder on first use and caches it locally.
- Plots decoded numeric telemetry versus time.
- Exports one CSV per APID.

## Runtime assumptions

The runtime paths are hard-coded:

- raw SQLite DBs are stored under `data/`
- compiled decoders are stored under `decoders/`
- plots are written wherever you pass `--output`
- the Kaitai compiler is invoked as the global command `kaitai-struct-compiler`

`config.toml` is only used for NORAD-to-decoder mappings.

## Installation

### 1. Install the Python environment

```bash
poetry install
```

### 2. Create a local `.env` file for the SatNOGS token

Create `.env` in the project root:

```text
SATNOGS_API_TOKEN=your_db_token_here
```

The app loads this automatically using `python-dotenv`.

### 3. Add `.env` to `.gitignore`

Make sure `.gitignore` contains:

```text
.env
```

### 4. Install Kaitai Struct Compiler globally

Poetry installs the Python `kaitaistruct` runtime, but **not** the compiler executable.
This project expects the global `kaitai-struct-compiler` command to be on your system `PATH`.

Verify it with:

```bash
kaitai-struct-compiler --version
```

On Windows, if needed:

```bat
where kaitai-struct-compiler
where kaitai-struct-compiler.bat
```

### 5. Make sure decoder `.ksy` files exist in the repo

This project expects decoder schemas under the repo, typically:

```text
tools/satnogs-decoders/ksy/
```

### 6. Create `config.toml`

Copy the example:

```bash
cp config.example.toml config.toml
```

Example contents:

```toml
[satellites.98386.decoder]
ksy_path = "tools/satnogs-decoders/ksy/cosmo.ksy"
root_class = "Cosmo"
```

You can add more satellites the same way.

## Cache layout

Compiled decoders are stored under:

```text
decoders/
  98386/
    cosmo.py
    .buildinfo.json
```

## Usage

### End-to-end incremental run

```bash
poetry run satnogs-telemetry --norad 98386
```

This will:

- create/open `data/98386.sqlite3`
- sync only new raw packets from SatNOGS
- parse unparsed raw rows
- auto-delete clearly malformed raw rows that can never parse

### Initialize database only

```bash
poetry run satnogs-telemetry init-db --norad 98386
```

### Download only new raw packets

```bash
poetry run satnogs-telemetry sync-raw-latest --norad 98386
```

### Download raw packets in a time range

```bash
poetry run satnogs-telemetry sync-raw-range   --norad 98386   --start 2026-04-11T00:00:00Z   --end 2026-04-12T00:00:00Z
```

### Parse stored raw rows that are still unparsed

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98386
```

### Reparse everything from raw

Use this after changing decoder or parser logic:

```bash
poetry run satnogs-telemetry reparse-all --norad 98386
```

### Show recent raw rows

```bash
poetry run satnogs-telemetry show-recent-raw --norad 98386 --limit 5
```

### Show recent parsed rows

```bash
poetry run satnogs-telemetry show-recent-parsed --norad 98386 --limit 5
```

### List numeric fields available for plotting

```bash
poetry run satnogs-telemetry list-fields --norad 98386
```

### Plot one telemetry field

```bash
poetry run satnogs-telemetry plot   --norad 98386   --field battery_voltage   --output plots/battery_voltage.png
```

The plot uses:

- X axis = metadata timestamp
- Y axis = Eng Units
- title = shortened field name

### Export one CSV per APID

```bash
poetry run satnogs-telemetry export-csv --norad 98386 --outdir csv
```

Each CSV contains columns in this order:

- `timestamp`
- `observer`
- CCSDS primary header fields
- CCSDS secondary header fields
- user data fields

Rows are ordered by metadata timestamp from oldest to newest.

## Notes

- Raw SatNOGS packets are stored unchanged.
- Metadata trimming happens during decode, not during download.
- If a raw row is malformed at the AX.25 / CCSDS level, it is removed automatically so it is not retried forever.
- If a row fails because of decoder issues or unsupported payload structure, the raw row is kept.
- Decoder compilation happens automatically on first use and is reused later unless the `.ksy` changed.
