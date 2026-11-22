"""usage: python infer.py --weights best.pt --source img_or_dir_or_video [--conf 0.25]"""
import argparse
from ultralytics import YOLO
ap=argparse.ArgumentParser()
ap.add_argument('--weights',required=True); ap.add_argument('--source',required=True)
ap.add_argument('--conf',type=float,default=0.15); ap.add_argument('--imgsz',type=int,default=960)
ap.add_argument('--out',default='runs/predict')
a=ap.parse_args()
m=YOLO(a.weights)
for r in m.predict(a.source,conf=a.conf,imgsz=a.imgsz,save=True,project=a.out,name='exp',exist_ok=True,stream=True):
    print(r.path,[(m.names[int(c)],round(float(s),2)) for c,s in zip(r.boxes.cls,r.boxes.conf)])
