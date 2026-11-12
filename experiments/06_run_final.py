import json, itertools, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from multiprocessing import Pool
from eonsim import EONSim
SCHEMES = ["FF", "FF+PP", "Proposed", "Prop-Zone", "Prop-Hold", "Prop-Zone+Hold"]
SEEDS = range(10)
def job(a):
    exp, sch, load, share, seed = a
    sim = EONSim(sch, load, periodic_share=share, n_requests=20000, warmup=2000, lead=0.2, seed=seed)
    r = sim.run(); sim.check()
    r.update(exp=exp, scheme=sch, load=load, share=share, seed=seed)
    return r
if __name__ == "__main__":
    jobs = [("load", s, l, 0.3, k) for l, s, k in itertools.product(range(50, 121, 10), SCHEMES, SEEDS)]
    jobs += [("share", s, 100, sh, k) for sh, s, k in itertools.product([0.0, 0.1, 0.3, 0.5], SCHEMES, SEEDS)]
    res = []
    with Pool() as p:
        for i, r in enumerate(p.imap_unordered(job, jobs, chunksize=2)):
            res.append(r)
            if i % 50 == 0: print(i, len(jobs), flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "results", "results_final.json"), "w"))
    print("done", len(res))
