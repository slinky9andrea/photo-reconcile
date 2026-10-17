"""Unit tests for the logic that decides what gets changed. No iPhone backup needed:
    python3 -m unittest discover tests
"""
import datetime as dt
import os
import tempfile
import unittest
from unittest import mock

from photoreconcile import common, inventory, match, replace, tag


class CropDetection(unittest.TestCase):
    def test_same_size_is_whole_frame(self):
        self.assertEqual(match.crop_reason((3024, 4032), (3024, 4032)), "")

    def test_square_crop(self):
        self.assertEqual(match.crop_reason((3024, 3024), (3024, 4032)), "cropped (different shape)")

    def test_standard_export_size_is_a_resize(self):
        self.assertEqual(match.crop_reason((1536, 2048), (3024, 4032)), "")

    def test_half_size_is_a_resize(self):
        self.assertEqual(match.crop_reason((1512, 2016), (3024, 4032)), "")

    def test_trimmed_edges_same_shape(self):   # e.g. 3755x2816 from a 4032x3024 original
        self.assertEqual(match.crop_reason((2816, 3755), (3024, 4032)), "cropped (edges trimmed)")


class ReplacePlan(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.f = lambda *p: os.path.join(self.d, *p)
        os.makedirs(self.f("a")); os.makedirs(self.f("b"))
        for p in ("a/x.jpg", "b/x.jpg", "a/y.jpg", "a/z.jpg", "h1.heic", "h2.heic"):
            open(self.f(p), "w").write(p)

    def row(self, jpg, heic, reason=""):
        return {"jpg_path": self.f(jpg), "heic_path": self.f(heic), "reason": reason, "note": ""}

    def test_same_photo_in_two_folders_both_replaced(self):
        plan = replace.build_plan([self.row("a/x.jpg", "h1.heic"), self.row("b/x.jpg", "h1.heic")])
        self.assertEqual([p["action"] for p in plan], ["replace", "replace"])

    def test_two_different_jpgs_one_heic_kept(self):
        plan = replace.build_plan([self.row("a/y.jpg", "h2.heic"), self.row("a/z.jpg", "h2.heic")])
        self.assertEqual([p["action"] for p in plan], ["keep_jpg", "keep_jpg"])

    def test_cropped_kept_unless_asked(self):
        r = [self.row("a/y.jpg", "h1.heic", "cropped (different shape)")]
        self.assertEqual(replace.build_plan(r)[0]["action"], "keep_jpg")
        self.assertEqual(replace.build_plan(r, replace_cropped=True)[0]["action"], "replace")

    def test_replace_then_undo_round_trip(self):
        pics, work = self.f("pics"), self.f("work")
        os.makedirs(os.path.join(pics, "2020"))
        jpg = os.path.join(pics, "2020", "Dog.jpg")
        open(jpg, "w").write("jpg")
        heic = self.f("h1.heic")
        w = common.Work(work, pics)
        common.write_csv(w.matches, [{"status": "confident", "reason": "", "note": "",
                                      "jpg_path": jpg, "heic_path": heic}])
        args = mock.Mock(go=True, replace_cropped=False)
        with mock.patch("builtins.input", return_value="YES"):
            replace.run(args, w)
        self.assertFalse(os.path.exists(jpg))
        self.assertTrue(os.path.exists(os.path.join(pics, "2020", "Dog.heic")))
        self.assertTrue(os.path.exists(os.path.join(w.hold_dir, "2020", "Dog.jpg")))
        with mock.patch("builtins.input", return_value="YES"):
            replace.undo(mock.Mock(list=None), w)
        self.assertTrue(os.path.exists(jpg))
        self.assertFalse(os.path.exists(os.path.join(pics, "2020", "Dog.heic")))

    def test_dry_run_changes_nothing(self):
        pics = self.f("pics2"); os.makedirs(pics)
        jpg = os.path.join(pics, "P.jpg"); open(jpg, "w").write("j")
        w = common.Work(self.f("work2"), pics)
        common.write_csv(w.matches, [{"status": "confident", "reason": "", "note": "",
                                      "jpg_path": jpg, "heic_path": self.f("h1.heic")}])
        replace.run(mock.Mock(go=False, replace_cropped=False), w)
        self.assertTrue(os.path.exists(jpg))
        self.assertFalse(os.path.exists(os.path.join(pics, "P.heic")))


class PhoneRecordMatching(unittest.TestCase):
    def setUp(self):
        utc = dt.datetime(2020, 10, 26, 22, 9, 3)         # 15:09:03 in UTC-7
        self.assets = {
            1: {"utc": utc, "tz": -7 * 3600, "file": "IMG_2826.HEIC", "model": "iPhone 11 Pro"},
            2: {"utc": utc, "tz": -7 * 3600, "file": "IMG_2827.HEIC", "model": "iPhone 11 Pro"},
            3: {"utc": dt.datetime(2010, 5, 1, 18, 0, 0), "tz": -7 * 3600, "file": "DSC0001.JPG", "model": "DSC-W7"},
            4: {"utc": dt.datetime(2019, 1, 1, 20, 0, 0), "tz": None, "file": "IMG_0500.HEIC", "model": ""},
        }
        self.f = tag.Finder(self.assets)

    def test_local_time_plus_file_name(self):
        local = dt.datetime(2020, 10, 26, 15, 9, 3)
        self.assertEqual(self.f.find(local, "IMG_2827"), 2)

    def test_same_second_without_name_is_ambiguous(self):
        self.assertIsNone(self.f.find(dt.datetime(2020, 10, 26, 15, 9, 3)))

    def test_old_camera_photo_by_time(self):
        self.assertEqual(self.f.find(dt.datetime(2010, 5, 1, 11, 0, 0), None, "DSC-W7"), 3)

    def test_record_without_time_zone_uses_name(self):
        self.assertEqual(self.f.find(dt.datetime(2019, 1, 1, 12, 0, 0), "IMG_0500"), 4)

    def test_stem(self):
        self.assertEqual(tag.stem_of("/x/IMG_5401_1.HEIC"), "IMG_5401")
        self.assertIsNone(tag.stem_of("2020-01-01 Dog.jpg"))

    def test_rename(self):
        self.assertEqual(tag.parse_renames(["Jane (Me)=Jane Doe"]), {"Jane (Me)": "Jane Doe"})


class Misc(unittest.TestCase):
    def test_exif_dates(self):
        self.assertEqual(common.parse_exif_dt("2023:12:14 13:48:07"), dt.datetime(2023, 12, 14, 13, 48, 7))
        self.assertIsNone(common.parse_exif_dt("0000:00:00 00:00:00"))

    def test_byte_dates(self):
        self.assertEqual(inventory.photo_date(b"xx2021:08:04 10:11:12yy"), "2021-08-04 10:11:12")
        self.assertEqual(inventory.video_date(b"..2022-01-02T03:04:05-0800.."), "2022-01-02 03:04:05")

    def test_fingerprint_same_content(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "a")
        open(p, "wb").write(b"abc" * 50000)
        self.assertEqual(common.fingerprint_file(p), common.fingerprint_bytes(b"abc" * 50000))


if __name__ == "__main__":
    unittest.main()
