# Failure analysis: tax-packet

No model runs yet. The two reference runs (main and missing_document) are scripted trajectories played on the real Apps by `tools/reference_run.cjs`; both score 20/20 with no forbidden item.

The grader was also checked on 17 synthetic end states (`tools/selftest_grader.py`): the reference, the accepted "regenerate each session" alternative, and summaries written as CSV, in whole dollars and as a compressed two-column PDF all pass at 20/20; doing nothing scores 0; the negative end states named in the proposal fail as intended (original uploaded, supplement counted, 2024 statement counted, Northfield export counted twice, Bayview missing, local-only packet, wrong workspace, delivery claimed without an upload, upload before authorization); and a summary whose amounts are correct but partly unreadable sends those points to review instead of failing them.

Failure codes FC1 to FC7 from the proposal will be applied to model runs here.
