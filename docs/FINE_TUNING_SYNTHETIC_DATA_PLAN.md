# Fine-Tuning with Synthetic Data Generation Plan

**Status**: 📋 **FUTURE WORK** - Execute when ready for production optimization
**Created**: October 16, 2025
**Priority**: Medium (defer until after Best-of-N + Qwen3 testing)

---

## Executive Summary

This plan outlines how to create a **fine-tuned model specialized for lift-sys IR generation** using synthetic data generation to overcome the limited training data problem.

**Core Strategy**: Generate 300-500 high-quality training examples using a combination of:
1. **Synthetic prompt generation** (automated)
2. **Strong model IR generation** (Claude 3.5 or GPT-4)
3. **Manual review and correction** (quality control)
4. **LoRA fine-tuning** of Qwen3-Coder-30B

**Expected Outcome**: 92-98% success rate with lower ongoing inference cost

---

## Part 1: Synthetic Data Generation

### Phase 1: Prompt Generation (Automated)

**Goal**: Generate 300-500 diverse function prompts covering all test categories

#### Technique 1: Template-Based Generation

**Templates by Category**:

```python
PROMPT_TEMPLATES = {
    "control_flow": [
        "Create a function that returns {value_a} if {condition}, {value_b} if {condition2}, otherwise {value_c}",
        "Create a function that validates {input}. Return '{error_msg}' if {invalid_condition}, otherwise return '{success_msg}'",
        "Create a function that classifies {input}. Return '{category_a}' for {condition_a}, '{category_b}' for {condition_b}, or '{category_c}' otherwise",
    ],
    "list_operations": [
        "Create a function that {operation} from a list of {type}",
        "Create a function that filters a list keeping only elements that {condition}",
        "Create a function that finds the {position} element in a list that {condition}",
    ],
    "string_manipulation": [
        "Create a function that {operation} each {unit} in a string",
        "Create a function that checks if a string {condition}. Must {requirement}",
        "Create a function that returns {result} if string {condition}",
    ],
    "type_operations": [
        "Create a function that checks the type of a value. Use isinstance() to check if the value is {type_a}, {type_b}, or {type_c}. Return the exact string '{type_a}', '{type_b}', '{type_c}', or '{other}'",
        "Create a function that converts {type_a} to {type_b}, returning {default} if conversion fails",
    ],
    "mathematical": [
        "Create a function that calculates the {operation} of {input}",
        "Create a function that returns the {position} {item} from {collection}",
    ],
    "edge_cases": [
        "Create a function that returns {value_a} or {value_b} if {condition}",
        "Create a function that handles {edge_case} by {action}",
    ],
}

# Variable pools
VALUES = ["'valid'", "'invalid'", "0", "None", "[]", "''", "True", "False"]
CONDITIONS = ["< 8 characters", "> 0", "is empty", "contains @", "equals {value}"]
OPERATIONS = ["sum", "count", "filter", "map", "find", "capitalize", "reverse"]
TYPES = ["int", "str", "list", "dict", "bool", "float"]
```

**Generation Script**:

```python
import random
import itertools

def generate_prompts(num_prompts: int = 300) -> list[dict]:
    """Generate diverse synthetic prompts."""
    prompts = []

    # Ensure balanced distribution across categories
    prompts_per_category = num_prompts // len(PROMPT_TEMPLATES)

    for category, templates in PROMPT_TEMPLATES.items():
        for _ in range(prompts_per_category):
            template = random.choice(templates)

            # Fill in template variables
            prompt = template.format(
                value_a=random.choice(VALUES),
                value_b=random.choice(VALUES),
                value_c=random.choice(VALUES),
                condition=random.choice(CONDITIONS),
                condition2=random.choice(CONDITIONS),
                operation=random.choice(OPERATIONS),
                type=random.choice(TYPES),
                type_a=random.choice(TYPES),
                type_b=random.choice(TYPES),
                type_c=random.choice(TYPES),
                other="'other'",
                error_msg=random.choice(["'too short'", "'invalid'", "'error'"]),
                success_msg=random.choice(["'valid'", "'success'", "'ok'"]),
                # ... more variables as needed
            )

            prompts.append({
                "category": category,
                "complexity": random.choice(["easy", "medium", "medium_hard"]),
                "prompt": prompt,
                "source": "template_generated"
            })

    return prompts
```

**Expected Output** (50 prompts per category):
- control_flow: 50 prompts
- list_operations: 50 prompts
- string_manipulation: 50 prompts
- type_operations: 50 prompts
- mathematical: 50 prompts
- edge_cases: 50 prompts

**Total**: 300 prompts

---

#### Technique 2: LLM-Based Prompt Expansion

**Goal**: Use a strong LLM to generate variations of existing prompts

```python
async def expand_prompts(seed_prompts: list[str], variations_per_prompt: int = 3) -> list[str]:
    """Use LLM to generate prompt variations."""

    expansion_prompt = """Given this function specification, generate {n} variations with different:
- Return values (different strings, numbers, or types)
- Conditions (different thresholds, checks)
- Edge cases (different boundary conditions)

Keep the same category and complexity, but vary the specifics.

Original: {original_prompt}

Generate {n} variations as JSON array:
[
  "variation 1...",
  "variation 2...",
  ...
]
"""

    all_variations = []
    for prompt in seed_prompts:
        response = await claude_client.generate(
            expansion_prompt.format(
                n=variations_per_prompt,
                original_prompt=prompt
            )
        )
        variations = json.loads(response)
        all_variations.extend(variations)

    return all_variations
```

**Input**: 18 existing test prompts
**Output**: 18 × 3 = 54 variations

**Combined Total**: 300 + 54 = **354 prompts**

---

### Phase 2: IR Generation (Strong Model)

**Goal**: Generate high-quality reference IRs using best available model

**Approach**: Use Claude 3.5 Sonnet (best instruction-following) to generate IRs

```python
async def generate_reference_irs(prompts: list[dict]) -> list[dict]:
    """Generate IRs using Claude 3.5 for high quality."""

    dataset = []

    for prompt_data in prompts:
        # Use enhanced prompt with few-shot examples
        ir_prompt = get_prompt_for_ir_generation(prompt_data["prompt"])

        # Generate with Claude (better than Qwen for training data quality)
        try:
            response = await claude_client.generate(ir_prompt)
            ir_json = extract_json(response)

            # Validate schema
            validate_schema(ir_json)

            dataset.append({
                "prompt": prompt_data["prompt"],
                "ir": ir_json,
                "category": prompt_data["category"],
                "complexity": prompt_data["complexity"],
                "source": "claude_generated",
                "needs_review": True  # Flag for manual review
            })

        except Exception as e:
            print(f"Failed to generate IR for: {prompt_data['prompt'][:50]}... Error: {e}")
            continue

    return dataset
```

**Expected**: ~340 generated IRs (96% success rate with Claude)

---

### Phase 3: Manual Review and Correction

**Goal**: Human-in-the-loop quality control

**Review Process**:

```python
def create_review_interface(dataset: list[dict]) -> None:
    """Create simple CLI for reviewing IRs."""

    for i, item in enumerate(dataset):
        print(f"\n{'='*70}")
        print(f"Review {i+1}/{len(dataset)}")
        print(f"Category: {item['category']}, Complexity: {item['complexity']}")
        print(f"\nPrompt:\n{item['prompt']}")
        print(f"\nGenerated IR:")
        print(json.dumps(item['ir'], indent=2))

        # Review questions
        print("\nReview Checklist:")
        print("1. Are literal strings marked as LITERAL?")
        print("2. Are Python quirks handled (bool/int, etc.)?")
        print("3. Are all edge cases covered in assertions?")
        print("4. Is the IR complete and correct?")

        action = input("\n[a]ccept / [e]dit / [r]eject / [s]kip: ").lower()

        if action == 'a':
            item['needs_review'] = False
            item['review_status'] = 'accepted'
        elif action == 'e':
            # Open editor for manual correction
            edited_ir = edit_ir(item['ir'])
            item['ir'] = edited_ir
            item['needs_review'] = False
            item['review_status'] = 'corrected'
        elif action == 'r':
            item['review_status'] = 'rejected'
        else:
            continue
```

**Review Focus**:
1. **Literal strings**: Ensure effects say "return LITERAL 'X'" not "return X"
2. **Python quirks**: Check bool/int ordering, mutability notes
3. **Assertions**: Verify edge cases covered (True → 'other', empty inputs, etc.)
4. **Completeness**: All return paths specified in effects

**Time Estimate**: 5-10 minutes per IR × 340 IRs = **28-57 hours** (spread over 1-2 weeks)

**Quality Target**: Accept 80%, correct 15%, reject 5%
- **Accepted**: 272 IRs (as-is)
- **Corrected**: 51 IRs (improved)
- **Rejected**: 17 IRs (discard)

**Final Dataset**: 323 high-quality training examples

---

### Phase 4: Negative Examples Generation

**Goal**: Teach model what NOT to do

**Strategy**: Create "bad IR" examples showing common mistakes

```python
def generate_negative_examples(positive_examples: list[dict]) -> list[dict]:
    """Create negative examples by introducing known errors."""

    negative_examples = []

    for example in positive_examples[:50]:  # Take subset
        # Mistake 1: Verbose strings instead of literals
        bad_ir_1 = copy.deepcopy(example['ir'])
        for effect in bad_ir_1.get('effects', []):
            if 'LITERAL' in effect['description']:
                effect['description'] = effect['description'].replace(
                    "return LITERAL 'too short'",
                    "return a message indicating the password is too short"
                )

        negative_examples.append({
            "prompt": example['prompt'],
            "ir": bad_ir_1,
            "label": "bad",
            "error_type": "verbose_string",
            "correction": example['ir']
        })

        # Mistake 2: Missing bool/int quirk
        if 'bool' in str(example['ir']) and 'int' in str(example['ir']):
            bad_ir_2 = copy.deepcopy(example['ir'])
            # Remove ordering constraint
            bad_ir_2['effects'] = [
                e for e in bad_ir_2['effects']
                if 'bool' not in e.get('description', '').lower() or 'before' not in e.get('description', '').lower()
            ]

            negative_examples.append({
                "prompt": example['prompt'],
                "ir": bad_ir_2,
                "label": "bad",
                "error_type": "missing_python_quirk",
                "correction": example['ir']
            })

    return negative_examples
```

**Output**: ~100 negative examples (2 per positive example for 50 prompts)

---

### Phase 5: Dataset Composition

**Final Training Dataset**:

```python
{
    "positive_examples": 323,  # High-quality IRs
    "negative_examples": 100,  # Common mistakes with corrections
    "total": 423
}

# Split
{
    "train": 338,      # 80%
    "validation": 42,  # 10%
    "test": 43         # 10%
}
```

**Format** (JSONL):
```jsonl
{"prompt": "Create a function...", "completion": "{\"intent\": {...}, ...}", "label": "good"}
{"prompt": "Create a function...", "completion": "{\"intent\": {...}, ...}", "label": "bad", "error": "verbose_string"}
```

---

## Part 2: Fine-Tuning Implementation

### Model Selection: Qwen3-Coder-30B-A3B-Instruct

**Why This Model**:
- ✅ MoE architecture: 30B params, ~3B active (efficient)
- ✅ Latest Qwen3 generation (better than Qwen2.5)
- ✅ Code-specialized training
- ✅ Fits on A100-40GB

**Base Performance** (expected): 82-88% success on Phase 3

---

### LoRA Configuration

**Approach**: Parameter-Efficient Fine-Tuning (PEFT) with LoRA

```python
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer

# LoRA configuration optimized for code generation
lora_config = LoraConfig(
    r=16,                    # Rank (higher = more capacity, slower)
    lora_alpha=32,           # Scaling factor (typically 2×r)
    target_modules=[
        "q_proj",            # Query projection (attention)
        "k_proj",            # Key projection
        "v_proj",            # Value projection
        "o_proj",            # Output projection
        "gate_proj",         # MoE gate (Qwen3 specific)
        "up_proj",           # MLP up projection
        "down_proj",         # MLP down projection
    ],
    lora_dropout=0.05,       # Regularization
    bias="none",
    task_type="CAUSAL_LM",
    modules_to_save=["embed_tokens", "lm_head"]  # Full fine-tune embeddings
)

# Load model with 4-bit quantization for memory efficiency
model = AutoModelForCausalLM.from_pretrained(
    "unsloth/Qwen3-Coder-30B-A3B-Instruct",
    load_in_4bit=True,
    device_map="auto",
    trust_remote_code=True
)

# Prepare for LoRA training
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

print(f"Trainable parameters: {model.print_trainable_parameters()}")
# Expected: ~50-100M trainable params (0.2-0.3% of total)
```

---

### Training Configuration

```python
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="./qwen3-coder-liftsys-lora",

    # Training hyperparameters
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,  # Effective batch size: 16

    # Optimization
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=50,
    weight_decay=0.01,

    # Evaluation
    eval_strategy="steps",
    eval_steps=50,
    save_steps=50,
    save_total_limit=3,

    # Logging
    logging_steps=10,
    report_to=["tensorboard"],

    # Performance
    fp16=True,
    dataloader_num_workers=4,

    # Early stopping (avoid overfitting)
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
)
```

**Training Time Estimate**:
- Dataset: 338 examples
- Batch size: 16 (effective)
- Steps per epoch: 338 / 16 = ~21 steps
- Total steps: 21 × 3 epochs = ~63 steps
- Time per step: ~30 seconds (A100)
- **Total training time**: ~30 minutes

**Training Cost**: 30 min × $3/hr = **$1.50**

---

### Training Script

**File**: `scripts/train_ir_lora.py`

```python
#!/usr/bin/env python3
"""Train LoRA adapter for IR generation on Qwen3-Coder-30B."""

import json
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

def load_training_data(data_path: str) -> Dataset:
    """Load training data from JSONL."""
    examples = []
    with open(data_path) as f:
        for line in f:
            examples.append(json.loads(line))

    return Dataset.from_list(examples)

def format_training_example(example: dict, tokenizer) -> dict:
    """Format example for instruction fine-tuning."""

    # Instruction-tuning format
    prompt = f"""You are an expert at converting natural language specifications into IR.

Generate a JSON IR for the following specification:

{example['prompt']}

Generate the IR as valid JSON:"""

    completion = json.dumps(example['completion'], indent=2)

    # Tokenize
    full_text = f"{prompt}\n{completion}"
    tokenized = tokenizer(
        full_text,
        truncation=True,
        max_length=2048,
        padding="max_length"
    )

    # Mask prompt tokens (only train on completion)
    prompt_tokens = tokenizer(prompt, truncation=True, max_length=2048)
    tokenized['labels'] = [-100] * len(prompt_tokens['input_ids']) + tokenized['input_ids'][len(prompt_tokens['input_ids']):]

    return tokenized

def main():
    # Load model and tokenizer
    model_name = "unsloth/Qwen3-Coder-30B-A3B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        load_in_4bit=True,
        device_map="auto",
        trust_remote_code=True
    )

    # Apply LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    # Load datasets
    train_dataset = load_training_data("data/train.jsonl")
    eval_dataset = load_training_data("data/validation.jsonl")

    # Format for training
    train_dataset = train_dataset.map(
        lambda x: format_training_example(x, tokenizer),
        remove_columns=train_dataset.column_names
    )
    eval_dataset = eval_dataset.map(
        lambda x: format_training_example(x, tokenizer),
        remove_columns=eval_dataset.column_names
    )

    # Training args
    training_args = TrainingArguments(
        output_dir="./qwen3-coder-liftsys-lora",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=50,
        save_total_limit=3,
    )

    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )

    trainer.train()

    # Save LoRA adapter
    model.save_pretrained("./qwen3-coder-liftsys-lora-final")
    tokenizer.save_pretrained("./qwen3-coder-liftsys-lora-final")

    print("✅ Training complete! Adapter saved to ./qwen3-coder-liftsys-lora-final")

if __name__ == "__main__":
    main()
```

---

### Deployment to Modal

**Update Modal App** to load LoRA adapter:

```python
# In lift_sys/inference/modal_app.py

@modal.enter()
def load_model(self):
    """Load base model + LoRA adapter."""
    from peft import PeftModel

    print("Loading base model...")
    base_model = LLM(
        model="unsloth/Qwen3-Coder-30B-A3B-Instruct",
        trust_remote_code=True,
        dtype="auto",
        gpu_memory_utilization=0.90,
        guided_decoding_backend="xgrammar",
    )

    # Load LoRA adapter (uploaded to Modal volume)
    print("Loading LoRA adapter...")
    self.llm = PeftModel.from_pretrained(
        base_model,
        "/models/qwen3-coder-liftsys-lora-final"
    )

    print("✅ Fine-tuned model loaded!")
```

---

## Part 3: Evaluation and Iteration

### Evaluation Metrics

```python
def evaluate_fine_tuned_model(model, test_dataset):
    """Evaluate on held-out test set."""

    results = {
        "schema_validity": 0,
        "literal_string_accuracy": 0,
        "python_quirk_handling": 0,
        "assertion_completeness": 0,
        "overall_quality": 0
    }

    for example in test_dataset:
        ir = generate_ir(model, example['prompt'])

        # Schema validity
        if validate_schema(ir):
            results["schema_validity"] += 1

        # Literal string detection
        if has_literal_markers(ir, example['prompt']):
            results["literal_string_accuracy"] += 1

        # Python quirk handling
        if handles_python_quirks(ir):
            results["python_quirk_handling"] += 1

        # Assertion completeness
        assertion_score = score_assertions(ir, example['completion'])
        results["assertion_completeness"] += assertion_score

        # Overall quality (manual review)
        quality = manual_quality_score(ir)
        results["overall_quality"] += quality

    # Normalize
    n = len(test_dataset)
    return {k: v / n * 100 for k, v in results.items()}
```

**Target Metrics**:
- Schema validity: >99%
- Literal string accuracy: >90%
- Python quirk handling: >85%
- Assertion completeness: >80%
- Overall quality: >85%

---

### Iteration Strategy

**If fine-tuned model doesn't meet targets**:

1. **Collect failure cases**: Run on all Phase 3 tests, identify patterns
2. **Augment training data**: Add more examples of failure patterns
3. **Adjust LoRA config**: Increase rank (r=16 → r=32) for more capacity
4. **Retrain**: New LoRA adapter with expanded dataset

**Expected iterations**: 1-2 retraining cycles to reach 95%+ quality

---

## Part 4: Timeline and Effort

### Week 1: Data Generation
- Day 1-2: Generate 300 prompts (template + LLM expansion) - **8 hours**
- Day 3-5: Generate IRs with Claude 3.5 - **12 hours** (includes debugging)

### Week 2-3: Manual Review
- Review 340 IRs at 5-10 min each - **28-57 hours**
- Spread over 2 weeks: 2-3 hours/day

### Week 4: Training Setup
- Create training script - **4 hours**
- Set up Modal training job - **4 hours**
- Initial training run - **2 hours**

### Week 5: Training and Iteration
- Train LoRA adapter - **30 minutes**
- Evaluate on test set - **2 hours**
- Iterate if needed (1-2 cycles) - **8 hours**

### Week 6: Deployment
- Deploy to Modal - **2 hours**
- Re-run Phase 3 tests - **1 hour**
- Document results - **2 hours**

**Total Effort**: 65-92 hours over 6 weeks
**Critical Path**: Manual review (28-57 hours)

---

## Part 5: Cost Estimate

| Item | Cost |
|------|------|
| Claude 3.5 API (340 IRs × $0.03) | $10.20 |
| A100 GPU training (30 min) | $1.50 |
| Modal inference (evaluation) | $2.00 |
| **Total** | **$13.70** |

**Ongoing Cost Reduction**:
- Current: Qwen3-30B @ $3/hr × 3s/request = $0.0025/request
- Fine-tuned: Can use smaller model (Qwen3-7B) @ $1.10/hr × 2s/request = $0.0006/request
- **Savings**: ~76% per request (amortizes training cost after ~5,500 requests)

---

## Part 6: Success Criteria

### Go/No-Go Decision

**Proceed with fine-tuning if**:
- ✅ Best-of-N + Qwen3-30B achieves <90% success
- ✅ Expect >5,000 production IR generations
- ✅ Manual review bandwidth available (28-57 hours)

**Skip fine-tuning if**:
- ✅ Best-of-N + Qwen3-30B achieves ≥90% success
- ✅ Production volume <1,000 IRs
- ✅ Requirements still changing rapidly

### Expected Results

**Conservative**: 92-95% Phase 3 success
**Optimistic**: 95-98% Phase 3 success
**Best Case**: 98%+ (near-perfect on standard patterns)

---

## Part 7: Risks and Mitigations

### Risk 1: Overfitting to Training Data

**Mitigation**:
- Use diverse synthetic prompts (not just variations of test cases)
- Monitor validation loss during training
- Early stopping if validation loss increases

### Risk 2: Manual Review Bottleneck

**Mitigation**:
- Parallelize review across team members
- Use automated pre-checks (schema validity, literal string detection)
- Focus review on complex cases only (simple cases auto-accept)

### Risk 3: Model Forgets General Code Knowledge

**Mitigation**:
- Low LoRA rank (r=16) preserves base model knowledge
- Short training (3 epochs max)
- Monitor performance on non-IR code tasks

---

## Conclusion

**Recommended Timeline**: Start after Best-of-N + Qwen3 testing (Week 3-4)

**Key Success Factors**:
1. High-quality synthetic data (Claude 3.5 generation)
2. Thorough manual review (focus on literal strings, quirks)
3. Conservative LoRA training (avoid overfitting)
4. Iterative refinement based on evaluation

**Expected ROI**: 76% cost reduction after ~5,500 requests

**This plan is ready to execute when production volume justifies the effort.**
