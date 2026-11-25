import sys, numpy as np
sys.path.insert(0, 'scripts')
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from seg_lib import luminance
# ---------- registration: trace from rectified photo (800 px/m, y 10.30..12.20, z 2.36..2.92)
reg = np.asarray(Image.open('work/reg_hi.png').convert('RGB'))
Y = luminance(reg); Ys = ndi.gaussian_filter(Y, 2.0)
bg = ndi.percentile_filter(ndi.zoom(Ys, 0.25, order=1), 70, size=45)        # local background (mid/light paint)
bg = ndi.zoom(bg, (Ys.shape[0] / bg.shape[0], Ys.shape[1] / bg.shape[1]), order=1)
dark = np.percentile(Ys, 3)
t = (Ys - dark) / np.maximum(bg - dark, 1e-3)
m = t < 0.50
m[:76] = False; m[404:] = False; m[:, :92] = False; m[:, 1436:] = False
m = ndi.binary_opening(m, iterations=3)
l, n = ndi.label(m); sizes = ndi.sum(m, l, np.arange(1, n + 1))
m = np.isin(l, 1 + np.argsort(sizes)[-5:])
# smooth outline
ms = ndi.gaussian_filter(m.astype(np.float32), 2.5) > 0.5
ys, xs = np.nonzero(ms)
print('reg letters bbox px', xs.min(), xs.max(), ys.min(), ys.max(), 'components', ndi.label(ms)[1])
ya = 10.30 + xs.min() / 800; yb = 10.30 + (xs.max() + 1) / 800; zb = 2.92 - ys.min() / 800; za = 2.92 - (ys.max() + 1) / 800
print('reg bbox model: y %.3f..%.3f z %.3f..%.3f' % (ya, yb, za, zb))
crop = ndi.gaussian_filter(ms[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32), 1.0)
Image.fromarray((crop * 255).astype(np.uint8)).save('work/decals/reg_mask.png')
np.save('work/decals/reg_bbox.npy', np.array([ya, yb, za, zb]))
# ---------- flag: locate extents in rectified photo (1200 px/m, y 13.02..13.94, z 3.86..4.47), then draw clean
fya, fyb, fza, fzb = 13.07, 13.88, 3.914, 4.424
cwf = 0.43
np.save('work/decals/flag_bbox.npy', np.array([fya, fyb, fza, fzb]))
SS = 4; FW = int((fyb - fya) * 1000) * SS; FH = int((fzb - fza) * 1000) * SS
LIGHT, DARK = (193, 193, 191), (96, 95, 102)
im = Image.new('RGB', (FW, FH), LIGHT); dr = ImageDraw.Draw(im)
sh = FH / 13.0
for i in range(0, 13, 2): dr.rectangle([0, round(i * sh), FW, round((i + 1) * sh) - 1], fill=DARK)
CW = int(min(max(cwf, 0.36), 0.44) * FW); CH = round(7 * sh)
dr.rectangle([0, 0, CW, CH - 1], fill=DARK)
def star(cx, cy, r):
    pts = []
    for k in range(10):
        a = -np.pi / 2 + k * np.pi / 5; rr = r if k % 2 == 0 else r * 0.40
        pts.append((cx + rr * np.cos(a), cy + rr * np.sin(a)))
    dr.polygon(pts, fill=LIGHT)
for r_ in range(9):
    n = 6 if r_ % 2 == 0 else 5
    for c_ in range(n):
        cx = CW * ((2 * c_ + 1 + (0 if n == 6 else 1)) / 12.0); cy = CH * ((r_ + 1) / 10.0)
        star(cx, cy, CH * 0.046)
im = im.resize((FW // SS, FH // SS), Image.LANCZOS); im.save('work/decals/flag.png'); print('flag img', im.size)
# ---------- winglet emblem: teal-ness from photo 2 (17 x 24 px source)
p2 = np.asarray(Image.open('photos/pinkfroot_tfs.jpg').convert('RGB')).astype(np.float32)
x0, x1, y0, y1 = 1830, 1853, 603, 636
c = p2[y0:y1, x0:x1]
teal = c[..., 1] - c[..., 0]
teal = teal - np.median(teal)
up = ndi.zoom(teal, 16, order=3)
th = 0.5 * np.percentile(up, 99.5)
em = ndi.gaussian_filter((up > th).astype(np.float32), 2.0)
ys, xs = np.nonzero(em > 0.5); print('emblem px bbox (x16):', xs.min(), xs.max(), ys.min(), ys.max(), ' src px size %.1f x %.1f' % ((xs.max() - xs.min()) / 16, (ys.max() - ys.min()) / 16))
em = em[ys.min() - 8:ys.max() + 9, xs.min() - 8:xs.max() + 9]
Image.fromarray((np.clip(em, 0, 1) * 255).astype(np.uint8)).save('work/decals/emblem_mask.png')
col = np.median(c[teal > 0.5 * teal.max()], 0); print('emblem colour in photo', col, 'winglet gray', np.median(c[teal < 0.1 * teal.max()], 0))
# preview sheet
a = Image.open('work/decals/reg_mask.png').convert('RGB'); b = Image.open('work/decals/flag.png'); e = Image.open('work/decals/emblem_mask.png').convert('RGB')
b2 = b.resize((b.size[0], b.size[1])); e2 = e.resize((e.size[0], e.size[1]))
cv = Image.new('RGB', (max(a.size[0], b2.size[0] + e2.size[0] + 20), a.size[1] + max(b2.size[1], e2.size[1]) + 10), (255, 0, 255))
cv.paste(a, (0, 0)); cv.paste(b2, (0, a.size[1] + 10)); cv.paste(e2, (b2.size[0] + 20, a.size[1] + 10)); cv.save('work/decals_preview.png'); print(cv.size)
