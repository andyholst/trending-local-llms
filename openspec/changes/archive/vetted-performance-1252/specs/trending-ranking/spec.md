## ADDED Requirements

### Requirement: Vetted performance view

The tool SHALL join shipped models and measurements, parse string t/s, band by VRAM,
deduplicate by (source post, engine, hardware, model), and render the highest t/s rows
per band with engine, quant, date, posts_7d and README band. Rows with no source post
SHALL be excluded from the vetted top and counted as UNVETTED. It SHALL NOT write either
store or change `sort_models`.

#### Scenario: A fast model has no recent posts

- **WHEN** a 700 t/s measurement has a vetted source post but posts_7d is 0
- **THEN** it appears at the top of its VRAM band
- **AND** its README band is shown, explaining why 🔥 omits it

#### Scenario: One post repeated in the store

- **WHEN** the same source/engine/hardware row appears twice
- **THEN** it contributes one row, not two
