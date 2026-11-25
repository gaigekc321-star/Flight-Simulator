import sys, os, re
from psd_tools import PSDImage
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
p=PSDImage.open(src)
W,H=p.size
def walk(l,path):
    for c in l:
        name=re.sub(r'[^A-Za-z0-9]+','_',c.name).strip('_')
        pp=path+[name]
        if c.is_group():
            walk(c,pp)
        else:
            im=c.topil()
            if im is None:
                print('EMPTY',pp); continue
            fn='__'.join(pp)+'.png'
            full=Image.new('RGBA',(W,H),(0,0,0,0))
            full.paste(im.convert('RGBA'),(c.left,c.top))
            full.save(os.path.join(out,fn),compress_level=1)
            pv=full.resize((2048,int(2048*H/W)),Image.LANCZOS)
            pv.save(os.path.join(out,'pv_'+fn))
            print('saved',fn,im.mode,im.size,flush=True)
walk(p,[])
