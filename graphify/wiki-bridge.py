#!/usr/bin/env python3
"""wiki-bridge — deterministic join: wiki ↔ Graphify code graph.

Instead of letting Graphify's LLM guess the code↔wiki edge (unreliable), this tool
joins the already-maintained `source:` anchors (from the wiki's manifest.json)
deterministically onto the code nodes in the Graphify graph.

Anti-rot: the anchors are symbol/file-level (never line-level). When code moves and
the anchor goes stale, rebuild and re-run — the tool is idempotent. No LLM, free,
repeatable.

Per repo: run once over the repo-local graph.

Tiers (map onto Graphify's EXTRACTED/INFERRED confidence):
  1. symbol  — anchor.symbol resolves to exactly one code node    (EXTRACTED 1.0)
  2. file    — fallback: anchor.path → all nodes of the file       (EXTRACTED 0.6)
               (only when NO symbol resolves — precision beats breadth)
  3. entity  — anchor.entities propagate onto anchored nodes       (INFERRED 0.7)
               -> conceptual blast-radius across file boundaries

Usage:
  wiki-bridge.py --graph graphify-out/graph.json \
                 --manifest docs/wiki/manifest.json \
                 --owner <repo> [--repo <repo>] \
                 [--wiki-dir docs/wiki] [--out PATH] [--report]
"""
from __future__ import annotations
import argparse, json, re, shutil, sys
from pathlib import Path

def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

def split_symbols(sym: str | None) -> list[str]:
    # Anchors sometimes carry multiple symbols ("_a / _b, _c") or prose ("Deploy section").
    # Prose (with spaces/non-ascii) is not an identifier -> it simply won't match below.
    return [s.strip() for s in re.split(r"[/,]", sym or "") if s.strip()]

def load_entities(wiki_dir: Path, slug: str) -> list[str]:
    f = wiki_dir / f"{slug}.md"
    if not f.exists():
        return []
    txt = f.read_text(encoding="utf-8")
    m = re.search(r"^entities:\s*\[(.*?)\]", txt, re.MULTILINE)
    if not m:
        return []
    return [e.strip().strip("\"'") for e in m.group(1).split(",") if e.strip()]

def main() -> int:
    ap = argparse.ArgumentParser(description="Join wiki source-anchors onto the Graphify code graph")
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", help="anchor.repo value to match (default: --owner)")
    ap.add_argument("--wiki-dir", type=Path, help="wiki corpus for entities (tier 3)")
    ap.add_argument("--out", type=Path, help="target (default: in-place, .bak backup)")
    ap.add_argument("--report", action="store_true", help="per-unit join report on stdout")
    args = ap.parse_args()
    repo = args.repo or args.owner

    g = json.loads(args.graph.read_text(encoding="utf-8"))
    nodes, links = g["nodes"], g["links"]

    # Index over code nodes only (AST origin).
    code = [n for n in nodes if n.get("_origin") == "ast" or n.get("file_type") == "code"]
    file_index: dict[str, list[str]] = {}
    label_index: dict[str, list[str]] = {}
    for n in code:
        file_index.setdefault(n.get("source_file") or "", []).append(n["id"])
        label_index.setdefault(norm(n.get("label")), []).append(n["id"])

    def by_path(path: str) -> list[str]:
        p = path.strip("/")
        return sorted({nid for sf, ids in file_index.items()
                       if sf == p or sf.endswith("/" + p) for nid in ids})

    man = json.loads(args.manifest.read_text(encoding="utf-8"))
    all_anchors = man.get("anchors", [])
    anchors = [a for a in all_anchors if a.get("repo") == repo]
    # Per-repo model: every unit anchors into the same repo. If the repo filter
    # matches nothing (name mismatch), fall back to all anchors.
    if not anchors and all_anchors:
        anchors = all_anchors

    node_ids = {n["id"] for n in nodes}
    added_nodes: dict[str, dict] = {}
    new_links: list[dict] = []
    stats = {"symbol": 0, "file": 0, "entity": 0}
    per_unit: dict[str, dict] = {}

    def ensure_node(nid, label, ftype, kind):
        if nid in node_ids or nid in added_nodes:
            return
        added_nodes[nid] = {"id": nid, "label": label, "file_type": ftype,
                            "source_file": None, "source_location": None,
                            "metadata": {"kind": kind}, "_origin": "wiki-bridge"}

    prov = str(args.manifest)

    def link(src, tgt, rel, conf, score, tier):
        new_links.append({"source": src, "target": tgt, "relation": rel,
                          "confidence": conf, "confidence_score": score,
                          "weight": score, "source_file": prov,
                          "source_location": None, "_origin": "wiki-bridge", "_tier": tier})

    for a in anchors:
        slug = a["slug"]
        wid = f"wiki_{norm(slug)}"
        targets = by_path(a.get("path", ""))
        if not targets:
            per_unit.setdefault(slug, {"symbol": 0, "file": 0, "entity": 0, "unresolved": []})
            per_unit[slug]["unresolved"].append(a.get("path"))
            continue
        ensure_node(wid, slug, "document", "wiki-unit")
        pu = per_unit.setdefault(slug, {"symbol": 0, "file": 0, "entity": 0, "unresolved": []})

        # Tier 1: symbol-precise
        sym_hits: set[str] = set()
        for s in split_symbols(a.get("symbol")):
            in_file = [nid for nid in label_index.get(norm(s), []) if nid in set(targets)]
            for nid in (in_file or label_index.get(norm(s), [])):
                if nid not in sym_hits:
                    link(wid, nid, "documents", "EXTRACTED", 1.0, "symbol")
                    sym_hits.add(nid); stats["symbol"] += 1; pu["symbol"] += 1
        # Tier 2: file fallback (only when NO symbol resolved)
        if not sym_hits:
            for nid in targets:
                link(wid, nid, "documents", "EXTRACTED", 0.6, "file")
                stats["file"] += 1; pu["file"] += 1
        # Tier 3: entities (conceptual). On the code side propagate ONLY to symbol-precise
        # nodes — file-level would be too coarse (one null-symbol anchor on a big file would
        # otherwise spam every node with all entities). Without a symbol the concept still
        # survives as a wiki→entity edge (a navigation node) without code noise.
        if args.wiki_dir:
            for e in load_entities(args.wiki_dir, slug):
                eid = f"entity_{norm(e)}"
                ensure_node(eid, e, "concept", "entity")
                link(wid, eid, "in_entity", "EXTRACTED", 1.0, "entity")
                for nid in sym_hits:
                    link(nid, eid, "tagged_entity", "INFERRED", 0.7, "entity")
                    stats["entity"] += 1
                    pu["entity"] += 1

    nodes.extend(added_nodes.values())
    links.extend(new_links)

    out = args.out or args.graph
    if out == args.graph and not args.out:
        shutil.copy2(args.graph, args.graph.with_suffix(".json.bak"))
    out.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")

    connected = sum(1 for u in per_unit.values() if u["symbol"] or u["file"])
    print(f"wiki-bridge[{args.owner}]: {len(anchors)} anchors → "
          f"{stats['symbol']} symbol-precise + {stats['file']} file-level "
          f"+ {stats['entity']} entity edges; {connected}/{len(per_unit)} units linked; "
          f"+{len(added_nodes)} nodes. → {out}")
    if args.report:
        for slug, u in sorted(per_unit.items()):
            tag = f"sym={u['symbol']} file={u['file']} ent={u['entity']}"
            if u["unresolved"]:
                tag += f" UNRESOLVED={u['unresolved']}"
            print(f"  {slug}: {tag}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
