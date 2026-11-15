"""Read-only Stage 1 audit for KITTI Raw synchronized drives.

Usage:
    python -m isj.kitti_audit --data-root /path/to/kitti \
        --drive 2011_10_03_drive_0027_sync

No training or factor-graph optimization is performed. No dataset is modified.
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

TIMESTAMP_PATTERN = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?$"
)
STREAM_SUFFIX = {
    "oxts": ".txt",
    "velodyne_points": ".bin",
    "image_00": ".png",
    "image_01": ".png",
    "image_02": ".png",
    "image_03": ".png",
}
REQUIRED_STREAMS = ("oxts", "velodyne_points", "image_02")


def timestamp_ns(value: str) -> int:
    match = TIMESTAMP_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError("Invalid KITTI timestamp: {!r}".format(value))
    y, m, d, hour, minute, second = map(int, match.groups()[:6])
    fractional = (match.group(7) or "").ljust(9, "0")
    instant = dt.datetime(y, m, d, hour, minute, second)
    return calendar.timegm(instant.timetuple()) * 1_000_000_000 + int(fractional or "0")


def read_timestamp_file(path: Path) -> List[int]:
    if not path.is_file():
        raise FileNotFoundError("Missing {}".format(path))
    output: List[int] = []
    for line_num, value in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        try:
            output.append(timestamp_ns(value))
        except ValueError as exc:
            raise ValueError("{} line {}: {}".format(path, line_num, exc)) from exc
    if not output:
        raise ValueError("Empty timestamps: {}".format(path))
    if any(b <= a for a, b in zip(output, output[1:])):
        raise ValueError("Timestamps are not strictly increasing: {}".format(path))
    return output


def find_drives(root: Path, requested: Optional[str] = None) -> List[Path]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError("KITTI root does not exist: {}".format(root))
    candidates = []
    if root.name.endswith("_sync"):
        candidates.append(root)
    patterns = ("*_sync", "*/*_sync", "raw/*/*_sync")
    for pattern in patterns:
        candidates.extend(p for p in root.glob(pattern) if p.is_dir())
    unique = sorted(set(p for p in candidates if p.is_dir()))
    if requested:
        unique = [p for p in unique if p.name == requested]
        if not unique:
            raise FileNotFoundError("Drive {!r} not found under {}".format(requested, root))
    if not unique:
        raise FileNotFoundError("No KITTI '*_sync' drive directory found under {}".format(root))
    return unique


def inspect_stream(drive: Path, name: str) -> Tuple[dict, List[int]]:
    directory = drive / name
    timestamp_file = directory / "timestamps.txt"
    times = read_timestamp_file(timestamp_file)
    data_dir = directory / "data"
    if not data_dir.is_dir():
        raise FileNotFoundError("Missing data directory: {}".format(data_dir))
    suffix = STREAM_SUFFIX[name]
    frames: Dict[int, Path] = {}
    for file in data_dir.iterdir():
        if not file.is_file() or file.suffix.lower() != suffix or not file.stem.isdigit():
            continue
        index = int(file.stem)
        if index in frames:
            raise ValueError("Duplicate frame index {} in {}".format(index, data_dir))
        frames[index] = file
    if not frames:
        raise ValueError("No {} frame files in {}".format(suffix, data_dir))
    unmatched_files = sorted(i for i in frames if i >= len(times))
    missing_frames = sorted(set(range(len(times))) - set(frames))
    matching_ids = sorted(i for i in frames if 0 <= i < len(times))
    if not matching_ids:
        raise ValueError("No frame IDs matched timestamp rows: {}".format(directory))
    aligned_times = [times[i] for i in matching_ids]  # index-preserving; no shifted timestamps
    sampled_ids = sorted(set([matching_ids[0], matching_ids[len(matching_ids) // 2], matching_ids[-1]]))
    samples = []
    for frame_id in sampled_ids:
        file = frames[frame_id]
        size = file.stat().st_size
        if name == "velodyne_points":
            valid = size >= 16 and size % 16 == 0  # KITTI: x,y,z,reflectance float32
            check = "4xfloat32 point stride (16 bytes)"
        elif name.startswith("image_"):
            with file.open("rb") as handle:
                valid = handle.read(8) == b"\x89PNG\r\n\x1a\n"
            check = "PNG signature"
        else:
            fields = file.read_text(encoding="utf-8").strip().split()
            try:
                values = [float(v) for v in fields]
                valid = len(values) >= 30 and -90 <= values[0] <= 90 and -180 <= values[1] <= 180
            except (ValueError, IndexError):
                valid = False
            check = "OXTS 30+ numeric fields and valid latitude/longitude"
        samples.append({"frame": frame_id, "bytes": size, "check": check, "valid": valid})
    report = {
        "directory": str(directory),
        "timestamp_rows": len(times),
        "frame_files": len(frames),
        "valid_frame_count": len(matching_ids),
        "missing_file_count": len(missing_frames),
        "missing_file_ids_first_20": missing_frames[:20],
        "files_without_timestamp_count": len(unmatched_files),
        "files_without_timestamp_ids_first_20": unmatched_files[:20],
        "first_timestamp": timestamp_file.read_text(encoding="utf-8-sig").splitlines()[matching_ids[0]],
        "last_timestamp": timestamp_file.read_text(encoding="utf-8-sig").splitlines()[matching_ids[-1]],
        "sample_checks": samples,
    }
    return report, aligned_times


def check_calibrations(drive: Path) -> dict:
    date_dir = drive.parent
    expected = {
        "calib_cam_to_cam.txt": {"R_rect_00": 9, "P_rect_02": 12},
        "calib_imu_to_velo.txt": {"R": 9, "T": 3},
        "calib_velo_to_cam.txt": {"R": 9, "T": 3},
    }
    report = {}
    for filename, keys in expected.items():
        path = date_dir / filename
        entry = {"path": str(path), "exists": path.is_file(), "problems": []}
        if not path.is_file():
            entry["problems"].append("Missing calibration file")
        else:
            fields = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if ":" not in line:
                    continue
                key, raw = line.split(":", 1)
                try:
                    fields[key.strip()] = [float(x) for x in raw.strip().split()]
                except ValueError:
                    continue
            for key, count in keys.items():
                if len(fields.get(key, [])) != count:
                    entry["problems"].append("{} expects {} numbers, got {}".format(
                        key, count, len(fields.get(key, []))
                    ))
        report[filename] = entry
    return report


def nearest_alignment(anchor_ns: Sequence[int], other_ns: Sequence[int], tolerance_ns: int) -> dict:
    if not anchor_ns or not other_ns:
        return {"matched": 0, "total": len(anchor_ns), "match_ratio": 0.0}
    errors_ms = []
    for stamp in anchor_ns:
        idx = bisect.bisect_left(other_ns, stamp)
        candidates = []
        if idx < len(other_ns):
            candidates.append(abs(other_ns[idx] - stamp))
        if idx > 0:
            candidates.append(abs(other_ns[idx - 1] - stamp))
        diff = min(candidates)
        if diff <= tolerance_ns:
            errors_ms.append(diff / 1_000_000)
    errors_ms.sort()
    return {
        "matched": len(errors_ms),
        "total": len(anchor_ns),
        "match_ratio": round(len(errors_ms) / len(anchor_ns), 6),
        "median_offset_ms": round(errors_ms[len(errors_ms) // 2], 6) if errors_ms else None,
        "max_offset_ms": round(errors_ms[-1], 6) if errors_ms else None,
    }


def audit_drive(drive: Path, max_offset_ms: float, min_match_ratio: float) -> dict:
    errors, warnings, stream_reports, all_times = [], [], {}, {}
    for name in STREAM_SUFFIX:
        if not (drive / name).exists():
            if name in REQUIRED_STREAMS:
                errors.append("Required sensor directory missing: {}".format(name))
            else:
                warnings.append("Optional sensor directory missing: {}".format(name))
            continue
        try:
            report, times = inspect_stream(drive, name)
            stream_reports[name] = report
            all_times[name] = times
            if report["files_without_timestamp_count"]:
                errors.append("{} has files without matching timestamp rows".format(name))
            if report["missing_file_count"]:
                warnings.append("{} has {} missing frame files".format(name, report["missing_file_count"]))
            if not all(s["valid"] for s in report["sample_checks"]):
                errors.append("{} has invalid sample frame content".format(name))
        except (OSError, ValueError) as exc:
            errors.append("{}: {}".format(name, exc))
    cal = check_calibrations(drive)
    for name, entry in cal.items():
        for issue in entry["problems"]:
            errors.append("{}: {}".format(name, issue))
    alignments = {}
    if "velodyne_points" in all_times:
        for name in ("oxts", "image_02", "image_00", "image_01", "image_03"):
            if name not in all_times:
                continue
            summary = nearest_alignment(
                all_times["velodyne_points"], all_times[name], round(max_offset_ms * 1_000_000)
            )
            alignments["lidar_to_" + name] = summary
            if summary["match_ratio"] < min_match_ratio and name in ("oxts", "image_02"):
                errors.append("LiDAR/{} match ratio {} below {}".format(
                    name, summary["match_ratio"], min_match_ratio
                ))
            elif summary["match_ratio"] < min_match_ratio:
                warnings.append("LiDAR/{} match ratio {} below {}".format(
                    name, summary["match_ratio"], min_match_ratio
                ))
    return {
        "drive": drive.name,
        "path": str(drive),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "streams": stream_reports,
        "calibrations": cal,
        "alignments": alignments,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path,
                        help="KITTI root, YYYY_MM_DD directory, or *_sync drive")
    parser.add_argument("--drive", help="Optional full synchronized-drive folder name")
    parser.add_argument("--max-offset-ms", type=float, default=80.0)
    parser.add_argument("--min-match-ratio", type=float, default=0.98)
    parser.add_argument("--output", type=Path, default=Path("results/stage1/kitti_audit.json"))
    args = parser.parse_args(argv)
    if args.max_offset_ms <= 0 or not (0 < args.min_match_ratio <= 1):
        parser.error("max-offset-ms must be > 0 and min-match-ratio in (0, 1]")
    try:
        drives = find_drives(args.data_root, args.drive)
        reports = [audit_drive(d, args.max_offset_ms, args.min_match_ratio) for d in drives]
    except (OSError, ValueError) as exc:
        print("DATA DISCOVERY FAILED: {}".format(exc), file=sys.stderr)
        return 1
    result = {
        "schema_version": 1,
        "note": "Read-only KITTI Raw sensor audit; not pose-estimation or independent-GT validation.",
        "max_offset_ms": args.max_offset_ms,
        "min_match_ratio": args.min_match_ratio,
        "drives": reports,
        "overall_status": "PASS" if all(r["status"] == "PASS" for r in reports) else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for report in reports:
        print("\n[{}] {}".format(report["status"], report["drive"]))
        for name, stream in report["streams"].items():
            print("  {:16s} frames={:5d} timestamps={:5d} missing={}".format(
                name, stream["valid_frame_count"], stream["timestamp_rows"], stream["missing_file_count"]
            ))
        for name, alignment in report["alignments"].items():
            print("  {}: {}/{} ({:.2%}), max={} ms".format(
                name, alignment["matched"], alignment["total"], alignment["match_ratio"],
                alignment.get("max_offset_ms"),
            ))
        for item in report["warnings"]:
            print("  WARNING:", item)
        for item in report["errors"]:
            print("  ERROR:", item)
    print("\nAudit: {}  |  Report: {}".format(result["overall_status"], args.output))
    return 0 if result["overall_status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())