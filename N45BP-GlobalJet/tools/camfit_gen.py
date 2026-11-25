import numpy as np, json, sys
sys.path.insert(0,'scripts')
from scipy.optimize import least_squares
from camlib import project
def fit(L, side, out, t0=(600,400), s_list=(30,45,60,90), rz_list=None):
    dL=json.load(open('work/cam1.json'))['persp'][6]
    X=np.array([l[1] for l in L],float); U=np.array([l[2] for l in L],float); G=np.array([l[3]=='F' for l in L]); Wt=np.array([l[4] for l in L],float)
    X[G,1]+=dL
    def res(q):
        p=np.r_[q[:6],dL,q[6]]
        return ((project(p,X,True,side)[:,:2]-U)*Wt[:,None]).ravel()
    best=None
    for rz0 in np.radians(np.arange(-80,81,10) if rz_list is None else rz_list):
        for invd0 in (0.003,0.01,0.03,0.06):
            for s0 in s_list:
                q0=np.array([s0,0,0,rz0,t0[0],t0[1],invd0])
                try: r=least_squares(res,q0,loss='soft_l1',f_scale=4.0,max_nfev=3000)
                except Exception: continue
                if r.x[6] <= 0 or r.x[0] <= 0: continue
                if best is None or r.cost<best.cost: best=r
    q=best.x; p=np.r_[q[:6],dL,q[6]]
    print('fit: s=%.2f rot(deg)=%s t=(%.1f,%.1f) invd=%.5f (dist %.0f m) cost %.2f'%(p[0],np.degrees(p[1:4]).round(2),p[4],p[5],p[7],1/p[7],best.cost))
    e=project(p,X,True,side)[:,:2]-U
    for l,ee in zip(L,e): print('  %-10s err=(%6.1f,%6.1f)'%(l[0],ee[0],ee[1]))
    json.dump(dict(persp=list(p)),open(out,'w'))
