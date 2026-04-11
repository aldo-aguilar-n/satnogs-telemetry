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

Recommended lookup strategy:

1. NORAD ID
2. transmitter UUID if available
3. SatNOGS `sat_id` if available
4. CCSDS APID

A decoder is resolved from `config.toml`.

## Quick start

### 1. Create/install the environment

```bash
poetry install
```

### 2. Add the SatNOGS decoders submodule

If this repo is already a Git repo:

```bash
git submodule add https://gitlab.com/librespacefoundation/satnogs/satnogs-decoders.git external/satnogs-decoders
git submodule update --init --recursive
```

Or use the helper script after `git init`:

```bash
bash scripts/init_submodule.sh
```

### 3. Copy and edit the config file

```bash
cp config.example.toml config.toml
```

### 4. Initialize the DB for a satellite

```bash
poetry run satnogs-telemetry init-db --norad 98338
```

### 5. Download raw telemetry

```bash
poetry run satnogs-telemetry sync-raw-latest --norad 98338 --config config.toml
```

### 6. Parse everything still unparsed

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98338 --config config.toml
```

### 7. Inspect parsed rows

```bash
poetry run satnogs-telemetry show-recent-parsed --norad 98338 --limit 5
```

### 8. List decoded numeric fields

```bash
poetry run satnogs-telemetry list-fields --norad 98338
```

### 9. Plot one field

```bash
poetry run satnogs-telemetry plot --norad 98338 --field eps.battery_voltage --output plots/battery_voltage.png
```

## Config file format

See `config.example.toml`.

The main decoder settings are under `[[satellites]]`.

Each satellite entry can specify:

- `norad_cat_id`
- optional `transmitter`
- optional `sat_id`
- `frame_protocol` (currently `ax25_ccsds`)
- zero or more `[[satellites.apid_decoders]]` entries

Each APID decoder can be one of:

- `type = "python"` using a generated Python decoder or helper module
- `type = "ksy"` using a `.ksy` file compiled with `ksc`

Optional fields:

- `strip_ccsds_primary_header = true` if the decoder expects only the payload after the 6-byte CCSDS primary header
- `parser_path` for Python module decoder
- `root_class` for Python/Kaitai parser root class
- `ksy_path` for Kaitai schema path

## Important assumptions

This starter project assumes:

- SatNOGS `frame` contains a complete AX.25 frame
- the AX.25 information field contains a CCSDS packet
- CCSDS primary header is the standard 6-byte primary header

If a specific mission differs from that, adapt `utils.extract_ax25_and_ccsds()` and/or the decoder config.

## Command summary

Initialize database:

```bash
poetry run satnogs-telemetry init-db --norad 98338
```

Download raw packets newer than the most recent stored row:

```bash
poetry run satnogs-telemetry sync-raw-latest --norad 98338 --config config.toml
```

Download raw packets in a range:

```bash
poetry run satnogs-telemetry sync-raw-range \
  --norad 98338 \
  --start 2026-04-01T00:00:00Z \
  --end 2026-04-12T00:00:00Z \
  --config config.toml
```

Parse stored raw rows that do not yet have parsed rows:

```bash
poetry run satnogs-telemetry parse-unparsed --norad 98338 --config config.toml
```

Show recent raw rows:

```bash
poetry run satnogs-telemetry show-recent-raw --norad 98338 --limit 5
```

Show recent parsed rows:

```bash
poetry run satnogs-telemetry show-recent-parsed --norad 98338 --limit 5
```

List decoded numeric fields:

```bash
poetry run satnogs-telemetry list-fields --norad 98338
```

Plot one decoded field:

```bash
poetry run satnogs-telemetry plot \
  --norad 98338 \
  --field eps.battery_voltage \
  --output plots/eps_battery_voltage.png
```
