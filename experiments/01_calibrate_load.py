"""Step 1 - find the useful load range (blocking between ~0.1% and ~15%)."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import time
from eonsim import EONSim
for load in [30, 45, 60, 75, 90, 110, 130]:
    out = []
    for sch in ["FF", "FF+PP"]:
        sim = EONSim(sch, load, n_requests=10000, warmup=2000, seed=1); r = sim.run(); sim.check()
        out.append("%s BBP %.4f" % (sch, r["BBP"]))
    print(load, " | ".join(out), "frag %.3f" % r["frag"], "moves", r["moves"])
