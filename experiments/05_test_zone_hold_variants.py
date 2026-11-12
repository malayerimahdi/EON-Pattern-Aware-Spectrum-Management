import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from eonsim import EONSim
import numpy as np
for load in [80,100,120]:
    for sch in ["FF+PP","Proposed","Prop-Zone","Prop-Hold","Prop-Zone+Hold"]:
        rs=[]
        for seed in range(3):
            sim=EONSim(sch,load,periodic_share=0.3,n_requests=12000,warmup=2000,lead=0.2,seed=seed); r=sim.run(); sim.check(); rs.append(r)
        m=lambda k: np.mean([r[k] for r in rs])
        print(load,"%-15s BBP %.4f BPper %.4f BPrand %.4f moves %6d prec %.3f rec %.3f held %d"%(sch,m("BBP"),m("BP_periodic"),m("BP_random"),m("moves"),m("res_precision") if sch!="FF+PP" else 0,m("res_recall"),m("held")),flush=True)
