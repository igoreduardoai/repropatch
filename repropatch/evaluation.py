"""Descriptive pilot accounting only. Fixture results never enter model metrics."""
from .models import TERMINAL

def summarize(runs):
    live=[r for r in runs if r['mode']=='live']
    closed=[r for r in live if r['status'] in TERMINAL and r.get('result')]
    pairs={}
    for r in closed:pairs.setdefault(r['case_id'],set()).add(r['method'])
    complete=sum(methods=={'W0','W1'} for methods in pairs.values())
    metrics={}
    for method in ['W0','W1']:
        rows=[r for r in closed if r['method']==method]
        metrics[method]={'attempted':sum(r['method']==method for r in live),'completed':len(rows),
          'verified':sum(r['status']=='VERIFIED' for r in rows),
          'independently_evaluated':sum(bool(r['result'].get('evaluation')) for r in rows),
          'regression_outcomes_unknown':sum(not bool(r['result'].get('evaluation')) for r in rows),
          'false_successes':sum(bool(r['result'].get('false_success')) for r in rows),
          'regressions':sum(r['result'].get('regressions',0) for r in rows),
          'abstentions':sum(r['status']=='NOT_REPRODUCED' or r['result'].get('reason') in {'model_ended_without_candidate','turn_limit'} for r in rows),
          'errors_or_blocked':sum(r['status'] in {'ERROR','BLOCKED','BUDGET_EXCEEDED','CANCELLED'} for r in rows),
          'settled_usd':round(sum(r['result'].get('settled_usd',r['result'].get('cost_usd',0)) for r in rows),6),
          'duration_ms':sum(r['result'].get('duration_ms',0) for r in rows),
          'human_interventions':sum(r['result'].get('operator_interventions',0) for r in rows)}
    return {'status':'NOT_MEASURED' if not closed else 'COMPLETED_EXPLORATORY' if complete>=4 else 'INCOMPLETE',
      'live_runs':len(live),'fixture_runs':sum(r['mode']=='fixture' for r in runs),
      'completed_real_cases':complete,'planned_real_cases':4,'planned_model_runs':8,
      'metrics':metrics if closed else None,
      'note':'Descriptive feasibility pilot; no superiority claim. Fixtures excluded. Costs here cover completed run summaries; /api/budget includes in-flight reservations. False successes use the recorded candidate-claim rule.'}
