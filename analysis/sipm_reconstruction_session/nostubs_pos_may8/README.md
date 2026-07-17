# No-Stubs Positive-Side SiPM Reconstruction

This folder contains compact analysis products for the `geom-nostubs-pos` geometry:

- Geometry: `geometry/final_no_stubs_pos_sipms.gdml`
- Meaning: no external fiber stubs, SiPMs coupled directly to fiber ends, all SiPMs on the positive readout sides as in `geometry/final.gdml`.
- Test sample: 1000 random `ADD_SCAN` events with source truth in `MUON-run0_nt_source_t*.csv`.
- Training sample: 1024 fixed scan positions with 10 events per position.

Large raw Geant4 CSVs and converted per-event SiPM count CSVs are saved separately and ignored by Git. The committed files here are compact summaries, figures, and metadata.

See `RUN_METADATA.yml` for exact paths and result values.

