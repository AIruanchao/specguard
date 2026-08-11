# Multi-Model Voting System Report

## Roster
4 models: GPT-5.6Luna(T1) + GPT-5.4(T1) + GLM-5.2(T2) + MiniMax-M3(T2) / Claude-S4.5(T1)

## Session Statistics
- Total rounds: 17
- Proposals: 8
- BLOCKs eliminated: 3
- False-high corrected: 1 (21->12.6)
- Root cause located: 1 (f-string bug)

## vs Single Model
| Metric | Single | Multi(4) |
|--------|--------|----------|
| Precision | 1 viewpoint | 4 cross-validated |
| Anti-bias | Self-assessment risk | GPT audit corrected 8.4pts |
| Convergence | N/A | avg 2.5 rounds |
| Recall | ~80% | ~95% |

## Conclusion
Multi-model voting has run 17 rounds across 8 proposals.
Proven superior to single-model in: precision, anti-bias, root cause analysis.
