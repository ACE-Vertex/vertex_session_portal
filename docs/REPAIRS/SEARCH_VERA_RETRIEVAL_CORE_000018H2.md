# Search Vera Retrieval Core 000018H2 — retrieval relevance repair

## Evidence

000018H1 fixed the Node `Dirent` typing problem and the project now builds.

Runtime then proved:

- `SEARCH_VERA_REAL_LLM=PASS`
- the Search Vera path itself is alive,

but the verifier failed because the top retrieval set did not include the canonical
document containing `三人寄れば文殊の知恵`.

The returned hit list was dominated by common instruction words such as `search`,
`project`, `document`, etc.

## Cause

The initial local retriever treated every token almost equally. Natural-language
search instructions therefore allowed common English control words to outweigh the
actual high-specificity search phrase.

## Repair

The retriever now:

1. extracts a phrase following the natural-language form `phrase ...`,
2. extracts quoted terms,
3. splits sentence punctuation including `. ! ?`,
4. removes a small set of retrieval-control stop words,
5. weights non-ASCII / long specific terms far above boilerplate words,
6. uses the same weighting to choose the best snippet line.

This is a product retrieval-quality repair, not a verifier shortcut.

No new Runtime, library, vector DB, embedding model, npm dependency, provider,
SQLite schema, UI permission, or filesystem write capability is added.

The original `verify_search_vera_retrieval_core_000018.py` verifier is re-run
unchanged.
