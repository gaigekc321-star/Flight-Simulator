import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from raster import *
from camlib import project
from PIL import Image
objs, d = load_model('work/model')
fix = np.load('work/stabfix.npz')
BAD = {'Object048', 'Object26450203', 'Object26450090', 'Object26450204', 'Object26450202', 'Tail_004', 'Tail_005', 'Tail_025'}   # parts misplaced in the kit FBX (preview only)
TEXDIR = 'work/final'
MATT = {'GLEX_EXT': ['EXT_%d' % (1001 + k) for k in range(7)], 'GLEX_ENG_L': ['ENG_L'], 'GLEX_ENG_R': ['ENG_R'],
        'GLEX_Wing_L': ['WING_L_1001', 'WING_L_1002'], 'GLEX_Wing_R': ['WING_R_1001', 'WING_R_1002']}
TILES = [t for m in MATT for t in MATT[m]]
_tex = {}
def tex(i):
    if i not in _tex: _tex[i] = np.asarray(Image.open(f'{TEXDIR}/{TILES[i]}.png').convert('RGB'))
    return _tex[i]
def gather_all():
    P = []; N = []; U = []; TI = []
    for o in objs:
        if o['name'] in BAD or o['mat'] not in MATT: continue
        i = o['i']; p = d[f'v{i}'][d[f'tv{i}']].astype(np.float64); n = d[f'tn{i}'].astype(np.float64); uv = d[f'tuv{i}'].astype(np.float64)
        if o['name'] == 'Object031': p = p @ fix['R'].T + fix['t']; n = n @ fix['R'].T
        if o['name'] == 'Fuselage_230':
            pf = np.load('work/posefix.npz'); p = p @ pf['R'].T + pf['t']; n = n @ pf['R'].T
        k = np.clip(np.floor(uv[:, :, 0].mean(1) + 1e-9).astype(int), 0, len(MATT[o['mat']]) - 1)
        base = TILES.index(MATT[o['mat']][0])
        uv = uv.copy(); uv[:, :, 0] -= k[:, None]
        P.append(p); N.append(n); U.append(uv); TI.append(base + k)
    return np.concatenate(P), np.concatenate(N), np.concatenate(U), np.concatenate(TI)
POS, NRM, UV, TI = gather_all()
def shade(S, W, H, light, bg=(96, 110, 135), amb=0.42, dif=0.72):
    idx, bc, zb = rasterize(S, W, H)
    m = idx >= 0
    uv = interp(UV, idx, bc); n = interp(NRM, idx, bc)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
    alb = np.zeros((H, W, 3), np.float32)
    ti = TI[np.clip(idx, 0, None)]
    for t in np.unique(ti[m]):
        sel = m & (ti == t); T = tex(t)
        x = np.clip((uv[..., 0][sel] * 4096).astype(int), 0, 4095); y = np.clip(((1 - uv[..., 1][sel]) * 4096).astype(int), 0, 4095)
        alb[sel] = T[y, x]
    lin = (alb / 255) ** 2.2
    L = np.array(light, float); L /= np.linalg.norm(L)
    sh = amb + dif * np.clip(n @ L, 0, 1) + 0.10 * np.clip(n[..., 2], 0, 1)
    out = np.clip(lin * sh[..., None], 0, 1) ** (1 / 2.2) * 255
    out[~m] = bg
    return out.astype(np.uint8)
def render_cam(camf, side, W, H, light, ss=1, dL=0.0):
    p = np.array(json.load(open(camf))['persp'], float)
    S = project(p, POS, True, side)
    S = S.copy(); S[..., :2] *= ss
    return shade(S, W * ss, H * ss, light)
def render_ortho(view, ppm, light, bounds=None):
    x, y, z = POS[..., 0], POS[..., 1], POS[..., 2]
    if view == 'top':   u, v, dpt = y, x, -z            # nose left, left wing at bottom
    if view == 'bottom': u, v, dpt = y, -x, z
    if view == 'left':  u, v, dpt = y, -z, -x
    if view == 'right': u, v, dpt = -y, -z, x
    if view == 'front': u, v, dpt = -x, -z, y
    if view == 'rear':  u, v, dpt = x, -z, -y
    u0, u1, v0, v1 = (u.min(), u.max(), v.min(), v.max()) if bounds is None else bounds
    W = int((u1 - u0) * ppm) + 20; H = int((v1 - v0) * ppm) + 20
    S = np.stack([(u - u0) * ppm + 10, (v - v0) * ppm + 10, dpt], -1)
    return shade(S, W, H, light)
if __name__ == '__main__':
    what = sys.argv[1:]
    if 'p1' in what:
        im = render_cam('work/cam1.json', 'L', 4832, 3215, (0.75, -0.25, 0.6))
        Image.fromarray(im[800:1900]).save('work/r_p1.png')
    if 'p2' in what:
        im = render_cam('work/cam2.json', 'R', 1920, 1280, (-0.5, -0.6, 0.6), ss=2)
        Image.fromarray(im[400:1720, 500:3840]).save('work/r_p2.png')
    if 'p3' in what:
        im = render_cam('work/cam3.json', 'R', 1280, 854, (-0.7, 0.4, 0.6), ss=2)
        Image.fromarray(im[300:1280]).save('work/r_p3.png')
    for v in ('top', 'bottom', 'left', 'right', 'front', 'rear'):
        if v in what:
            L = dict(top=(0.2, -0.2, 1), bottom=(0.2, -0.2, -1), left=(0.8, -0.2, 0.55), right=(-0.8, -0.2, 0.55), front=(0.2, -0.8, 0.55), rear=(0.2, 0.8, 0.55))[v]
            Image.fromarray(render_ortho(v, 110, L)).save(f'work/r_{v}.png')
    print('rendered', what)
