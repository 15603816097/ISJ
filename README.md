# ISJ — multi-sensor fusion experiments

**New experimental repository.** The historical `DFG` repository is only a reference. No prior results or model weights have been imported.

## Roadmap

1. **Stage 1 (current):** KITTI Raw directory, timestamp, image/point cloud/OXTS frame and calibration audit.
2. Stage 2: fixed-noise four-sensor factor-graph baseline, data split and metric verification.
3. Stage 3: reproducible GPS/IMU/camera degradation simulation.
4. Stage 4: GRU/Mamba sensor reliability and Beta evidential uncertainty.
5. Stage 5: reliability/uncertainty-aware factor weights and matched optimization budgets.
6. Stage 6: controlled comparisons, ablations, robustness and cross-date tests.

No training, GTSAM, or GPU is required for Stage 1; Python 3.8+ is sufficient.

## Install / test

```bash
git clone https://github.com/15603816097/ISJ.git
cd ISJ
python --version
python -m unittest discover -s tests -v
```

## Put the KITTI Raw synchronized dataset on your server

Expected layout (example):

```text
/root/autodl-tmp/KITTI/
└── 2011_10_03/
    ├── calib_cam_to_cam.txt
    ├── calib_imu_to_velo.txt
    ├── calib_velo_to_cam.txt
    └── 2011_10_03_drive_0027_sync/
        ├── oxts/timestamps.txt
        ├── oxts/data/0000000000.txt
        ├── velodyne_points/timestamps.txt
        ├── velodyne_points/data/0000000000.bin
        └── image_02/
            ├── timestamps.txt
            └── data/0000000000.png
```

The checker accepts the root directory, date directory, or synchronized drive directory. **Do not duplicate the dataset inside the Git repository.** `image_00`, `image_01`, and `image_03` are audited when present; for this project `image_02` is initially required.

```bash
python -m isj.kitti_audit \
  --data-root /root/autodl-tmp/KITTI \
  --drive 2011_10_03_drive_0027_sync \
  --max-offset-ms 80 \
  --min-match-ratio 0.98
```

Successful completion prints `[PASS]`, exits 0 and creates `results/stage1/kitti_audit.json`; exit 2 indicates a failed sensor audit, exit 1 indicates data discovery failure. A JSON report lists all missing frames, timestamp precision and nearest-neighbor offsets. **No data is modified.**

KITTI Raw OXTS contains both GPS and IMU signals in one channel; the audit does not claim independent reference ground truth. Reference/test independence will be checked before paper experiments.

## Cleanup policy

Keep only active source modules and tests. After each milestone, identify unused scripts, confirm their imports/CLI entrypoints are unused, archive a Git revision, then delete through a separate reviewed commit. Never delete dataset files or prior experiments in the separate `DFG` repository.