"""Decision-tree prediction of per-node-pair demand: will pair (s,d) exceed the transmission
threshold (mean per-pair demand per window) in the next window?"""
import re, json, os, numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import precision_score, recall_score, f1_score

def load_trace(path):
    rows=[]
    for l in open(path):
        m=re.search(r"SIMTIME: ([\d.]+)\s+source:(\d+) and Dest:(\d+) and needed:(\d+)",l)
        if m: rows.append((float(m[1]),int(m[2]),int(m[3]),int(m[4])))
    return np.array(rows)

def synth_trace(load, share, duration, seed, n_flows=20, mean_hold=20.0):
    rng=np.random.default_rng(seed); rows=[]
    lam=(1-share)*load/mean_hold; t=0
    while True:
        t+=rng.exponential(1/lam)
        if t>duration: break
        s,d=rng.choice(14,2,replace=False); rows.append((t,s,d,rng.integers(5,21)))
    if share>0:
        rate=share*load/mean_hold/n_flows
        for _ in range(n_flows):
            s,d=rng.choice(14,2,replace=False); b=rng.integers(5,21); T=1/rate; t=rng.uniform(0,T)
            while t<duration: rows.append((t,s,d,b)); t+=T
    a=np.array(rows,dtype=float); return a[np.argsort(a[:,0])]

def windows(tr, delta):
    nw=int(tr[:,0].max()//delta)+1
    D=np.zeros((14,14,nw))
    for t,s,d,b in tr: D[int(s),int(d),int(t//delta)]+=b
    return D[:,:,:-1]          # drop last (partial) window

def dt_eval(D, lags=3, seed=0):
    tau=D.mean()              # transmission threshold = mean demand per pair per window
    X,y,w=[],[],[]
    nw=D.shape[2]
    for s in range(14):
        for d in range(14):
            if s==d: continue
            for k in range(lags,nw):
                X.append(list(D[s,d,k-lags:k])); y.append(int(D[s,d,k]>tau)); w.append(k)
    X,y,w=np.array(X),np.array(y),np.array(w)
    cut=int(nw*0.7)
    tr,te=w<cut,w>=cut
    clf=DecisionTreeClassifier(max_depth=5,random_state=seed).fit(X[tr],y[tr])
    p=clf.predict(X[te])
    return dict(precision=precision_score(y[te],p,zero_division=0),recall=recall_score(y[te],p,zero_division=0),
                f1=f1_score(y[te],p,zero_division=0),pos_rate=float(y[te].mean()),tau=float(tau))

out={}
tr=load_trace(os.path.join(os.path.dirname(__file__), "..", "data", "cons22.txt"))
out["opnet_trace"]=dt_eval(windows(tr,5.0))
for share in [0.0,0.1,0.3,0.5]:
    rs=[dt_eval(windows(synth_trace(90,share,4000,seed),20.0),seed=seed) for seed in range(10)]
    out[f"synthetic_share_{share}"]={k:float(np.mean([r[k] for r in rs])) for k in rs[0]}
    out[f"synthetic_share_{share}"].update({k+"_std":float(np.std([r[k] for r in rs])) for k in ["precision","recall","f1"]})
json.dump(out,open(os.path.join(os.path.dirname(__file__), "..", "results", "dt_results.json"),"w"),indent=1)
for k,v in out.items(): print(k, {a:round(b,3) for a,b in v.items()})
