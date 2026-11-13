"""
Discrete-event simulator for dynamic elastic optical networks (EONs).

Schemes
  FF        : k-shortest-path routing + First-Fit spectrum assignment, no defragmentation
  FF+PP     : FF + reactive Push-Pull defragmentation when a request is blocked
  Proposed  : FF+PP + periodic-request detection and proactive (advance) spectrum reservation

Traffic follows the OPNET model of the MSc thesis (Poisson arrivals, uniform node pairs,
uniform FS demand 5-20, exponential holding time with mean 20), plus optional periodic flows
(fixed node pair and FS demand, constant inter-arrival time) that carry a given share of the load.
"""
import heapq, itertools, math
import numpy as np

# ---------------------------------------------------------------- topology
# NSFNET, 14 nodes, 21 links, lengths in km (nodes numbered 1..14 as in the thesis figure)
NSFNET_LINKS = [
    (1, 2, 1100), (1, 3, 1600), (1, 8, 2800), (2, 3, 600), (2, 4, 1000), (3, 6, 2000),
    (4, 5, 600), (4, 11, 2400), (5, 6, 1100), (5, 7, 800), (6, 10, 1200), (6, 13, 2000),
    (7, 8, 700), (8, 9, 700), (9, 10, 900), (9, 12, 500), (9, 14, 500), (11, 12, 800),
    (11, 14, 800), (12, 13, 300), (13, 14, 300),
]
N_NODES = 14


def build_graph():
    adj = {n: {} for n in range(N_NODES)}
    link_id = {}
    for i, (a, b, L) in enumerate(NSFNET_LINKS):
        a -= 1; b -= 1
        adj[a][b] = L; adj[b][a] = L
        link_id[(a, b)] = i; link_id[(b, a)] = i      # one spectrum resource per (bidirectional) link
    return adj, link_id


def k_shortest_paths(adj, s, d, k):
    """Yen's algorithm on link length."""
    def dijkstra(src, dst, banned_nodes, banned_edges):
        dist = {src: 0}; prev = {}; pq = [(0, src)]
        while pq:
            du, u = heapq.heappop(pq)
            if u == dst:
                break
            if du > dist.get(u, math.inf):
                continue
            for v, w in adj[u].items():
                if v in banned_nodes or (u, v) in banned_edges:
                    continue
                nd = du + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if dst not in dist:
            return None
        p = [dst]
        while p[-1] != src:
            p.append(prev[p[-1]])
        return p[::-1]

    def plen(p):
        return sum(adj[p[i]][p[i + 1]] for i in range(len(p) - 1))

    A = [dijkstra(s, d, set(), set())]
    B = []
    for _ in range(1, k):
        last = A[-1]
        for i in range(len(last) - 1):
            spur, root = last[i], last[:i + 1]
            be = set()
            for p in A:
                if p[:i + 1] == root:
                    be.add((p[i], p[i + 1])); be.add((p[i + 1], p[i]))
            sp = dijkstra(spur, d, set(root[:-1]), be)
            if sp:
                cand = root[:-1] + sp
                if cand not in [c for _, c in B] and cand not in A:
                    heapq.heappush(B, (plen(cand), cand))
        if not B:
            break
        A.append(heapq.heappop(B)[1])
    return A


# ---------------------------------------------------------------- simulator
class EONSim:
    def __init__(self, scheme, load, periodic_share=0.0, n_periodic_flows=20, n_requests=20000,
                 warmup=2000, S=320, guard=1, k=3, mean_hold=20.0, fs_min=5, fs_max=20,
                 eps=0.1, lead=0.5, seed=0, jitter=0.0, hold_budget=1.0):
        assert scheme in ("FF", "FF+PP", "Proposed", "Prop-Zone", "Prop-Hold", "Prop-Zone+Hold")
        self.scheme, self.S, self.guard = scheme, S, guard
        self.proposed = scheme.startswith("Prop")
        self.zone = "Zone" in scheme          # detected periodic flows use Last-Fit (top of the band)
        self.hold = "Hold" in scheme          # keep a periodic flow's spectrum between repeats
        self.rng = np.random.default_rng(seed)
        adj, self.link_id = build_graph()
        self.n_links = len(NSFNET_LINKS)
        self.paths = {}
        for s in range(N_NODES):
            for d in range(N_NODES):
                if s != d:
                    ps = k_shortest_paths(adj, s, d, k)
                    self.paths[(s, d)] = [[self.link_id[(p[i], p[i + 1])] for i in range(len(p) - 1)] for p in ps]
        self.spec = np.zeros((self.n_links, S), dtype=bool)        # True = occupied
        self.mean_hold, self.fs_min, self.fs_max = mean_hold, fs_min, fs_max
        self.n_requests, self.warmup = n_requests, warmup
        self.eps, self.lead = eps, lead
        self.jitter = jitter              # std. dev. of periodic arrival-time noise (time units)
        self.hold_budget = hold_budget    # max share of a link's slots that may sit idle in held/reserved blocks

        # traffic: random part + periodic flows carrying `periodic_share` of the offered load (Erlang)
        self.lam_rand = (1 - periodic_share) * load / mean_hold
        self.flows = []
        if periodic_share > 0:
            per_flow_rate = periodic_share * load / mean_hold / n_periodic_flows
            for _ in range(n_periodic_flows):
                s, d = self.rng.choice(N_NODES, 2, replace=False)
                b = int(self.rng.integers(fs_min, fs_max + 1))
                self.flows.append((int(s), int(d), b, 1.0 / per_flow_rate))

        self.conns = {}                  # id -> dict(path, links, start, width, key, reserved)
        self.cid = itertools.count()
        self.events = []                 # (time, seq, type, payload)
        self.seq = itertools.count()
        # detection state (Proposed)
        self.history = {}                # (s,d,b) -> list of last arrival times
        self.patterns = {}               # (s,d,b) -> period T
        self.reservations = {}           # (s,d,b) -> conn id of the reserved block
        # stats
        self.st = dict(req=0, blk=0, bw_req=0, bw_blk=0, req_per=0, blk_per=0, bw_req_per=0, bw_blk_per=0,
                       req_rand=0, blk_rand=0, defrag_calls=0, moves=0, rounds_grouped=0,
                       res_made=0, res_used=0, res_expired=0, res_failed=0, per_after_detect=0,
                       per_served_by_res=0, held=0, frag_samples=[])

    # ----------------------------------------------------- spectrum helpers
    def _first_fit(self, links, w, last=False):
        free = ~np.logical_or.reduce(self.spec[links], axis=0)
        cs = np.concatenate(([0], np.cumsum(free)))
        idx = np.flatnonzero(cs[w:] - cs[:-w] == w)
        if not idx.size:
            return None
        return int(idx[-1]) if last else int(idx[0])

    def _alloc(self, s, d, b, last=False):
        w = b + self.guard
        for links in self.paths[(s, d)]:
            st = self._first_fit(links, w, last)
            if st is not None:
                return links, st, w
        return None

    def _is_high(self, key):
        return self.zone and key in self.patterns

    def _occupy(self, links, start, w, val):
        self.spec[np.ix_(links, range(start, start + w))] = val

    def frag_index(self):
        """Average over links of 1 - (largest free block / total free slots)."""
        vals = []
        for l in range(self.n_links):
            free = (~self.spec[l]).astype(np.int8)
            tot = int(free.sum())
            if tot == 0:
                vals.append(1.0); continue
            d = np.diff(np.concatenate(([0], free, [0])))
            runs = np.flatnonzero(d == -1) - np.flatnonzero(d == 1)
            vals.append(1 - runs.max() / tot)
        return float(np.mean(vals))

    def check(self):
        """Consistency test: the spectrum map equals the union of active connections, no overlaps."""
        m = np.zeros_like(self.spec, dtype=np.int16)
        for c in self.conns.values():
            m[np.ix_(c["links"], range(c["start"], c["start"] + c["width"]))] += 1
        assert m.max() <= 1, "overlapping lightpaths"
        assert np.array_equal(m.astype(bool), self.spec), "spectrum map out of sync"

    # ----------------------------------------------------- Push-Pull defragmentation
    def push_pull(self):
        """Shift every active lightpath to the lowest spectrum position reachable through
        contiguous free slots (no hopping over other lightpaths = non-disruptive Push-Pull).
        Returns the moved connection ids."""
        moved = []
        low = [c for c in self.conns if not self.conns[c].get("high")]
        high = [c for c in self.conns if self.conns[c].get("high")]
        for cid in sorted(low, key=lambda c: self.conns[c]["start"]):
            c = self.conns[cid]
            links, st, w = c["links"], c["start"], c["width"]
            occ = np.logical_or.reduce(self.spec[links], axis=0)
            new = st
            while new - 1 >= 0 and not occ[new - 1]:
                new -= 1
            if new < st:
                self._occupy(links, st, w, False); self._occupy(links, new, w, True)
                c["start"] = new; moved.append(cid)
        for cid in sorted(high, key=lambda c: -self.conns[c]["start"]):
            c = self.conns[cid]
            links, st, w = c["links"], c["start"], c["width"]
            occ = np.logical_or.reduce(self.spec[links], axis=0)
            new = st
            while new + w < self.S and not occ[new + w]:
                new += 1
            if new > st:
                self._occupy(links, st, w, False); self._occupy(links, new, w, True)
                c["start"] = new; moved.append(cid)
        return moved

    def _group_rounds(self, moved):
        """Greedy maximal-independent-set grouping of moved routes: routes sharing no link
        are shifted in parallel. Returns the number of sequential rounds needed."""
        remaining = list(moved)
        rounds = 0
        while remaining:
            rounds += 1
            used, rest = set(), []
            for cid in sorted(remaining, key=lambda c: len(self.conns[c]["links"]) if c in self.conns else 0):
                ls = set(self.conns[cid]["links"]) if cid in self.conns else set()
                if ls & used:
                    rest.append(cid)
                else:
                    used |= ls
            remaining = rest
        return rounds

    def _try_with_defrag(self, s, d, b, last=False):
        r = self._alloc(s, d, b, last)
        if r is None and self.scheme != "FF":
            self.st["defrag_calls"] += 1
            moved = self.push_pull()
            self.st["moves"] += len(moved)
            self.st["rounds_grouped"] += self._group_rounds(moved)
            r = self._alloc(s, d, b, last)
        return r

    # ----------------------------------------------------- events
    def _push(self, t, typ, payload):
        heapq.heappush(self.events, (t, next(self.seq), typ, payload))

    def _schedule_traffic(self):
        if self.lam_rand > 0:
            self._push(self.rng.exponential(1 / self.lam_rand), "arr_rand", None)
        self.nominal = {}
        for i, (s, d, b, T) in enumerate(self.flows):
            self.nominal[i] = self.rng.uniform(0, T)
            self._push(self.nominal[i] + self._noise(T), "arr_per", i)

    def _noise(self, T):
        if self.jitter <= 0:
            return 0.0
        return float(np.clip(self.rng.normal(0, self.jitter), -T / 4, T / 4))

    def _idle_ok(self, links, w):
        """Hold budget: True if keeping w more idle slots on these links stays within the budget."""
        if self.hold_budget >= 1.0:
            return True
        idle = np.zeros(self.n_links)
        for c in self.conns.values():
            if c["reserved"]:
                idle[c["links"]] += c["width"]
        return bool(np.all(idle[links] + w <= self.hold_budget * self.S))

    def _arrival(self, t, s, d, b, periodic):
        n = self.st["req"]
        count = n >= self.warmup
        key = (s, d, b)
        served_by_res = False
        r = None
        if self.proposed and key in self.reservations:
            rid = self.reservations.pop(key)
            c = self.conns[rid]
            c["reserved"] = False            # reservation becomes the real connection
            served_by_res = True
            hold = self.rng.exponential(self.mean_hold)
            self._push(t + hold, "dep", rid)
            if count:
                self.st["res_used"] += 1
        else:
            hi = self._is_high(key)
            r = self._try_with_defrag(s, d, b, hi)
            if r is not None:
                links, st, w = r
                cid = next(self.cid)
                self._occupy(links, st, w, True)
                self.conns[cid] = dict(links=links, start=st, width=w, key=key, reserved=False, high=hi)
                self._push(t + self.rng.exponential(self.mean_hold), "dep", cid)
        blocked = (not served_by_res) and r is None
        self.st["req"] += 1
        if count:
            self.st["bw_req"] += b
            if blocked:
                self.st["blk"] += 1; self.st["bw_blk"] += b
            if periodic:
                self.st["req_per"] += 1; self.st["bw_req_per"] += b
                if blocked:
                    self.st["blk_per"] += 1; self.st["bw_blk_per"] += b
                if key in self.patterns:
                    self.st["per_after_detect"] += 1
                    if served_by_res:
                        self.st["per_served_by_res"] += 1
            else:
                self.st["req_rand"] += 1
                if blocked:
                    self.st["blk_rand"] += 1
            if self.st["req"] % 500 == 0:
                self.st["frag_samples"].append(self.frag_index())
        if self.proposed:
            self._detect(t, key)

    def _detect(self, t, key):
        h = self.history.setdefault(key, [])
        h.append(t)
        if len(h) > 4:
            h.pop(0)
        if len(h) >= 4:
            diffs = np.diff(h)
            T = float(np.mean(diffs))
            if np.all(np.abs(diffs - T) <= self.eps):
                self.patterns[key] = T
                self._push(t + T - self.lead, "reserve", (key, t + T))
                return
        self.patterns.pop(key, None) if len(h) >= 4 else None

    def _reserve(self, t, key, t_expected):
        if key not in self.patterns or key in self.reservations:
            return
        s, d, b = key
        hi = self._is_high(key)
        r = self._try_with_defrag(s, d, b, hi)
        count = self.st["req"] >= self.warmup
        if r is None:
            if count:
                self.st["res_failed"] += 1
            return
        links, st, w = r
        cid = next(self.cid)
        self._occupy(links, st, w, True)
        self.conns[cid] = dict(links=links, start=st, width=w, key=key, reserved=True, high=hi)
        self.reservations[key] = cid
        if count:
            self.st["res_made"] += 1
        self._push(t_expected + self.eps + self.lead, "expire", (key, cid))

    def _release(self, cid):
        c = self.conns.pop(cid)
        self._occupy(c["links"], c["start"], c["width"], False)

    def run(self):
        self._schedule_traffic()
        while self.st["req"] < self.n_requests + self.warmup:
            t, _, typ, p = heapq.heappop(self.events)
            if typ == "arr_rand":
                s, d = self.rng.choice(N_NODES, 2, replace=False)
                b = int(self.rng.integers(self.fs_min, self.fs_max + 1))
                self._arrival(t, int(s), int(d), b, False)
                self._push(t + self.rng.exponential(1 / self.lam_rand), "arr_rand", None)
            elif typ == "arr_per":
                s, d, b, T = self.flows[p]
                self._arrival(t, s, d, b, True)
                self.nominal[p] += T
                self._push(self.nominal[p] + self._noise(T), "arr_per", p)
            elif typ == "dep":
                if p in self.conns:
                    c = self.conns[p]
                    key = c["key"]
                    if (self.hold and key in self.patterns and key not in self.reservations
                            and self.history.get(key)):
                        t_next = self.history[key][-1] + self.patterns[key]
                        if t_next > t and self._idle_ok(c["links"], c["width"]):   # keep the block for the next repeat
                            c["reserved"] = True
                            self.reservations[key] = p
                            if self.st["req"] >= self.warmup:
                                self.st["res_made"] += 1; self.st["held"] += 1
                            self._push(t_next + self.eps + self.lead, "expire", (key, p))
                            continue
                    self._release(p)
            elif typ == "reserve":
                self._reserve(t, *p)
            elif typ == "expire":
                key, cid = p
                if self.reservations.get(key) == cid:      # never claimed -> false positive
                    del self.reservations[key]
                    self._release(cid)
                    if self.st["req"] >= self.warmup:
                        self.st["res_expired"] += 1
        return self.summary()

    def summary(self):
        s = self.st
        out = dict(
            BP=s["blk"] / max(1, self.n_requests),
            BBP=s["bw_blk"] / max(1, s["bw_req"]),
            BP_periodic=s["blk_per"] / s["req_per"] if s["req_per"] else float("nan"),
            BP_random=s["blk_rand"] / s["req_rand"] if s["req_rand"] else float("nan"),
            frag=float(np.mean(s["frag_samples"])) if s["frag_samples"] else float("nan"),
            defrag_calls=s["defrag_calls"], moves=s["moves"], rounds=s["rounds_grouped"],
            res_made=s["res_made"], res_used=s["res_used"], res_expired=s["res_expired"],
            res_failed=s["res_failed"], held=s["held"],
            res_precision=s["res_used"] / s["res_made"] if s["res_made"] else float("nan"),
            res_recall=s["per_served_by_res"] / s["req_per"] if s["req_per"] else float("nan"),
        )
        return out
