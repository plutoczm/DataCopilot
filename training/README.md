# Text2SQL QLoRA / SFT

This directory adds a **measurable model-adaptation path** to DataCopilot without making GPU training a runtime dependency.

The goal is not to claim that fine-tuning is automatically better than prompting or RAG. The workflow is designed to answer one concrete question:

> On the same frozen Golden Result benchmark, does a domain-adapted model improve business-result accuracy or schema grounding enough to justify serving it?

## Guardrails against fake gains

1. **Schema-group split**: `build_text2sql_dataset.py` splits by `schema_id`, not by random question rows, so the same schema cannot appear in train and validation/test.
2. **Benchmark contamination check**: `validate_dataset.py --benchmark-questions ...` fails if a training/validation/test question exactly overlaps the held-out retail benchmark.
3. **Same benchmark fingerprint**: `compare_reports.py` refuses to compare reports produced from different benchmark definitions.
4. **Same RAG setting**: base and candidate reports must use the same `use_rag` setting.
5. **Business metrics, not training loss**: promotion decisions use `business_result_accuracy`, `schema_hallucination_rate`, execution success, latency and token usage.

The included `sample_text2sql.jsonl` exists only to validate the pipeline contract in CI. It is intentionally tiny and must **not** be used to claim model-quality improvements.

## Dataset contract

Source JSONL rows:

```json
{
  "id": "support-open-priority",
  "schema_id": "support_v1",
  "engine": "sqlite",
  "schema": "CREATE TABLE ...",
  "question": "统计仍未关闭的高优先级工单数量",
  "sql": "SELECT ...",
  "explanation": "optional",
  "optimization_suggestions": []
}
```

For a meaningful experiment, prepare multiple independent schemas and enough examples per schema. Keep the production benchmark questions out of the SFT corpus.

Build leakage-resistant splits:

```bash
python training/data/build_text2sql_dataset.py \
  --source /path/to/curated_text2sql.jsonl \
  --output-dir data/training/text2sql
```

Validate the contract and ensure no benchmark-question overlap:

```bash
python training/data/validate_dataset.py \
  data/training/text2sql/train.jsonl \
  data/training/text2sql/validation.jsonl \
  data/training/text2sql/test.jsonl \
  --benchmark-questions examples/retail_analytics/questions.json
```

## QLoRA training

Training dependencies are isolated from the API runtime:

```bash
pip install -r training/requirements.txt
```

Run SFT:

```bash
python training/train/train_sft.py \
  --config training/configs/qlora_text2sql.json \
  --train data/training/text2sql/train.jsonl \
  --validation data/training/text2sql/validation.jsonl \
  --output-dir data/models/text2sql-qwen3-8b-lora
```

The default config targets `Qwen/Qwen3-8B` with 4-bit NF4 quantization and LoRA on linear layers. Treat the config as an experiment baseline, not a magic recipe: batch size, sequence length, LoRA rank and learning rate should be changed only with recorded benchmark evidence.

## Export / serving

To create a merged checkpoint for a local serving stack:

```bash
python training/export/merge_adapter.py \
  --base-model Qwen/Qwen3-8B \
  --adapter data/models/text2sql-qwen3-8b-lora \
  --output-dir data/models/text2sql-qwen3-8b-merged
```

Serve the merged model through the local serving mechanism you use for DataCopilot (for example an OpenAI-compatible local server or an Ollama-compatible converted artifact), then run the existing application benchmark. Training code is deliberately kept out of the FastAPI process so model-tooling dependencies do not inflate the production image.

## A/B evaluation

Run the exact same benchmark once with the base model and once with the fine-tuned model:

```bash
python examples/retail_analytics/evaluate_text2sql.py \
  --report data/evaluation/base.json

python examples/retail_analytics/evaluate_text2sql.py \
  --report data/evaluation/finetuned.json
```

Then compare:

```bash
python training/evaluation/compare_reports.py \
  --base data/evaluation/base.json \
  --candidate data/evaluation/finetuned.json \
  --report data/evaluation/model_comparison.json \
  --min-business-accuracy-delta 0.0 \
  --max-hallucination-regression 0.0
```

A model should not be promoted merely because loss decreased. A practical promotion policy should require non-regression on safety/schema hallucination and a measured benefit on the task metric that matters.

## Interview framing

A defensible explanation is:

> I first established a fixed Text2SQL Golden Result baseline. I then built a schema-grouped SFT dataset, used QLoRA for low-cost domain adaptation, and compared the base and tuned model under the same benchmark fingerprint. I only treat fine-tuning as useful if business-result accuracy improves without worsening schema hallucination or operational cost.

That demonstrates model training **and** the engineering judgment to know when the training is actually justified.
