# Novelty and evidence gates for IEEE Sensors Journal

**Status:** evidence audit after frozen V7 0016/0020 scores; not yet an acceptance prediction.

| Claimed method element | Code status | Direct evidence | Paper-safe statement |
| --- | --- | --- | --- |
| 21-D causal degraded-GPS features | Implemented | 0027 frozen inference parity 0.0 m GPS sigma delta | Causal GPS-only feature engineering |
| Mamba/GRU current reliability h0 | Implemented | 0016 and 0020 graph score results | Different networks give sequence-dependent results |
| Beta h0/h1/h2 heads | Trained | Only h0 used in held-out graph | Forecast heads exist, but graph forecasting benefit untested |
| Evidential uncertainty U | Emitted | No calibrated covariances / no heldout U usage | Concentration proxy, not calibrated uncertainty |
| Train-fitted axis noise mapping | Implemented | Frozen Cap4 comparison vs Axis-Fixed | Heuristic train-only mapping improves some synthetic scores |
| Cap4 fourfold precision limit | Implemented | Code tested and frozen across drives | Bounded information heuristic, not formal chance-constrained optimization |
| Joint GPS + IMU + LiDAR + Camera graph | Implemented | Fixed factor counts and solver results | Offline Pose3 FGO; simplified gyro factor |
| Feedforward-feedback reliability trajectory | Not implemented in tested graph | None | Proposed future work only |
| Reliability change-point / factor forgetting | Not implemented | None | Proposed future work only |
| iSAM2 incremental optimization | Not used in current evaluation | None | Cannot claim real-time incremental method |
| Velocity / yaw-rate state accuracy | Not assessed | None | Current metric is pose translation |
| Independent absolute position reference | Not available in V7 test | OXTS reused for corruption/reference | Synthetic GPS recovery with correlated reference |
| General Mamba superiority | Contradicted by 0020 | GRU96 3.2032 m vs Mamba 6.9844 m | Architecture robustness is sequence-dependent |

## Immediate writing tasks (do not touch heldout hyperparameters)

1. Finish the reproducible description of *what is already implemented*;
   check all equations against the frozen DFG source.
2. Add related-work citations from verified peer-reviewed papers to clarify
   differences versus adaptive noise estimation and robust FGO. No invented citations.
3. Add dev-only evidence that the temporal h0 weights matter, or identify
   the lack of such evidence; do not reuse scored 0016/0020 for model tuning.
4. For any new predictive-feedback module, define it separately from V7,
   register a NEW dataset/independent GT and evaluation protocol BEFORE looking
   at outcomes. Keep the frozen V7 baseline and its archives immutable.
5. Avoid claiming an original predictive/future-head innovation until it
   improves a proper predeclared new evaluation under matched compute.

## Manuscript positioning

The currently defensible empirical observation is: frozen current-GPS
reliability can guide bounded, per-axis covariance weighting in a
four-sensor batch pose graph under synthetic GPS corruption; substantial
drive dependence exists, and Mamba does not consistently outperform GRU.
This alone may be insufficient novelty for a selective sensors journal.
The original thesis title involving time-varying sensor uncertainty
remains a research direction rather than a fully validated contribution.

**Evidence red line:** the 0020 first-three-frame synchronization exception
was implemented after first release. State it openly in any final paper.