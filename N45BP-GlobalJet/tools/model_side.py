import sys, numpy as np
sys.path.insert(0, 'scripts')
from raster import *
from PIL import Image, ImageDraw, ImageFont
objs, d = load_model('work/model')
fix = np.load('work/stabfix.npz')
BAD = {'Object048', 'Object26450203', 'Object26450090', 'Object26450204'}
def gather_fixed(select=None):
    P=[];N=[];O=[]
    for o in objs:
        if o['name'] in BAD: continue
        if select and not select(o): continue
        i=o['i']; p=d[f'v{i}'][d[f'tv{i}']].astype(np.float64); n=d[f'tn{i}'].astype(np.float64)
        if o['name']=='Object031': p=p@fix['R'].T+fix['t']; n=n@fix['R'].T
        P.append(p);N.append(n);O.append(np.full(len(p),i,np.int32))
    return np.concatenate(P),np.concatenate(N),np.concatenate(O)
if __name__=='__main__':
    side=sys.argv[1]; y0,y1,z0,z1=map(float,sys.argv[2:6]); S=float(sys.argv[6]); out=sys.argv[7]
    pos,nrm,ob=gather_fixed()
    sx=1.0 if side=='L' else -1.0   # camera at +x looking -x for L
    W=int((y1-y0)*S); H=int((z1-z0)*S)
    if side=='L': u=(pos[...,1]-y0)*S
    else: u=(y1-pos[...,1])*S
    v=(z1-pos[...,2])*S
    P=np.stack([u,v,-sx*pos[...,0]],-1)
    idx,bc,zb=rasterize(P,W,H)
    n=interp(nrm,idx,bc)
    L=np.array([sx*0.8,-0.2,0.55]); L/=np.linalg.norm(L)
    sh=np.clip(n@L,0,1)*0.6+0.4
    img=np.repeat(sh[...,None],3,2)
    # edge lines between objects
    o=ob[np.clip(idx,0,None)]; o[idx<0]=-1
    e=(o!=np.roll(o,1,0))|(o!=np.roll(o,1,1))
    img[e]*=0.35
    img[idx<0]=(0.1,0.12,0.2)
    im=Image.fromarray((img*255).astype(np.uint8)); dr=ImageDraw.Draw(im,'RGBA')
    f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
    step=float(sys.argv[8]) if len(sys.argv)>8 else 0.5
    g=np.ceil(y0/step)*step
    while g<y1:
        X=(g-y0)*S if side=='L' else (y1-g)*S
        dr.line([(X,0),(X,H)],fill=(255,255,0,90)); dr.text((X+2,2),f'{g:g}',fill=(255,255,0,255),font=f); g+=step
    g=np.ceil(z0/step)*step
    while g<z1:
        Y=(z1-g)*S; dr.line([(0,Y),(W,Y)],fill=(0,255,255,90)); dr.text((2,Y+1),f'{g:g}',fill=(0,255,255,255),font=f); g+=step
    im.save(out); print(out,im.size)
