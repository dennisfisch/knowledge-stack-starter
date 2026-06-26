#!/usr/bin/env python3
"""build.py — deterministic Graphify build backbone.

The deterministic half of the stack: detect → AST → cluster → labels (reuse) →
wiki-bridge → export. NO LLM, NO API token (subscription-only: the *semantic* doc
extraction and the community *naming* are separate host/skill steps on the
subscription, NOT here).

Labels: if graphify-out/.graphify_labels.json exists it is reused (naming survives
rebuilds). Otherwise placeholder "Community N" — the host names them once
(skill.md Step 5) and persists.

Usage (per repo):
  build.py --repo . [--manifest docs/wiki/manifest.json --owner <owner>
                     --wiki-dir docs/wiki] [--no-bridge]
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from collections import defaultdict
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--owner")
    ap.add_argument("--wiki-dir", type=Path)
    ap.add_argument("--no-bridge", action="store_true")
    args = ap.parse_args()

    repo = args.repo.resolve()
    out = repo / "graphify-out"
    out.mkdir(exist_ok=True)

    from graphify.detect import detect
    from graphify.extract import collect_files, extract
    from graphify.build import build, build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_html, to_json, _git_head

    # 1) detect + AST (local, free)
    det = detect(repo)
    (out / ".graphify_detect.json").write_text(json.dumps(det, ensure_ascii=False), encoding="utf-8")
    code_files = []
    for f in det.get("files", {}).get("code", []):
        p = Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])
    ast = extract(code_files, cache_root=repo) if code_files else {"nodes": [], "edges": []}
    (out / ".graphify_ast.json").write_text(json.dumps(ast, ensure_ascii=False), encoding="utf-8")

    # 2) build + cluster → graph.json. Clustering prefers Leiden (graspologic, Python
    # <3.13) and falls back to Louvain (networkx, built in) otherwise — it never fails;
    # blast-radius is unaffected either way.
    G = build([ast], root=str(repo))
    comm = cluster(G)
    labels_path = out / ".graphify_labels.json"
    labels = {c: f"Community {c}" for c in comm}
    if labels_path.exists():
        saved = json.loads(labels_path.read_text(encoding="utf-8"))
        labels = {c: saved.get(str(c), f"Community {c}") for c in comm}
    to_json(G, comm, str(out / "graph.json"), community_labels=labels,
            built_at_commit=_git_head(), force=True)

    # 3) wiki-bridge (deterministic anchor join). Skipped gracefully if no manifest yet.
    if not args.no_bridge and args.manifest and args.owner and not args.manifest.exists():
        print(f"build: no manifest at {args.manifest} — skipping wiki bridge "
              f"(run docs/wiki/wiki-manifest first to link wiki↔code)")
    if not args.no_bridge and args.manifest and args.owner and args.manifest.exists():
        cmd = [sys.executable, str(Path(__file__).parent / "wiki-bridge.py"),
               "--graph", str(out / "graph.json"),
               "--manifest", str(args.manifest), "--owner", args.owner]
        if args.wiki_dir:
            cmd += ["--wiki-dir", str(args.wiki_dir)]
        subprocess.run(cmd, check=True)
        # after the join, reload and keep the communities from the graph (do NOT re-cluster)
        raw = json.loads((out / "graph.json").read_text(encoding="utf-8"))
        G = build_from_json(raw, directed=False)
        comm = defaultdict(list)
        for n in raw["nodes"]:
            if n.get("community") is not None:
                comm[n["community"]].append(n["id"])
        comm = dict(comm)
        labels = {c: labels.get(c, f"Community {c}") for c in comm}

    # 4) export html + report (always from the final graph)
    rep = generate(G, comm, score_all(G, comm), labels, god_nodes(G),
                   surprising_connections(G, comm), det, {"input": 0, "output": 0},
                   str(repo), suggested_questions=suggest_questions(G, comm, labels),
                   built_at_commit=_git_head())
    (out / "GRAPH_REPORT.md").write_text(rep, encoding="utf-8")
    to_html(G, comm, str(out / "graph.html"), community_labels=labels)
    to_json(G, comm, str(out / "graph.json"), community_labels=labels,
            built_at_commit=_git_head(), force=True)
    print(f"build: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"{len(comm)} communities → {out}/  (commit {_git_head()})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
