# data-gap-analysis

## ADDED Requirements

### Requirement: A storage offload needs a medium and an offload wording

The `storage_offload` free-text detector MUST require a storage medium
(`ssd`/`nvme`/`flash`/`disk`/`hdd`/`storage`) AND an offload/streaming wording in the same
sentence.

#### Scenario: a memory offload

- **Given** `"Q4_K_M with 26 MoE layers offloaded to the CPU"`
- **When** the store is analysed
- **Then** the model is NOT reported as naming a storage offload
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload

#### Scenario: a file size and a machine's own disk

- **Given** `"4-bit MLX, 2.1GB on disk"` and `"M2 Ultra, 2TB SSD, 192GB unified memory"`
- **When** the store is analysed
- **Then** neither is reported
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload

#### Scenario: a genuine storage requirement

- **Given** `"experts streamed from NVMe SSD"` and `"MoE expert offload to SSD"`
- **When** the store is analysed
- **Then** both are reported
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload
