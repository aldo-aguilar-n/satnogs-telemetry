"""
satnogs_telemetry package.

This project provides a small telemetry pipeline for SatNOGS data.
The package is intentionally organized into a few broad modules:

- 'cli': command-line entry points and user-facing commands
- 'download': SatNOGS API access and raw packet synchronization
- 'decode': AX.25/CCSDS parsing, decoder selection, Kaitai compilation,
            and payload decoding
- 'database': SQLite schema and CRUD helpers
- 'plotting': simple time-series plotting from parsed rows
- 'csv_export': one-CSV-per-APID export helpers

The package-level module is intentionally lightweight; it only exists to 
mark 'satnogs_telemetry' as a Python package.
"""
