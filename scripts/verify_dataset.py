import os, json, collections
from pathlib import Path
from PIL import Image
R=Path('ds/ppe_4classes')
names=['Hardhat_Worn','Hardhat_Not_Worn','Safety_Vest_Worn','Safety_Vest_Not_Worn']
exp={'train':(521,1385),'valid':(114,295),'test':(82,302)}
res={};problems=[];tot=collections.Counter()
for s in ['train','valid','test']:
    imgs=sorted(p for p in (R/s/'images').iterdir() if p.is_file())
    lbls=sorted(p for p in (R/s/'labels').iterdir() if p.is_file())
    istem={p.stem for p in imgs}; lstem={p.stem for p in lbls}
    miss_l=istem-lstem; miss_i=lstem-istem
    cc=collections.Counter(); n=0; empty=0; bad=[]; unread=[]; exts=collections.Counter(p.suffix.lower() for p in imgs)
    for p in imgs:
        try:
            with Image.open(p) as im: im.verify()
        except Exception as e: unread.append((p.name,str(e)))
    for l in lbls:
        lines=[x for x in l.read_text().splitlines() if x.strip()]
        if not lines: empty+=1
        for i,x in enumerate(lines):
            t=x.split()
            try:
                if len(t)!=5: raise ValueError('fields=%d'%len(t))
                c=int(t[0]); v=list(map(float,t[1:]))
                if c not in range(4): raise ValueError('class %d'%c)
                xc,yc,w,h=v
                if w<=0 or h<=0 or xc-w/2<-1e-4 or yc-h/2<-1e-4 or xc+w/2>1+1e-4 or yc+h/2>1+1e-4: raise ValueError('bbox out of range/degenerate')
                cc[c]+=1;n+=1
            except Exception as e: bad.append((l.name,i+1,str(e)))
    res[s]=dict(images=len(imgs),labels=len(lbls),annotations=n,empty_labels=empty,per_class={names[k]:cc[k] for k in range(4)},missing_label=len(miss_l),missing_image=len(miss_i),bad_lines=len(bad),unreadable=len(unread),exts=dict(exts))
    tot.update(cc)
    if miss_l or miss_i or bad or unread: problems.append((s,list(miss_l)[:5],list(miss_i)[:5],bad[:5],unread[:5]))
    e=exp[s]; 
    if (len(imgs),n)!=e: problems.append((s,'COUNT MISMATCH',(len(imgs),n),e))
# cross-split stem leakage
st={s:{p.stem for p in (R/s/'images').iterdir()} for s in exp}
leak={f'{a}&{b}':len(st[a]&st[b]) for a,b in [('train','valid'),('train','test'),('valid','test')]}
print(json.dumps(res,indent=1)); print('totals',{names[k]:tot[k] for k in range(4)}, sum(tot.values()))
print('filename overlap',leak); print('problems',problems)
print(os.listdir(R/'reports'))
