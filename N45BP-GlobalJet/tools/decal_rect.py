"""High-res rectification of a planar patch on the fin from photo 1 (left side). Patch: y in [ya,yb], z in [za,zb] at x = fin surface."""
import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from camlib import *
from PIL import Image
from scipy import ndimage as ndi
def rect_patch(camf, side, photo, ya, yb, za, zb, ppm, chart='finL'):
    p = np.array(json.load(open(camf))['persp'])
    rgb = np.asarray(Image.open(photo).convert('RGB')).astype(np.float32)
    c = np.load(f'work/charts/{chart}.npz'); pos = c['pos']; cov = c['cover']
    # x of fin surface as function of chart (y,z): sample chart pos x via bilinear on chart grid (160 ppm)
    from charts import FIN_Y0, FIN_Z1, PPM
    W = int((yb - ya) * ppm); H = int((zb - za) * ppm)
    yy = ya + (np.arange(W) + 0.5) / ppm; zz = zb - (np.arange(H) + 0.5) / ppm
    Y, Z = np.meshgrid(yy, zz)
    cx = (Y - FIN_Y0) * PPM - 0.5; cy = (FIN_Z1 - Z) * PPM - 0.5
    X = ndi.map_coordinates(np.where(cov, pos[..., 0], 0.15 if side == 'L' else -0.15), [cy, cx], order=1, mode='nearest')
    P = np.stack([X, Y, Z], -1)
    S = project(p, to5000(P, p[6]), True, side)
    out = np.stack([ndi.map_coordinates(rgb[..., k], [S[..., 1] - 0.5, S[..., 0] - 0.5], order=3, mode='nearest') for k in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)
if __name__ == '__main__':
    reg = rect_patch('work/cam1.json', 'L', 'photos/aeroxplorer_51315_uploads.jpg', 10.30, 12.20, 2.36, 2.92, 800)
    Image.fromarray(reg).save('work/reg_hi.png'); print('reg', reg.shape)
    fl = rect_patch('work/cam1.json', 'L', 'photos/aeroxplorer_51315_uploads.jpg', 13.02, 13.94, 3.86, 4.47, 1200)
    Image.fromarray(fl).save('work/flag_hi.png'); print('flag', fl.shape)
