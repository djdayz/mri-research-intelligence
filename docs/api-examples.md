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

List seeded discovery topics:

```bash
curl http://localhost:8000/topics
```

Create a subscription:

```bash
curl -X POST http://localhost:8000/subscriptions \
  -H "content-type: application/json" \
  -d '{"name":"Weekly MRI CVR","discovery_query":"MRI CVR","topic_ids":[1],"minimum_relevance_score":0.2,"digest_cadence":"weekly"}'
```

List subscriptions:

```bash
curl http://localhost:8000/subscriptions
```

Run a manual digest preview:

```bash
curl -X POST http://localhost:8000/subscriptions/1/digest-preview \
  -H "content-type: application/json" \
  -d '{"period_start":"2026-01-01","period_end":"2026-01-31","rows":10}'
```

Fetch a rendered digest:

```bash
curl http://localhost:8000/digests/1
```

CLI digest preview:

```bash
python -m mrinsight.cli digest run --subscription-id 1 --rows 10
python -m mrinsight.cli digest run-due --rows 20
python -m mrinsight.cli digest retry-deliveries --limit 20
```

CLI deterministic evaluation:

```bash
python -m mrinsight.cli eval run --output var/evaluation/golden-report.json
```
