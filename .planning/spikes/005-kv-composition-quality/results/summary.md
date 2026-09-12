# Spike 005 head-to-head (identical inputs per row)

| q | variant | tok | full TTFT | full ok | warm TTFT | warm x | warm=full | shift TTFT | shift x | shift=full |
|---|---|---|---|---|---|---|---|---|---|---|
| q1 | distr+gold | 339 | 0.0545 | 1.0 | 0.013 | 4.19 | 1.0 | 0.0505 | 1.08 | 1.0 |
| q1 | distr-only | 208 | 0.0355 | 1.0 | 0.0127 | 2.8 | 1.0 | 0.0324 | 1.1 | 1.0 |
| q1 | dup | 250 | 0.0402 | 1.0 | 0.0128 | 3.14 | 1.0 | 0.0393 | 1.02 | 1.0 |
| q1 | empty | 31 | 0.0149 | 1.0 | 0.0129 | 1.16 | 1.0 | 0.0148 | 1.01 | 1.0 |
| q1 | gold+distr | 339 | 0.0551 | 1.0 | 0.013 | 4.24 | 0.0 | 0.0508 | 1.08 | 0.0 |
| q1 | gold-AB | 162 | 0.0316 | 1.0 | 0.0128 | 2.47 | 1.0 | 0.0287 | 1.1 | 1.0 |
| q1 | gold-BA | 162 | 0.0312 | 1.0 | 0.0128 | 2.44 | 1.0 | 0.0285 | 1.09 | 1.0 |
| q1 | long | 637 | 0.1149 | 1.0 | 0.0135 | 8.51 | 0.0 | 0.1257 | 0.91 | 0.0 |
| q1 | single-1 | 119 | 0.0248 | 1.0 | 0.0128 | 1.94 | 1.0 | 0.0217 | 1.14 | 1.0 |
| q1 | single-2 | 74 | 0.02 | 1.0 | 0.0128 | 1.56 | 1.0 | 0.0177 | 1.13 | 1.0 |
| q2 | distr+gold | 394 | 0.0704 | 1.0 | 0.0144 | 4.89 | 0.0 | 0.058 | 1.21 | 0.0 |
| q2 | distr-only | 217 | 0.0361 | 0.0 | 0.0138 | 2.62 | 0.0 | 0.0355 | 1.02 | 1.0 |
| q2 | dup | 301 | 0.0501 | 1.0 | 0.0144 | 3.48 | 1.0 | 0.045 | 1.11 | 1.0 |
| q2 | empty | 40 | 0.0158 | 0.0 | 0.0139 | 1.14 | 1.0 | 0.015 | 1.05 | 1.0 |
| q2 | gold+distr | 394 | 0.0703 | 1.0 | 0.0143 | 4.92 | 0.0 | 0.057 | 1.23 | 1.0 |
| q2 | gold-AB | 217 | 0.0363 | 1.0 | 0.0139 | 2.61 | 1.0 | 0.0322 | 1.13 | 0.0 |
| q2 | gold-BA | 217 | 0.0364 | 1.0 | 0.0139 | 2.62 | 1.0 | 0.0356 | 1.02 | 1.0 |
| q2 | long | 692 | 0.1255 | 0.0 | 0.0152 | 8.26 | 0.0 | 0.1348 | 0.93 | 0.0 |
| q2 | single-1 | 124 | 0.0253 | 0.0 | 0.0138 | 1.83 | 1.0 | 0.0218 | 1.16 | 1.0 |
| q2 | single-2 | 133 | 0.0283 | 0.0 | 0.0139 | 2.04 | 1.0 | 0.0237 | 1.19 | 1.0 |

TTFT fit full: 0.2279 ms/tok + -0.0321 s intercept; warm: 0.0006 ms/tok + 0.0131 s intercept.
Order swap: {"q1": {"ab_correct": 1.0, "ba_correct": 1.0, "ab_eq_ba": true}, "q2": {"ab_correct": 1.0, "ba_correct": 1.0, "ab_eq_ba": false}}
Partition probe: [["oneshot", true, null], ["54", true, null], ["81", true, null], ["108", true, null]]
State paths: [["exact_repeat_no_reset", true], ["warm_no_saveload", true], ["warm_saveload", true]]
q2 ambassador-mention (full): {"distr+gold": true, "distr-only": false, "dup": true, "empty": false, "gold+distr": true, "gold-AB": true, "gold-BA": true, "long": false, "single-1": false, "single-2": true}
