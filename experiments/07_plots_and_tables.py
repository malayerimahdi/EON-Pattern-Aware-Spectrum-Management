"""Step 6 - figures and tables for the paper from results/results_final.json."""
import json, os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "results", "results_final.json")))
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "pdf.fonttype": 42})
C = {"FF": "#2a78d6", "FF+PP": "#eb6834", "Proposed": "#1baf7a"}
M = {"FF": "o", "FF+PP": "s", "Proposed": "^"}; LS = {"FF": "-", "FF+PP": "--", "Proposed": "-."}
def st(exp, sch, key, x, m):
    a = np.array([r[m] for r in R if r["exp"] == exp and r["scheme"] == sch and r[key] == x], dtype=float)
    a = a[~np.isnan(a)]
    return float(a.mean()), float(1.96 * a.std(ddof=1) / np.sqrt(len(a)))
loads = list(range(50, 121, 10))
fig, ax = plt.subplots(figsize=(3.4, 2.3))
for s in ["FF", "FF+PP", "Proposed"]:
    m, e = zip(*[st("load", s, "load", x, "BBP") for x in loads])
    ax.errorbar(loads, m, yerr=e, color=C[s], marker=M[s], ls=LS[s], lw=1.4, ms=4, capsize=2, elinewidth=0.8,
                label={"Proposed": "Reservation"}.get(s, s))
ax.set_yscale("log"); ax.set_xlabel("Offered load (Erlang)"); ax.set_ylabel("Bandwidth blocking probability")
ax.grid(True, lw=0.3, color="#d0d0d0"); ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "figures", "fig_bbp.pdf")); fig.savefig(os.path.join(ROOT, "figures", "fig_bbp.png"), dpi=200)
fig, ax = plt.subplots(figsize=(3.4, 2.2))
mv = [st("load", "FF+PP", "load", x, "moves")[0] / 1000 for x in loads]
rd = [st("load", "FF+PP", "load", x, "rounds")[0] / 1000 for x in loads]
ax.plot(loads, mv, color=C["FF"], marker="o", lw=1.4, ms=4, label="Sequential shifts")
ax.plot(loads, rd, color=C["FF+PP"], marker="s", ls="--", lw=1.4, ms=4, label="Grouped rounds")
ax.set_xlabel("Offered load (Erlang)"); ax.set_ylabel("Shift operations (thousands)")
ax.grid(True, lw=0.3, color="#d0d0d0"); ax.legend(loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "figures", "fig_rounds.pdf")); fig.savefig(os.path.join(ROOT, "figures", "fig_rounds.png"), dpi=200)
summary = {"load": {}, "share": {}}
SCH = ["FF", "FF+PP", "Proposed", "Prop-Zone", "Prop-Hold", "Prop-Zone+Hold"]
for x in range(50, 121, 10):
    summary["load"][x] = {s: {m: st("load", s, "load", x, m) for m in
                              ["BBP", "BP_periodic", "BP_random", "frag", "moves", "rounds", "defrag_calls", "res_precision", "res_recall"]} for s in SCH}
for x in [0.0, 0.1, 0.3, 0.5]:
    summary["share"][x] = {s: {m: st("share", s, "share", x, m) for m in ["BBP", "BP_periodic", "BP_random", "moves"]} for s in SCH}
json.dump(summary, open(os.path.join(ROOT, "results", "summary_final.json"), "w"), indent=1)
print("moves/rounds:", [round(a / b, 2) for a, b in zip(mv, rd)])
for x in [80, 100, 120]:
    print("\nload", x)
    for s in SCH:
        d = summary["load"][x][s]
        print("%-15s BBP %.4f±%.4f  per %.4f±%.4f  rand %.4f±%.4f  moves %6.0f  prec %.3f rec %.3f" % (
            s, *d["BBP"], *d["BP_periodic"], *d["BP_random"], d["moves"][0], d["res_precision"][0], d["res_recall"][0]))
print("\nshare sweep @100")
for x in [0.0, 0.1, 0.3, 0.5]:
    print(x, "  ".join("%s %.4f±%.4f" % (s, *summary["share"][x][s]["BBP"]) for s in SCH))
