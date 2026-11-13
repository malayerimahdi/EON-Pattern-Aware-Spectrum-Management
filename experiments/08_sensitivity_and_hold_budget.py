"""Step 7 experiments (ONDM version):
 A. detection under arrival-time jitter sigma, for two tolerances eps (Prop-Hold, 100 Erlang)
 B. reservation lead time delta (Proposed = Reservation, 100 Erlang)
 C. Hold with a budget beta on idle held spectrum per link (100 and 120 Erlang)
All at phi = 0.3, 10 seeds. Defaults (jitter=0, hold_budget=1) reproduce results_final.json exactly."""
import json, itertools, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from multiprocessing import Pool
from eonsim import EONSim
SEEDS = range(10)
def job(a):
    exp, sch, load, kw, seed = a
    args = dict(periodic_share=0.3, n_requests=20000, warmup=2000, lead=0.2, seed=seed)
    args.update(kw)
    sim = EONSim(sch, load, **args)
    r = sim.run(); sim.check()
    r.update(exp=exp, scheme=sch, load=load, seed=seed, **kw)
    return r
if __name__ == "__main__":
    jobs  = [("jitter", "Prop-Hold", 100, dict(jitter=j, eps=e), k)
             for j, e, k in itertools.product([0.0, 0.02, 0.05, 0.1, 0.2], [0.1, 0.3], SEEDS)]
    jobs += [("lead", "Proposed", 100, dict(lead=d), k) for d, k in itertools.product([0.2, 1.0, 2.0, 5.0], SEEDS)]
    jobs += [("budget", "Prop-Hold", L, dict(hold_budget=b), k)
             for L, b, k in itertools.product([100, 120], [0.02, 0.05, 0.1, 0.2], SEEDS)]
    res = []
    with Pool() as p:
        for i, r in enumerate(p.imap_unordered(job, jobs, chunksize=2)):
            res.append(r)
            if i % 20 == 0: print(i, len(jobs), flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "results", "results_sensitivity.json"), "w"))
    print("done", len(res))
