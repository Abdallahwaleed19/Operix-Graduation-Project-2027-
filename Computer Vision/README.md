# Operix CV — Computer Vision Team Guide

> **Project:** Operix – AI-Powered Industrial Vision & Safety Intelligence Platform
> **Scope of this document:** how the three-person Computer Vision team builds, tests, and integrates its modules.
> **Research date:** 2026-11-19. Dataset facts below were checked against official pages or original papers on this date. Anything we could not confirm is tagged **Needs Verification**.

---

## How to read the tags

| Tag | Meaning |
|---|---|
| **[Confirmed]** | Checked on an official source (dataset page, paper, or Ultralytics docs). |
| **[Recommendation]** | Our engineering advice. Not a fact about a tool. |
| **[Assumption]** | Something we assume about our own setup. Change it if it turns out wrong. |
| **Needs Verification** | Could not be confirmed. The text says how to verify it. |

---

## Table of Contents

1. [Project context](#1-project-context)
2. [The three modules and who owns them](#2-the-three-modules-and-who-owns-them)
3. [Datasets](#3-datasets)
4. [Google Colab: the shared environment](#4-google-colab-the-shared-environment)
5. [Repository structure and Git rules](#5-repository-structure-and-git-rules)
6. [Shared interface and event contract](#6-shared-interface-and-event-contract)
7. [Workflow per member](#7-workflow-per-member)
8. [Data splitting and evaluation standards](#8-data-splitting-and-evaluation-standards)
9. [Testing and final integration plan](#9-testing-and-final-integration-plan)
10. [Work distribution and timeline](#10-work-distribution-and-timeline)
11. [Troubleshooting](#11-troubleshooting)
12. [Open items (Needs Verification)](#12-open-items-needs-verification)
13. [References](#13-references)

---

## 1. Project context

Operix turns existing CCTV cameras into a safety-monitoring system. The CV team builds three independent modules. Each module takes video frames and returns structured results. A separate backend layer (not part of this repo) will consume them later.

### 1.1 Our camera

| Item | Value |
|---|---|
| Model | Skyworth LC2308 (I63D4H2-AWT) |
| Resolution | 2304 × 1296 |
| Native FPS | about 19.9 |
| Transport | RTSP over TCP |
| URL | **Never written in this repo.** Read it from the environment variable `OPERIX_RTSP_URL`. |

We already have a local Python RTSP ingestion module (OpenCV, threading, auto-reconnect), called `CameraStream` in this guide. **We do not modify it.**

> **[Recommendation]** Add `OPERIX_RTSP_URL` to your local shell profile or a local `.env` file. `.env` is in `.gitignore`. Never paste the URL in notebooks, commits, issues, or screenshots.

### 1.2 Colab versus local: what runs where

| Environment | Used for | Can reach the camera? |
|---|---|---|
| **Google Colab** | Development, experiments, training, evaluation on uploaded MP4 files | **No.** Colab runs in Google's cloud. It cannot reach a private LAN address such as `192.168.x.x`. |
| **Local laptop/PC** (same network as the camera) | Final RTSP tests using our existing `CameraStream` | Yes |

**[Confirmed by design]** Colab cannot open our private camera address. So the plan is:

1. **In Colab:** work on MP4 clips (public datasets plus our own recordings).
2. **Capture real camera footage** locally and upload it to Colab as MP4:
   ```bash
   # Run on a local machine on the camera's network. The URL comes from the environment.
   ffmpeg -rtsp_transport tcp -i "$OPERIX_RTSP_URL" -c copy -t 60 clip_cam01_001.mp4
   ```
   `-c copy` avoids re-encoding. If the clip does not play, drop `-c copy` and let ffmpeg re-encode.
3. **Later, on a local machine:** run the same module code with frames from `CameraStream` (see [§9.4](#94-mp4-first-then-rtsp)).

> **[Assumption]** Colab is for development and training, not production. Production inference will run on a machine we control. That machine is decided later and is outside this guide.

> **[Recommendation]** The camera is 2304 × 1296. Ultralytics resizes input internally (default `imgsz=640`) and reports boxes in the original frame's pixel coordinates. Do not resize the frame yourself before calling the model. Verify this on your first test by drawing a box on the original frame.

---

## 2. The three modules and who owns them

| Member | Module | Main tasks | Training required | Main deliverables |
|---|---|---|---|---|
| **Member 1** | Person Detection + Tracking + Restricted-Zone | Detect people, track with ByteTrack, define polygon zones, emit zone entry/exit events | **No** (pretrained YOLO + ByteTrack) | `PersonTrackingModule`, zone config format, tracking evaluation notebook, sample events |
| **Member 2** | Fall Detection | Pose estimation, temporal rules, distinguish falls from normal activities, emit potential-fall events | **No** (pretrained pose + rules, threshold tuning only) | `FallDetectionModule`, tuned thresholds file, evaluation report, sample events |
| **Member 3** | PPE Detection (helmet / vest) | Fine-tune a YOLO detector, associate PPE with the right person, decide compliance, emit violation events | **Yes** (fine-tune) | `best.pt` checkpoint, `PPEDetectionModule`, dataset-preparation scripts, evaluation report, sample events |

> We never describe the system as diagnosing a person's health. Member 2's module detects **potential fall events** only.

### 2.1 Member 1: Person Detection + Tracking + Restricted-Zone

**Pipeline:** frame → YOLO person detection → ByteTrack (Track IDs) → foot point per person → point-in-polygon test per zone → enter/exit events.

- **Detector [Confirmed]:** Ultralytics YOLO26 detection models (`yolo26n.pt` … `yolo26x.pt`) are pretrained on COCO, which includes the class `person` (class id 0).
- **Tracker [Confirmed]:** Ultralytics supports BoT-SORT and ByteTrack. **The default tracker is BoT-SORT.** To use ByteTrack you must pass `tracker="bytetrack.yaml"`.
- **ByteTrack is an algorithm, not a model we train [Confirmed by design].** It takes detections each frame and links them across frames. It has parameters (thresholds, buffer size), but no weights to train.
- **Zones:** polygon coordinates and a point-in-polygon test (geometry, not machine learning).

**Is fine-tuning ever needed? [Recommendation]** Only if the pretrained detector measurably fails on our camera. Typical triggers:

- People are missed because of high mounting angle, small size, or heavy occlusion.
- Many false detections (mannequins, posters, reflections).
- Poor detection in our lighting.

If that happens: collect and label frames from our own camera, then fine-tune the same way Member 3 does. Do not do this until the pretrained baseline has been evaluated on our own clips.

**MOT17 for Member 1:** see [§3.3](#33-member-1-datasets).

### 2.2 Member 2: Fall Detection

**Pipeline:** frame → pose model (people + 17 keypoints) → per-person keypoint history → rule-based temporal analysis → potential-fall event.

- **Pose model [Confirmed]:** Ultralytics docs state that YOLO26 pose models use the `-pose` suffix and are pretrained on COCO keypoints. Checkpoint names listed in the official YOLO26 table: `yolo26n-pose.pt`, `yolo26s-pose.pt`, `yolo26m-pose.pt`, `yolo26l-pose.pt`, `yolo26x-pose.pt`. Start with `yolo26n-pose.pt`.
- **Tracking works with pose models [Confirmed]:** the Ultralytics docs say tracking is available for Detect, Segment, and Pose models. So Member 2 can run `model.track(...)` on the pose model to get per-person history.
- **No training from scratch. No training initially.** We tune thresholds on fall and normal-activity videos.

**When would fine-tuning or a separate classifier become necessary? [Recommendation]**

- Rules produce too many false alarms on activities we care about (e.g., crouching to pick something up) and threshold tuning cannot fix it.
- Keypoints are unreliable on our camera (small people, occlusion by machines).
- In that case, consider a small classifier on keypoint sequences (the input is numbers, not images). Fall datasets are small, so evaluate carefully and keep the rule-based version as the baseline.

### 2.3 Member 3: PPE Detection

**Pipeline:** frame → YOLO detector fine-tuned on PPE classes → associate each PPE box with a person → compliance decision → violation event.

**Why detecting a helmet "somewhere in the frame" is not enough:** if worker A wears a helmet and worker B does not, a frame-level "helmet present" check says everything is fine. We must tie each helmet/vest to a specific person, and look in the right region (helmet → head region, vest → torso region).

Details in [§7.3](#73-member-3-ppe-detection-workflow).

---

## 3. Datasets

> **Roles used in this guide**
>
> | Role | Meaning |
> |---|---|
> | **Training** | Used to update model weights. |
> | **Validation** | Used during development to evaluate and tune (checkpoint choice, thresholds). |
> | **Testing** | Held out until the final evaluation. Never used for tuning. |
> | **Benchmarking** | Compare against established published results. |
> | **Dev / Pipeline testing** | Check that code, inference, and integration work. No performance claim. |
>
> A dataset can have more than one role **only if the split is done correctly** (see [§8](#8-data-splitting-and-evaluation-standards)).
>
> Do not confuse: *publicly downloadable* ≠ *free for commercial use*; *unlabeled video* ≠ *supervised training data*; *evaluating* a model ≠ *training* it; a *tracking benchmark* ≠ a *detector training set*.

### 3.1 Comparison table

| Dataset | Module | Official Link | Content | Labels/Annotations | Format | Training Use | Validation Use | Testing Use | License | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| **MOT17** | M1 | https://motchallenge.net/data/MOT17 | Pedestrian videos: 14 base sequences (7 train, 7 test); each provided with 3 public detection sets (DPM, FRCNN, SDP) | Train: ground-truth boxes with identities. Test: ground truth **not public** (evaluated by submitting to the MOTChallenge server) | Image sequences + MOTChallenge text files (`gt/gt.txt`, `det/det.txt`) | **Not used** (not our workflow) | Optional: tune tracker parameters on train sequences | **Benchmark / evaluation**: tracking metrics on the train sequences; test split only via server | **Needs Verification** (follow the terms on the MOTChallenge site; a Hugging Face mirror lists `license: other`) | Street/surveillance scenes, not factories; many sequences have moving cameras |
| **UR Fall (URFD)** | M2 | https://fenix.ur.edu.pl/~mkepski/ds/uf.html | 70 sequences: 30 falls + 40 ADL, 2 Kinect cameras (falls), 1 camera (ADL), plus accelerometer data | Sequence type (fall/ADL) from file names; extracted-feature CSVs with a per-frame posture label from depth: `-1` not lying, `1` lying, `0` transition | RGB and depth PNG sequences (zip), synchronization CSV, accelerometer CSV, and an MP4 per sequence | Not for training our rule system | **Yes** (threshold tuning) | **Yes** (if held out) | **CC BY-NC-SA 4.0**, non-commercial academic use | Indoor staged scenes (office/home). Few sequences. Depth-based labels. |
| **GMDCSA-24** | M2 | https://doi.org/10.5281/zenodo.13354453 (also GitHub `ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos`) | 160 clips: 81 falls + 79 ADL, 4 subjects, 3 homes, includes occlusions | Raw MP4 + CSV text files (exact CSV contents **Needs Verification**: open a sample) | MP4 + CSV | Not for training our rule system | **Yes** | **Yes** (held out by subject) | **Needs Verification** | Homes, not factories. Few subjects. |
| **CAUCAFall** | M2 | https://data.mendeley.com/datasets/7w7fccy7ky (DOI 10.17632/7w7fccy7ky.5) | 10 subjects × (5 falls + 5 ADL), one fixed camera at a corner, varied lighting including night | Per-frame labels `fall` / `no-fall` (manual), stored as `.txt` per frame | Per activity: `.avi` video + `.png` frames + `.txt` labels | Not for training our rule system | **Yes** | **Yes** (held out by subject) | **Needs Verification** (the Mendeley page shows a licence field; read it) | Home environment. 100 clips. |
| **SH17** | M3 | https://github.com/ahmadmughees/SH17dataset , https://zenodo.org/records/12659325 | 8,099 images, 75,994 instances, 17 classes | YOLO and Pascal VOC labels; `train_files.txt` and `val_files.txt` lists | JPEG images + `.txt` (YOLO) + `.xml` (VOC) | **Yes** (fine-tune) | **Yes** (official val list) | **No official test split** (we create our own) | **Conflicting statements, see §3.5.** Treat as **non-commercial, research only**. | Pexels stock photos, not real CCTV. Not every classes' example count is large. No explicit "no helmet" / "no vest" class. |
| **Roboflow "Helmet Vest Only"** | M3 | https://universe.roboflow.com/zols/helmet-vest-only | PPE images. The page's class list (from its code sample) includes `Person`, `Hardhat`, `Safety Vest`, `NO-Hardhat`, `NO-Safety Vest` | Bounding boxes; export to YOLO format is offered by Roboflow | Roboflow export (YOLO available) | Possible (vest strengthening) | Possible | Possible if the dataset has a test split | **Needs Verification** (image count, split sizes, licence not visible to us) | Bot-protected page: open it in a browser. Class names differ from SH17. |
| **Ultralytics Construction-PPE** | M3 | https://docs.ultralytics.com/datasets/detect/construction-ppe/ | See §3.5: **two inconsistent descriptions found** | YOLO boxes | YOLO format, `construction-ppe.yaml` | Possible | Possible | Possible (if it has a separate test split) | **Conflicting: AGPL-3.0 vs CC BY 4.0, see §3.5** | Construction scenes. Check the page you download from. |
| **Our own recorded clips** | M1, M2, M3 | n/a | Staged scenarios in our own environment | We label them ourselves | MP4 | Only if we label and split correctly | Yes | **Yes: this is our main test set** | Ours (get consent from everyone filmed) | Small |

### 3.2 General rules

- Download only what you need first. Large downloads can wait.
- Keep a `DATASETS.md` in `docs/` with source URL, date, license text, split, and preprocessing for every dataset you use.
- Never commit datasets to Git (see [§5.3](#53-git-rules)).

### 3.3 Member 1 datasets

**What MOT17 contains [Confirmed]:** 14 pedestrian sequences (7 train + 7 test). The same videos as MOT16, but with more accurate ground truth. Each sequence comes in three variants (`-DPM`, `-FRCNN`, `-SDP`) that differ in the public detection files, not in the video. Training sequences: MOT17-02, 04, 05, 09, 10, 11, 13. Test sequences: MOT17-01, 03, 06, 07, 08, 12, 14. Training sequences include `gt/gt.txt`.

**Do we need MOT17?**

| Question | Answer |
|---|---|
| Needed for training YOLO person detection? | **No.** We use the pretrained COCO model as-is. MOT17 is a tracking benchmark, not part of our detector training. |
| Needed for the initial YOLO + ByteTrack implementation? | **No.** Our own clips are enough to get started. |
| What is it good for? | **Benchmarking / evaluating tracking** (ID stability, ID switches) on the training sequences, using their ground truth. It also gives us ready-made multi-person video for pipeline testing. |
| Can MOT17 annotations evaluate Track IDs and metrics? | **Yes, on the training sequences** (ground truth with identities). Metrics such as MOTA, IDF1, ID switches can be computed with an evaluation library. **Test-sequence ground truth is not public**; scores for the test split come only from the MOTChallenge server. |

**Which parts are relevant?** **[Recommendation]** Download only **MOT17-04** (1920×1080, pedestrian street at night, **elevated viewpoint**, similar to a CCTV view) and **MOT17-02** (1920×1080, people walking in a large square), from the training split. Images are the same across the `-DPM/-FRCNN/-SDP` folders. Pick one folder per sequence. Verify the folder layout after download.

**Caution:** MOT17 ground truth contains entries that are not ordinary visible pedestrians (the `conf` and `class` columns mark what counts). Filter them according to the MOTChallenge format description before computing metrics. Check the exact filtering rule in the MOTChallenge paper or the devkit before you trust a number. **Needs Verification.**

> **[Recommendation]** For practical testing, record clips with our actual camera (2304 × 1296): people walking in different directions, entering and leaving a taped-off zone, crossing each other.

### 3.4 Member 2 datasets

The rule-based system does **not** train on these. They are used for **tuning thresholds (validation)** and **final testing**. Split **by subject or recording session**, never by random frame (see [§8](#8-data-splitting-and-evaluation-standards)).

#### URFD (UR Fall Detection)

- **Content [Confirmed]:** 70 sequences (30 falls + 40 ADL). Falls recorded with 2 Kinect cameras plus accelerometer data; ADL with one camera. Camera 0 is parallel to the floor, camera 1 is ceiling-mounted.
- **Files [Confirmed]:** for every sequence the page offers depth zip, RGB zip (PNG sequences), a synchronization CSV, an accelerometer CSV, and **MP4 videos** (`fall-XX-cam0.mp4`, `adl-XX-cam0.mp4`). Use the MP4 files with a pose model.
- **Labels [Confirmed]:** the sequence type is in the name (`fall-` or `adl-`). The extracted-features files `urfall-cam0-falls.csv` and `urfall-cam0-adls.csv` hold a per-frame posture label (`-1` not lying, `1` lying, `0` transition).
- **Works with a pose + rule system?** Yes, via the MP4 files. Sequence type gives event-level ground truth.
- **License [Confirmed]:** CC BY-NC-SA 4.0, intended for non-commercial academic use. Commercial use requires contacting the authors.
- **Access:** direct download from the page, no registration visible. **Size:** not verified. Download a few sequences first.
- **Preprocessing:** none for MP4. If you use PNG sequences, convert to video or iterate over frames in order.

#### GMDCSA-24

- **Content [Confirmed]:** 160 clips (81 falls, 79 ADL), 4 subjects, three home setups, varied lighting, includes occlusions. ADL includes complex activities (the paper mentions sleeping, picking up objects, push-ups).
- **Format [Confirmed]:** raw video (MP4) and text files (CSV).
- **Size [Confirmed from the paper]:** about 1.95 GB (as of July 2024).
- **Access:** Zenodo record (DOI 10.5281/zenodo.13354453) and the GitHub repository named above. A Zenodo version 2.0 record is listed as "Open". Whether a login is required for the file download: **Needs Verification.**
- **Labels:** the CSV files are the annotations. **Needs Verification:** open one CSV and document the columns in `docs/DATASETS.md` before writing evaluation code.
- **License:** **Needs Verification** (read the Zenodo record and GitHub README).
- **Good for:** testing false alarms on non-fall activities (the paper states robustness against false positives is an explicit goal), and testing with occlusion.

#### CAUCAFall

- **Official source [Confirmed]:** Mendeley Data, https://data.mendeley.com/datasets/7w7fccy7ky (DOI `10.17632/7w7fccy7ky.5`, version 5 published 2025-03-18; version 4 was published 2022-07-12 and is described in the Data in Brief paper).
- **Content [Confirmed]:** 10 subjects, each performing 5 fall types (forward, backward, left, right, from sitting) and 5 ADLs (walking, hopping, picking up an object, sitting, kneeling). One fixed HIKVISION camera at an upper corner. Lighting: natural, artificial, and night. Reported camera capture: 23 fps, 1080 × 960.
- **Format [Confirmed]:** 10 subject folders × 10 activity folders; each activity has an `.avi` video, `.png` frames, and a `.txt` label per frame.
- **Labels [Confirmed]:** frames labelled `fall` or `no-fall` (manual). The paper describes the labels as segmentation-style files for YOLO detectors. **Needs Verification:** open a label file and document its format before evaluation.
- **Size:** the GMDCSA-24 paper's comparison table lists 7.75 GB for CAUCAFall (as of July 2024). Download only a few subjects at first.
- **License:** **Needs Verification** (read the licence field on the Mendeley page).
- **Good for:** frame-level and event-level evaluation with clear fall/ADL labels, and lighting variety. Includes kneeling, sitting, and picking-up as non-fall activities.

#### Recommended starting dataset for Member 2

**Start with URFD.** Reasons: small, per-sequence MP4 files, clear fall/ADL naming, direct download. Then add **CAUCAFall** (a few subjects) for frame-level labels and lighting variation, and **GMDCSA-24** for false-alarm testing. Finish with our own clips, which are the closest to our camera.

#### Making our own controlled test videos safely

- Use a **thick crash mat** (gym or judo mat) large enough for the whole fall. Remove hard objects nearby.
- Falls are **staged by volunteers who agree**. Practice slow motion first. No one falls from a height, and no one falls onto a hard floor.
- Record with an adult supervising. Stop immediately if anyone is uncomfortable.
- Scenarios (several takes each, both directions, near/far from the camera): forward fall, backward fall, sideways fall, fall from a sitting position.
- Non-fall activities: walking, sitting down on a chair, bending to pick something up, kneeling, crouching, deliberately lying down slowly, stretching.
- Get verbal or written consent from everyone filmed, and store videos only in the team's private Drive folder.

### 3.5 Member 3 datasets

> **Important discrepancies found while checking sources.** We could not make these consistent. Treat the **strictest** statement as binding until the team verifies directly.

#### SH17

- **Official links:** GitHub https://github.com/ahmadmughees/SH17dataset , Zenodo https://zenodo.org/records/12659325 , paper https://arxiv.org/abs/2407.04590 .
- **Size [Confirmed]:** 8,099 annotated images, 75,994 instances, 17 classes.
- **Classes [Confirmed from the Zenodo description]:** Person, Head, Face, Glasses, Face-mask-medical, Face-guard, Ear, Earmuffs, Hands, Gloves, Foot, Shoes, Safety-vest, Tools, Helmet, Medical-suit, Safety-suit.
- **Contains helmet and vest classes? Yes:** `Helmet` and `Safety-vest`, plus `Person` and `Head`.
- **Does NOT contain "no helmet" / "no vest" classes.** A person without a helmet is represented by a visible `Head` with no `Helmet`. This matters for how we decide compliance (see §7.3).
- **Annotation format [Confirmed]:** YOLO `.txt` labels (`labels/`) and VOC (`voc_labels/`), plus `train_files.txt` and `val_files.txt`. **There is no test list.** We must create our own test set.
- **Where to download:** the GitHub README says the images and labels are on **Kaggle**, and that images can also be downloaded with a script from Pexels. The Zenodo page lists the files as **Restricted** (a login or access request is needed). Whether Kaggle requires an account: **Needs Verification** (Kaggle normally requires a free account).
- **Class IDs:** the order in the Zenodo list is 1–17, but the YOLO label files use their own numeric IDs. **Needs Verification:** read the dataset's `.yaml`/class list. **Never hard-code class IDs from memory;** map by class name (§7.3).
- **License: conflicting statements.**
  - GitHub README: **CC BY-NC-SA 4.0**.
  - Zenodo record: **CC BY-NC 4.0** (without ShareAlike).
  - An EurekAlert press image caption: **CC BY-NC-ND** (no derivatives).
  - The README and Zenodo also say the images were scraped from Pexels and the data is "intended for educational, research, and analysis purposes only" and may be used "for training of the machine learning models only"; users must follow the Pexels licence.
  - **What this means for us [Recommendation]:** treat SH17 as **non-commercial, research/educational use only**. **NC** = no commercial use. **SA** (if applicable) = anything we publish that is derived from the dataset must carry the same license. **ND** (if applicable) = no derivative works, which could even affect relabeling and merging. Credit the authors. Do not redistribute the images. A trained model's licence status is legally unclear: **Needs Verification** with your supervisor before any commercial use. For a graduation project, non-commercial use is the stated intent.
- **Strengths:** industrial/manufacturing scenes, many classes, large, official train/val lists.
- **Limitations:** stock photos (clear, well-lit), not low-quality CCTV; small objects such as ears are included; no test split; no explicit violation classes.

#### Roboflow "Helmet Vest Only"

- Link: https://universe.roboflow.com/zols/helmet-vest-only (opens in a browser; automated access was blocked during our check).
- **Classes [from the page's code sample]:** `Person, Hardhat, Safety Vest, NO-Hardhat, NO-Safety Vest`.
- **Image count, split sizes, and license: Needs Verification.** Open the page and record them. (Another dataset by the same author, `all-apd`, shows CC BY 4.0, but that does **not** prove this one has the same license.)
- **Download:** Roboflow requires a (free) account to download an export. **Needs Verification.**
- **Use:** possible source of extra vest examples. **Format:** YOLO export available.
- **Class mapping needed:** yes (`Hardhat` → `helmet`, `Safety Vest` → `safety_vest`, `Person` → `person`). **Do not import the `NO-*` classes** (see strategy below).

#### Ultralytics Construction-PPE

- Docs: https://docs.ultralytics.com/datasets/detect/construction-ppe/
- **We found two inconsistent descriptions. Check the page and the file you actually download:**

| Source | Images | Classes | Splits | License |
|---|---|---|---|---|
| Ultralytics dataset docs page | **1,416** (1,132 train / 143 val / 141 test) | **11**: helmet, gloves, vest, boots, goggles, none, Person, no_helmet, no_goggle, no_gloves, no_boots | train/val/**test** | **AGPL-3.0** |
| Ultralytics blog post (dated Nov 2026, says it was released with Ultralytics 8.4.200) | **1,000** (14,863 boxes) | **12** (includes forklift) | fixed 800/200 train/val, **no test split** | **CC BY 4.0** |

- **Conclusion:** the docs page and the blog describe different versions. **Needs Verification.** Download the dataset, count images and classes yourself, and save the license file you receive.
- The docs page says there is **no dedicated "missing vest" label** (`vest` has no `no_vest` counterpart). So vest violations cannot be learned directly from this dataset. They must come from absence logic.
- **Strengths:** small, YOLO format, ready to train, includes missing-PPE labels for helmet. **Limitations:** construction rather than factory scenes; small.

#### Recommended dataset strategy for Member 3

1. **Define our own class list first** (a small `ppe.yaml`): `person`, `head`, `helmet`, `safety_vest`. Keep `head` because SH17 has no "no helmet" class: a visible head without a helmet is the violation signal.
2. **Stage A (baseline): SH17 only**, keeping only the four classes above (remap by name, drop the others). Use SH17's own train/val lists. Train, evaluate.
3. **Stage B (optional): add Construction-PPE** `helmet`, `vest`, `Person` classes only, after verifying its license and version. Drop `none`, `no_*`, gloves, boots, goggles.
4. **Stage C (optional): add Roboflow vest-only** images, `Person`, `Hardhat`, `Safety Vest` only, after verifying the license. Do not import `NO-*` labels.
5. **Why not import "NO-*" / "none" classes?** Datasets disagree on how they label missing PPE (SH17 has none; Construction-PPE has none for vests; Roboflow has `NO-Safety Vest`). Mixing them gives the model conflicting signals about what an unlabeled head or torso means. Decide violations from detection of `person` + absence of `helmet`/`safety_vest`, not from a learned "NO-" class.
6. **Avoid annotation problems when merging:**
   - Convert everything to the same YOLO format and class IDs through a mapping dict (by name).
   - Drop images whose boxes become empty only if you document it.
   - **Deduplicate** images across datasets (stock-photo sites overlap). Never let a near-duplicate end up in both train and test.
   - Keep a column `source` for every image so you can evaluate per source.
7. **Held-out test set [Recommendation]:** SH17 has no test list. Hold out a set by **image source/photographer-batch if known, else random images that are not near-duplicates**, plus **our own recorded clips (labeled)**. Do not touch it during training or tuning.

### 3.6 What to download first, later, and optionally

| Member | Download first | Postpone | Optional |
|---|---|---|---|
| M1 | Our own recorded clips (2–3 min of people walking, entering a zone). MOT17-04 and MOT17-02 **train** sequences, one detector folder each. | The rest of MOT17. | Test-split server submission. |
| M2 | A handful of URFD sequences (MP4, both fall and ADL). Our own staged clips. | Remaining URFD, remaining CAUCAFall subjects. | A few CAUCAFall subjects and GMDCSA-24 for frame-level labels and false-alarm testing. |
| M3 | SH17 (images + labels + `train_files.txt` / `val_files.txt`). Our own PPE clips for the test set. | Roboflow vest-only. | Construction-PPE (after resolving the version/license discrepancy). |

---

## 4. Google Colab: the shared environment

**Colab GPU availability and session duration are not guaranteed.** Free sessions can end, GPUs can be unavailable, and the runtime type can change. Plan for disconnects (§4.5).

### 4.1 Version policy

| Item | Decision |
|---|---|
| Python | **Use Colab's default Python.** Do not install a custom Python. [Recommendation] Ultralytics requires Python ≥ 3.8 [Confirmed]. A previously published Colab runtime (2025.10) used Python 3.12.12 and PyTorch 2.8.0 [Confirmed from Google's backend-info page]. The version in today's runtime: **Needs Verification: run the version-report cell below on Day 1 and record it in `docs/ENVIRONMENT.md`.** |
| PyTorch / torchvision / NumPy | **Do not reinstall.** Colab ships them built for its GPU runtime [Confirmed]. Reinstalling often breaks CUDA compatibility. |
| OpenCV | **Do not install** `opencv-python-headless`. Colab already has OpenCV and Ultralytics depends on OpenCV. Two OpenCV packages conflict. |
| Ultralytics | **One version for the whole team.** On Day 1, one member installs the latest release, runs the smoke test, and records the exact version. Everyone then pins it in `requirements.txt` (e.g. `ultralytics==X.Y.Z`). The exact number to pin: **Needs Verification on Day 1** (use `pip index versions ultralytics` or the PyPI page, then pick the version that passes the smoke test). Do not copy a version number from this README. |
| Model checkpoints | Record the checkpoint file names and their SHA-256 hashes (see §4.7). |

### 4.2 Standard first cell (copy-paste)

```python
# --- Cell 1: runtime check ---
!nvidia-smi
import sys, torch
print("Python:", sys.version)
print("PyTorch:", torch.__version__, "| CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

If CUDA is not available: **Runtime → Change runtime type → choose a GPU**, then run the cell again.

```python
# --- Cell 2: install (team requirements) ---
# Clone the repo (token/URL handled via Colab Secrets, never pasted in the notebook).
!git clone https://github.com/<ORG>/operix-cv.git /content/operix-cv
%cd /content/operix-cv
!pip install -q -r requirements.txt
```

**When to restart the runtime [Confirmed rule from Colab practice]:** if `pip` upgraded or replaced a package that was already imported in this session (for example NumPy), use **Runtime → Restart session**, then run the cells again (skip the install). Otherwise you do not need to restart.

```python
# --- Cell 3: verify installation ---
import ultralytics, cv2, numpy
ultralytics.checks()
print("ultralytics", ultralytics.__version__, "| opencv", cv2.__version__, "| numpy", numpy.__version__)
```

### 4.3 Shared `requirements.txt` (starting point)

```text
# Pin ultralytics to the version the team agreed on Day 1, for example:
# ultralytics==X.Y.Z
ultralytics
pyyaml
pandas
tqdm
```

- **Do not pin** `torch`, `torchvision`, `numpy`, or `opencv-python`. Colab provides them.
- Module-specific extras go in `member_X/requirements-extra.txt` (e.g. Member 1: a MOT-metrics library for evaluation). Install them after the shared file and re-run `ultralytics.checks()`.
- **Never** add a package that silently upgrades NumPy or OpenCV without telling the team.

### 4.4 Google Drive layout

```python
from google.colab import drive
drive.mount('/content/drive')
```

```text
MyDrive/operix-cv/
├── datasets/        # raw downloads, per dataset
├── test_clips/      # shared recorded videos (see §9.1)
├── weights/         # best.pt files, named with date + member + dataset
├── runs/            # Ultralytics training outputs
└── notes/
```

**[Recommendation]** Copy datasets from Drive to Colab's local disk (`/content/data/...`) before training. Reading thousands of small files directly from Drive is slow. Keep the **outputs** (`runs`, weights) on Drive.

### 4.5 Surviving disconnects

- Save training outputs to Drive: `project="/content/drive/MyDrive/operix-cv/runs"`.
- Ultralytics saves `last.pt` and `best.pt` in the run's `weights/` folder. To resume an interrupted training: load `last.pt` and call `model.train(resume=True)` [Confirmed in the Ultralytics train docs: `resume` restores weights, optimizer, scheduler, and epoch].
- Use `save_period=5` (checkpoint every 5 epochs) for long runs. **Needs Verification** that your Ultralytics version supports this argument: check the Train page of the docs.
- Commit notebooks and code to Git often. Do not leave unsaved work in a Colab session.
- Never keep the only copy of a dataset or weight file in `/content`. It disappears with the session.

### 4.6 Reproducible experiments

- Fix seeds: `model.train(..., seed=0, deterministic=True)`. **Needs Verification** of exact argument names in your Ultralytics version (see the Train page).
- Record each experiment in `docs/experiments.md`: date, member, dataset versions, class mapping file, split files, command, Ultralytics version, GPU, metrics, run folder.
- Save the exact train/val/test file lists with the run, not just the YAML.

### 4.7 Recording package and checkpoint versions

```python
# Version report: paste the output into docs/ENVIRONMENT.md
import sys, platform, torch, ultralytics, cv2, numpy, hashlib, pathlib
print("Python", sys.version.split()[0], "|", platform.platform())
print("torch", torch.__version__, "| cuda", torch.version.cuda, "| gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
print("ultralytics", ultralytics.__version__, "| opencv", cv2.__version__, "| numpy", numpy.__version__)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# for p in pathlib.Path("weights").glob("*.pt"): print(p.name, sha256(p))
```

Also run `!pip freeze > requirements.lock.txt` after a successful run and keep it with the experiment.

### 4.8 Colab security

- Use **Colab Secrets** (the key icon) for tokens such as a GitHub token or Kaggle credentials.
- Do not print secrets. Clear notebook outputs before committing (outputs can contain paths or keys).
- Colab sessions are shared infrastructure: do not upload the real RTSP URL or any unreleased footage that identifies workers.

---

## 5. Repository structure and Git rules

### 5.1 Structure

```text
operix-cv/
├── README.md                     # this file
├── requirements.txt              # shared dependencies
├── .gitignore
├── .env.example                  # names of variables only, no values
│
├── shared/                       # owned jointly; changes need all-member review
│   ├── config.py                 # loads env vars, defaults
│   ├── schemas.py                # FrameResult / Detection / Event dataclasses (§6)
│   ├── video_utils.py            # open MP4, frame iterator, timestamps
│   ├── visualization.py          # draw boxes, tracks, zones
│   ├── events.py                 # event debouncer (start/ongoing/end)
│   └── README.md
│
├── member_1_person_tracking/     # owned by Member 1
│   ├── notebooks/                # exploration only
│   ├── src/                      # reusable code (PersonTrackingModule)
│   ├── configs/                  # tracker yaml, zones.json
│   ├── tests/
│   └── README.md
├── member_2_fall_detection/      # owned by Member 2
│   ├── notebooks/
│   ├── src/                      # FallDetectionModule
│   ├── configs/                  # thresholds.yaml
│   ├── tests/
│   └── README.md
├── member_3_ppe_detection/       # owned by Member 3
│   ├── notebooks/
│   ├── src/                      # PPEDetectionModule, dataset scripts
│   ├── configs/                  # ppe.yaml (class list), class_mapping.yaml
│   ├── tests/
│   └── README.md
│
├── integration/                  # shared; written together in Days 10–11
│   ├── test_pipeline.py
│   └── README.md
├── docs/                         # DATASETS.md, ENVIRONMENT.md, experiments.md
└── outputs/                      # git-ignored: generated videos, JSON, plots
```

| Folder | Contains | Owner |
|---|---|---|
| `shared/` | Interface, schema, utilities used by all | Everyone. **Changes only through a Pull Request approved by all three.** |
| `member_X_*/` | That member's module | The member. Others do not edit it. |
| `integration/` | Script running all three modules | Everyone, in Days 10–11 |
| `docs/` | Dataset notes, environment record, experiment log | Everyone, one file section per member |
| `outputs/` | Generated outputs | Nobody commits it |

**Notebooks vs reusable code [Recommendation]:** exploring and plotting stays in `notebooks/`. As soon as something works, move it into `src/` as a function or class with a clear input/output. Integration code must import from `src/`, **never from a notebook.**

**Configuration files** go in the member's `configs/` folder (YAML or JSON). No magic numbers in code: thresholds, model paths, and zone polygons come from config.

**Model weights and datasets** live on Google Drive (see §4.4). In Git you keep only a small `weights/README.md` with the Drive link, file name, SHA-256, and the training run that produced it.

### 5.2 `.gitignore` (minimum)

```text
.venv/
venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
.env
datasets/
runs/
outputs/
*.pt
*.onnx
*.mp4
*.avi
*.zip
```

### 5.3 Git rules

1. **One shared repository.** `main` is protected: nobody pushes directly.
2. **Branch per member:** `member1/person-tracking`, `member2/fall-detection`, `member3/ppe-detection`. For smaller tasks use `member1/feature-name`.
3. **Pull Requests** into `main`. Another member reviews before merging. The PR description says what changed and how it was tested.
4. **Do not edit someone else's folder.** If you need a change in `shared/`, open an issue or a PR and tell the others first.
5. **Pull before you push:**
   ```bash
   git checkout member1/person-tracking
   git fetch origin
   git merge origin/main      # bring main's updates into your branch
   ```
6. **Basic merge conflict resolution:**
   - Run `git status` to see conflicted files. Open each file and find the markers `<<<<<<<`, `=======`, `>>>>>>>`.
   - Decide with the other person which version to keep (or combine them), remove the markers, then:
     ```bash
     git add <file>
     git commit
     ```
   - Conflicts in `shared/` usually mean two people changed the contract. Talk first, then edit.
7. **Never commit:** datasets, `.venv`, temp files, secrets (`.env`, tokens, RTSP URL), notebook outputs with secrets, large model weights.
8. **Large files [Recommendation]:** use Google Drive for datasets and weights. **Git LFS** is an option for a few small important files (like a final `best.pt`), but note that Git hosting providers limit LFS storage and bandwidth. **Needs Verification** of your provider's limits before relying on it.
9. If a secret is committed by mistake, tell the team immediately, rotate it (change the camera password / token), and do not just delete the commit.

---

## 6. Shared interface and event contract

**Principle:** CV modules return structured Python objects (dicts or dataclasses). They **do not depend on FastAPI or PostgreSQL.** A separate backend adapter will send the results onward later.

### 6.1 Module interface

Modules need **temporal state** (tracker memory, keypoint history), so we do not force a stateless function.

```python
# shared/schemas.py (sketch; the exact file is agreed on Day 1)
from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class Detection:              # an observation in ONE frame (not a confirmed violation)
    label: str                # e.g. "person", "helmet", "safety_vest", "person_pose"
    bbox: list[float]         # [x1, y1, x2, y2] in ORIGINAL frame pixels
    confidence: float         # 0.0 – 1.0
    track_id: Optional[int] = None      # only if this module tracks; else None
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass
class Event:                  # a rule-confirmed thing worth telling the backend
    module: str               # "person_tracking" | "fall_detection" | "ppe_detection"
    event_type: str           # see naming table below
    event_id: str             # uuid4 string; the SAME id for start/ongoing/ended of one episode
    event_state: str          # "started" | "ongoing" | "ended"
    camera_id: str
    timestamp: str            # ISO 8601 UTC, e.g. "2026-11-19T10:30:00.123Z"
    frame_index: int
    bbox: Optional[list[float]] = None
    track_id: Optional[int] = None
    confidence: Optional[float] = None
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass
class FrameResult:
    module: str
    camera_id: str
    frame_index: int
    timestamp: str
    frame_size: list[int]     # [width, height] of the frame the boxes refer to
    detections: list[Detection] = field(default_factory=list)   # never None
    events: list[Event] = field(default_factory=list)           # never None
    schema_version: str = "1.0"
```

```python
class CVModule:
    def __init__(self, config: dict): ...
    def process_frame(self, frame, timestamp=None, camera_id="camera_01", context=None) -> "FrameResult": ...
    def reset(self) -> None: ...      # clear tracker/history (new video, reconnect after long gap)
```

- `frame`: a BGR `numpy.ndarray` (OpenCV convention), shape `(H, W, 3)`, `uint8`.
- `context` (optional dict): lets the integration layer pass other modules' output, e.g. `{"persons": [...Member 1 detections...]}`. A module must work **without** `context` (standalone mode).
- A module **never raises on bad input**: for `None` or an invalid frame it returns an empty `FrameResult` and logs a warning.

### 6.2 Fields

| Field | Required? | Rules |
|---|---|---|
| `module`, `event_type`, `event_id`, `event_state`, `camera_id`, `timestamp`, `frame_index` | **Mandatory** (events) | Strings/ints as described. |
| `bbox` | Optional for events (mandatory for detections) | `[x1, y1, x2, y2]`, **absolute pixels in the original frame**, origin at the top-left, `x2 > x1`, `y2 > y1`. Float allowed. |
| `frame_size` | Mandatory in `FrameResult` | `[width, height]` (e.g. `[2304, 1296]`). Lets anyone convert to normalized coordinates. |
| `confidence` | Optional (events), mandatory (detections) | Float in `[0.0, 1.0]`. For rule-based events (zone entry) use `1.0` or omit and explain in `attributes`. |
| `track_id` | Optional, may be `null` | Integer. **Local to one tracker session on one camera**. Not globally unique, not stable across cameras or after `reset()`. |
| `attributes` | Optional | Module-specific details (see samples). Keep values JSON-serializable. |
| `timestamp` | Mandatory | ISO 8601, **UTC, with `Z`**, milliseconds allowed. For MP4 input: start time + `frame_index / fps`. For live input: capture time. |
| `camera_id` | Mandatory | String such as `camera_01`. Comes from config; never derived from the RTSP URL. |

### 6.3 Event naming

`snake_case`, `<thing>_<what happened>`:

| Module | `event_type` values |
|---|---|
| `person_tracking` | `restricted_zone_entry`, `restricted_zone_exit` |
| `fall_detection` | `potential_fall` |
| `ppe_detection` | `ppe_violation` |

`attributes.zone_id` for zone events; `attributes.missing` (list such as `["helmet"]`) for PPE.

### 6.4 Detections vs confirmed violations

- **Detections** = per-frame observations ("a person box here, a helmet box there"). They are noisy and **are not violations.**
- **Events** = what a **rule** decided after enough evidence (minimum frames / duration). Only events go to the backend as alerts.

### 6.5 Avoiding duplicate events every frame

Every module uses the shared debouncer in `shared/events.py`:

1. A condition must hold for **N consecutive frames (or T seconds)** before an event **starts**.
2. When it starts, emit **one** event with `event_state="started"` and a new `event_id`.
3. While the condition continues, **do not emit again.** (Optionally emit `ongoing` every K seconds.)
4. When the condition is absent for **M consecutive frames**, emit **one** `ended` event with the same `event_id`.
5. After `ended`, a **cooldown** avoids immediate re-trigger.

N, M, T, K and cooldown are **config values**, tuned per module.

### 6.6 Special cases

| Case | How to represent |
|---|---|
| Empty result | `FrameResult` with `detections=[]` and `events=[]`. Never `None`. |
| Multiple people / events in one frame | One `Detection` per person; one `Event` per person per event type. |
| Module doesn't track | `track_id = None`. **Never invent IDs.** |
| Same person across modules | Integration layer matches boxes (IoU) between Member 1's tracks and the other modules' boxes, and adds `attributes.person_track_id`. Member 2 may keep its own pose-tracker IDs in `attributes.local_track_id`. |

### 6.7 Realistic sample outputs

**Member 1: restricted-zone entry**
```json
{
  "schema_version": "1.0",
  "module": "person_tracking",
  "camera_id": "camera_01",
  "frame_index": 1432,
  "timestamp": "2026-11-19T10:30:12.450Z",
  "frame_size": [2304, 1296],
  "detections": [
    {"label": "person", "bbox": [1020.4, 310.2, 1190.8, 760.9], "confidence": 0.91, "track_id": 3, "attributes": {"in_zones": ["zone_press_01"]}},
    {"label": "person", "bbox": [210.0, 420.5, 330.7, 810.1], "confidence": 0.84, "track_id": 5, "attributes": {"in_zones": []}}
  ],
  "events": [
    {"module": "person_tracking", "event_type": "restricted_zone_entry", "event_id": "b7a1c2e0-4f3d-4a52-9d0e-1d1f8c1a7e11",
     "event_state": "started", "camera_id": "camera_01", "timestamp": "2026-11-19T10:30:12.450Z", "frame_index": 1432,
     "bbox": [1020.4, 310.2, 1190.8, 760.9], "track_id": 3, "confidence": 1.0,
     "attributes": {"zone_id": "zone_press_01", "point_used": "bottom_center"}}
  ]
}
```

**Member 2: potential fall**
```json
{
  "schema_version": "1.0",
  "module": "fall_detection",
  "camera_id": "camera_01",
  "frame_index": 2210,
  "timestamp": "2026-11-19T10:31:51.100Z",
  "frame_size": [2304, 1296],
  "detections": [
    {"label": "person_pose", "bbox": [880.0, 640.0, 1290.0, 790.0], "confidence": 0.88, "track_id": null,
     "attributes": {"local_track_id": 2, "torso_angle_deg": 78.5, "aspect_ratio": 2.7, "state": "lying"}}
  ],
  "events": [
    {"module": "fall_detection", "event_type": "potential_fall", "event_id": "6c5e3a90-0f7b-4c1e-8a44-2f6d8b9a3c20",
     "event_state": "started", "camera_id": "camera_01", "timestamp": "2026-11-19T10:31:51.100Z", "frame_index": 2210,
     "bbox": [880.0, 640.0, 1290.0, 790.0], "track_id": null, "confidence": 0.81,
     "attributes": {"local_track_id": 2, "rapid_descent": true, "lying_duration_s": 2.1, "rule_version": "v1"}}
  ]
}
```

**Member 3: PPE violation**
```json
{
  "schema_version": "1.0",
  "module": "ppe_detection",
  "camera_id": "camera_01",
  "frame_index": 880,
  "timestamp": "2026-11-19T10:29:40.020Z",
  "frame_size": [2304, 1296],
  "detections": [
    {"label": "person", "bbox": [600.0, 250.0, 790.0, 840.0], "confidence": 0.93, "track_id": null,
     "attributes": {"person_index": 0, "helmet": false, "safety_vest": true, "compliance": "violation"}}
  ],
  "events": [
    {"module": "ppe_detection", "event_type": "ppe_violation", "event_id": "9d2f7a11-3b6c-4d85-b3a9-5e0c1f2a7d44",
     "event_state": "started", "camera_id": "camera_01", "timestamp": "2026-11-19T10:29:40.020Z", "frame_index": 880,
     "bbox": [600.0, 250.0, 790.0, 840.0], "track_id": null, "confidence": 0.79,
     "attributes": {"helmet": false, "safety_vest": true, "missing": ["helmet"], "person_track_id": null}}
  ]
}
```

(`person_track_id` is filled later by the integration layer from Member 1's output.)

---

## 7. Workflow per member

**Common stages:** (1) prepare Colab → (2) download/inspect data → (3) understand labels → (4) prepare paths → (5) baseline → (6) implement → (7) evaluate → (8) test on unseen videos → (9) test on our own videos → (10) export → (11) implement the interface → (12) commit to your branch → (13) integration examples.

### 7.1 Member 1: Person Detection + Tracking + Restricted-Zone workflow

**No training is required initially.**

1. **Colab:** run §4.2 cells. Mount Drive.
2. **Data:** upload 2–3 own clips; optionally MOT17-04 and MOT17-02 (train).
3. **Baseline detection:**
   ```python
   from ultralytics import YOLO
   model = YOLO("yolo26n.pt")                      # pretrained on COCO
   results = model.predict("clip.mp4", classes=[0], conf=0.3, save=True)   # class 0 = person
   ```
4. **Add ByteTrack [Confirmed API]:**
   ```python
   results = model.track("clip.mp4", classes=[0], tracker="bytetrack.yaml", persist=True, stream=True)
   for r in results:
       ids = r.boxes.id            # may be None when nothing is tracked in this frame
   ```
   For frame-by-frame input (needed for RTSP later), call `model.track(frame, persist=True, tracker="bytetrack.yaml")` for each frame. `persist=True` tells the tracker that frames belong to one sequence [Confirmed].
   - Tracker settings (thresholds, buffer) live in a **copy** of the tracker YAML in `configs/` (e.g. `bytetrack_custom.yaml`). Copy the file from the Ultralytics package; do not change `tracker_type` [Confirmed in docs].
   - **ID persistence:** IDs persist only while the same tracker object lives and the same `persist=True` sequence continues. Calling `reset()` (new video) must create a fresh tracker.
5. **Zone logic (pure geometry):**
   - Store polygons in `configs/zones.json` as **normalized coordinates (0–1)**, so they work at any resolution. Multiply by `frame_size` at runtime.
   - Use the person's **foot point** (bottom-center of the box) rather than the box center.
   ```python
   import cv2, numpy as np
   def inside(poly_px: np.ndarray, point) -> bool:
       return cv2.pointPolygonTest(poly_px.astype(np.float32), (float(point[0]), float(point[1])), False) >= 0
   ```
   - Debounce: **entry** after N consecutive frames inside; **exit** after M consecutive frames outside (see §6.5). Keep state per `(track_id, zone_id)`.
6. **Evaluate (see §8):** detection quality and tracking quality on MOT17 train sequences (with a metrics library; **Needs Verification** of the library and the ground-truth filtering rule); zone events on our own labeled clips.
7. **Unseen + own videos:** run on our camera clips; check ID switches visually (draw IDs).
8. **Export:** `PersonTrackingModule` in `src/` implementing `CVModule`. Output `FrameResult` (§6).
9. **Commit** to `member1/person-tracking`. Open a PR when the unit tests pass.
10. **Integration example:** `integration/test_pipeline.py` calls `process_frame` on every frame of an MP4.

### 7.2 Member 2: Fall Detection workflow

**No training initially.**

1. **Colab + data:** a few URFD MP4 sequences (falls + ADL) and own clips.
2. **Baseline pose inference:**
   ```python
   from ultralytics import YOLO
   pose = YOLO("yolo26n-pose.pt")
   results = pose.track("clip.mp4", tracker="bytetrack.yaml", persist=True, stream=True)
   for r in results:
       kpts = r.keypoints.xy      # shape (num_people, 17, 2) in original pixels
       conf = r.keypoints.conf    # per-keypoint confidence (may be None if no keypoints)
       ids  = r.boxes.id
   ```
   Verify the attribute names against the pose docs in your installed version before relying on them.
3. **Keypoints (COCO-17 order):** 0 nose, 1–2 eyes, 3–4 ears, **5–6 shoulders**, 7–8 elbows, 9–10 wrists, **11–12 hips**, 13–14 knees, 15–16 ankles.
4. **Per-person history:** keep the last W seconds of features per track ID (a `collections.deque` per ID). Drop IDs not seen for a while.
5. **Features per frame (computed from keypoints with sufficient confidence):**
   - `torso_angle`: angle between the shoulder-center → hip-center vector and the vertical axis (near 0° standing, near 90° lying).
   - `aspect_ratio`: box width / height (grows when lying).
   - `hip_drop_speed`: vertical speed of the hip center, normalized by person height (pixel size changes with distance).
6. **Temporal rule (sketch):**
   ```text
   FALL CANDIDATE: within window W seconds, hip_drop_speed > S_fast  AND  torso_angle goes from < A_up to > A_lying
   POTENTIAL FALL (event): the candidate is followed by "lying" (torso_angle > A_lying or aspect_ratio > R)
                           staying low and mostly still for >= T_lie seconds
   ```
   `W, S_fast, A_up, A_lying, R, T_lie` are **placeholders in `configs/thresholds.yaml`. We do not claim values. Tune them.**
7. **Distinguishing falls from normal activity:**
   - *Sitting / kneeling / crouching / bending:* torso angle may change, but the hips do not fall quickly to floor level and the person does not stay horizontal.
   - *Lying down on purpose:* slow descent → no `rapid descent` → not a fall.
   - Use the rapid-descent condition **and** the persistence condition together.
8. **Tune thresholds on a validation set** of normal and fall clips (e.g. a few URFD + CAUCAFall subjects). **Keep a separate test set untouched** (different subjects).
9. **Evaluate (see §8):** fall-event precision/recall, missed falls, false alarms per hour (limited by the length of normal footage we have), detection latency, which normal activities cause false alarms.
10. **Own videos:** staged falls on a mat; long normal-activity footage for false alarms.
11. **Export:** `FallDetectionModule` implementing `CVModule`. If Member 1's `context["persons"]` is available, map IDs by IoU; otherwise use local pose-tracker IDs in `attributes.local_track_id` and leave `track_id` as `null`.
12. **Commit** to `member2/fall-detection`; PR.

### 7.3 Member 3: PPE Detection workflow

**Fine-tune a pretrained detector; do not train from scratch.**

**Step 1: Get and inspect SH17.**
Download, then check: image count, label folder, `train_files.txt`, `val_files.txt`, and the class list/YAML. Print the class names with their numeric IDs, from the files you actually downloaded.

**Step 2: Understand the YOLO label format.**
One `.txt` per image, one line per object: `class_id x_center y_center width height`, all coordinates **normalized to 0–1 relative to the image size**.

**Step 3: Remap classes by name (not by number).**

```yaml
# configs/ppe.yaml  (our class list)
names:
  0: person
  1: head
  2: helmet
  3: safety_vest
```

```yaml
# configs/class_mapping.yaml  (source name → our name; anything not listed is dropped)
sh17:
  Person: person
  Head: head
  Helmet: helmet
  Safety-vest: safety_vest
```

Write a script (`src/prepare_dataset.py`) that: reads the dataset's own class list, builds `source_id → our_id` **by name**, rewrites every label file, drops unmapped boxes, and reports counts before and after. **Check the exact class spelling in the dataset files you downloaded (e.g. `Safety-vest` vs `safety vest`). Needs Verification.**

**Step 4: Create the splits.**
Use SH17's `train_files.txt` and `val_files.txt` for train/val. Create a **test** set (§3.5 step 7) that is never used for tuning. Write the file lists to disk and commit the lists (not the images).

**Step 5: Dataset YAML (Ultralytics format).**

```yaml
# configs/ppe_data.yaml
path: /content/data/ppe          # dataset root on Colab local disk
train: images/train
val: images/val
test: images/test
names:
  0: person
  1: head
  2: helmet
  3: safety_vest
```

**Step 6: Fine-tune.**

```python
from ultralytics import YOLO
model = YOLO("yolo26n.pt")                         # COCO-pretrained starting point
model.train(
    data="configs/ppe_data.yaml",
    epochs=50, imgsz=640, batch=16,
    project="/content/drive/MyDrive/operix-cv/runs", name="ppe_sh17_v1",
)
```

- Start with a **short run** to prove the pipeline works, then a longer run.
- Small objects (helmets far from the camera) may need a larger `imgsz`. Try after the baseline.
- Outputs: `weights/best.pt` and `weights/last.pt`. Copy `best.pt` to `weights/` on Drive with a descriptive name.

**Step 7: Validate and test.**

```python
model = YOLO("/content/drive/MyDrive/operix-cv/weights/ppe_sh17_v1_best.pt")
metrics = model.val(data="configs/ppe_data.yaml", split="val")    # Precision, Recall, mAP
print(metrics.box.map50, metrics.box.map)                          # mAP50, mAP50-95
# Final, once: split="test"
```

- **Precision**: of the detections, how many are correct. **Recall**: of the real objects, how many were found. **mAP50**: average precision at IoU 0.5. **mAP50-95**: averaged over IoU 0.5–0.95 (stricter).
- Look at the confusion matrix and per-class results, not only the average.

**Step 8: Inference on unseen videos and our clips.** Run `predict` on MP4s. Check failures: far-away helmets, dark vests, helmets worn at an angle, occlusion.

**Step 9: Person-to-PPE association (compliance).**

```python
def box_contains_point(box, p):               # box = [x1,y1,x2,y2]
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]

def inter_area(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)

def area(b): return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])

def head_region(person, frac=0.35):           # upper part of the person box
    return [person[0], person[1], person[2], person[1] + frac * (person[3] - person[1])]

def has_helmet(person, helmets):
    hr = head_region(person)
    return any(box_contains_point(hr, ((h[0]+h[2])/2, (h[1]+h[3])/2)) for h in helmets)

def has_vest(person, vests, min_frac=0.5):    # vest mostly inside the person box
    return any(inter_area(person, v) / max(area(v), 1e-6) >= min_frac for v in vests)
```

Rules:
- A **person** must be detected with confidence above a threshold. Missing PPE is decided **per person**.
- **Helmet** is associated if a helmet box center is in the person's head region (or overlaps a detected `head` box). **Vest** is associated if a vest box lies mostly inside the person box.
- **Violation** if the person is detected but no helmet (or vest) is associated for **N consecutive frames**.
- **Unknown, not violation:** if the head is not visible (person turned away, heavily occluded, cropped at the top of the frame), mark `compliance: "unknown"` instead of `violation`. This reduces false alarms.
- Overlapping people (two workers close together) are a known failure case: use the head region and one-to-one matching (a helmet can belong to only one person; match by smallest distance).
- Thresholds (`frac`, `min_frac`, N) are config values, tuned on validation clips.

**Step 10: Export `PPEDetectionModule`.** If `context["persons"]` (Member 1 boxes and track IDs) is provided, use those person boxes and copy the track IDs. Otherwise use the model's own `person` detections and leave `track_id` as `null`.

**Step 11: Commit** to `member3/ppe-detection`; PR.

---

## 8. Data splitting and evaluation standards

### 8.1 Rules for everyone

1. Use **train / validation / test** where applicable.
2. **Avoid data leakage.** Never put frames from the same original video (adjacent frames) into both training and testing.
3. **Split by original video, recording session, subject, or camera,** never by random frames.
4. **Keep the final test set untouched** during training and threshold tuning. Look at it once, at the end.
5. **Record in `docs/DATASETS.md`:** dataset source and version, license, split lists, preprocessing, class mappings.
6. Do not report a number without saying which split and which dataset it came from.

### 8.2 Metrics per module, and what each dataset can actually support

| Module | Metric | Possible with | Not possible with |
|---|---|---|---|
| **M1 detection** | Precision, Recall, mAP | MOT17 **train** ground truth (pedestrian boxes) after format conversion; our own clips if we label boxes | MOT17 test (no public ground truth) |
| **M1 tracking** | IDF1, MOTA, ID switches, other MOT metrics | MOT17 **train** sequences (identities in `gt.txt`) | MOT17 test (server only); our clips unless we label identities |
| **M1 restricted zone** | Event-level precision/recall, missed entries, false entries | Our own clips, with manually noted entry/exit times | Public datasets (no zones for our scenes) |
| **M2** | Fall-event precision/recall, missed falls, detection latency, confusion with normal activities | URFD (sequence type), CAUCAFall (per-frame labels), GMDCSA-24 (labels in CSV, **verify columns**), our clips | None of the public sets is long enough for a reliable *false-alarms-per-hour* estimate: the clips are short. Use our own long normal-activity recordings for that. |
| **M3 detection** | Per-class Precision/Recall, mAP50, mAP50-95, confusion matrix, FP/FN | SH17 val list; our own labeled test frames | A true test number on SH17 (no official test split) |
| **M3 compliance decision** | Per-person compliance accuracy | **Only our own labeled clips:** public PPE sets label objects, not "this person is compliant". We label per-person compliance ourselves for a test set. | Any public dataset directly |

- *Latency (M2)* = time from the actual fall start (from labels) to the event timestamp.
- *False alarms per hour* = false events ÷ hours of normal footage. State the footage length used.
- **Do not promise a metric the ground truth cannot support.** If a metric is not computable, write "not measured" in the report.

---

## 9. Testing and final integration plan

### 9.1 Shared test clip collection

| # | Clip content | Used by |
|---|---|---|
| 1 | Person wearing helmet and vest | M3, M1 |
| 2 | Person without helmet (vest on) | M3 |
| 3 | Person without vest (helmet on) | M3 |
| 4 | Person without both | M3 |
| 5 | Person enters and leaves a taped restricted zone | M1 |
| 6 | Several people walking, crossing each other | M1, M3 |
| 7 | Staged fall on a safe mat (several takes, directions, distances) | M2 |
| 8 | Normal sitting, bending, kneeling, crouching, walking | M2 (false alarms), M3 |
| 9 | Difficult: low light, partial occlusion by a table/machine, backlight | All |

**How to record, name, store, and share:**
- Prefer the **actual camera** (record with `ffmpeg`, §1.2) so resolution, angle, and compression match the real system. Backup: a phone mounted at a similar height.
- **Naming:** `<scenario>_<camera>_<take>_<yyyymmdd>.mp4`, for example `fall_forward_cam01_003_20261120.mp4`.
- **Ground truth file:** one `test_clips/labels.csv` with columns: `clip, scenario, start_s, end_s, event, notes` (event times written by hand while watching the clip).
- **Storage:** the team's private Drive folder `test_clips/`. Never in Git.
- **Consent:** everyone filmed agrees. Avoid filming faces more than needed.
- **Safety:** all fall scenarios on a mat, with supervision, no stunts.
- **Split rule:** decide which clips are validation (for tuning) and which are **test (never tuned on)** before looking at results. Record the decision in `docs/DATASETS.md`.

### 9.2 Final integration checklist

- [ ] All modules accept a BGR `numpy` frame of the same shape convention.
- [ ] All boxes are `[x1,y1,x2,y2]` in **original-frame pixels**; `frame_size` is set.
- [ ] All modules return the `FrameResult` schema (§6). Empty results are lists, not `None`.
- [ ] All timestamps are UTC ISO 8601 with `Z`.
- [ ] Bad input (`None`, empty frame, wrong dtype) is handled without crashing.
- [ ] Tracker/history state is preserved between frames and cleared by `reset()`.
- [ ] Duplicate events are controlled with the shared debouncer.
- [ ] All model paths and thresholds come from config files, not hard-coded paths.
- [ ] No module imports another member's notebook.
- [ ] `integration/test_pipeline.py` runs all three modules on the same MP4.
- [ ] The same modules accept frames from `CameraStream` without code changes.
- [ ] `track_id` is treated as local to a camera session. No code assumes IDs are global.
- [ ] Output JSON validates against the schema (write a small validation test).

### 9.3 Integration design

`integration/test_pipeline.py` (written together):

```text
for each frame (from MP4 or CameraStream):
    r1 = person_tracking.process_frame(frame, ts, camera_id)                    # M1 first
    ctx = {"persons": r1.detections}
    r2 = fall_detection.process_frame(frame, ts, camera_id, context=ctx)
    r3 = ppe_detection.process_frame(frame, ts, camera_id, context=ctx)
    collect events from r1, r2, r3  → print / write JSON lines
```

Each module also works alone (without `context`). This is the contract that lets members work independently and still integrate.

### 9.4 MP4 first, then RTSP

1. **Phase 1: MP4.** Run `test_pipeline.py` on a recorded clip, locally and in Colab. Check output JSON and an annotated video.
2. **Phase 2: local MP4 on the real machine.** Same script on the local machine to rule out environment problems.
3. **Phase 3: RTSP via our `CameraStream`** (unchanged), locally only:
   ```python
   # sketch: do not modify CameraStream; just consume its frames
   import os
   url = os.environ["OPERIX_RTSP_URL"]            # never hard-code
   stream = CameraStream(url)                      # our existing module
   # loop: frame = stream.read() ; timestamp = utc_now() ; call process_frame(frame, timestamp, "camera_01")
   ```
   The exact `CameraStream` method names are in our existing code: **use them as they are**. Log frames per second and per-module latency. Process at most as fast as frames arrive; if the module is slower than the camera, drop frames instead of letting a queue grow.
4. **Compare** the event output for the same scene in MP4 and RTSP mode. Differences usually come from compression, dropped frames, or timestamps.

---

## 10. Work distribution and timeline

### 10.1 Responsibilities

| Member | Module | Main Tasks | Training Required | Main Deliverables |
|---|---|---|---|---|
| 1 | Person + Tracking + Zones | Pretrained detect + ByteTrack, zones, events, tracking evaluation | No | Module, zones config, evaluation notebook, samples |
| 2 | Fall Detection | Pose features, temporal rules, threshold tuning, evaluation | No (tuning only) | Module, thresholds, evaluation report, samples |
| 3 | PPE Detection | Dataset prep, fine-tune, person–PPE association, compliance, evaluation | Yes | `best.pt`, module, dataset scripts, evaluation report, samples |

### 10.2 Schedule (14 days)

| Days | Tasks | Together or alone |
|---|---|---|
| **1** | Create repo, branches, `.gitignore`; agree the schema (§6); standardize the Colab environment and record versions; record the first shared test clips | **Together** |
| **2–3** | Download and inspect datasets (§3.6); run baseline inference on one clip each | Alone |
| **4–7** | Implement modules: M1 tracking + zones; M2 features + rules; M3 dataset prep + training + association | Alone (short daily check-in) |
| **8–9** | Evaluation (§8) and testing on unseen + shared clips; write short evaluation reports | Alone, then compare |
| **10–11** | Implement the common interface (if not already), write `integration/test_pipeline.py`, debounce events | **Together** |
| **12–14** | RTSP testing on a local machine, debugging, final documentation | **Together** |

### 10.3 Dependencies and risks

| Risk | Effect | Mitigation |
|---|---|---|
| Schema changes late | Rewrites in all modules | Freeze the schema on Day 1. Version it (`schema_version`). |
| Colab GPU unavailable or session lost | M3 training delayed | Short runs, `last.pt` on Drive, `resume=True`; shift training to off-peak. |
| Dataset license/format surprises (§3.5) | M3 delays | Start with SH17 only. Resolve discrepancies on Day 2. |
| M3 depends on person boxes | Waiting for M1 | M3 works standalone with its own `person` class; M1's boxes are optional context. |
| Public data differs from our camera | Poor real-world results | Test early on clips from our camera; fine-tune only if needed. |
| False alarms in fall detection | Unusable alerts | Collect long normal footage; tune with persistence rules. |
| RTSP issues at the end | Late discovery of timing bugs | Record a real camera clip on Day 1 and test with `CameraStream` earlier if possible. |

---

## 11. Troubleshooting

| Problem | Checklist / fix |
|---|---|
| **CUDA unavailable in Colab** | *Runtime → Change runtime type → GPU*. Re-run Cell 1. If no GPU is offered, the free quota may be used up: wait, or use fewer/shorter runs on CPU for inference. |
| **Package/version conflicts** | Did someone reinstall `torch`/`numpy`/`opencv`? Restart the session, re-run only the shared install. Compare `pip freeze` with the team's `requirements.lock.txt`. |
| **Colab runtime disconnects** | Outputs on Drive; resume with `last.pt` and `resume=True`; commit code often. |
| **Drive mount / path errors** | Re-run `drive.mount`. Paths are case-sensitive. Print `os.listdir()` of the parent folder. Use absolute paths. |
| **Dataset download fails** | Re-try later; check login/consent (Kaggle, Zenodo restricted files, Roboflow). Download in smaller parts. Keep a checksum list. |
| **Incorrect YOLO YAML paths** | `path:` plus `train:`/`val:` must resolve to the image folders. Check that `labels/` mirrors `images/`. Run a tiny 1-epoch train to see if images are found. |
| **Wrong class IDs / mapping** | Print the class list from the source dataset; map by **name**; after conversion, count boxes per class and visualize ten images with labels drawn. |
| **Invalid or missing annotations** | Check every label has an image, and every value is in `[0,1]`. Remove empty or corrupt labels and log them. Ultralytics prints warnings for corrupt files: read them. |
| **Inconsistent image sizes** | Ultralytics resizes for you; but never hard-code a resolution in post-processing. Always read `frame_size` from the frame. |
| **Out-of-memory (OOM)** | Reduce `batch`, reduce `imgsz`, use a smaller model (`n` instead of `s`), restart runtime to free memory. |
| **Slow inference** | Smaller model, lower `imgsz`, process every Nth frame, confirm GPU is used, avoid per-frame disk writes. |
| **FPS drops** | Measure each stage. Drop frames instead of queuing. For RTSP, keep capture and inference in separate threads (our `CameraStream` already uses a thread). |
| **Tracker IDs change or reset** | Is `persist=True` used for frame-by-frame calls? Is a *new* tracker created each frame by accident? Did `reset()` run? Lower the detection threshold slightly so people are not dropped; raise the tracker buffer; check for large occlusions. |
| **False fall detections** | Review the clip: what activity triggered it? Increase the lying-persistence time, require rapid descent, ignore low-confidence keypoints, add that clip to the negative set. |
| **PPE not matched to the right person** | Draw the head region and PPE boxes. Check overlaps between neighbouring people; use one-to-one matching; mark `unknown` when the head is not visible. |
| **RTSP connection fails** | Camera reachable on the LAN? Correct port (554) and path? TCP transport? Check credentials (env var). Colab cannot reach the camera: test locally. |
| **Different output formats between members** | Validate every output against `shared/schemas.py` in a unit test before merging. |
| **Git merge conflicts** | §5.3 rule 6. Conflicts in `shared/` need a conversation first. |
| **Missing or incompatible weights** | Confirm file name and path. Re-download official weights. Compare the Ultralytics version used to train with the one used to load. Compare SHA-256. |

---

## 12. Open items (Needs Verification)

| # | Item | How to verify | Owner |
|---|---|---|---|
| 1 | Exact Colab Python / PyTorch versions today | Run the version-report cell (§4.7); record in `docs/ENVIRONMENT.md` | All, Day 1 |
| 2 | Ultralytics version to pin | Check PyPI, install, smoke test (§4.1); pin in `requirements.txt` | One member, Day 1 |
| 3 | Training arguments (`seed`, `deterministic`, `save_period`) in the pinned version | Ultralytics Train docs page | M3 |
| 4 | SH17 license (CC BY-NC-SA vs CC BY-NC vs CC BY-NC-ND), and whether Kaggle needs an account | Read each license text; ask the supervisor; treat as non-commercial research only until resolved | M3 |
| 5 | SH17 class IDs and spelling in the downloaded label files | Read the dataset's class list | M3 |
| 6 | Construction-PPE version (1,416 imgs / 11 classes / AGPL vs 1,000 imgs / 12 classes / CC BY 4.0) | Download; count; read the shipped license | M3 |
| 7 | Roboflow Helmet-Vest-Only image count, license, splits, download rights | Open the page in a browser, record in `docs/DATASETS.md` | M3 |
| 8 | GMDCSA-24 license, download login, CSV annotation columns | Zenodo/GitHub pages, open one CSV | M2 |
| 9 | CAUCAFall license; label file format | Mendeley page; open one label file | M2 |
| 10 | MOT17 license terms; the ground-truth filtering rule used for metrics; evaluation library choice | MOTChallenge site and devkit documentation | M1 |
| 11 | Git LFS limits of our Git host | Provider documentation | All |

---

## 13. References

**Models and tooling (Ultralytics docs)**
- YOLO26 models overview: https://docs.ultralytics.com/models/yolo26/
- Detection task: https://docs.ultralytics.com/tasks/detect/
- Pose task: https://docs.ultralytics.com/tasks/pose
- Train mode: https://docs.ultralytics.com/modes/train/
- Track mode (BoT-SORT default, ByteTrack via `bytetrack.yaml`, `persist=True`): https://docs.ultralytics.com/modes/track
- Construction-PPE dataset page: https://docs.ultralytics.com/datasets/detect/construction-ppe/
- Ultralytics licensing (AGPL-3.0 / Enterprise): https://www.ultralytics.com/license

**Datasets**
- MOT17 / MOTChallenge: https://motchallenge.net/data/MOT17 · benchmark paper: https://arxiv.org/abs/2010.07548
- UR Fall Detection (URFD): https://fenix.ur.edu.pl/~mkepski/ds/uf.html
- GMDCSA-24: https://doi.org/10.5281/zenodo.13354453 · paper: https://doi.org/10.1016/j.dib.2024.110892 · GitHub: https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos
- CAUCAFall: https://data.mendeley.com/datasets/7w7fccy7ky · paper (Data in Brief 2022): https://pmc.ncbi.nlm.nih.gov/articles/PMC9508401
- SH17: https://github.com/ahmadmughees/SH17dataset · https://zenodo.org/records/12659325 · paper: https://arxiv.org/abs/2407.04590
- Roboflow Helmet Vest Only: https://universe.roboflow.com/zols/helmet-vest-only

**Colab**
- Past runtime versions (Python/PyTorch per release): https://github.com/googlecolab/backend-info

*Last reviewed: 2026-11-19. If you verify one of the Needs Verification items, update §12 and the table in §3.1 in the same commit.*
