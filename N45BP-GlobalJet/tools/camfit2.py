import numpy as np, json, sys
sys.path.insert(0,'scripts')
from scipy.optimize import least_squares
from camlib import project
dL=json.load(open('work/cam1.json'))['persp'][6]
print('dL from photo1:',dL)
L=[
 ('nose',(0,-11.667,0.258),(1830,691.6),'F',1),
 ('cwinAT',(-1.010,-8.15,1.742),(1602.6,582.1),'F',1),
 ('cwinAB',(-1.267,-8.15,1.3125),(1596.3,609.5),'F',1),
 ('bullettop',(0,14.14,5.907),(807.1,254.3),'A',1),
 ('stabtipR',(-4.76,18.744,4.945),(329.5,304.8),'A',1),
 ('stabtipL',(4.76,18.744,4.945),(976.2,313.8),'A',1),
 ('ringOut',(-3.124,7.36,1.508),(886.7,581.9),'A',0.6),
 ('ringIn',(-1.429,7.36,1.508),(985.7,574.8),'A',0.6),
 ('ringTop',(-2.278,7.39,2.356),(938.1,529.5),'A',0.6),
 ('ringBot',(-2.278,7.33,0.663),(935.7,630.5),'A',0.6),
 ('wingletR',(-14.2,10.13,1.548),(40,567),'A',0.3),
 ('wingletL',(14.2,10.13,1.548),(1826.3,556.8),'A',0.3),
]
wy=[4.904,4.179,3.397,2.53,1.776,0.917,0.02,-0.76,-1.59,-2.42,-3.24,-4.058]
wu=[(1091.1,605.8),(1119.5,606.8),(1150,607.4),(1184.2,607.9),(1215.8,608.4),(1248.9,608.9),(1286.8,610),(1320,611),(1353.7,611.6),(1386.8,612.1),(1421,612.6),(1455.3,613.2)]
for k,(y,uv) in enumerate(zip(wy,wu)): L.append((f'win{k+1}',(-1.337,y,1.267),uv,'A',1))
L.append(('win13',(-1.337,-5.702,1.267),(1489.5,613.7),'F',1)); L.append(('win14',(-1.337,-6.65,1.267),(1527.4,614.2),'F',1))
X=np.array([l[1] for l in L],float); U=np.array([l[2] for l in L],float); G=np.array([l[3]=='F' for l in L]); Wt=np.array([l[4] for l in L],float)
X[G,1]+=dL
def res(q):
    p=np.r_[q[:6],dL,q[6]]
    return ((project(p,X,True,'R')[:,:2]-U)*Wt[:,None]).ravel()
best=None
for rz0 in np.radians(np.arange(-80,81,10)):
    for invd0 in (0.003,0.01,0.03):
        for s0 in (30,45,60):
            q0=np.array([s0,0,0,rz0,1200,650,invd0])
            try: r=least_squares(res,q0,loss='soft_l1',f_scale=4.0,max_nfev=3000)
            except Exception as e: continue
            if best is None or r.cost<best.cost: best=r
q=best.x; p=np.r_[q[:6],dL,q[6]]
print('fit: s=%.2f rot(deg)=%s t=(%.1f,%.1f) invd=%.5f (dist %.0f m) cost %.2f'%(p[0],np.degrees(p[1:4]).round(2),p[4],p[5],p[7],1/p[7],best.cost))
e=project(p,X,True,'R')[:,:2]-U
for l,ee in zip(L,e): print('  %-10s err=(%6.1f,%6.1f)'%(l[0],ee[0],ee[1]))
json.dump(dict(persp=list(p)),open('work/cam2.json','w'))
