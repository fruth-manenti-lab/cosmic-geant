# New Geometry May 7 Reconstruction

This folder contains compact analysis products for the `geom-nostubs-alt` geometry:

- Geometry: `geometry/final_no_stubs.gdml`
- Meaning: no external fiber stubs, SiPMs coupled directly to fiber ends, alternating positive/negative readout sides.
- Test sample: 1000 random `ADD_SCAN` events with source truth in `MUON-run0_nt_source_t*.csv`.
- Training samples:
  - 1024 fixed scan positions with 10 events per position.
  - 10000 fixed scan positions with 1 event per position.

Large raw Geant4 CSVs and converted per-event SiPM count CSVs are saved separately and ignored by Git. The committed files here are compact summaries, figures, and metadata.

See `RUN_METADATA.yml` for the exact paths and result values.

