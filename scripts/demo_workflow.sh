#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
: "${DEMO_DOI:?Set DEMO_DOI to a DOI resolvable by the configured bibliographic provider.}"

tmp_dir="$(mktemp -d)"

echo "Checking liveness and readiness..."
curl --fail --silent --show-error "$BASE_URL/health" > "$tmp_dir/health.json"
curl --fail --silent --show-error "$BASE_URL/ready" > "$tmp_dir/ready.json"

echo "Ingesting paper $DEMO_DOI..."
curl --fail --silent --show-error \
  -X POST "$BASE_URL/papers" \
  -H "content-type: application/json" \
  -d "{\"doi\":\"$DEMO_DOI\"}" \
  > "$tmp_dir/paper.json"
paper_id="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$tmp_dir/paper.json")"

echo "Computing relevance for paper $paper_id..."
curl --fail --silent --show-error \
  -X POST "$BASE_URL/papers/$paper_id/relevance" \
  > "$tmp_dir/relevance.json"

echo "Generating fake or configured LLM analysis for paper $paper_id..."
curl --fail --silent --show-error \
  -X POST "$BASE_URL/papers/$paper_id/analysis" \
  > "$tmp_dir/analysis.json"
analysis_id="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$tmp_dir/analysis.json")"

echo "Reading analysis $analysis_id and retrieval views..."
curl --fail --silent --show-error "$BASE_URL/analyses/$analysis_id" > "$tmp_dir/analysis-read.json"
curl --fail --silent --show-error "$BASE_URL/papers/$paper_id" > "$tmp_dir/paper-read.json"
curl --fail --silent --show-error "$BASE_URL/papers/$paper_id/chunks" > "$tmp_dir/chunks.json"

echo "MVP workflow complete."
echo "Artifacts were written under $tmp_dir for this run."
