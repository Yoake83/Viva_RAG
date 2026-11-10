"""Knowledge-base tooling.  python -m app.cli ingest | status | search "<query>" --role ai_ml_engineer"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.roles import ROLES
from app.services.knowledge.embeddings import SentenceTransformerEmbedder
from app.services.knowledge.ingestion import ingest_book
from app.services.knowledge.retriever import Retriever
from app.services.knowledge.store import ChromaStore


def _build():
    s = get_settings()
    store = ChromaStore(s.chroma_dir, s.chroma_collection)
    embedder = SentenceTransformerEmbedder(s.embedding_model, s.embedding_query_prefix)
    return s, store, embedder


def cmd_ingest(args) -> None:
    s, store, embedder = _build()
    if args.reset:
        store.reset()
        print("Collection reset.")
    manifest = json.loads(Path(s.knowledge_manifest).read_text())
    total = 0
    for meta in manifest["books"]:
        if args.only and args.only not in meta["file"]:
            continue
        path = Path(s.knowledge_dir) / meta["file"]
        if not path.exists():
            print(f"  skip   {meta['file']} (not found in {s.knowledge_dir})")
            continue
        n = ingest_book(path, meta, store, embedder, s)
        total += n
        print(f"  ingest {meta['file']}: {n} chunks for roles {meta['roles']}")
    print(f"Done. {total} chunks written.")


def cmd_status(_) -> None:
    _, store, _ = _build()
    print(json.dumps(store.stats(list(ROLES)), indent=2))


def cmd_search(args) -> None:
    s, store, embedder = _build()
    result = Retriever(store, embedder, s).retrieve([args.query], role=args.role, k=args.k)
    print(f"quality={result.meta.get('quality')} candidates={result.meta.get('candidates')}")
    for rc in result.chunks:
        c = rc.chunk
        print(f"\n[{rc.score:.3f}] {c.source} / {c.section} (pp. {c.page_start}-{c.page_end})\n{c.text[:400]}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="chunk, embed and store the books listed in data/manifest.json")
    ing.add_argument("--only", help="only files whose name contains this text")
    ing.add_argument("--reset", action="store_true", help="drop the collection first")
    ing.set_defaults(fn=cmd_ingest)
    sub.add_parser("status", help="chunk counts per role").set_defaults(fn=cmd_status)
    se = sub.add_parser("search", help="debug retrieval for one query")
    se.add_argument("query")
    se.add_argument("--role", default="ai_ml_engineer", choices=list(ROLES))
    se.add_argument("-k", type=int, default=4)
    se.set_defaults(fn=cmd_search)
    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
