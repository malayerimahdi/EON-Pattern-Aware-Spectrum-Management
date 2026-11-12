import json, itertools, sys
from multiprocessing import Pool
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from eonsim import EONSim
SEEDS = range(10)
def job(a):
    exp, sch, load, share, seed = a
    sim = EONSim(sch, load, periodic_share=share, n_requests=20000, warmup=2000, lead=0.2, seed=seed)
    r = sim.run(); sim.check()
    r.update(exp=exp, scheme=sch, load=load, share=share, seed=seed)
    return r
if __name__ == "__main__":
    jobs = []
    for load, sch, seed in itertools.product(range(40, 121, 10), ["FF", "FF+PP", "Proposed"], SEEDS):
        jobs.append(("load", sch, load, 0.3, seed))
    for share, sch, seed in itertools.product([0.0, 0.1, 0.3, 0.5], ["FF", "FF+PP", "Proposed"], SEEDS):
        jobs.append(("share", sch, 90, share, seed))
    with Pool() as p:
        res = []
        for i, r in enumerate(p.imap_unordered(job, jobs, chunksize=2)):
            res.append(r)
            if i % 40 == 0: print(i, len(jobs), flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "results", "results_v1.json"), "w"))
    print("done", len(res))
