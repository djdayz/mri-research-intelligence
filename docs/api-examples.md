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

List papers with bounded offset pagination:

```bash
curl 'http://localhost:8000/papers?limit=25&offset=0&sort=newest_publication'
```

Filter papers:

```bash
curl 'http://localhost:8000/papers?title_query=MRI&content_scope=abstract&extraction_status=succeeded&relevance_label=high&mri_category=cvr&analysis_status=succeeded&analysis_scope=abstract_only&sort=relevance_score'
```

Retrieve paper detail and related resource summaries:

```bash
curl http://localhost:8000/papers/1
```

List content metadata without extracted full text:

```bash
curl http://localhost:8000/papers/1/contents
```

Retrieve explicit evidence chunks:

```bash
curl 'http://localhost:8000/papers/1/chunks?section=methods&limit=50'
```
