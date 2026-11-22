# Dataset attribution and license

**Dataset:** Construction Site Safety
**Version:** v30 – raw-images_latestversion
**Author/Publisher:** Roboflow Universe Projects
**Source:** https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety/dataset/30
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0) – https://creativecommons.org/licenses/by/4.0/

## Changes made (as required by CC BY 4.0)
The original dataset was modified for this project:
- Reduced to four PPE classes: Hardhat_Worn (0), Hardhat_Not_Worn (1), Safety_Vest_Worn (2), Safety_Vest_Not_Worn (3).
- Person and all other original classes were removed from the working dataset.
- Result: 717 images and 1982 target annotations in train (521) / valid (114) / test (82) splits.
- The original raw dataset was not modified; the four-class set is a separate working copy.

## Model software
Ultralytics YOLO11 (AGPL-3.0), https://github.com/ultralytics/ultralytics. COCO-pretrained weights were fine-tuned on the dataset above.

## Notice
The trained weights are derived from CC BY 4.0 data. Any redistribution of the dataset, or of material derived from it, must keep this attribution, link to the license, and state that changes were made. This is a project notice, not legal advice.
