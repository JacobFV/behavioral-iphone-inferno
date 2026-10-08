# Actual 84: healthy pending-equality calibration

The independently parsed raw prefix contains 786 complete CPU snapshots at all five fixed production PCs, with no unknown PCs, malformed blocks, or semantic violations. The exact filter, binary/build pins, same-attempt zero slide, nine disabled ADP events, one-second enable and acknowledged restoration are retained in raw transcripts and replayed by `audit.py`.

| Independent population | Snapshots |
| --- | ---: |
| Accepted mode (all mode 0) | 200 |
| Requested token equals pipeline_bf4_token (468–472) | 192 |
| Matching-request local false | 191 |
| Matching-request local true | 4 |
| Final return pending 0xe00002d5 | 195 |
| Final return zero | 4 |

Root reviewed the stopwatch advancing before and after the diagnostic window; `visual-context.json` pins the actual images and attributes the pixel readings to that review. This calibration follows a healthy strict journey and warm cycles. It is not a failed-window sample.

Equality, a false matching local, and pending returns therefore occur in an advancing display context. They do not individually establish the persistent freeze's cause. Tokens vary across the equality population, and successful returns also occur. Counts deliberately remain unequal: these are snapshots, not paired calls or invocation counts. Mode observations cannot be propagated to other blocks, and no CPU, thread, or process attribution is available. The neutral bf4 field name does not assert fence completion. Global `nochain` perturbs execution; this is not a performance measurement.

All retained logs are explicitly captured live prefixes after restoration, not final stopped reports. `capture-provenance.json` records source paths, read intervals, file identities and hashes. No guest control or input was issued by this audit.

Replay with the reviewed parser:

```sh
python3 companion/evidence/pending-equality-84-healthy-actual/audit.py --parser companion/pending-equality-result.py
```
