"""Evaluate FINAL chosen weights; run on test ONLY after model selection.
usage: python evaluate.py --weights best.pt --data data.yaml --split test --out results"""
import argparse, json, csv
from pathlib import Path
from ultralytics import YOLO
ap=argparse.ArgumentParser(); ap.add_argument('--weights',required=True); ap.add_argument('--data',required=True)
ap.add_argument('--split',default='test'); ap.add_argument('--out',default='results'); ap.add_argument('--imgsz',type=int,default=640)
a=ap.parse_args(); out=Path(a.out); out.mkdir(exist_ok=True,parents=True)
m=YOLO(a.weights)
r=m.val(data=a.data,split=a.split,imgsz=a.imgsz,plots=True,project=str(out),name=f'{a.split}_eval',exist_ok=True)
rows=[dict(cls='ALL',precision=r.box.mp,recall=r.box.mr,map50=r.box.map50,map50_95=r.box.map)]
for i,c in enumerate(r.box.ap_class_index):
    p,rc,a50,a5095=r.box.class_result(i)
    rows.append(dict(cls=m.names[int(c)],precision=p,recall=rc,map50=a50,map50_95=a5095))
json.dump(rows,open(out/f'{a.split}_metrics.json','w'),indent=1)
w=csv.DictWriter(open(out/f'{a.split}_metrics.csv','w',newline=''),fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
for x in rows: print(x)
