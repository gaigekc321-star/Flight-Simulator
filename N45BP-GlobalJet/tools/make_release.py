import sys, os, json, shutil, numpy as np
sys.path.insert(0, 'scripts')
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import render as R
from raster import rasterize
from camlib import project
OUT = sys.argv[1]
for d in ('textures', 'paintkit-sheets', 'thumbnail', 'previews', 'tools/data'): os.makedirs(f'{OUT}/{d}', exist_ok=True)
# ---- final textures
for t in R.TILES: shutil.copy(f'work/final/{t}.png', f'{OUT}/textures/{t}.png')
shutil.copy('work/out/Registration_ALBD.png', f'{OUT}/textures/Registration_ALBD.png')
# ---- paint-only sheets in the paint kit PSD layouts ("Paint Here" layer)
T = 4096
def sheet(name, W, H, tiles):
    im = Image.new('RGB', (W, H), (170, 169, 169))
    for t, (cx, cy) in tiles.items(): im.paste(Image.open(f'work/paint/{t}.png').convert('RGB'), (cx * T, cy * T))
    im.save(f'{OUT}/paintkit-sheets/{name}', optimize=True); print(name, os.path.getsize(f'{OUT}/paintkit-sheets/{name}') // 1024, 'KB')
sheet('Master_EXT_PaintHere_16384x8192.png', 16384, 8192, {f'EXT_{1001 + k}': (k % 4, k // 4) for k in range(7)})
sheet('Engine_Master_PaintHere_8192x4096.png', 8192, 4096, {'ENG_L': (0, 0), 'ENG_R': (1, 0)})
sheet('Wing_Master_PaintHere_8192x8192.png', 8192, 8192, {'WING_L_1001': (0, 0), 'WING_L_1002': (1, 0), 'WING_R_1001': (0, 1), 'WING_R_1002': (1, 1)})
# ---- renders
KEY = (3, 251, 7)
def ortho(view, ppm, light, bg):
    x, y, z = R.POS[..., 0], R.POS[..., 1], R.POS[..., 2]
    u, v, dpt = dict(top=(y, x, -z), bottom=(y, -x, z), left=(y, -z, -x), right=(-y, -z, x), front=(-x, -z, y), rear=(x, -z, -y))[view]
    u0, u1, v0, v1 = u.min(), u.max(), v.min(), v.max()
    W = int((u1 - u0) * ppm) + 40; H = int((v1 - v0) * ppm) + 40
    return R.shade(np.stack([(u - u0) * ppm + 20, (v - v0) * ppm + 20, dpt], -1), W, H, light, bg=bg)
def cam(camf, side, W, H, light, bg, ss=1):
    p = np.array(json.load(open(camf))['persp'], float); S = project(p, R.POS, True, side).copy(); S[..., :2] *= ss
    return R.shade(S, W * ss, H * ss, light, bg=bg)
def keyed(a):
    al = (np.abs(a.astype(int) - np.array(KEY)).sum(2) > 0)
    rgba = np.dstack([a, (al * 255).astype(np.uint8)]); return Image.fromarray(rgba)
def fit(im, W, H, pad=0.04):
    bb = im.getbbox() if im.mode == 'RGBA' else None
    if bb: im = im.crop(bb)
    s = min(W * (1 - 2 * pad) / im.size[0], H * (1 - 2 * pad) / im.size[1])
    im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
    cv = Image.new('RGBA', (W, H), (0, 0, 0, 0)); cv.alpha_composite(im.convert('RGBA'), ((W - im.size[0]) // 2, (H - im.size[1]) // 2)); return cv
LIGHTS = dict(top=(0.2, -0.2, 1), bottom=(0.2, -0.2, -1), left=(0.8, -0.2, 0.55), right=(-0.8, -0.2, 0.55), front=(0.2, -0.8, 0.55), rear=(0.2, 0.8, 0.55))
BG = (96, 110, 135)
side = keyed(ortho('left', 110, LIGHTS['left'], KEY))
fit(side, 930, 340).save(f'{OUT}/thumbnail/thumbnail_side.png')
fit(side, 830, 260).save(f'{OUT}/thumbnail/thumbnail_button.png')
q = cam('work/cam3.json', 'R', 1280, 854, (-0.7, 0.4, 0.6), KEY, ss=2)
q = keyed(q)
sky = Image.new('RGBA', (720, 344)); px = np.linspace(0, 1, 344)[:, None, None]
grad = (np.array([118, 150, 196]) * (1 - px) + np.array([196, 208, 222]) * px).astype(np.uint8)
sky = Image.fromarray(np.dstack([np.repeat(grad, 720, 1), np.full((344, 720, 1), 255, np.uint8)]))
sky.alpha_composite(fit(q, 720, 344, pad=0.03)); sky.convert('RGB').save(f'{OUT}/thumbnail/thumbnail.png')
def save_jpg(a, name, maxw=2200):
    im = Image.fromarray(a) if not isinstance(a, Image.Image) else a
    if im.size[0] > maxw: im = im.resize((maxw, int(im.size[1] * maxw / im.size[0])), Image.LANCZOS)
    im.convert('RGB').save(f'{OUT}/previews/{name}', quality=88); print(name, im.size)
for v in ('left', 'right', 'top', 'bottom', 'front', 'rear'): save_jpg(ortho(v, 110, LIGHTS[v], BG), f'{v}.jpg')
a = cam('work/cam1.json', 'L', 4832, 3215, (0.75, -0.25, 0.6), BG); save_jpg(a[800:1900], 'view_left_takeoff_angle.jpg')
a = cam('work/cam2.json', 'R', 1920, 1280, (-0.5, -0.6, 0.6), BG, ss=2); save_jpg(a[400:1720, 500:3840], 'view_front_right.jpg')
a = cam('work/cam3.json', 'R', 1280, 854, (-0.7, 0.4, 0.6), BG, ss=2); save_jpg(a[300:1280], 'view_rear_right.jpg')
# ---- portable copies of the hand-off data needed to regenerate / tweak the paint
pal = [143, 141, 144, 170, 169, 169, 203, 202, 198]
for n in ('fus', 'finL', 'finR', 'engL', 'engR', 'top'):
    im = Image.fromarray(np.load(f'work/charts/{n}_labels.npy').astype(np.uint8), 'P'); im.putpalette(pal + [0] * (768 - 9)); im.save(f'{OUT}/tools/data/{n}_labels.png', optimize=True)
Image.fromarray((np.load('work/charts/fus_known.npz')['known'] * 255).astype(np.uint8)).save(f'{OUT}/tools/data/fus_known.png', optimize=True)
for f in ('reg_mask.png', 'flag.png', 'emblem_mask.png'): shutil.copy(f'work/decals/{f}', f'{OUT}/tools/data/{f}')
meta = dict(reg_bbox_y0_y1_z0_z1=np.load('work/decals/reg_bbox.npy').tolist(), flag_bbox_y0_y1_z0_z1=np.load('work/decals/flag_bbox.npy').tolist(),
            stabfix={k: np.load('work/stabfix.npz')[k].tolist() for k in ('R', 't')}, posefix={k: np.load('work/posefix.npz')[k].tolist() for k in ('R', 't')},
            fus_centreline=np.load('work/charts/fus_zc.npy').tolist(),
            cameras={k: json.load(open(f'work/{k}.json'))['persp'] for k in ('cam1', 'cam2', 'cam3')},
            palette_sRGB=dict(dark=[143, 141, 144], mid=[170, 169, 169], light=[203, 202, 198], green=[56, 190, 162], registration=[100, 101, 108], flag_dark=[96, 95, 102], flag_light=[193, 193, 191]))
json.dump(meta, open(f'{OUT}/tools/data/meta.json', 'w'), indent=1)
for f in sorted(os.listdir('scripts')):
    if f.endswith(('.py', '.js')) and not f.startswith(('fsto', 'seg1', 'fix_check', 'view_geom', 'uv_stats', 'psdtree', 'gridcrop', 'overlay1', 'h2t', 'pick', 'model_side.')) : shutil.copy(f'scripts/{f}', f'{OUT}/tools/{f}')
for f in ('model_side.py', 'overlay1.py', 'gridcrop.py', 'psdtree.py', 'seg1.py'):
    if os.path.exists(f'scripts/{f}'): shutil.copy(f'scripts/{f}', f'{OUT}/tools/{f}')
print('done')
