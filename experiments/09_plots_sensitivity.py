"""Step 7 - figures and summary for the sensitivity / hold-budget experiments (results_sensitivity.json)."""
import json, os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "results", "results_sensitivity.json")))
F = json.load(open(os.path.join(ROOT, "results", "results_final.json")))
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "pdf.fonttype": 42})
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
def st(rows, m):
    a = np.array([r[m] for r in rows], dtype=float); a = a[~np.isnan(a)]
    return float(a.mean()), float(1.96 * a.std(ddof=1) / np.sqrt(len(a)))
def sel(D, **kw):
    return [r for r in D if all(r.get(k) == v for k, v in kw.items())]
out = {}
# ---- A. jitter
J = [0.0, 0.02, 0.05, 0.1, 0.2]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(3.5, 1.9))
ref = st(sel(F, exp="load", scheme="FF+PP", load=100), "BP_periodic")
for e, c, mk, ls in [(0.1, BLUE, "o", "-"), (0.3, ORANGE, "s", "--")]:
    rec = [st(sel(R, exp="jitter", jitter=j, eps=e), "res_recall") for j in J]
    bp = [st(sel(R, exp="jitter", jitter=j, eps=e), "BP_periodic") for j in J]
    pre = [st(sel(R, exp="jitter", jitter=j, eps=e), "res_precision") for j in J]
    out["jitter_eps%.1f" % e] = dict(sigma=J, recall=rec, precision=pre, BP_periodic=bp,
                                      BBP=[st(sel(R, exp="jitter", jitter=j, eps=e), "BBP") for j in J],
                                      BP_random=[st(sel(R, exp="jitter", jitter=j, eps=e), "BP_random") for j in J])
    a1.errorbar(J, [m for m, _ in rec], yerr=[x for _, x in rec], color=c, marker=mk, ls=ls, lw=1.2, ms=3.5, capsize=2, elinewidth=0.7, label=r"$\varepsilon=%.1f$" % e)
    a2.errorbar(J, [100 * m for m, _ in bp], yerr=[100 * x for _, x in bp], color=c, marker=mk, ls=ls, lw=1.2, ms=3.5, capsize=2, elinewidth=0.7)
a2.axhline(100 * ref[0], color="#707070", lw=0.9, ls=":"); a2.text(0.2, 100 * ref[0] + 0.08, "FF+PP", ha="right", va="bottom", fontsize=7, color="#505050")
a1.set_xlabel(r"Jitter $\sigma$"); a1.set_ylabel("Detection recall"); a1.set_ylim(0, 1)
a2.set_xlabel(r"Jitter $\sigma$"); a2.set_ylabel("Periodic BP (%)")
for a in (a1, a2): a.grid(True, lw=0.3, color="#d0d0d0")
a1.legend(loc="lower left", fontsize=7)
fig.tight_layout(w_pad=1.0); fig.savefig(os.path.join(ROOT, "figures", "fig_jitter.pdf")); fig.savefig(os.path.join(ROOT, "figures", "fig_jitter.png"), dpi=200)
# ---- B. lead
out["lead"] = {d: {m: st(sel(R, exp="lead", lead=d), m) for m in ["BBP", "BP_periodic", "BP_random", "res_precision", "res_recall"]}
               for d in [0.2, 1.0, 2.0, 5.0]}
# ---- C. budget (Pareto: random BP vs periodic BP)
B = [0.02, 0.05, 0.1, 0.2]
fig, ax = plt.subplots(figsize=(3.4, 2.4))
for L, c, mk, ls in [(100, BLUE, "o", "-"), (120, ORANGE, "s", "--")]:
    pts = [st(sel(F, exp="load", scheme="FF+PP", load=L), "BP_random") + st(sel(F, exp="load", scheme="FF+PP", load=L), "BP_periodic")]
    for b in B:
        rows = sel(R, exp="budget", load=L, hold_budget=b)
        pts.append(st(rows, "BP_random") + st(rows, "BP_periodic"))
    rows = sel(F, exp="load", scheme="Prop-Hold", load=L)
    pts.append(st(rows, "BP_random") + st(rows, "BP_periodic"))
    out["budget_%d" % L] = dict(beta=[0] + B + [1], points=pts,
                                BBP=[st(sel(F, exp="load", scheme="FF+PP", load=L), "BBP")] + [st(sel(R, exp="budget", load=L, hold_budget=b), "BBP") for b in B] + [st(rows, "BBP")])
    x = [100 * p[0] for p in pts]; y = [100 * p[2] for p in pts]
    ax.plot(x, y, color=c, marker=mk, ls=ls, lw=1.2, ms=4, label="%d Erlang" % L)
    for xi, yi, b in zip(x, y, [0] + B + [1]):
        if b in (0, 0.05, 1):
            ax.annotate(r"$\beta=%s$" % ("0" if b == 0 else ("1" if b == 1 else b)), (xi, yi), textcoords="offset points",
                        xytext=(4, 3), fontsize=6.5, color="#404040")
    for sch, m2 in [("Prop-Zone", "D"), ("Prop-Zone+Hold", "v")]:
        r2 = sel(F, exp="load", scheme=sch, load=L)
        ax.plot(100 * st(r2, "BP_random")[0], 100 * st(r2, "BP_periodic")[0], marker=m2, color=c, ms=4, mfc="white", ls="none")
ax.plot([], [], marker="D", color="#606060", mfc="white", ls="none", ms=4, label="Zone")
ax.plot([], [], marker="v", color="#606060", mfc="white", ls="none", ms=4, label="Zone+Hold")
ax.set_xlabel("Blocking of random requests (%)"); ax.set_ylabel("Blocking of periodic requests (%)")
ax.grid(True, lw=0.3, color="#d0d0d0"); ax.legend(loc="upper right", fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "figures", "fig_budget.pdf")); fig.savefig(os.path.join(ROOT, "figures", "fig_budget.png"), dpi=200)
json.dump(out, open(os.path.join(ROOT, "results", "summary_sensitivity.json"), "w"), indent=1)
for k, v in out.items():
    print(k); print(json.dumps(v, indent=None)[:1500])
