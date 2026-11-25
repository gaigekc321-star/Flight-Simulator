# Render per-pixel model attributes into a photo's frame: object id, model position (6000 coords), normal, depth
import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from raster import *
from model_side import gather_fixed, objs
from camlib import *
from PIL import Image
cam=json.load(open(sys.argv[1])); key=sys.argv[2]; photo=sys.argv[3]; out=sys.argv[4]; side=sys.argv[5] if len(sys.argv)>5 else 'L'
p=np.array(cam[key]); persp=(key!='ortho')
pos,nrm,ob=gather_fixed()
W,H=Image.open(photo).size
S=project(p,to5000(pos,p[6]),persp,side)
idx,bc,zb=rasterize(S,W,H)
P=interp(pos,idx,bc); N=interp(nrm,idx,bc)
o=np.full((H,W),-1,np.int16); m=idx>=0; o[m]=ob[idx[m]]
np.savez(out,pos=P.astype(np.float32),nrm=N.astype(np.float32),obj=o,depth=np.where(np.isfinite(zb),zb,1e9).astype(np.float32))
print('saved',out,W,H)
