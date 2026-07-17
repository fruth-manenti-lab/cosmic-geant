# Simulation Data Tracking

Use a stable campaign ID plus metadata for every generated dataset. Dates are useful, but they are not enough once geometry, source logic, and reconstruction settings start changing independently.

## Recommended Folder Names

Use this pattern:

```text
<campaign_id>_<geometry_id>_<sample>_<source>_<version>
```

Examples:

```text
20260507_geom-nostubs-alt_test1000_random_addscan_v01
20260508_geom-nostubs-pos_train10000_grid_addscan_v01
```

The campaign ID can start with a date, but the geometry ID and sample description should carry the real meaning.

## Required Files In Each Data Folder

Each raw-data or converted-data folder should contain:

- `RUN_METADATA.yml`: machine-readable provenance.
- `README.md`: short human summary, with the main command used to generate the data.

Large raw CSVs and converted per-event CSVs can stay outside Git, but these small metadata files should be committed.

## Required Metadata Fields

Use `docs/RUN_METADATA.template.yml` as the starting point. At minimum, record:

- `campaign_id`
- `geometry_id`
- `geometry_file`
- `git_commit`
- `build_dir`
- `compile_options`
- `macro`
- `source_position_file`
- `event_position_mapping`
- `n_events`
- `raw_output_path`
- `converted_output_path`
- `analysis_results`

## Event-To-Position Mapping

For old multi-run scans:

```text
run_id -> scan position row
event_id -> repeated event at that same position
```

For `ADD_SCAN` one-run scans:

```text
EventID -> SourceIndex -> source position row
SourceCycle -> repeated pass through the source table
```

Prefer `ADD_SCAN` source-truth ntuples when they are available. They remove ambiguity from thread-split output files and make the event labels self-describing.

## Geometry Rule

Never describe a dataset only as "May 7 geometry" or "new geometry". Use the registry ID from `geometry/GEOMETRY_REGISTRY.md`, such as:

```text
geom-nostubs-alt
geom-nostubs-pos
```

