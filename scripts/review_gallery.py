"""Phase 2: draw GT boxes on random images for MANUAL visual review. Never edits labels.
usage: python review_gallery.py DATASET_DIR [split] [n]"""
import sys, random, cv2
from pathlib import Path
R=Path(sys.argv[1]); split=sys.argv[2] if len(sys.argv)>2 else 'train'; n=int(sys.argv[3]) if len(sys.argv)>3 else 24
names=['Hardhat_Worn','Hardhat_Not_Worn','Safety_Vest_Worn','Safety_Vest_Not_Worn']
col=[(0,200,0),(0,0,255),(0,200,0),(0,0,255)]
out=Path('review_gallery'); out.mkdir(exist_ok=True)
imgs=sorted((R/split/'images').glob('*.jpg')); random.seed(0)
for p in random.sample(imgs,min(n,len(imgs))):
    im=cv2.imread(str(p)); h,w=im.shape[:2]
    for l in (R/split/'labels'/(p.stem+'.txt')).read_text().split('\n'):
        t=l.split()
        if len(t)!=5: continue
        c=int(t[0]); x,y,bw,bh=map(float,t[1:])
        a=(int((x-bw/2)*w),int((y-bh/2)*h)); b=(int((x+bw/2)*w),int((y+bh/2)*h))
        cv2.rectangle(im,a,b,col[c],2); cv2.putText(im,names[c],(a[0],max(12,a[1]-4)),0,0.5,col[c],1)
    cv2.imwrite(str(out/p.name),im)
print('saved to',out)
