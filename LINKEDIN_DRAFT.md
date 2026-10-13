# LinkedIn draft — owner review required (not posted)

An 8,760-row energy dataset can still be missing hours. A duplicate timestamp may conceal a gap, while daylight-saving transitions and hour-ending conventions introduce a different class of errors entirely.

I built a small Python audit that makes these assumptions explicit: UTC-aware timestamps, fixed local standard time, or civil time with an unambiguous DST fold. It reports missing and duplicate hours, checks optional numeric values, and produces a monthly SVG coverage diagnostic without changing the underlying data.

On a synthetic 2025 example, it correctly identified two missing hours and one duplicate. This is a timestamp-integrity check, not a guarantee of measurement accuracy. Code and reproducible example: **[add public repository link only after release approval]**.

*Draft only. 113 words. Do not post until the owner verifies the claims and approves public release.*
