"""Step 8 experiments (journal version):
 A. Germany50 (SNDlib, 50 nodes, 88 links): all schemes over 70-150 Erlang
 B. Germany50 at 100 Erlang: reservation lead delta and Hold budget beta
 C. NSFNET: Reservation with lead 1.0 at every load of the main sweep
 D. NSFNET at 100 Erlang: periodic share phi in {0.1..0.5}, lead scaled to 7.5% of the period
phi = 0.3 unless stated, 10 seeds. NSFNET defaults reproduce results_final.json exactly."""
import json, itertools, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from multiprocessing import Pool
from eonsim import EONSim
SEEDS = range(10)
SCHEMES = ["FF", "FF+PP", "Proposed", "Prop-Zone", "Prop-Hold", "Prop-Zone+Hold"]
def job(a):
    exp, sch, load, kw, seed = a
    args = dict(periodic_share=0.3, n_requests=20000, warmup=2000, lead=0.2, seed=seed)
    args.update(kw)
    sim = EONSim(sch, load, **args)
    r = sim.run(); sim.check()
    r.update(exp=exp, scheme=sch, load=load, seed=seed, **kw)
    return r
if __name__ == "__main__":
    G = dict(topology="germany50")
    jobs  = [("g50_load", s, L, G, k) for s, L, k in itertools.product(SCHEMES, [70, 80, 100, 120, 150], SEEDS)]
    jobs += [("g50_lead", "Proposed", 100, dict(G, lead=d), k) for d, k in itertools.product([1.0, 2.0, 5.0], SEEDS)]
    jobs += [("g50_budget", "Prop-Hold", 100, dict(G, hold_budget=b), k) for b, k in itertools.product([0.02, 0.05, 0.1, 0.2], SEEDS)]
    jobs += [("nsf_lead1", "Proposed", L, dict(lead=1.0), k) for L, k in itertools.product([50, 60, 70, 80, 100, 120], SEEDS)]
    for phi in [0.1, 0.2, 0.3, 0.4, 0.5]:
        T = 20.0 * 20 / (phi * 100)              # period of each periodic flow at 100 Erlang
        for s, k in itertools.product(["FF+PP", "Proposed", "Prop-Hold"], SEEDS):
            kw = dict(periodic_share=phi)
            if s == "Proposed":
                kw["lead"] = round(0.075 * T, 3)
            jobs.append(("nsf_phi", s, 100, kw, k))
    res = []
    with Pool() as p:
        for i, r in enumerate(p.imap_unordered(job, jobs, chunksize=2)):
            res.append(r)
            if i % 50 == 0: print(i, len(jobs), flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "results", "results_journal.json"), "w"))
    print("done", len(res))
