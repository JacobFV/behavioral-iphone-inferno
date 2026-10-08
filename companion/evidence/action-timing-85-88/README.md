# Host action timing: runs 85–88

Seconds use the host QMP `cont` request and serial `before-send` timestamps. Raw rows, byte offsets, request geometry, and successful transport responses are retained in `comparison.json`; no timestamps come from file metadata.

| Run | cont→unlock 1 | unlock 1→unlock 2 | cont→unlock 2 | setup dismissal→tap |
| --- | ---: | ---: | ---: | ---: |
| 85, generic counter unchanged | 149.07 | 396.21 | 545.27 | 12.62 |
| 86, fixture counter advanced | 114.70 | 48.73 | 163.44 | 46.62 |
| 87, fixture counter advanced | 110.94 | 51.95 | 162.89 | 34.91 |
| 88, fixture counter advanced | 136.04 | 80.83 | 216.87 | 39.13 |

The exceptional delay is between the first and second unlock requests, not simply time before the first request. A controlled delayed-second-unlock trial is therefore a concrete next comparison, preferably holding fixture/source and post-setup timing fixed. These four observations cannot establish a causal timing threshold. Run85 uses a different generic app, and its setup-to-tap interval is also shorter.

Actual accepted-launch serial lines are retained, but their guest clock or untimestamped raw text has no explicit host-arrival mapping here. They cannot honestly be inserted into this host elapsed-time chain. Host submission likewise is not guest processing, visible unlock, or callback delivery time. Outcome labels come from the parent's actual pixel reviews, not inferred from timing.
