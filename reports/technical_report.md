# PPE Detection for Construction Sites – Technical Report

## 1. Objective
Detect four PPE states in construction-site images: Hardhat_Worn, Hardhat_Not_Worn, Safety_Vest_Worn, Safety_Vest_Not_Worn. "Person" is not a model class.

## 2. Dataset
Derived from Roboflow *Construction Site Safety* v30 (CC BY 4.0), reduced to four classes. Verified on the actual files (reports/phase1_verification_output.txt): every image has a label file, all class IDs are 0-3, all boxes are inside the image, all images are readable, no filename overlap between splits.

| Split | Images | Annotations | Empty-label images |
|---|---:|---:|---:|
| Train | 521 | 1385 | 180 |
| Valid | 114 | 295 | 33 |
| Test | 82 | 302 | 27 |

Class totals: Hardhat_Worn 574, Hardhat_Not_Worn 402, Safety_Vest_Worn 424, Safety_Vest_Not_Worn 582. Test-set instances per class: 110 / 41 / 61 / 90.

## 3. Method
Fine-tuning of COCO-pretrained YOLO11s (Ultralytics 8.4.216) on the four-class dataset: imgsz 640, up to 100 epochs, patience 30, batch 16, seed 0, deterministic mode, checkpoints every 10 epochs. `best.pt` was selected using the validation set. The test set was evaluated once, after selection. The evaluation log shows a Tesla T4 GPU (CUDA:0).

## 4. Results (real values from the Colab run)

Validation (model-selection set): P 0.879, R 0.567, mAP@50 0.663, mAP@50-95 0.410.

Test (final, single evaluation):

| Class | Test images | Instances | Precision | Recall | mAP@50 | mAP@50-95 |
|---|---:|---:|---:|---:|---:|---:|
| All | 82 | 302 | 0.792 | 0.529 | 0.602 | 0.360 |
| Hardhat_Worn | 30 | 110 | 0.976 | 0.655 | 0.797 | 0.484 |
| Hardhat_Not_Worn | 25 | 41 | 0.639 | 0.415 | 0.408 | 0.225 |
| Safety_Vest_Worn | 22 | 61 | 0.762 | 0.623 | 0.668 | 0.432 |
| Safety_Vest_Not_Worn | 36 | 90 | 0.790 | 0.422 | 0.536 | 0.298 |

Full-precision values: results/test_metrics.csv and .json.

## 4b. Version 2 (final model): higher input resolution
**Motivation (from the data):** images are large (mostly 1280x720 or bigger) and about half of the hardhat boxes are under 32 px in original resolution, so 640 px training shrinks small objects further. Some Hardhat_Not_Worn boxes are only 5-9 px wide, and the class also covers caps and beanies, not only bare heads (visual check of 20 random training boxes).

**Protocol:** two candidates trained from COCO-pretrained weights, 80 epochs, patience 25, seed 0, imgsz 960 (YOLO11s, batch 16, 26.4 min; YOLO11m, batch 8, 64.7 min) on a Tesla T4. Selection was done on the validation set only. The confidence threshold was also chosen on validation (maximum macro F2, which weights recall more than precision): **0.151** (max macro-F1 would have been 0.294). The test set was then evaluated once for the chosen model.

| Model (validation) | P | R | mAP@50 | mAP@50-95 |
|---|---:|---:|---:|---:|
| v1 YOLO11s @640 | 0.879 | 0.567 | 0.663 | 0.410 |
| v2a YOLO11s @960 (selected) | 0.823 | 0.619 | 0.678 | 0.421 |
| v2b YOLO11m @960 | 0.759 | 0.612 | 0.661 | 0.419 |

The larger YOLO11m did not beat YOLO11s and took about 2.5x longer.

**Test results, v2a (single evaluation).** mAP values are independent of the threshold; P/R at the max-F1 point are Ultralytics' default reporting.

| | v1 | v2 |
|---|---:|---:|
| mAP@50 | 0.602 | 0.642 |
| mAP@50-95 | 0.360 | 0.387 |
| Precision (max-F1 point) | 0.792 | 0.814 |
| Recall (max-F1 point) | 0.529 | 0.599 |

v2 per class at the max-F1 point (test): Hardhat_Worn P 0.960 R 0.653 mAP50 0.806 mAP50-95 0.535; Hardhat_Not_Worn P 0.703 R 0.585 mAP50 0.483 mAP50-95 0.245; Safety_Vest_Worn P 0.776 R 0.623 mAP50 0.706 mAP50-95 0.458; Safety_Vest_Not_Worn P 0.816 R 0.533 mAP50 0.575 mAP50-95 0.309.

At the recall-oriented threshold 0.151 chosen on validation (test, macro over classes): precision 0.654, recall 0.647. Per class precision/recall: Hardhat_Worn 0.887/0.711; Hardhat_Not_Worn 0.552/0.610; Safety_Vest_Worn 0.644/0.721; Safety_Vest_Not_Worn 0.531/0.544. Lowering the threshold trades precision for recall, as intended. Full values: results/test_metrics_v2.csv and .json.

### v2 confusion matrix (test set, threshold 0.151; screenshot in results/confusion_matrix_v2_screenshot.png)
Rows = predicted, columns = true. Column sums equal the test instance counts (110 / 41 / 61 / 90), which confirms the reading.

| True class | Detected correctly | Predicted as another class | Missed (background) |
|---|---:|---|---:|
| Hardhat_Worn (110) | 77 (0.70) | 6 as Hardhat_Not_Worn | 27 |
| Hardhat_Not_Worn (41) | 24 (0.59) | 1 as Hardhat_Worn | 16 |
| Safety_Vest_Worn (61) | 42 (0.69) | 5 as Safety_Vest_Not_Worn | 14 |
| Safety_Vest_Not_Worn (90) | 49 (0.54) | 1 as Hardhat_Worn, 2 as Safety_Vest_Worn | 38 |

False detections on background (predicted object, nothing true there): Hardhat_Worn 9, Hardhat_Not_Worn 15, Safety_Vest_Worn 24, Safety_Vest_Not_Worn 38 (86 in total).

What it shows:
- Overall 192 of 302 objects were detected with the right class at this threshold; 95 were missed entirely and 15 were detected as the wrong class.
- As in v1, errors are mostly misses and background false alarms, not class swaps. Hardhat/vest confusion is almost absent.
- Safety_Vest_Not_Worn is the hardest class in absolute terms: most misses (38 of 90) and most false alarms (38).
- Safety vest classes produce most background false alarms (62 of 86), which is a plausible effect of the low, recall-oriented threshold; it was not investigated further which image content triggers them.
- Class swaps are mainly Worn/Not_Worn within the same item (hardhat 6+1, vest 5+2).
- Per-class recall read from this matrix differs slightly from results/test_metrics_v2.csv because the matrix uses its own matching procedure; the CSV values are the reference. Because the v1 matrix above was produced at a much lower threshold, the two matrices are not directly comparable.

**Reading the comparison honestly:**
- On both validation and test the improvement is modest (test mAP@50 +0.040, mAP@50-95 +0.027). With 82 test images and only 41 Hardhat_Not_Worn boxes, differences of this size are within what sampling noise could produce; no confidence intervals or multiple seeds were run, so the improvement is not statistically established.
- Test recall at the max-F1 point rose mainly for the Not_Worn classes (Hardhat_Not_Worn 0.415 to 0.585, Safety_Vest_Not_Worn 0.422 to 0.533), while Hardhat_Worn and Safety_Vest_Worn recall were essentially unchanged (0.655 to 0.653, 0.623 to 0.623). This is consistent with, but does not prove, the small-object explanation.
- The test set had already been used once (for v1). The choice between v1, v2a and v2b was made on validation only, but the test set is no longer a pristine, never-seen set.
- Not analysed for v2: training curves and prediction images (files exist in PPE_v2_outputs.zip). The v1 confusion-matrix and curve analysis above still describes v1 only.
- Inference should use imgsz 960. The threshold 0.151 is a recall-priority choice; 0.294 would favour balance.

## 5. Analysis of v1 (based only on the v1 numbers above)
- Precision is higher than recall in every class (overall 0.79 vs 0.53): when the model fires it is usually right, but it misses a large share of ground-truth objects at the operating point Ultralytics uses to report P and R (the confidence that maximises F1).
- Hardhat_Worn is the strongest class (mAP@50 0.797). Hardhat_Not_Worn is the weakest (mAP@50 0.408, recall 0.415), and has the fewest test instances (41).
- Both "Not_Worn" classes have lower recall (about 0.42) than the "Worn" classes (0.62-0.65). For a safety-monitoring use, missing violations is the costly error.
- Test scores are below validation (mAP@50 0.602 vs 0.663). Some gap is expected because validation was used to pick the checkpoint; with 82 test images the difference is also within what small-sample noise can produce.
- Two of the first four test images produced no detections in the printed prediction log.

### Confusion matrix (test set, from the saved confusion_matrix.png)
Rows = predicted, columns = true. Column sums equal the test instance counts (110 / 41 / 61 / 90), which confirms the reading.

| True class | Detected correctly | Predicted as another class | Missed (background) |
|---|---:|---|---:|
| Hardhat_Worn (110) | 92 (0.84) | 6 as Hardhat_Not_Worn, 2 as Safety_Vest_Worn | 10 |
| Hardhat_Not_Worn (41) | 24 (0.59) | 3 as Hardhat_Worn | 14 |
| Safety_Vest_Worn (61) | 51 (0.84) | 1 as Hardhat_Worn, 4 as Safety_Vest_Not_Worn | 5 |
| Safety_Vest_Not_Worn (90) | 60 (0.67) | 1 as Hardhat_Worn, 7 as Safety_Vest_Worn | 22 |

What it shows:
- Errors are mainly misses, not class swaps. Confusion between hardhat and vest classes is almost absent (1-2 cases).
- The main class-to-class confusion is within the same item: Worn vs Not_Worn (hardhat 6+3, vest 7+4).
- Most missed objects: Safety_Vest_Not_Worn (22 of 90) and Hardhat_Not_Worn (14 of 41).
- The matrix also lists very large "predicted object, true background" counts (512-877 per class). They come from the very low confidence threshold used by the validation routine and are not a realistic deployment figure. Because of the different threshold, per-class recall here (0.84 / 0.59 / 0.84 / 0.67) is higher than the recall in the metrics table (0.655 / 0.415 / 0.623 / 0.422); the two are different operating points, not a contradiction. A fair false-positive analysis needs a rerun at a deployment threshold such as 0.25.

### v1 training curves (from results.png; values read visually, so approximate)
- The run reached epoch 100 on the x-axis, so early stopping (patience 30) did not trigger and `best.pt` was chosen among the 100 epochs by validation fitness.
- Training box/cls/DFL losses decrease steadily until the end. Validation box and DFL losses flatten after roughly epoch 50-60 (about 1.35 and 1.33) and do not show a clear rise. Together this suggests a growing train/validation gap with mild overfitting, not a collapse.
- Validation mAP@50 plateaus around 0.62-0.65 and mAP@50-95 around 0.40 after roughly epoch 60, with epoch-to-epoch noise. Recall still creeps up slowly near the end; precision is flat at about 0.8 and noisy.
- Epochs 1-10 are unstable (validation class loss spike, precision dip), which is typical warm-up behaviour and was not investigated further.
- The exact best epoch was not read from the logs.

### Prediction examples (3 images, anecdotal; screenshots in results/prediction_examples)
Ground-truth labels for these images were not compared, so these are visual observations only, not measurements.
1. Worker with a clearly visible blue hardhat, camouflage jacket, no vest: no boxes drawn. If this is an unaltered model output, it is a missed Hardhat_Worn detection (consistent with the 0.655 Hardhat_Worn recall) and also no Safety_Vest_Not_Worn detection.
2. Indoor close-up of a person with no hardhat and a grey T-shirt: the model drew Hardhat_Not_Worn (0.92) on the head and Safety_Vest_Not_Worn (0.95) on the torso. This matches the dataset's "Not_Worn" idea (bare head/torso) but shows the model fires with high confidence on a non-construction scene, so it may flag any person without PPE.
3. Race-car cockpit with no person visible: no detections, which is the expected behaviour for a scene without PPE.
These three images are too few to generalise from.

## 6. Limitations
- Small dataset (about 1.4k training boxes), single source dataset; results may not transfer to other sites, cameras or lighting.
- Small test set; per-class values, especially Hardhat_Not_Worn (41 boxes), are noisy.
- 146 heuristic review candidates were not manually confirmed; no labels were changed.
- One training run, one seed; no confidence-interval or multi-seed estimate.
- Worn/not-worn depends on box semantics in the original annotations, which were not fully re-audited.

## 7. Possible improvements
Review annotation quality of the Not_Worn classes, add more Not_Worn examples, tune the confidence threshold (trade recall for precision), try a larger model or higher resolution, and repeat with several seeds.

## 8. Attribution
Dataset: Roboflow Construction Site Safety v30, CC BY 4.0 (see ATTRIBUTION_AND_LICENSE.md). Model: Ultralytics YOLO11 (AGPL-3.0).
