# Evaluation

MRInsight includes a deterministic golden evaluation command for structured LLM analysis safety.

Run the offline regression suite:

```bash
.venv/bin/python -m mrinsight.cli eval run --output var/evaluation/golden-report.json
```

The default provider is `fake`, so this command does not call OpenAI or any live LLM. It evaluates synthetic, legally reusable cases for:

- schema validity;
- evidence coverage;
- unsupported claims;
- numerical attribution;
- abstract/full-text scope correctness;
- repair rate;
- validation failure rate;
- token usage;
- latency;
- estimated cost.

The report is machine-readable JSON and is suitable for CI artifacts. Deterministic regressions should be treated as failures when `summary.failed_cases` is nonzero.

Optional live evaluation:

```bash
MRINSIGHT_LLM_PROVIDER=openai \
MRINSIGHT_LLM_API_KEY=<key> \
.venv/bin/python -m mrinsight.cli eval run --provider configured --allow-live \
  --output var/evaluation/live-report.json
```

Live evaluation can cost money and vary over time. Do not use it as a required CI gate.
