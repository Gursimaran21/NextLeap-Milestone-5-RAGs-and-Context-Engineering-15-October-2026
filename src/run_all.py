"""One-command pipeline: ingest -> cluster -> insights -> retrieve -> pulse -> explainer.

Usage:
    python -m src.run_all --weeks 12
    python -m src.run_all --input data/groww_reviews_sample.csv
"""

from __future__ import annotations

import argparse
import time

from . import cluster as cluster_mod
from . import config, fee_explainer, ingest, insights as insights_mod, pulse, retrieval


def main() -> None:
    ap = argparse.ArgumentParser(description="Groww Milestone 5 — run the full pipeline")
    ap.add_argument("--weeks", type=int, default=config.WEEKS)
    ap.add_argument("--input", default=None, help="path to reviews CSV")
    args = ap.parse_args()

    config.ensure_dirs()
    t0 = time.time()

    print("== 1/6 ingest ==");        df = ingest.run(args.input, args.weeks)
    print("== 2/6 cluster ==");       df = cluster_mod.run(df)
    print("== 3/6 insights ==");      ins = insights_mod.run(df, args.weeks)
    print("== 4/6 retrieval ==");     ctx = retrieval.run(df, ins["fee_issue"]["label"])
    print("== 5/6 pulse ==");         pulse.run(ins, ctx)
    print("== 6/6 fee explainer =="); fee_explainer.run(ins, ctx)

    print(f"\nDone in {time.time() - t0:.1f}s. Outputs in {config.OUTPUTS_DIR}")
    print("Next: open the Streamlit app -> `streamlit run app.py` -> approve the MCP actions.")


if __name__ == "__main__":
    main()
