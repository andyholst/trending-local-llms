# data-gap-analysis

## ADDED Requirements

### Requirement: A judged dimension is not re-filed inside its window

When an issue carrying the current gap signature is CLOSED, the analysis MUST record the judgement
per DIMENSION in the baseline, and MUST NOT file a gap set whose dimensions were all judged within
`JUDGED_DAYS` (21). After the window the dimension is re-examined, and a dimension the signature no
longer carries is unaffected.

#### Scenario: a close three days ago

- **Given** a closed issue carrying the signature, closed 3 days before the analysis
- **When** `--issue` runs on a changed gap set
- **Then** no issue is filed, the run exits 0, and the baseline records `judged`
- **Test:** tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window

#### Scenario: a close thirty days ago

- **Given** the same closed issue, closed 30 days before the analysis
- **When** `--issue` runs
- **Then** the gap set IS filed again
- **Test:** tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window

#### Scenario: the reason is never silent

- **Given** every dimension is inside its window
- **When** the run files nothing
- **Then** it names each dimension and the stamp that judged it on stderr
- **Test:** tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window
