---
name: search-sort-efficiency
description: Mandatory efficiency standards for search and sort operations in VibeGuard's code (data structures, algorithmic complexity). Consult whenever writing code that looks up, filters, deduplicates, or orders any collection of findings, rules, files, or scan data. Applies for the entire life of the project.
user-invocable: true
---

# Search & Sort Efficiency

TRIGGER: read whenever writing code that searches for an item in a
collection, checks membership, deduplicates, filters, or orders any set
of findings, rules, files, or scan data.

## Core principle

Pick the data structure and algorithm whose complexity actually matches
how the data will be used, before writing the loop. VibeGuard's inputs
(files scanned, findings collected, rules evaluated) can scale into the
thousands — a list-and-loop habit that's fine at 10 items becomes the
bottleneck at 10,000.

## Search & lookup

- Membership tests and key lookups: use `set`/`dict`/`frozenset`, not
  repeated linear scans of a `list`. O(1) average vs O(n) — this is not
  optional at scale.
- If the same collection is queried inside a loop, build the index
  (`dict`/`set`) once outside the loop. Never rebuild or rescan it per
  iteration.
- Nested loops comparing every item of A against every item of B are an
  O(n·m) smell — key one side into a dict/set first and reduce it to a
  lookup.
- For repeated pattern search across many files/lines, compile regexes
  once (`re.compile`) rather than recompiling per call. For a fixed set
  of literal patterns tested against every line, prefer a single
  combined pass (`re.compile("|".join(...))`, an early-exit substring
  check, or a multi-pattern scanner like Aho-Corasick for large pattern
  sets) over N separate searches per line.
- Prefer generators/lazy iteration for large scan input (file trees,
  line streams) consumed once, rather than materializing full lists
  just to search them.

## Sort & order

- Use the builtin `sorted()`/`list.sort()` (Timsort, O(n log n)) with a
  `key=` function. Never hand-roll a comparison sort.
- If only the top-k items are needed (e.g. the 10 most severe
  findings), use `heapq.nlargest`/`nsmallest` (O(n log k)) instead of
  sorting the whole collection and slicing.
- Sort once and reuse the result. Don't re-sort the same collection
  repeatedly across a scan/request lifecycle when the underlying data
  hasn't changed.
- If items are added incrementally and order must be maintained (e.g.
  streaming findings into a running "worst first" view), use a heap
  rather than re-sorting the full list after every insert.
- Findings output must be deterministically ordered: when a primary key
  (e.g. severity) ties, define an explicit secondary/tertiary sort key
  (e.g. file path, then line number) rather than leaving tie order to
  incidental insertion order.

## Before optimizing further

The rules above are mandatory baseline hygiene regardless of scale —
they're not premature optimization, they're picking the right tool.
Anything beyond them (manual loop unrolling, speculative caching,
micro-tuning) needs a measured bottleneck first, not a guess — profile
before going further.

## Testing tie-in

Per [testing-standards](../testing-standards/SKILL.md), search/sort
logic whose behavior depends on input size needs a test against a
larger fixture (hundreds+ items), not just a 2-3 item happy path — that
size is what actually catches an accidental O(n²) before it ships.
