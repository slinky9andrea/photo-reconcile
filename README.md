# photo-reconcile

Swap the JPGs in your organized photo folders for the **original HEIC files** from your iPhone,
and bring along what your phone knows about each photo: **captions, people's names and the
locations you set**, all without touching your folder structure or file names.

Built for people who have years of iPhone photos exported as JPGs into hand-organized,
hand-renamed folders (`~/Pictures/2019/2019-07-12 Pittsburgh/...`) and want the
higher-quality originals back in place.

```
~/Pictures/2023/2023-12-14 Birthday-Trip-03.jpg   ->   ~/Pictures/2023/2023-12-14 Birthday-Trip-03.heic
                                                       + caption, people, location from your iPhone
```

## What it does

| Step | Command | Changes your photos? |
|---|---|---|
| 1 | `extract`: copy HEIC originals and the Photos database out of an iPhone backup | No |
| 2 | `match`: pair each JPG with its HEIC by exact capture time | No |
| 3 | `replace`: put the HEIC where the JPG was, same name, same file dates | Yes (dry run first, undoable) |
| 4 | `tag`: write phone captions, people and locations into every matched photo | Yes (dry run first, backed up) |
| - | `report`: list replacements where the HEIC added nothing | No |
| - | `undo`: put JPGs back (all, or a list) | Yes |

**Safety first:**
- Every changing step is a **dry run** unless you add `--go`, and then asks you to type `YES`.
- Nothing is deleted. Replaced JPGs are **moved** to `~/PhotoReconcile/replaced_jpgs`, and `undo` puts them back.
- Files are copied to `~/PhotoReconcile/tag_backup` before tags are written.
- Your iPhone backup is only ever read.

**Smart about edge cases:**
- **Crops are kept.** If your JPG was cropped (a different shape, or trimmed edges), it stays a JPG. Replacing it would undo your crop.
- **Burst shots:** when several frames share the same second, the images are compared and only a clear match is used.
- **Copies:** the same photo filed in two folders gets the HEIC in both. Two *different* JPGs claiming one HEIC are left alone.
- **Captions and names aren't stored inside iPhone photo files.** They live in the phone's Photos database, so step 4 reads them from there and writes them into the files where Finder, Spotlight, Preview and Photos can see them.
- **Locations you added by hand** on the iPhone (even to old camera photos in your iCloud library) are written only where a file has no location.
- **Incomplete backups:** if the Photos database in the backup is incomplete (common while the phone is still syncing with iCloud), every readable record is recovered.

## Requirements

- macOS (uses Finder backups, Keychain, `sips`)
- Python 3.9+
- [exiftool](https://exiftool.org): `brew install exiftool`
- An **encrypted** local iPhone backup: in Finder, select the iPhone, tick *Encrypt local backup*, then *Back Up Now*.
  (Unencrypted backups leave out the Photos database.)
- Terminal needs **Full Disk Access** to read backups:
  System Settings > Privacy & Security > Full Disk Access > add Terminal.

```bash
git clone https://github.com/<you>/photo-reconcile.git
cd photo-reconcile
python3 -m pip install -r requirements.txt
```

## Usage

Run everything from the `photo-reconcile` folder.

```bash
python3 -m photoreconcile backups            # which backups exist (newest first)

python3 -m photoreconcile extract            # 1. HEICs + Photos database -> ~/PhotoReconcile
python3 -m photoreconcile match              # 2. read-only; writes matches.csv

python3 -m photoreconcile replace            # 3. dry run: shows the plan
python3 -m photoreconcile replace --go       #    do it

python3 -m photoreconcile tag                # 4. dry run: what would be written
python3 -m photoreconcile tag --go           #    write it

python3 -m photoreconcile report             # optional: where did the HEIC add nothing?
python3 -m photoreconcile undo --list ~/PhotoReconcile/no_extras.csv   # ...and put those JPGs back
```

The backup password is read from Keychain (entries named "iOS Backup" or "iPhone Backup"),
or from `$PHOTO_RECONCILE_BACKUP_PASSWORD`. Otherwise you're asked for it.

### Useful options

| Option | Step | What it does |
|---|---|---|
| `--pictures DIR` | all | Your photo folder (default `~/Pictures`) |
| `--workdir DIR` | all | Where everything this tool creates goes (default `~/PhotoReconcile`) |
| `--backup ID_OR_PATH` | extract, tag, inventory | Use a specific backup instead of the newest |
| `--existing DIR` | extract | HEICs you extracted before; identical ones are skipped |
| `--heic-dir DIR` | match | Extra folder of HEICs to match against |
| `--replace-cropped` | replace | Also replace cropped JPGs (loses the crop) |
| `--what caption,people` | tag | Only write some kinds of tags |
| `--rename "Jane (Me)=Jane Doe"` | tag | Write a person's name differently |
| `--include-png` | tag | Also tag PNGs (screenshots) |
| `--refresh-db` | tag | Re-read the Photos database from a newer backup |
| `--copy-since 2026-06-01` | inventory | Copy everything taken since a date out of the backup |

### Files it creates (in `~/PhotoReconcile`)

| File | Contents |
|---|---|
| `heic/` | HEIC originals from the backup |
| `phone_photos.sqlite` | The phone's Photos database |
| `matches.csv` | Every JPG/HEIC pair, with `confident` / `review` and why |
| `heic_without_jpg.csv` | Photos on the phone you never kept in your folders |
| `replace_plan.csv`, `replace_log.csv` | What `replace` will do / did (`undo` uses the log) |
| `replaced_jpgs/` | Your original JPGs, same subfolders |
| `tag_plan.csv`, `tag_backup/` | What `tag` writes / copies of files before tagging |
| `heic_extras_report.csv`, `no_extras.csv` | What each HEIC adds over its JPG |

## How matching works

1. **Same moment:** a JPG and a HEIC must have the same EXIF capture time, to the second.
2. **Burst shots:** sub-second time decides if both files have it. Otherwise each candidate is
   shrunk to a 32x32 grayscale thumbnail and compared with the JPG; a winner must be both close
   and clearly closer than the runner-up, or the JPG is kept.
3. **Crops:** a JPG with a different aspect ratio, or the same ratio at a non-standard smaller size
   (edges trimmed), is treated as cropped and kept.
4. **Phone records (tag step):** files are matched to the Photos database by local capture time,
   using the original `IMG_1234` name and camera model to break ties.

## Good to know

- **Few HEICs in the backup?** With *Optimize iPhone Storage* on, full-size originals stay in iCloud.
  Turn on *Download and Keep Originals* (Settings > Photos), let it finish, then back up again.
- **Recent photos are JPG, not HEIC?** Check Settings > Camera > Formats. *Most Compatible* saves JPGs.
- **Live Photos:** the video half isn't copied.
- **Portrait depth and HDR** data stay in the HEIC; they can't be added to a cropped JPG.
- Run `python3 -m unittest discover tests` to check the decision logic.

## License

MIT

## Credit

Vibe-coded with Claude Opus 5.5 Medium
