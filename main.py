"""Lights vs Numbers - pipeline orchestration.

Runs the four signal modules (each isolated: a failure falls back to
cached/mock outputs) then the descriptive join. No indexes, no verdicts.

    python main.py            # run full pipeline once
"""
import logging
import os
import sys

import yaml
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")


def load_cfg():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def run_all():
    from modules import nightlights, electricity, trends, ports, combine

    cfg = load_cfg()
    steps = [
        ("nightlights", nightlights.run),
        ("electricity", electricity.run),
        ("trends", trends.run),
        ("ports", ports.run),
    ]
    failures = []
    for name, fn in steps:
        try:
            fn(cfg)
            log.info("[%s] OK", name)
        except Exception as e:
            failures.append(name)
            log.error("[%s] FAILED: %s", name, e)

    if combine._inputs_exist():
        try:
            combine.run(cfg)
            log.info("[combine] OK")
        except Exception as e:
            log.error("[combine] FAILED: %s", e)
            failures.append("combine")
    else:
        log.error("combine skipped: missing processed inputs (%s)", failures)
    return failures


if __name__ == "__main__":
    failed = run_all()
    sys.exit(1 if failed else 0)
    # schedule block (laptop cron-style), keep commented for MVP:
    # import schedule, time
    # schedule.every().day.at("06:00").do(run_all)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)
