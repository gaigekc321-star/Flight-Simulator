#!/usr/bin/env python3
"""Encode ../textures/*.png into MSFS 2024 KTX2 (+ .KTX2.json) for the installer.

Container layout follows the MSFS 2024 KTX2 format as documented (and verified byte-for-byte against
sim-built files) by the MSFS Livery Forge project: standard KTX2, vkFormat 145 (BC7_UNORM), no
supercompression, Asobo DFD + KVD (ASOBO_flags / ASOBO_opacities / ASOBO_transp / ASOBOtexversion / KTXwriter),
mip data stored smallest-first, albedo stored as raw sRGB values.
Needs: pip install numpy pillow etcpak
"""
import json, os, struct, sys, time
import numpy as np
from PIL import Image
import etcpak

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'install', 'files')
IDENT = bytes.fromhex('ab4b5458203230bb0d0a1a0a')
DFD_BC7 = bytes.fromhex('2c00000000000000020028008601010003030000100000000000000000007f000000000000000000ffffffff')
KVD_FLAGS = ['BILINEAR', 'COMPRESSION', 'MIPMAP', 'REDUCE_LESS', 'PLATFORM_FORMAT', 'QUALITY_HIGH']
JSON_FLAGS = ['FL_BITMAP_COMPRESSION', 'FL_BITMAP_MIPMAP', 'FL_BITMAP_QUALITY_HIGH']
assert len(DFD_BC7) == 44

def kvd(has_transp):
    entries = [('ASOBO_flags', b''.join(t.encode() + b'\0' for t in KVD_FLAGS)), ('ASOBO_opacities', b''),
               ('ASOBO_transp', b'\x01' if has_transp else b'\x00'), ('ASOBOtexversion', struct.pack('<I', 1)),
               ('KTXwriter', b'ASOBO_FlightSim\0')]
    out = bytearray()
    for k, v in entries:
        blob = k.encode() + b'\0' + v
        out += struct.pack('<I', len(blob)) + blob + b'\0' * ((-(4 + len(blob))) % 4)
    return bytes(out)

def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.maximum(c, 0) ** (1 / 2.4) - 0.055)

def mips_bc7(png):
    im = Image.open(png).convert('RGBA'); a = np.asarray(im).astype(np.float32) / 255
    rgb, al = s2l(a[..., :3]), a[..., 3:4]
    has_transp = bool(al.min() < 0.999)
    w, h = im.size; out = []
    while True:
        u8 = np.clip(np.rint(np.concatenate([l2s(rgb), al], -1) * 255), 0, 255).astype(np.uint8)
        hh, ww = u8.shape[:2]
        if hh < 4 or ww < 4: u8 = np.pad(u8, ((0, max(0, 4 - hh)), (0, max(0, 4 - ww)), (0, 0)), mode='edge')
        out.append(etcpak.compress_bc7(np.ascontiguousarray(u8).tobytes(), u8.shape[1], u8.shape[0]))
        if hh == 1 and ww == 1: break
        nh, nw = max(1, hh // 2), max(1, ww // 2)
        rgb = rgb[:nh * 2, :nw * 2].reshape(nh, 2, nw, 2, 3).mean((1, 3)) if hh > 1 and ww > 1 else rgb[:nh, :nw]
        al = al[:nh * 2, :nw * 2].reshape(nh, 2, nw, 2, 1).mean((1, 3)) if hh > 1 and ww > 1 else al[:nh, :nw]
    return w, h, out, has_transp

def ktx2(w, h, payloads, has_transp):
    n = len(payloads); k = kvd(has_transp)
    dfd_off = 80 + 24 * n; kvd_off = dfd_off + 44; start = (kvd_off + len(k) + 15) // 16 * 16
    offs = [0] * n; cur = start; blob = bytearray()
    for lv in range(n - 1, -1, -1): offs[lv] = cur; blob += payloads[lv]; cur += len(payloads[lv])
    out = bytearray(IDENT) + struct.pack('<9I', 145, 1, w, h, 0, 0, 1, n, 0) + struct.pack('<4I', dfd_off, 44, kvd_off, len(k)) + struct.pack('<2Q', 0, 0)
    for lv in range(n): out += struct.pack('<3Q', offs[lv], len(payloads[lv]), len(payloads[lv]))
    out += DFD_BC7 + k; out += b'\0' * (start - len(out)); out += blob
    return bytes(out)

os.makedirs(OUT, exist_ok=True)
ft = int((time.time() + 11644473600) * 10_000_000)
names = ['EXT_%d' % (1001 + k) for k in range(7)] + ['ENG_L', 'ENG_R'] + ['WING_%s_%d' % (s, k) for s in 'LR' for k in (1001, 1002)] + ['Registration_ALBD']
only = sys.argv[1:]
for nm in names:
    if only and nm not in only: continue
    w, h, pl, tr = mips_bc7(os.path.join(ROOT, 'textures', nm + '.png'))
    dst = os.path.join(OUT, nm + '.PNG.KTX2')
    open(dst, 'wb').write(ktx2(w, h, pl, tr))
    meta = {'Version': 2, 'SourceFileDate': ft, 'Flags': JSON_FLAGS}
    if tr: meta['HasTransp'] = True
    open(dst + '.json', 'wb').write(json.dumps(meta, separators=(',', ':')).encode())
    print(nm, w, h, 'levels', len(pl), 'transp', tr, '%.1f MB' % (os.path.getsize(dst) / 1e6), flush=True)
