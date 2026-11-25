import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from raster import *
from model_side import gather_fixed
from camlib import *
from PIL import Image
cam=json.load(open(sys.argv[1])); key=sys.argv[2]; photo=sys.argv[3]; out=sys.argv[4]; side=sys.argv[5] if len(sys.argv)>5 else 'L'
p=np.array(cam[key]); persp=(key!='ortho')
pos,nrm,ob=gather_fixed()
im=Image.open(photo).convert('RGB'); W,H=im.size
Q=to5000(pos,p[6])
S=project(p,Q,persp,side)
idx,bc,zb=rasterize(S,W,H)
o=ob[np.clip(idx,0,None)].astype(np.int32); o[idx<0]=-1
e=(o!=np.roll(o,1,0))|(o!=np.roll(o,1,1))
z=np.where(np.isfinite(zb),zb,99)
e|=(np.abs(z-np.roll(z,1,0))>0.25)|(np.abs(z-np.roll(z,1,1))>0.25)
from scipy import ndimage as ndi
e=ndi.binary_dilation(e,iterations=1)
a=np.asarray(im).copy()
a[e]=(255,0,255)
Image.fromarray(a).save(out,quality=90)
np.save(out+'.idx.npy',idx)
print('saved',out)
