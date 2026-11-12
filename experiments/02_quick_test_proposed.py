import time
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from eonsim import EONSim
for share in [0.0,0.3]:
  for load in [60,90]:
    for sch in ["FF","FF+PP","Proposed"]:
        t=time.time(); sim=EONSim(sch,load,periodic_share=share,n_requests=10000,warmup=2000,seed=2); r=sim.run(); sim.check()
        print(share,load,sch,"BBP %.4f BPper %.4f BPrand %.4f moves %d rounds %d made %d used %d exp %d fail %d prec %.3f rec %.3f %.1fs"%(r["BBP"],r["BP_periodic"],r["BP_random"],r["moves"],r["rounds"],r["res_made"],r["res_used"],r["res_expired"],r["res_failed"],r["res_precision"],r["res_recall"],time.time()-t),flush=True)
