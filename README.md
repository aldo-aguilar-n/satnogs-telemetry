# satnogs-telemetry

Headless SatNOGS telemetry downloader, parser, and per-satellite SQLite store.

## What this project does

- Downloads raw telemetry packets from SatNOGS for a NORAD ID.
- Stores the **full raw SatNOGS packet unchanged** in SQLite.
- Uses **one SQLite database per satellite**.
- Parses each stored raw packet later in a separate step.
- Extracts and stores:
  - `timestamp`
  - `observer`
  - AX.25 destination and source callsigns
  - raw AX.25 frame
  - CCSDS APID and sequence count
  - raw CCSDS packet
  - optional parsed packet if a decoder is configured and succeeds
- Uses decoders from the `satnogs-decoders` Git submodule.
- Compiles the selected `.ksy` decoder on first use and caches it locally.
- Saves plots in headless mode as PNG files.

## Per-satellite database layout

Each satellite gets its own SQLite database file:

```text
data/
  98338.sqlite3
  98386.sqlite3
```

## Decoder integration model

This project is designed to work with `satnogs-decoders` as a Git submodule.

Current decoder behavior:

- The app uses **one decoder per satellite**, selected by **NORAD ID**.
- The same decoder may parse multiple APIDs for that satellite.
- APID is still extracted and stored, but is **not** used to choose the decoder.
- On first parse of an unknown satellite, the app will prompt the user to choose a `.ksy` decoder from the existing `satnogs-decoders` submodule.
- That decoder choice is saved in `config.toml`.
- The `.ksy` is compiled on first use and cached locally for later parses.

## Quick start

### 1. Create/install the environment

```bash
poetry install
```

### 2. Create a local `.env` file for the SatNOGS token

Create a file named `.env` in the project root:

```text
SATNOGS_API_TOKEN=your_db_token_here
```

This project uses `python-dotenv`, so the token is loaded automatically from `.env` when the app starts.

### 3. Add `.env` to `.gitignore`

Make sure `.gitignore` contains:

```text
.env
```

### 4. Install Kaitai Struct Compiler

Poetry installs the **Python runtime** package `kaitaistruct`, but this project also needs the separate command-line compiler `kaitai-struct-compiler` to turn `.ksy` files into Python parsers.

On Windows, install Kaitai Struct Compiler by downloading the official compiler release or Windows package, then extract/install it somewhere on your machine.

A common location looks like:

```text
C:\Program Files (x86)\kaitai-struct-compiler\
```

### 5. Point `config.toml` to the compiler

Set `ksc_bin` under `[app]` to the full path of the compiler launcher.

Example:

```toml
[app]
db_dir = "data"
satnogs_base_url = "https://db.satnogs.org/api/telemetry/"
request_timeout_s = 60
source_name = "satnogs_db"
satnogs_decoders_dir = "tools/satnogs-decoders"
generated_decoders_dir = "decoders"
ksc_bin = "C:/Program Files (x86)/kaitai-struct-compiler/bin/kaitai-struct-compiler.bat"
```

Use forward slashes in TOML paths on Windows.

### 6. Verify the compiler path

In Command Prompt:

```bat
where kaitai-struct-compiler
where kaitai-struct-compiler.bat
```

If those commands return a full path, use that path in `config.toml`.

You can also test the configured compiler directly:

```bat
"C:\Program Files (x86)\kaitai-struct-compiler\bin\kaitai-struct-compiler.bat" --version
```

If that prints a version, the path is valid and the app should be able to invoke the compiler.

### 7. Run the app for a satellite

```bash
poetry run satnogs-telemetry --norad 98338
```

On first run, this will:

- create `data/98338.sqlite3` if it does not exist
- initialize the schema
- ask you to choose a decoder for satellite `98338` if none is configured yet
- save that decoder selection in `config.toml`
- download the latest raw telemetry
- parse all unparsed rows

On later runs, the same command will:

- reuse the existing database
- reuse the saved decoder
- download only new raw telemetry
- parse only new rows

## `.env` file

Example:

```env
SATNOGS_API_TOKEN=your_db_token_here
```

Important:

- use the **SatNOGS DB API token**
- keep `.env` local only
- do **not** commit `.env` to Git

## Config file format

See `config.example.toml`.

Main runtime settings live under `[app]`.

Satellite decoder mappings live under:

```toml
[satellites.98338.decoder]
ksy_path = "ksy/cosmo.ksy"
root_class = "Cosmo"
```

### Main config fields

Under `[app]`:

- `db_dir`
- `satnogs_base_url`
- `request_timeout_s`
- `source_name`
- `satnogs_decoders_dir`
- `generated_decoders_dir`
- `ksc_bin`

### Satellite decoder fields

Under `[satellites.<norad>.decoder]`:

- `ksy_path` = path to `.ksy` relative to the `satnogs-decoders` submodule root
- `root_class` = root class name to use from the generated Python parser

## Important assumptions

This starter project assumes:

- SatNOGS `frame` contains a complete AX.25 frame
- the AX.25 information field contains a CCSDS packet
- CCSDS primary header is the standard 6-byte primary header

If a specific mission differs from that, adapt `utils.extract_ax25_and_ccsds()` and/or the satellite decoder config.

## Command summary

### Default end-to-end run

```bash
poetry run satnogs-telemetry --norad 98338
```

### Initialize database only

```bash
poetry run satnogs-telemetry init-db --norad 98338
```

### Download raw packets newer than the most recent stored row

```bash
poetry run satnogs-telemetry sync-raw-latest --norad 98338 --config config.toml
```

### Download raw packets in a range

```bash
poetry run satnogs-telemetry sync-raw-range \
  --norad 98338 \
  --start 2026-04-01T00:00:00Z \
  --end 2026-04-12T00:00:00Z \
  --config config.toml
```

### Parse stored raw rows that do not yet have parsed rows

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98338 --config config.toml
```

### Show recent raw rows

```bash
poetry run satnogs-telemetry show-recent-raw --norad 98338 --limit 5
```

### Show recent parsed rows

```bash
poetry run satnogs-telemetry show-recent-parsed --norad 98338 --limit 5
```

### List decoded numeric fields

```bash
poetry run satnogs-telemetry list-fields --norad 98338
```

### Plot one decoded field

```bash
poetry run satnogs-telemetry plot \
  --norad 98338 \
  --field eps.battery_voltage \
  --output plots/eps_battery_voltage.png
```

## Decoder compilation and caching

When the app needs a decoder for the first time:

- it compiles the selected `.ksy` using `kaitai-struct-compiler`
- it stores the generated Python decoder under `decoders/`
- it reuses that compiled decoder on future runs
- if the source `.ksy` changes later, it recompiles automatically

Typical cache layout:

```text
decoders/
  98338/
    satellite_decoder/
      some_decoder.py
      .buildinfo.json
```

## Notes

- Raw SatNOGS packets are stored unchanged.
- Metadata trimming happens during the parse stage, not ingest.
- AX.25 and CCSDS metadata are stored even if payload decoding fails.
- A satellite decoder may successfully parse multiple APIDs.
- Some packets may still fail payload decode even when the decoder is correct.
- This is expected and does not prevent storage of the extracted metadata.
