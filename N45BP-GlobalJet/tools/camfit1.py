import numpy as np, json
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
# (name, model xyz, photo uv, group F=forward (shifted by dL) / A=aft)
L=[
 ('nose',(0,-11.667,0.258),(65,1328),'F'),
 ('doorTL',(0.830,-7.333,1.996),(716.7,1141.7),'F'),
 ('doorTR',(0.843,-6.392,1.996),(852.8,1155.6),'F'),
 ('doorBL',(0.827,-7.333,-0.108),(682,1452.8),'F'),
 ('doorBR',(0.821,-6.392,-0.108),(822,1472),'F'),
 ('cwinAT',(1.010,-8.15,1.742),(587,1161),'F'),
 ('cwinAB',(1.267,-8.15,1.3125),(572,1233),'F'),
 ('tailtip',(0,14.807,1.264),(4048,1637),'A'),
 ('bagTL',(1.317,5.47,1.18),(2570,1493),'A'),
 ('bagTR',(1.202,6.60,1.18),(2746.7,1506.7),'A'),
 ('bagBL',(1.210,5.47,0.23),(2560,1620),'A'),
 ('bagBR',(1.062,6.60,0.23),(2740,1643),'A'),
 ('bullettop',(0,14.14,5.907),(4010,890),'A'),
 ('finroot',(0,8.57,2.52),(3095,1328),'A'),
 ('stabtipL',(4.76,18.744,4.945),(4745,1087),'A'),
]
wy=[-4.058,-3.24,-2.42,-1.59,-0.76,0.02,0.917,1.776,2.53,3.397,4.179]
wu=[(1069.4,1297.5),(1195.6,1311.3),(1323.1,1326.9),(1450,1341.3),(1580,1356.3),(1701.9,1370),(1843.8,1386.3),(1976.3,1401.3),(2094.7,1415.3),(2231.3,1430.7),(2349.3,1445.3)]
for k,(y,uv) in enumerate(zip(wy,wu)): L.append((f'win{k+1}',(1.337,y,1.267),uv,'A'))
X=np.array([l[1] for l in L],float); U=np.array([l[2] for l in L],float); G=np.array([l[3]=='F' for l in L])
def project(params, X, fwd, persp=True):
    s, rx, ry, rz, tu, tv, dL, invd = params
    Xs = X.copy(); Xs[fwd,1] += dL
    R = Rot.from_euler('xyz',[rx,ry,rz]).as_matrix()
    # base camera: looking from +x toward -x; image u = +y, v = -z, depth = -x (bigger = farther)
    B = np.array([[0,1,0],[0,0,-1],[-1,0,0]],float)
    C = (Xs @ R.T) @ B.T
    if persp:
        w = 1.0/(1.0 + invd*C[:,2])
    else: w = 1.0
    return np.stack([s*C[:,0]*w+tu, s*C[:,1]*w+tv],1)
def res(p, persp): return (project(p,X,G,persp)-U).ravel()
p0=np.array([153,0,0,0.115,2000,1300,0.8,0.0])
r=least_squares(lambda p:res(np.r_[p,0.0],False),p0[:7])
pa=np.r_[r.x,0.0]
print('affine/orthographic fit: s=%.2f rot(deg)=%s t=(%.1f,%.1f) dL=%.3f'%(pa[0],np.degrees(pa[1:4]).round(2),pa[4],pa[5],pa[6]))
e=project(pa,X,G,False)-U
for l,ee in zip(L,e): print('  %-10s err=(%6.1f,%6.1f)'%(l[0],ee[0],ee[1]))
print(' rms',np.sqrt((e**2).mean()))
r2=least_squares(lambda p:res(p,True),pa)
pp=r2.x
print('perspective fit: s=%.2f rot(deg)=%s t=(%.1f,%.1f) dL=%.3f invd=%.5f (dist %.0f m)'%(pp[0],np.degrees(pp[1:4]).round(2),pp[4],pp[5],pp[6],pp[7],1/pp[7] if pp[7] else 0))
e=project(pp,X,G,True)-U
for l,ee in zip(L,e): print('  %-10s err=(%6.1f,%6.1f)'%(l[0],ee[0],ee[1]))
print(' rms',np.sqrt((e**2).mean()))
json.dump(dict(ortho=list(pa),persp=list(pp)),open('work/cam1.json','w'))
