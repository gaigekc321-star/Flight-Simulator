"""Project a photo's class map into charts. usage: project_photo.py cam.json key side classes.npz pm.npz outprefix charts..."""
import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from camlib import *
from scipy.spatial.transform import Rotation as Rot
camf, key, side, clsf, pmf, outp = sys.argv[1:7]; charts = sys.argv[7:]
p = np.array(json.load(open(camf))[key]); persp = key != 'ortho'
cl = np.load(clsf); C = cl['C']; M = cl['mask']; Y0 = int(cl['y0'])
depth = np.load(pmf)['depth']
Hc, Wc = C.shape; Hd, Wd = depth.shape
R = Rot.from_euler('xyz', p[1:4]).as_matrix()
B = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], float) if side == 'L' else np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
view = R.T @ B.T @ np.array([0, 0, -1.0])          # direction towards camera (world)
print('view dir', view.round(3))
for ch in charts:
    c = np.load(f'work/charts/{ch}.npz'); pos = c['pos'].astype(np.float64); nrm = c['nrm'].astype(np.float64); cov = c['cover']
    S = project(p, to5000(pos, p[6]), persp, side)
    u = S[..., 0]; v = S[..., 1]; dz = S[..., 2]
    iu = np.rint(u - 0.5).astype(np.int64); iv = np.rint(v - 0.5).astype(np.int64)
    inb = cov & (iu >= 0) & (iu < Wd) & (iv >= 0) & (iv < Hd)
    iu = np.clip(iu, 0, Wd - 1); iv = np.clip(iv, 0, Hd - 1)
    vis = inb & (np.abs(depth[iv, iu] - dz) < 0.12)
    cosi = nrm @ view
    ivc = iv - Y0
    inc = vis & (ivc >= 0) & (ivc < Hc)
    ivc = np.clip(ivc, 0, Hc - 1)
    ok = inc & M[ivc, iu] & (cosi > 0.28)
    obs = np.zeros(cov.shape + (3,), np.float32)
    cls = C[ivc, iu]
    for k in range(3): obs[..., k] = np.where(ok & (cls == k), cosi, 0)
    np.savez_compressed(f'{outp}_{ch}.npz', obs=obs, vis=vis, cosi=cosi.astype(np.float32))
    print(ch, 'observed %.1f%% of covered' % (100 * ok.sum() / max(cov.sum(), 1)))
