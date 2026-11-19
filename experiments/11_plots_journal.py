"""Step 8 - journal figures and summary (results_final.json, results_sensitivity.json, results_journal.json)."""
import json, os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
ld = lambda f: json.load(open(os.path.join(ROOT, "results", f)))
F, S, J = ld("results_final.json"), ld("results_sensitivity.json"), ld("results_journal.json")
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "pdf.fonttype": 42})
BLUE, ORANGE, GREEN, PURPLE, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a5cc2", "#555555"
def sel(D, **kw):
    return sorted([r for r in D if all(r.get(k) == v for k, v in kw.items())], key=lambda r: r["seed"])
def st(rows, m):
    a = np.array([r[m] for r in rows], float); return a.mean(), 1.96 * a.std(ddof=1) / np.sqrt(len(a))
def paired(rows, base, m):
    d = (np.array([r[m] for r in rows]) - np.array([r[m] for r in base])) / np.mean([r[m] for r in base]) * 100
    return d.mean(), 2.262 * d.std(ddof=1) / np.sqrt(len(d))
def save(fig, name):
    fig.savefig(os.path.join(ROOT, "figures", name + ".pdf")); fig.savefig(os.path.join(ROOT, "figures", name + ".png"), dpi=200)
NL = [50, 60, 70, 80, 100, 120]; GL = [70, 80, 100, 120, 150]
def rows(topo, sch, L):
    if topo == "nsf":
        return sel(J, exp="nsf_lead1", load=L) if sch == "Res1" else sel(F, exp="load", scheme=sch, load=L)
    return sel(J, exp="g50_load", scheme=sch, load=L)
STY = [("FF", "FF", GRAY, "o", ":"), ("FF+PP", "FF+PP", BLUE, "s", "-"), ("Prop-Zone", "Zone", GREEN, "D", "-."),
       ("Prop-Hold", "Hold", ORANGE, "^", "--")]
out = {}
# ---- Fig: BBP vs load, two topologies
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.8))
for ax, topo, Ls, title in [(axs[0], "nsf", NL, "NSFNET"), (axs[1], "g50", GL, "Germany50")]:
    sty = STY + [("Proposed", r"Reservation ($\delta=0.2$)", PURPLE, "v", "-")]
    for sch, lab, c, mk, ls in sty:
        v = [st(rows(topo, sch, L), "BBP") for L in Ls]
        ax.errorbar(Ls, [x[0] for x in v], yerr=[x[1] for x in v], label=lab, color=c, marker=mk, ls=ls, lw=1.2, ms=4, capsize=2, elinewidth=0.7)
    ax.set_yscale("log"); ax.set_xlabel("Offered load (Erlang)"); ax.set_title(title, fontsize=9)
    ax.grid(True, lw=0.3, color="#d0d0d0", which="both")
axs[0].set_ylabel("Bandwidth blocking probability")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=5, fontsize=7.5)
fig.tight_layout(rect=(0, 0, 1, 0.9)); save(fig, "j_fig_bbp")
# ---- Fig: shifts vs rounds
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.5))
for ax, topo, Ls, title in [(axs[0], "nsf", NL, "NSFNET"), (axs[1], "g50", GL, "Germany50")]:
    mv = [st(rows(topo, "FF+PP", L), "moves")[0] / 1e3 for L in Ls]; rd = [st(rows(topo, "FF+PP", L), "rounds")[0] / 1e3 for L in Ls]
    out["rounds_" + topo] = dict(loads=Ls, moves_k=mv, rounds_k=rd, ratio=[a / b for a, b in zip(mv, rd)])
    ax.plot(Ls, mv, color=BLUE, marker="o", lw=1.2, ms=4, label="Sequential shifts")
    ax.plot(Ls, rd, color=ORANGE, marker="s", ls="--", lw=1.2, ms=4, label="Parallel rounds")
    ax.set_xlabel("Offered load (Erlang)"); ax.set_title(title, fontsize=9); ax.grid(True, lw=0.3, color="#d0d0d0")
axs[0].set_ylabel("Operations per run (thousands)"); axs[0].legend(loc="upper left", fontsize=7.5)
fig.tight_layout(); save(fig, "j_fig_rounds")
# ---- Fig: trade-off at 100 Erlang, two topologies
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0))
for ax, topo in [(axs[0], "nsf"), (axs[1], "g50")]:
    if topo == "nsf":
        base = sel(F, exp="load", scheme="FF+PP", load=100)
        lead = {0.2: sel(F, exp="load", scheme="Proposed", load=100), **{d: sel(S, exp="lead", lead=d) for d in [1.0, 2.0, 5.0]}}
        bud = {b: sel(S, exp="budget", load=100, hold_budget=b) for b in [0.02, 0.05, 0.1, 0.2]}
        zone = {k: sel(F, exp="load", scheme=k, load=100) for k in ["Prop-Zone", "Prop-Zone+Hold"]}
        hold = sel(F, exp="load", scheme="Prop-Hold", load=100); title = "NSFNET, 100 Erlang"
    else:
        base = sel(J, exp="g50_load", scheme="FF+PP", load=100)
        lead = {0.2: sel(J, exp="g50_load", scheme="Proposed", load=100), **{d: sel(J, exp="g50_lead", lead=d) for d in [1.0, 2.0, 5.0]}}
        bud = {b: sel(J, exp="g50_budget", hold_budget=b) for b in [0.02, 0.05, 0.1, 0.2]}
        zone = {k: sel(J, exp="g50_load", scheme=k, load=100) for k in ["Prop-Zone", "Prop-Zone+Hold"]}
        hold = sel(J, exp="g50_load", scheme="Prop-Hold", load=100); title = "Germany50, 100 Erlang"
    P = lambda r: (100 * st(r, "BP_random")[0], 100 * st(r, "BP_periodic")[0])
    b0 = P(base)
    lp = [b0] + [P(lead[d]) for d in [0.2, 1.0, 2.0, 5.0]]
    hp = [b0] + [P(bud[b]) for b in [0.02, 0.05, 0.1, 0.2]] + [P(hold)]
    out["tradeoff_" + topo] = dict(lead=lp, budget=hp, lead_paired={d: {m: paired(lead[d], base, m) for m in ["BBP", "BP_periodic", "BP_random"]} for d in lead},
                                   budget_paired={b: {m: paired(bud[b], base, m) for m in ["BBP", "BP_periodic", "BP_random"]} for b in bud})
    ax.plot([p[0] for p in hp], [p[1] for p in hp], color=BLUE, marker="o", lw=1.2, ms=4, label=r"Hold, budget $\beta$")
    ax.plot([p[0] for p in lp], [p[1] for p in lp], color=ORANGE, marker="s", ls="--", lw=1.2, ms=4, label=r"Reservation, lead $\delta$")
    for (x, y), d in zip(lp[1:], [0.2, 1, 2, 5]):
        ax.annotate(r"$\delta=%g$" % d, (x, y), textcoords="offset points", xytext=(4, -9), fontsize=7, color="#404040")
    for (x, y), b in zip(hp[1:], [0.02, 0.05, 0.1, 0.2, 1]):
        if b in (0.02, 0.2, 1):
            ax.annotate(r"$\beta=%g$" % b, (x, y), textcoords="offset points", xytext=(3, -11) if b == 1 else (-8, 6), fontsize=7, color="#404040")
    for k, mk, lab in [("Prop-Zone", "D", "Zone"), ("Prop-Zone+Hold", "v", "Zone+Hold")]:
        ax.plot(*P(zone[k]), marker=mk, color=GREEN, mfc="white", mew=1.2, ms=5, ls="none", label=lab)
    ax.plot(*b0, marker="*", color="#303030", ms=9, ls="none", label="FF+PP")
    ax.margins(y=0.12); ax.set_xlabel("Blocking of random requests (%)"); ax.set_title(title, fontsize=9); ax.grid(True, lw=0.3, color="#d0d0d0")
axs[0].set_ylabel("Blocking of periodic requests (%)")
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=5, fontsize=7.5)
fig.tight_layout(rect=(0, 0, 1, 0.9)); save(fig, "j_fig_tradeoff")
# ---- Fig: periodic share phi
PH = [0.1, 0.2, 0.3, 0.4, 0.5]
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.6))
out["phi"] = {}
for sch, lab, c, mk, ls in [("Proposed", r"Reservation ($\delta=0.075\,T$)", PURPLE, "v", "-"), ("Prop-Hold", "Hold", ORANGE, "^", "--")]:
    vals = {m: [paired(sel(J, exp="nsf_phi", scheme=sch, periodic_share=p), sel(J, exp="nsf_phi", scheme="FF+PP", periodic_share=p), m) for p in PH] for m in ["BP_periodic", "BBP", "BP_random"]}
    out["phi"][sch] = vals
    for ax, m in [(axs[0], "BP_periodic"), (axs[1], "BBP")]:
        ax.errorbar(PH, [v[0] for v in vals[m]], yerr=[v[1] for v in vals[m]], color=c, marker=mk, ls=ls, lw=1.2, ms=4, capsize=2, elinewidth=0.7, label=lab)
for ax, yl in [(axs[0], "Periodic BP change (%)"), (axs[1], "BBP change (%)")]:
    ax.axhline(0, color="#707070", lw=0.8); ax.set_xlabel(r"Share of periodic load $\phi$"); ax.set_ylabel(yl); ax.grid(True, lw=0.3, color="#d0d0d0")
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=2, fontsize=7.5)
fig.tight_layout(rect=(0, 0, 1, 0.9)); save(fig, "j_fig_phi")
out["phi"]["FF+PP_BBP"] = [st(sel(J, exp="nsf_phi", scheme="FF+PP", periodic_share=p), "BBP") for p in PH]
# ---- tables
def trow(r, base=None):
    d = dict(BBP=st(r, "BBP")[0], per=st(r, "BP_periodic")[0], rand=st(r, "BP_random")[0], shifts=st(r, "moves")[0])
    if base is not None: d.update({k: paired(r, base, m) for k, m in [("dBBP", "BBP"), ("dper", "BP_periodic"), ("drand", "BP_random")]})
    return d
out["table_nsf"] = {L: {lab: trow(rows("nsf", s, L), rows("nsf", "FF+PP", L)) for s, lab in [("FF+PP", "FF+PP"), ("Proposed", "Res02"), ("Res1", "Res1"), ("Prop-Zone", "Zone"), ("Prop-Hold", "Hold"), ("Prop-Zone+Hold", "ZoneHold")]} for L in [80, 100, 120]}
out["table_g50"] = {L: {lab: trow(rows("g50", s, L), rows("g50", "FF+PP", L)) for s, lab in [("FF+PP", "FF+PP"), ("Proposed", "Res02"), ("Prop-Zone", "Zone"), ("Prop-Hold", "Hold"), ("Prop-Zone+Hold", "ZoneHold")]} for L in [80, 100, 150]}
out["pp_gain"] = {t: {L: 1 - st(rows(t, "FF+PP", L), "BBP")[0] / st(rows(t, "FF", L), "BBP")[0] for L in Ls} for t, Ls in [("nsf", NL), ("g50", GL)]}
out["detect_g50"] = {L: (st(rows("g50", "Proposed", L), "res_precision")[0], st(rows("g50", "Proposed", L), "res_recall")[0]) for L in GL}
json.dump(out, open(os.path.join(ROOT, "results", "summary_journal.json"), "w"), indent=1, default=float)
print("ok")
