# Stubbed Alternating-Side SiPM Reconstruction

This folder contains compact analysis products for the `geom-stubs-alt` geometry:

- Geometry: `geometry/final_stubs_alternating.gdml`
- Meaning: external coated fiber stubs are present, and SiPM readout alternates positive/negative sides by lane.
- Test sample: 1000 random `ADD_SCAN` events with source truth in `MUON-run0_nt_source_t*.csv`.
- Training sample: 1024 fixed scan positions with 10 events per position.

Large raw Geant4 CSVs and converted per-event SiPM count CSVs are saved separately and ignored by Git. The committed files here are compact summaries, figures, and metadata.

See `RUN_METADATA.yml` for exact paths and result values.

