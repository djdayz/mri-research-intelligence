# API Examples

Health:

```bash
curl http://localhost:8000/health
```

Ingest a DOI:

```bash
curl -X POST http://localhost:8000/papers \
  -H "content-type: application/json" \
  -d '{"doi":"10.1234/example"}'
```

Upload permitted PDF full text:

```bash
curl -X POST http://localhost:8000/papers/1/full-text \
  -F "file=@paper.pdf;type=application/pdf"
```

Compute or retrieve deterministic relevance:

```bash
curl -X POST http://localhost:8000/papers/1/relevance
```

Compute or retrieve structured analysis:

```bash
curl -X POST http://localhost:8000/papers/1/analysis
```

List analyses for a paper:

```bash
curl http://localhost:8000/papers/1/analysis
```

Fetch one analysis:

```bash
curl http://localhost:8000/analyses/1
```
