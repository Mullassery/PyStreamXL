# Performance Model

## Memory

| Component         | Cost                        |
|-------------------|-----------------------------|
| sharedStrings SST | O(unique strings) — once    |
| Current row       | O(columns) — replaced each row |
| Sheet XML         | O(1) streaming read         |

Total: effectively constant as row count grows.

## Time complexity

- ZIP decompression: O(file size), streamed
- XML parsing per row: O(columns)
- SST lookup: O(1) (Vec index)

## Bottlenecks

1. ZIP decompression (deflate) — CPU-bound in Rust, fast
2. XML tokenization — `quick-xml` is among the fastest XML parsers in any language
3. PyO3 conversion — one Python list allocation per row, unavoidable
