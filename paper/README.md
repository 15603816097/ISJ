# V7 English manuscript draft — evidence-bounded

This folder is a **first article draft**, not a finished IEEE Sensors Journal submission.
All results are grounded in the DFG V7 frozen experimental code and the archived
cross-sequence scores. The original ISJ code/audit roadmap remains unchanged.

## Files

- `sections/02_method_v7.tex`: implemented four-sensor offline batch pose graph,
  GRU/Mamba current reliability, Beta evidence output, training-only axis noise
  mapping and Cap4 information constraint.
- `sections/03_experiments_v7.tex`: data splits, 0016/0020 tables, metrics,
  convergence and explicit post-release synchronization incident.
- `NOVELTY_AND_EVIDENCE_GAPS.md`: implemented-vs-unverified matrix and submission gates.

## Overleaf incorporation

Copy the two LaTeX files to the `sections/` folder in an existing
IEEEtran document. Include `amsmath` in the main preamble, then add:

    \input{sections/02_method_v7}
    \input{sections/03_experiments_v7}

These sections intentionally contain no fabricated external citations.
Prior-art research, bibliography, figures, complete system details and
independent evaluation are required before submission.

## Provenance

- Implementation: `15603816097/DFG`, branch `isj-supplementary-experiments-20261115`.
- Initial cross-date release: `2bfeb6f`.
- Audited interrupted-run recovery: `71cf91a`.
- Archived result notes: `DFG/experiments/isj_v7/HELDOUT_RESULTS_0016_0020.md`.
- Final score report SHA256: `acc333e491e3ed189d04bc5c6082f1d609342823b6a3c1114459e06c1be82589`.
- The 0016 and 0020 results must never be retuned or rerun to optimize reported scores.

## Critical claims NOT supported by the current implementation

- Mamba is universally superior to GRU (0020 clearly favors GRU96).
- h1/h2 forecast or uncertainty U modulates the tested FGO (only h0 does).
- Fully independent physical ground truth is available (OXTS/GPS is shared).
- The graph is online iSAM2, IMU-preintegrated, or full vehicle-state estimation.
- The reserved evaluation is perfectly preregistered (0020 had a disclosed post-release timestamp exception).