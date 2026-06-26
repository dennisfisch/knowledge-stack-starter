#!/usr/bin/env python3
"""gquery.py — deterministic graph queries, with lazy auto-rebuild.

The reading side: blast-radius, path, neighbors — pure graph traversal over
graphify-out/graph.json. (Natural-language `graphify query "…"` is a separate
host/skill step on the subscription.)

LAZY FRESHNESS: before querying, gquery compares the graph's `built_at_commit` to the
repo's HEAD. If the graph is stale or missing, it rebuilds (via graphify/run build.py,
which needs the shared venv) — so the graph is fresh exactly when you ask, with zero
cost when it's already current. Disable with --no-rebuild (pure read, no venv).
Note: staleness is commit-based — it won't detect uncommitted working-tree edits;
rebuild manually if you've changed code without committing.

Blast-radius is deliberately UNDIRECTED (correct in both directions): Graphify's native
`affected` follows only incoming edges and is orientation-nondeterministic on undirected
graphs — so we use our own symmetric BFS here.

  gquery.py blast <seed> [--depth 2]    # what is connected to <seed> (code+wiki+entity)
  gquery.py path  <a> <b>               # shortest path
  gquery.py neighbors <seed>            # direct neighbors
  [--repo PATH] [--no-rebuild]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

REL_DEFAULT = {"calls","references","imports","imports_from","contains","defines",
               "method","inherits","documents","documented_by","tagged_entity","in_entity"}

def norm(s): return re.sub(r"[^a-z0-9]+","",(s or "").lower())

# --- lazy freshness -------------------------------------------------------------
def _head(repo: Path):
    try:
        r = subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                           capture_output=True, text=True)
        return r.stdout.strip() or None
    except Exception:
        return None

def _built_commit(graph_path: Path):
    try:
        return json.loads(graph_path.read_text(encoding="utf-8")).get("built_at_commit") or None
    except Exception:
        return None

def _fresh(head, built):
    if not built: return False
    if not head:  return True            # can't determine HEAD -> don't churn
    n = min(len(head), len(built))
    return head[:n] == built[:n]

def ensure_fresh(repo: Path, no_rebuild: bool):
    gp = repo / "graphify-out" / "graph.json"
    if no_rebuild:
        return
    if gp.exists() and _fresh(_head(repo), _built_commit(gp)):
        return
    run = repo / "graphify" / "run"
    if not run.exists():
        print("gquery: graph stale/missing and graphify/run not found — using existing graph if any.",
              file=sys.stderr)
        return
    reason = "missing" if not gp.exists() else "stale"
    print(f"gquery: graph {reason} — rebuilding (needs the shared venv; --no-rebuild to skip)…",
          file=sys.stderr)
    cmd = [str(run), "build.py", "--repo", str(repo), "--owner", repo.name]
    wiki = repo / "docs" / "wiki"
    try:
        if wiki.exists():
            mt = wiki / "wiki-manifest"
            if mt.exists():
                subprocess.run(["python3", str(mt), str(wiki), "--repo", repo.name],
                               check=False, cwd=str(repo))
            cmd += ["--manifest", str(wiki / "manifest.json"), "--wiki-dir", str(wiki)]
        subprocess.run(cmd, check=True, cwd=str(repo))
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError) as e:
        if gp.exists():
            print(f"gquery: rebuild failed ({e}); querying the stale graph. "
                  f"Fix: graphify/setup-venv.sh", file=sys.stderr)
        else:
            print(f"gquery: rebuild failed ({e}) and no graph exists. "
                  f"Run graphify/setup-venv.sh, then graphify/run build.py …", file=sys.stderr)
            sys.exit(1)

# --- graph load + queries -------------------------------------------------------
def load(repo: Path):
    g = json.loads((repo/"graphify-out"/"graph.json").read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in g["nodes"]}
    adj = {}
    for l in g["links"]:
        s,t,r = l["source"], l["target"], l.get("relation","")
        adj.setdefault(s,[]).append((t,r)); adj.setdefault(t,[]).append((s,r))
    return g, nodes, adj

def resolve(nodes, q):
    if q in nodes: return q
    nq = norm(q)
    exact = [nid for nid,n in nodes.items() if norm(n.get("label"))==nq or norm(nid)==nq]
    if exact: return exact[0]
    part = [nid for nid,n in nodes.items() if nq in norm(n.get("label")) or nq in norm(nid)]
    return part[0] if part else None

def kind(n):
    nid = n["id"]
    if nid.startswith("wiki_"): return "WIKI"
    if nid.startswith("entity_"): return "ENTITY"
    return "code"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["blast","path","neighbors"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--no-rebuild", action="store_true",
                    help="don't auto-rebuild a stale graph (pure read, no venv)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    ensure_fresh(repo, a.no_rebuild)
    try:
        g, nodes, adj = load(repo)
    except FileNotFoundError:
        print("gquery: no graph found. Build it: graphify/run build.py --repo . "
              "--manifest docs/wiki/manifest.json --owner <name> --wiki-dir docs/wiki", file=sys.stderr)
        return 1

    if a.cmd in ("blast","neighbors"):
        seed = resolve(nodes, a.args[0])
        if not seed: print(f"not found: {a.args[0]}"); return 1
        depth = 1 if a.cmd=="neighbors" else a.depth
        seen={seed}; frontier=[(seed,0)]; hits=[]
        while frontier:
            cur,d = frontier.pop(0)
            if d>=depth: continue
            for nb,rel in adj.get(cur,[]):
                if rel not in REL_DEFAULT or nb in seen: continue
                seen.add(nb); hits.append((nb,d+1,rel)); frontier.append((nb,d+1))
        label=nodes[seed].get("label") or seed
        print(f"{a.cmd} '{label}' ({seed}), depth {depth}: {len(hits)} affected")
        for grp in ("WIKI","ENTITY","code"):
            sel=[(nb,d,rel) for nb,d,rel in hits if kind(nodes[nb])==grp]
            if not sel: continue
            print(f"  [{grp}] {len(sel)}:")
            for nb,d,rel in sorted(sel,key=lambda x:x[1])[:20]:
                print(f"    d{d} --{rel}-> {nodes[nb].get('label') or nb}  ({nb})")
        return 0

    if a.cmd=="path":
        s=resolve(nodes,a.args[0]); t=resolve(nodes,a.args[1])
        if not s or not t: print("seed not found"); return 1
        prev={s:None}; q=[s]
        while q:
            c=q.pop(0)
            if c==t: break
            for nb,_ in adj.get(c,[]):
                if nb not in prev: prev[nb]=c; q.append(nb)
        if t not in prev: print("no path"); return 1
        path=[]; c=t
        while c is not None: path.append(c); c=prev[c]
        path.reverse()
        print(" -> ".join(nodes[p].get("label") or p for p in path))
        return 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
