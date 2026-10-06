# Beta Close → strict capture → counter action timing

Actual retained host control, serial transmission and QMP reply records were available for all12 requested runs. There is **timing overlap**, not a separating threshold:

| Run | Prior observed outcome | Close wire → counter wire (s) | Before-frame QMP reply → counter wire (s) |
|---|---|---:|---:|
|41|stalled|16.052|0.20524|
|44|stalled|20.054|0.20497|
|47|stalled|17.049|0.20630|
|45|healthy|23.266|0.20573|
|46|healthy|28.273|0.20582|
|49|healthy|24.869|0.20565|
|50|healthy|23.473|0.20617|
|54|healthy|33.489|0.20540|
|58|healthy|17.257|0.20578|
|59|healthy|31.489|0.41449|
|60|healthy|42.312|0.20597|
|61|healthy|35.281|0.20501|

Every selected Close requested normalized16384,18560 for150ms; every selected counter tap requested16384,20316 for150ms. Both guest attempt acknowledgments were retained in every run. The strict before-frame QMP request/reply itself took approximately4.93–7.32ms. The ~205ms post-QMP counter dispatch occurs in failed and healthy runs alike. Healthy58 has a Close-to-counter interval within the failed range and only~209ms longer than failed47.

Consequently a simple “counter was too soon after screendump” explanation is not supported by timing separation. A controlled short-versus-long delay trial on identical bits/observer cadence remains an **untested experimental factor**, but these data do not establish it as a cause or a fix. The earlier failed runs do cluster at shorter Close intervals than most selected healthy runs; excluding the overlapping healthy58 would misrepresent the evidence.

`audit.py` reads only original retained reports; `audit.json` retains exact structured/raw records, byte/line/hash references, request geometry, guest ACK text and source hashes. No file modification times are used. Close labels rely on the prior operator-reviewed beta-dialog context, not coordinate inference alone. Host transmission/reply time is not guest delivery, animation completion or presentation time. These are selected, nonrandomized runs with different helper/emulator/observer/host conditions. No runtime actions or code changes occurred.
