"""Synthetic-only, single-writer integration. Caller owns the open TaskMemory."""
import re
import sqlite3
import task_runner


def run_recorded(memory, task_id, a, b, model, **options):
    if type(task_id) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', task_id):
        raise ValueError('invalid id')
    # Reject previous receipts before contacting the model. No automatic replay.
    if memory.get(task_id) is not None:
        raise ValueError('task id already recorded')
    outcome = task_runner.run(a, b, model, **options)
    if not outcome['executed']:
        return {**outcome, 'memory_saved': False, 'memory_status': 'not_executed'}
    try:
        memory.append(task_id, a, b, outcome['result'])
    except (sqlite3.Error, OSError, ValueError):
        # Execution happened: do not misreport rejection or automatically retry.
        return {**outcome, 'memory_saved': False,
                'memory_status': 'write_failed_no_retry'}
    return {**outcome, 'memory_saved': True, 'memory_status': 'saved'}
