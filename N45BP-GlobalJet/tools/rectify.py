"""Rectify a photo into a chart (RGB). usage: rectify.py cam.json key side photo pm.npz chart out.png"""
import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from camlib import *
from PIL import Image
from scipy import ndimage as ndi
camf, key, side, photo, pmf, ch, out = sys.argv[1:8]
p = np.array(json.load(open(camf))[key])
rgb = np.asarray(Image.open(photo).convert('RGB')).astype(np.float32)
depth = np.load(pmf)['depth']; Hd, Wd = depth.shape
c = np.load(f'work/charts/{ch}.npz'); pos = c['pos'].astype(np.float64); cov = c['cover']
S = project(p, to5000(pos, p[6]), True, side)
u = S[..., 0] - 0.5; v = S[..., 1] - 0.5
iu = np.clip(np.rint(u).astype(int), 0, Wd - 1); iv = np.clip(np.rint(v).astype(int), 0, Hd - 1)
vis = cov & (u >= 0) & (u < Wd - 1) & (v >= 0) & (v < Hd - 1) & (np.abs(depth[iv, iu] - S[..., 2]) < 0.15)
o = np.zeros(pos.shape[:2] + (3,), np.float32)
for k in range(3): o[..., k] = ndi.map_coordinates(rgb[..., k], [v, u], order=1, mode='nearest')
o[~vis] = (90, 0, 90)
Image.fromarray(o.astype(np.uint8)).save(out)
print(out, o.shape)
