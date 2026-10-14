"""Fetch every due source and write data/<key>.json plus data/manifest.json.

Usage: python -m collect.run [--data-dir data] [--force] [--only KEY ...]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from collect import manifest as manifest_file
from collect.registry import SOURCES, Context, Source

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 0.25
MAX_WORKERS = 3


@dataclass
class RunResult:
    attempted: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    not_configured: list[str] = field(default_factory=list)


def exceeds_threshold(result: RunResult) -> bool:
    if not result.attempted:
        return False
    return len(result.failed) / len(result.attempted) > FAILURE_THRESHOLD


def _write_payload(path: Path, payload: object) -> None:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("fetch returned an empty or non-dict payload")
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"  # fails before touching the file
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def run(sources: Mapping[str, Source], data_dir: Path, ctx: Context, force: bool = False,
        only: set[str] | None = None) -> RunResult:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_file.load(data_dir)
    now_iso = ctx.now.isoformat(timespec="seconds")
    result = RunResult()
    due: list[Source] = []

    for key, src in sources.items():
        if only and key not in only:
            continue
        entry = manifest.setdefault(key, {})
        entry["ttl_seconds"] = src.ttl_seconds
        missing = [name for name in src.requires_env if not ctx.env.get(name, "").strip()]
        if missing:
            entry.update(status="not_configured", error=f"set {', '.join(missing)} to enable")
            result.not_configured.append(key)
        elif force or manifest_file.is_due(entry, src.ttl_seconds, ctx.now):
            due.append(src)
        else:
            result.skipped.append(key)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(src.fetch, ctx): src for src in due}
        for future in as_completed(futures):
            src = futures[future]
            entry = manifest[src.key]
            entry["last_attempt"] = now_iso
            result.attempted.append(src.key)
            try:
                _write_payload(data_dir / f"{src.key}.json", future.result())
                entry.update(status="ok", error=None, last_success=now_iso)
            except Exception as exc:  # any failure keeps the previous JSON
                logger.exception("source %s failed", src.key)
                entry.update(status="error", error=f"{type(exc).__name__}: {exc}"[:500])
                result.failed.append(src.key)

    result.attempted.sort()
    result.failed.sort()
    manifest_file.save(data_dir, manifest)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--force", action="store_true", help="re-fetch every source")
    parser.add_argument("--only", action="append", metavar="KEY", help="fetch only these sources")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    import collect.sources  # noqa: F401  (registers sources)
    from collect.dns import dns_has_aaaa
    from collect.http import make_session

    ctx = Context(session=make_session(), env=os.environ, now=datetime.now(timezone.utc),
                  has_aaaa=dns_has_aaaa)
    result = run(SOURCES, Path(args.data_dir), ctx, force=args.force,
                 only=set(args.only) if args.only else None)

    for key in result.failed:
        print(f"::warning::source {key} failed; keeping its previous data")
    print(f"attempted={len(result.attempted)} failed={len(result.failed)} "
          f"skipped={len(result.skipped)} not_configured={len(result.not_configured)}")
    if exceeds_threshold(result):
        print(f"::error::{len(result.failed)} of {len(result.attempted)} sources failed; not publishing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
