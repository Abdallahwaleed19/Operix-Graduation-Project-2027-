Put the trained weights here (not generated in this folder):
- best_v2.pt  <- final model, from PPE_v2_outputs.zip > winner_training_run/weights/best.pt
- best_v1.pt  <- optional baseline, from PPE_outputs.zip > training_run/weights/best.pt
Use v2 with: python scripts/infer.py --weights weights/best_v2.pt --source <image_or_folder>
