import sys
from PIL import Image, ImageDraw, ImageFont
src, out, x0, y0, x1, y1, step = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
scale = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
if scale != 1: im = im.resize((int(im.size[0]*scale), int(im.size[1]*scale)), Image.LANCZOS)
d = ImageDraw.Draw(im, 'RGBA')
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13) if __import__('os').path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') else ImageFont.load_default()
gx = (x0 // step + 1) * step
while gx < x1:
    X = (gx - x0) * scale
    d.line([(X, 0), (X, im.size[1])], fill=(255, 255, 0, 110), width=1)
    d.text((X + 2, 2), str(gx), fill=(255, 255, 0, 255), font=f)
    d.text((X + 2, im.size[1] - 16), str(gx), fill=(255, 255, 0, 255), font=f)
    gx += step
gy = (y0 // step + 1) * step
while gy < y1:
    Y = (gy - y0) * scale
    d.line([(0, Y), (im.size[0], Y)], fill=(0, 255, 255, 110), width=1)
    d.text((2, Y + 1), str(gy), fill=(0, 255, 255, 255), font=f)
    d.text((im.size[0] - 40, Y + 1), str(gy), fill=(0, 255, 255, 255), font=f)
    gy += step
im.save(out, quality=92)
print(out, im.size)
