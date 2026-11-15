"""Small self-contained fake-KITTI fixtures (no real dataset required)."""
import tempfile
import unittest
from pathlib import Path
from isj.kitti_audit import (audit_drive, find_drives, inspect_stream,
                             nearest_alignment, timestamp_ns)


class Stage1AuditTests(unittest.TestCase):
    def test_nanosecond_precision(self):
        a = timestamp_ns("2011-10-03 13:02:45.123456789")
        b = timestamp_ns("2011-10-03 13:02:45.123456790")
        self.assertEqual(b - a, 1)

    def test_bad_timestamp(self):
        with self.assertRaises(ValueError):
            timestamp_ns("2011-10-03 99:99:99")

    def test_alignment_threshold(self):
        base = [10_000_000_000, 10_100_000_000]
        other = [10_020_000_000, 10_170_000_000]
        v = nearest_alignment(base, other, 40_000_000)
        self.assertEqual(v["matched"], 1)
        self.assertEqual(v["total"], 2)

    def test_full_fake_drive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            date = root / "2011_10_03"
            drive = date / "2011_10_03_drive_0027_sync"
            drive.mkdir(parents=True)
            (date / "calib_cam_to_cam.txt").write_text(
                "R_rect_00: " + " ".join(["1"] * 9) + "\n" +
                "P_rect_02: " + " ".join(["1"] * 12) + "\n")
            for name in ("calib_imu_to_velo.txt", "calib_velo_to_cam.txt"):
                (date / name).write_text(
                    "R: " + " ".join(["1"] * 9) + "\n" +
                    "T: 0 0 0\n")
            for name, ext, data in (
                ("oxts", "txt", b"50.0 10.0 " + b"0 " * 28),
                ("velodyne_points", "bin", b"\0" * 16),
                ("image_02", "png", b"\x89PNG\r\n\x1a\n"),
            ):
                folder = drive / name / "data"
                folder.mkdir(parents=True)
                (drive / name / "timestamps.txt").write_text(
                    "2011-10-03 13:02:45.000000001\n"
                    "2011-10-03 13:02:45.100000001\n"
                    "2011-10-03 13:02:45.200000001\n")
                for idx in range(3):
                    (folder / ("{:010d}.{}".format(idx, ext))).write_bytes(data)
            self.assertEqual(find_drives(root), [drive])
            self.assertEqual(audit_drive(drive, 80, 0.98)["status"], "PASS")
            # Verify missing frame 1 cannot cause index-shifted timestamps.
            (drive / "image_02" / "data" / "0000000001.png").unlink()
            r, aligned_times = inspect_stream(drive, "image_02")
            self.assertEqual(r["missing_file_ids_first_20"], [1])
            self.assertEqual(aligned_times[1] - aligned_times[0], 200_000_000)


if __name__ == "__main__":
    unittest.main()