"""Separate queue worker. API requests never execute target code."""
import argparse
import logging
import time
from .config import Settings
from .models import TERMINAL
from .store import Store
from .fixture import run_fixture, Cancelled
from .live import run_live

log=logging.getLogger('repropatch.worker')

def process_next(store,settings):
    run=store.claim()
    if not run:return False
    try:
        if run['mode']=='fixture':
            run_fixture(store,settings,run)
        elif run['mode']=='live':
            # Registry acceptance, sandbox image and ledger are re-checked inside run_live.
            run_live(store,settings,run)
        else:
            store.transition(run['id'],'BLOCKED','Unknown run mode.',{'verified':False,'reason':'unknown_mode','model_calls':0})
    except Cancelled:
        pass
    except Exception as exc:
        log.error('Run %s failed: %s',run['id'],type(exc).__name__)
        current=store.get(run['id'])
        if current and current['status'] not in TERMINAL:
            store.transition(run['id'],'ERROR','Execution failed; inspect operator logs.',
               {'verified':False,'error_type':type(exc).__name__})
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true')
    args=parser.parse_args();logging.basicConfig(level=logging.INFO)
    settings=Settings.load();store=Store(settings.db_path)
    # Only one worker is supported. Use OS lock to prevent accidental duplicates.
    import fcntl
    lock=(settings.data_dir/'worker.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Another worker is already active')
    store.fail_interrupted()
    from .budget import Budget
    Budget(settings.db_path,settings.live_budget_usd,settings.run_budget_usd).recover_inflight()
    try:
        from .docker_runtime import DockerRuntime
        removed=DockerRuntime().sweep()
        if removed:log.warning('Removed %d orphaned sandbox containers',removed)
    except Exception as exc:log.warning('Container sweep skipped: %s',type(exc).__name__)
    if args.once:process_next(store,settings);return
    while True:
        if not process_next(store,settings):time.sleep(0.5)

if __name__=='__main__':main()
