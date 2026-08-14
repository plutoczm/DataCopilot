from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def _load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="QLoRA SFT for DataCopilot Text2SQL.")
    parser.add_argument("--config", type=Path, default=Path("training/configs/qlora_text2sql.json"))
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    cfg = _load_config(args.config)
    model_name = str(cfg["base_model"])
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    compute_dtype_name = str(cfg.get("bnb_4bit_compute_dtype", "bfloat16"))
    compute_dtype = getattr(torch, compute_dtype_name, None)
    if compute_dtype is None:
        raise ValueError(f"unsupported torch dtype: {compute_dtype_name}")

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=str(cfg.get("bnb_4bit_quant_type", "nf4")),
        bnb_4bit_use_double_quant=bool(cfg.get("bnb_4bit_use_double_quant", True)),
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    files = {"train": str(args.train)}
    if args.validation:
        files["validation"] = str(args.validation)
    dataset = load_dataset("json", data_files=files)

    def render(example):
        return {
            "text": tokenizer.apply_chat_template(
                example["messages"],
                tokenize=False,
                add_generation_prompt=False,
            )
        }

    rendered = dataset.map(render)

    peft_config = LoraConfig(
        r=int(cfg.get("lora_r", 16)),
        lora_alpha=int(cfg.get("lora_alpha", 32)),
        lora_dropout=float(cfg.get("lora_dropout", 0.05)),
        target_modules=cfg.get("target_modules", "all-linear"),
        bias="none",
        task_type="CAUSAL_LM",
    )
    training_args = SFTConfig(
        output_dir=str(args.output_dir),
        num_train_epochs=float(cfg.get("num_train_epochs", 2)),
        per_device_train_batch_size=int(cfg.get("per_device_train_batch_size", 1)),
        per_device_eval_batch_size=int(cfg.get("per_device_eval_batch_size", 1)),
        gradient_accumulation_steps=int(cfg.get("gradient_accumulation_steps", 16)),
        learning_rate=float(cfg.get("learning_rate", 2e-4)),
        warmup_ratio=float(cfg.get("warmup_ratio", 0.03)),
        logging_steps=int(cfg.get("logging_steps", 10)),
        save_strategy="epoch",
        eval_strategy="epoch" if "validation" in rendered else "no",
        bf16=bool(cfg.get("bf16", True)),
        max_length=int(cfg.get("max_seq_length", 4096)),
        dataset_text_field="text",
        report_to=[],
        seed=int(cfg.get("seed", 42)),
    )
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=rendered["train"],
        eval_dataset=rendered.get("validation"),
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))

    provenance = {
        "base_model": model_name,
        "config": cfg,
        "train_dataset": str(args.train),
        "validation_dataset": str(args.validation) if args.validation else None,
    }
    (args.output_dir / "training_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
