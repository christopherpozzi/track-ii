# Discarded runs

`head_ABORTED_harness_bug.jsonl` — 12 negotiations, stage 4, aborted.

Not a model result and must not be aggregated. The engine's `max_tokens` was
1200, tuned against a non-reasoning model. GLM-5.3, DeepSeek-v4 and MiniMax-M3
emit a `reasoning` field before `content`; with a full role sheet plus running
transcript in context they spent the whole budget reasoning and returned empty
content. That recorded as a parse failure — GLM 0/6 and DeepSeek 1/6 on closing
turns, against Haiku's 11/12.

Reporting those numbers would have been a serious error: it reads as the Chinese
models being unable to follow the output format, when in fact the harness never
let them finish a sentence. Fixed by raising max_tokens to 4000 and falling back
to the reasoning text when content is empty; both models then parse correctly.
