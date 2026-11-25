import sys, numpy as np, json, time
sys.path.insert(0, 'scripts')
from seg_lib import *
from PIL import Image
from skimage import color
objs = json.load(open('work/model.json')); nm = {o['i']: o for o in objs}
Y0, Y1 = 840, 1780
rgb = np.asarray(Image.open('photos/aeroxplorer_51315_uploads.jpg').convert('RGB'))[Y0:Y1]
pm = np.load('work/pm1.npz'); obj = pm['obj'][Y0:Y1]
H, W = obj.shape
# camo candidate objects: EXT + ENG materials
camo_ids = np.array([o['i'] for o in objs if o['mat'] in ('GLEX_EXT', 'GLEX_ENG_L', 'GLEX_ENG_R')])
inmodel = np.isin(obj, camo_ids)
lab = color.rgb2lab(rgb.astype(np.float32) / 255)
chroma = np.hypot(lab[..., 1], lab[..., 2])
Y = luminance(rgb); logY = np.log(np.maximum(Y, 1e-4))
gray = (chroma < 11) & (lab[..., 0] > 22)
mask = ndi.binary_erosion(inmodel, iterations=3) & gray
mask = ndi.binary_opening(mask, iterations=1)
print('mask px', mask.sum())
t = time.time()
R, E = retinex(logY, mask, T=float(sys.argv[1]) if len(sys.argv) > 1 else 0.022)
print('retinex done %.1fs' % (time.time() - t), 'R range', np.nanmin(R), np.nanmax(R))
np.savez_compressed('work/seg1_stage1.npz', R=R, mask=mask, logY=logY.astype(np.float32), E=E)
v = R[mask]; lo, hi = np.percentile(v, [1, 99])
vis = np.zeros((H, W, 3), np.uint8); g = np.clip((R - lo) / (hi - lo), 0, 1); g[~mask] = 0
vis[...] = (g * 255)[..., None]; vis[~mask] = (60, 0, 60)
Image.fromarray(vis).save('work/seg1_R.png')
Image.fromarray(vis).resize((W // 3, H // 3), Image.LANCZOS).save('work/seg1_R_small.png')
h, e = np.histogram(v, bins=80, range=(lo, hi)); print('hist', h.tolist())
