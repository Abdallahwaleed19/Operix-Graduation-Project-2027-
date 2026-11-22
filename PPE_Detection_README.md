# PPE Detection (4 classes) - YOLO11s

## STATUS
- Dataset verification: done (reports/phase1_verification_output.txt).
- v1 (YOLO11s @640): test P 0.792 R 0.529 mAP@50 0.602 mAP@50-95 0.360.
- **v2 = final model (YOLO11s @960, recall-priority threshold 0.151):** test P 0.814 R 0.599 (max-F1 point), mAP@50 0.642, mAP@50-95 0.387. Modest improvement, not statistically established (small test set). Details: reports/technical_report.md, results/test_metrics_v2.csv.
- Both trained in Google Colab on a Tesla T4.
- Weights: place best_v2.pt (final) in weights/ (see weights/README.md). Full training outputs (curves, plots, last.pt) stay in the Colab download ZIPs and are not in this repository.
- Dataset is NOT included; download it from Roboflow (link in ATTRIBUTION_AND_LICENSE.md).

## Reproduce training (Google Colab, T4 GPU)
1. v1 baseline: open `colab/PPE_train_colab.ipynb`, run all cells, choose `ppe_4classes.zip` when asked.
2. v2 (final): open `colab/PPE_improve_v2_colab.ipynb` and do the same (about 1.5-3 hours).
Each notebook downloads a ZIP with weights, curves, confusion matrices and metrics at the end.

## Inference
pip install ultralytics
python scripts/infer.py --weights weights/best_v2.pt --source image_or_folder   # v2 defaults: imgsz 960, conf 0.15

Other scripts: verify_dataset.py, review_gallery.py (draws boxes for manual review; never edits labels), evaluate.py.
Classes: 0 Hardhat_Worn, 1 Hardhat_Not_Worn, 2 Safety_Vest_Worn, 3 Safety_Vest_Not_Worn. License: ATTRIBUTION_AND_LICENSE.md.
