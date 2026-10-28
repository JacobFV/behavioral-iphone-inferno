# boot 49: the healthy display trace, as first retained

These files are the evidence from commit `c65d405c893` ("Retain healthy boot49
display trace before original stack sampling", 2026-10-06), which lived only on
the `companion/display-query` branch. The parent directory holds the later,
revised audit of the same run that landed on master; the four trace and report
files here (`display-trace-control-final.jsonl`, `guest-errors-final.log`,
`qmp-trace-excerpt.jsonl`, `report-final.json`) never reached master, and the
branch's own `audit.json`, `audit.py` and `provenance.json` are kept beside them
so the earlier record can be re-checked as it was.
