# SWE-smith Integration Plan for lift-sys
**Created**: 2025-10-16
**Goal**: Break 90% plateau by integrating SWE-smith's proven synthetic data and fine-tuning methodologies
**Expected Outcome**: 95%+ success rate through specialized model training

---

## Phase 1: Foundation - Infrastructure for Synthetic Data Generation

### lift-sys-200: Design GitHub Data Collection Architecture
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 4 hours

Design the system for collecting training data from GitHub repositories. Define:
- Repository selection criteria (permissive licenses, good tests, quality code)
- Function extraction strategy (which functions to extract, filters)
- Data storage format (JSONL schema for training examples)
- Rate limiting and API usage (GitHub API quotas)
- Quality metrics (how to score extracted examples)

**Deliverables**:
- `docs/SYNTHETIC_DATA_ARCHITECTURE.md` - Architecture doc
- Schema definitions for training data format
- Repository selection criteria

**Dependencies**: None

**Integration with lift-sys**:
- Leverages existing reverse mode infrastructure
- Complements IR design with real-world examples
- Uses Modal for scalable processing

---

### lift-sys-201: Implement GitHub Repository Scraper
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1 day

Create scraper that clones and analyzes top Python repositories from GitHub.

**Implementation**:
```python
# lift_sys/data_synthesis/github_scraper.py

class GitHubRepoScraper:
    """Scrape Python repositories from GitHub for training data."""

    def __init__(self, github_token: str):
        self.github = Github(github_token)

    def get_top_repos(
        self,
        language: str = "python",
        min_stars: int = 1000,
        licenses: list[str] = ["mit", "apache-2.0", "bsd"],
        limit: int = 100,
    ) -> list[Repository]:
        """Fetch top Python repos with good licenses."""
        pass

    def clone_repo(self, repo: Repository, dest: Path) -> Path:
        """Clone repository locally for analysis."""
        pass

    def extract_functions(self, repo_path: Path) -> list[FunctionInfo]:
        """Extract all functions with tests from repo."""
        pass
```

**Deliverables**:
- `lift_sys/data_synthesis/github_scraper.py` (~300 lines)
- Unit tests for scraper
- CLI: `uv run python -m lift_sys.data_synthesis.scraper --repos 100`

**Dependencies**: lift-sys-200

**Success Criteria**:
- Can fetch 100+ repos from GitHub
- Filters by license correctly
- Extracts functions with metadata

---

### lift-sys-202: Enhance Reverse Mode for Batch Processing
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 2 days

Optimize reverse mode to process thousands of functions efficiently.

**Current Issue**: Reverse mode designed for interactive use, not batch processing
**Solution**: Add batch mode with parallelization and caching

**Implementation**:
```python
# lift_sys/data_synthesis/batch_lifter.py

class BatchLifter:
    """Process thousands of functions efficiently."""

    def __init__(self, config: LifterConfig):
        self.lifter = SpecificationLifter(config)
        self.cache = LRUCache(maxsize=10000)

    async def lift_batch(
        self,
        functions: list[FunctionInfo],
        max_workers: int = 10,
    ) -> list[tuple[FunctionInfo, Optional[IR]]]:
        """Lift multiple functions in parallel."""
        # Use asyncio to parallelize
        # Cache results to avoid re-processing
        # Handle failures gracefully
        pass

    def filter_quality(
        self,
        pairs: list[tuple[FunctionInfo, IR]],
        min_score: float = 0.7,
    ) -> list[tuple[FunctionInfo, IR]]:
        """Keep only high-quality IR extractions."""
        pass
```

**Deliverables**:
- `lift_sys/data_synthesis/batch_lifter.py` (~400 lines)
- Parallel processing with asyncio
- Progress tracking and error handling
- Performance tests (100+ functions/minute target)

**Dependencies**: lift-sys-201

**Success Criteria**:
- Process 100+ functions/minute
- 80%+ extraction success rate
- Graceful error handling

---

### lift-sys-203: Implement Prompt Synthesis from Code
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1 day

Generate natural language prompts from function signatures and docstrings.

**SWE-smith Insight**: Need (prompt, IR, code) triples, not just (IR, code) pairs

**Implementation**:
```python
# lift_sys/data_synthesis/prompt_synthesizer.py

class PromptSynthesizer:
    """Generate natural language prompts from code."""

    def synthesize_from_docstring(self, func: FunctionInfo) -> str:
        """Extract prompt from docstring."""
        # Parse docstring (Google/NumPy/reStructuredText)
        # Extract description
        # Clean and format
        pass

    def synthesize_from_signature(self, func: FunctionInfo) -> str:
        """Generate prompt from function signature."""
        # "Create a function named {name} that takes {params} and returns {return_type}"
        pass

    def synthesize_from_tests(self, func: FunctionInfo) -> str:
        """Infer intent from test cases."""
        # Analyze test inputs/outputs
        # Infer behavior patterns
        pass

    def combine_sources(self, func: FunctionInfo) -> str:
        """Combine all sources for best prompt."""
        pass
```

**Deliverables**:
- `lift_sys/data_synthesis/prompt_synthesizer.py` (~300 lines)
- Support for common docstring formats
- Fallback strategies if docstring missing
- Examples of generated prompts

**Dependencies**: lift-sys-201

**Success Criteria**:
- Generate clear, natural prompts
- 90%+ of prompts match human intent
- Handle missing docstrings gracefully

---

## Phase 2: Data Generation - SWE-smith-Inspired Synthetic Dataset

### lift-sys-204: Implement Training Data Pipeline
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 2 days

Orchestrate end-to-end pipeline: GitHub → Functions → IRs → Prompts → Training Data

**Implementation**:
```python
# lift_sys/data_synthesis/pipeline.py

class TrainingDataPipeline:
    """SWE-smith-inspired training data generation."""

    def __init__(self):
        self.scraper = GitHubRepoScraper()
        self.lifter = BatchLifter()
        self.synthesizer = PromptSynthesizer()
        self.validator = ExecutionValidator()

    async def generate_dataset(
        self,
        num_repos: int = 100,
        target_examples: int = 5000,
    ) -> Dataset:
        """Generate complete training dataset."""
        # 1. Fetch repos from GitHub
        repos = self.scraper.get_top_repos(limit=num_repos)

        # 2. Extract functions with tests
        functions = []
        for repo in repos:
            functions.extend(self.scraper.extract_functions(repo))

        # 3. Lift functions to IR (parallel)
        ir_pairs = await self.lifter.lift_batch(functions)

        # 4. Synthesize prompts
        triples = []
        for func, ir in ir_pairs:
            prompt = self.synthesizer.combine_sources(func)
            triples.append((prompt, ir, func))

        # 5. Validate and filter (SWE-smith-style)
        validated = await self.validator.filter_valid(triples)

        # 6. Quality scoring and ranking
        dataset = self.rank_and_store(validated, target_examples)

        return dataset
```

**Deliverables**:
- `lift_sys/data_synthesis/pipeline.py` (~500 lines)
- Progress tracking with rich console output
- Checkpoint/resume capability
- Error reporting and statistics

**Dependencies**: lift-sys-201, lift-sys-202, lift-sys-203

**Success Criteria**:
- Generate 5,000+ training examples
- Pipeline completes in 8-12 hours (Modal)
- Clear progress reporting

---

### lift-sys-205: Implement SWE-smith-Style Execution Validator
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1.5 days

Validate training examples through execution, keeping only working examples (like SWE-smith).

**SWE-smith Insight**: Filter by execution - keep only examples where generated code passes tests

**Implementation**:
```python
# lift_sys/data_synthesis/execution_validator.py

class ExecutionValidator:
    """SWE-smith-style validation through execution."""

    async def filter_valid(
        self,
        triples: list[tuple[str, IR, FunctionInfo]],
    ) -> list[TrainingExample]:
        """Keep only examples where IR → Code → Tests pass."""
        validated = []

        for prompt, ir, func in triples:
            # Generate code from IR
            code = await self.generate_code(ir)

            # Execute against function's test cases
            result = await self.execute_tests(code, func.tests)

            # SWE-smith criterion: must pass all tests
            if result.all_passed:
                validated.append(TrainingExample(
                    prompt=prompt,
                    ir=ir.to_dict(),
                    code=code,
                    tests=func.tests,
                    metadata={
                        "repo": func.repo_name,
                        "file": func.file_path,
                        "stars": func.repo_stars,
                    }
                ))

        return validated

    async def execute_tests(
        self,
        code: str,
        tests: list[TestCase],
    ) -> ExecutionResult:
        """Execute tests in isolated environment."""
        # Use Modal sandbox for isolation
        # Run each test case
        # Collect results
        pass
```

**Deliverables**:
- `lift_sys/data_synthesis/execution_validator.py` (~300 lines)
- Modal-based test execution
- Parallel validation (10+ examples/second)
- Detailed failure logging

**Dependencies**: lift-sys-204

**Success Criteria**:
- 100% of validated examples pass tests
- Validation throughput: 10+ examples/second
- Clear failure categorization

---

### lift-sys-206: Run Initial Dataset Generation (Milestone)
**Type**: milestone
**Priority**: 0 (critical path)
**Estimate**: 12 hours (wall time)

Execute the pipeline to generate 5,000-10,000 validated training examples.

**Execution Plan**:
```bash
# Run on Modal for scalability
uv run python -m lift_sys.data_synthesis.pipeline \
  --repos 100 \
  --target-examples 5000 \
  --output training_data/synthetic_v1.jsonl \
  --workers 20 \
  --checkpoint-every 100
```

**Deliverables**:
- `training_data/synthetic_v1.jsonl` (5,000-10,000 examples)
- `training_data/generation_report.md` (statistics and analysis)
- Quality distribution analysis
- Error report for failed extractions

**Dependencies**: lift-sys-205

**Success Criteria**:
- 5,000+ validated examples
- Diverse coverage (repositories, patterns, complexity)
- All examples pass execution tests
- Balanced distribution across categories

---

## Phase 3: Test Expansion - Programmatic Test Generation

### lift-sys-207: Design Template-Based Test Generator
**Type**: task
**Priority**: 1 (important)
**Estimate**: 0.5 days

Design systematic test generation following SWE-smith's task synthesis approach.

**Current Issue**: Only 18 tests per phase - insufficient for measuring true performance
**SWE-smith Approach**: Generate hundreds of task instances programmatically

**Design**:
```python
# Extend existing FINE_TUNING_SYNTHETIC_DATA_PLAN.md approach

TEST_TEMPLATES = {
    "control_flow": [
        # Conditionals
        "grade classifier",
        "validation with error messages",
        "multi-way classifier",
    ],
    "list_operations": [
        # Search
        "find index with fallback",
        "filter by condition",
        "first matching element",
    ],
    # ... more categories
}

# For each template:
# - Generate variations (different types, values, conditions)
# - Create IR specification
# - Generate reference implementation
# - Create test cases
# - Validate template works
```

**Deliverables**:
- `docs/TEST_GENERATION_DESIGN.md` (~30 pages)
- Template taxonomy (categories, patterns)
- Variation strategy (how to create diverse tests)
- Quality criteria for generated tests

**Dependencies**: None (can run parallel to Phase 2)

**Success Criteria**:
- Coverage of all function patterns
- Systematic edge case generation
- Clear template taxonomy

---

### lift-sys-208: Implement Programmatic Test Generator
**Type**: task
**Priority**: 1 (important)
**Estimate**: 2 days

Implement test generator that creates 300-500 tests from templates.

**Implementation**:
```python
# lift_sys/testing/test_generator.py

class ProgrammaticTestGenerator:
    """Generate test cases systematically."""

    def generate_from_template(
        self,
        template: TestTemplate,
        num_variants: int = 10,
    ) -> list[GeneratedTest]:
        """Create variants of a template."""
        tests = []

        for _ in range(num_variants):
            # Vary parameters
            params = self.vary_parameters(template)

            # Generate IR
            ir = self.generate_ir(template, params)

            # Generate reference implementation
            reference = self.generate_reference(template, params)

            # Create test cases
            test_cases = self.generate_test_cases(template, params)

            tests.append(GeneratedTest(
                name=f"{template.name}_{len(tests)}",
                ir=ir,
                reference=reference,
                test_cases=test_cases,
                category=template.category,
                difficulty=self.estimate_difficulty(template, params),
            ))

        return tests

    def generate_test_suite(
        self,
        num_tests: int = 300,
    ) -> TestSuite:
        """Generate complete test suite."""
        # Balanced distribution across categories
        # Mix of difficulties
        # Edge case coverage
        pass
```

**Deliverables**:
- `lift_sys/testing/test_generator.py` (~600 lines)
- 300-500 generated tests
- Test suite validation
- CLI: `uv run python -m lift_sys.testing.generate --output tests/synthetic/phase_synthetic.py`

**Dependencies**: lift-sys-207

**Success Criteria**:
- Generate 300+ valid tests
- Balanced category distribution
- All generated tests executable

---

### lift-sys-209: Validate and Integrate Generated Test Suite
**Type**: task
**Priority**: 1 (important)
**Estimate**: 1 day

Run generated tests, fix issues, integrate into CI pipeline.

**Validation Steps**:
1. Execute all generated tests
2. Identify failures (template bugs)
3. Fix templates and regenerate
4. Measure difficulty distribution
5. Compare vs. hand-written tests

**Deliverables**:
- `tests/synthetic/phase_synthetic.py` (300-500 tests)
- Validation report
- CI integration (pytest configuration)
- Baseline performance measurement

**Dependencies**: lift-sys-208

**Success Criteria**:
- All 300+ tests execute successfully
- Clear difficulty distribution
- Integrated into pytest suite

---

## Phase 4: Model Fine-Tuning - SWE-smith Methodology

### lift-sys-210: Prepare Training Data for LoRA Fine-Tuning
**Type**: task
**Priority**: 0 (critical path, blocked by lift-sys-206)
**Estimate**: 1 day

Convert synthetic dataset to format required for LoRA fine-tuning.

**Data Format**:
```json
// For IR generation task
{
  "instruction": "Generate a formal IR specification for the following function request.",
  "input": "Create a function that finds the index of a value in a list, returning -1 if not found",
  "output": "{\"intent\": {...}, \"signature\": {...}, \"effects\": [...], \"assertions\": [...]}"
}

// For code generation task (optional: could fine-tune both stages)
{
  "instruction": "Generate Python code from the following IR specification.",
  "input": "{IR as JSON}",
  "output": "def find_index(lst, value):\n    for i, item in enumerate(lst):\n        if item == value:\n            return i\n    return -1"
}
```

**Implementation**:
```python
# lift_sys/training/data_prep.py

class TrainingDataPreparation:
    """Prepare data for LoRA fine-tuning."""

    def convert_to_instruction_format(
        self,
        dataset: Dataset,
        task: str = "ir_generation",  # or "code_generation"
    ) -> list[dict]:
        """Convert to instruction-tuning format."""
        pass

    def split_train_val_test(
        self,
        data: list[dict],
        ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    ) -> tuple[list, list, list]:
        """Split into train/val/test sets."""
        pass

    def balance_categories(self, data: list[dict]) -> list[dict]:
        """Ensure balanced representation."""
        pass
```

**Deliverables**:
- `lift_sys/training/data_prep.py` (~200 lines)
- `training_data/train.jsonl` (4,000 examples)
- `training_data/val.jsonl` (500 examples)
- `training_data/test.jsonl` (500 examples)
- Data statistics report

**Dependencies**: lift-sys-206

**Success Criteria**:
- Data in correct format for LoRA
- Balanced category distribution
- Train/val/test splits created

---

### lift-sys-211: Set Up Modal LoRA Training Infrastructure
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1.5 days

Create Modal app for LoRA fine-tuning of Qwen3-30B-FP8.

**Implementation**:
```python
# lift_sys/training/modal_lora_training.py

import modal
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

app = modal.App("lift-sys-lora-training")

# Large model requires A100 or H100
@app.function(
    gpu="A100",  # or "H100" for faster training
    timeout=86400,  # 24 hours
    volumes={
        "/data": modal.Volume.from_name("lift-sys-training-data"),
        "/models": modal.Volume.from_name("lift-sys-models"),
    },
    secrets=[modal.Secret.from_name("huggingface")],
)
def train_lora(
    model_name: str = "Qwen/Qwen3-30B-FP8",
    train_data: str = "/data/train.jsonl",
    output_dir: str = "/models/qwen3_lift_sys_lora_v1",
    num_epochs: int = 3,
):
    """Fine-tune Qwen3 with LoRA on lift-sys data."""
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
    )

    # Load model in 8-bit for LoRA
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        load_in_8bit=True,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA config (targeting attention layers)
    lora_config = LoraConfig(
        r=16,  # LoRA rank
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        evaluation_strategy="steps",
        eval_steps=100,
    )

    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    trainer.train()

    # Save LoRA weights
    model.save_pretrained(output_dir)
    print(f"✅ LoRA weights saved to {output_dir}")
```

**Deliverables**:
- `lift_sys/training/modal_lora_training.py` (~400 lines)
- Modal volume setup scripts
- Training monitoring dashboard
- Cost estimation calculator

**Dependencies**: lift-sys-210

**Success Criteria**:
- Training runs successfully on Modal
- Can monitor training progress
- LoRA weights saved correctly

---

### lift-sys-212: Execute LoRA Fine-Tuning (Milestone)
**Type**: milestone
**Priority**: 0 (critical path)
**Estimate**: 8-24 hours (wall time, depends on GPU)

Run the LoRA fine-tuning on Modal with A100/H100 GPU.

**Execution Plan**:
```bash
# Deploy training app to Modal
modal deploy lift_sys/training/modal_lora_training.py

# Start training
modal run lift_sys.training.modal_lora_training::train_lora \
  --model-name "Qwen/Qwen3-30B-FP8" \
  --train-data "/data/train.jsonl" \
  --num-epochs 3

# Monitor training (in separate terminal)
modal logs lift-sys-lora-training
```

**Monitoring**:
- Loss curves (training and validation)
- GPU utilization
- Memory usage
- Time remaining estimate

**Deliverables**:
- Trained LoRA weights in Modal volume
- Training logs and metrics
- Loss curves (plotted)
- Final evaluation on validation set

**Dependencies**: lift-sys-211

**Success Criteria**:
- Training completes without errors
- Validation loss decreases consistently
- Final model checkpoint saved
- Cost within budget ($200-500)

---

### lift-sys-213: Validate Fine-Tuned Model Performance
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1 day

Evaluate fine-tuned model vs. base model on held-out test set.

**Evaluation Protocol**:
1. Load base Qwen3-30B-FP8
2. Load fine-tuned Qwen3-30B-FP8 + LoRA
3. Run both on test set (500 examples)
4. Compare: success rate, error types, quality scores
5. Run on Phase 2/3 tests (18 tests)
6. Analyze improvements and regressions

**Metrics**:
- Success rate (base vs. fine-tuned)
- Compilation rate
- Execution rate
- Quality score distribution
- Error type frequency
- Category-wise performance

**Deliverables**:
- `training_data/evaluation_report.md`
- Performance comparison charts
- Error analysis
- Recommendation: deploy or iterate

**Dependencies**: lift-sys-212

**Success Criteria**:
- Fine-tuned model shows improvement
- Target: 90% → 95%+ success rate
- No major regressions
- Clear documentation of results

---

## Phase 5: Integration - Deploy Fine-Tuned Model

### lift-sys-214: Integrate LoRA Weights with Modal Inference
**Type**: task
**Priority**: 0 (critical path)
**Estimate**: 1 day

Modify Modal inference app to load LoRA weights on top of base model.

**Current**: `lift_sys/inference/modal_app.py` loads base Qwen3-30B-FP8
**New**: Load base model + merge LoRA weights for inference

**Implementation**:
```python
# lift_sys/inference/modal_app.py (modified)

@app.function(gpu="L40S")
def load_model_with_lora(
    base_model: str = "Qwen/Qwen3-30B-FP8",
    lora_weights: str = "/models/qwen3_lift_sys_lora_v1",
):
    """Load base model with LoRA weights."""
    from peft import PeftModel

    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
    )

    # Load and merge LoRA weights
    model = PeftModel.from_pretrained(model, lora_weights)
    model = model.merge_and_unload()  # Merge for faster inference

    return model

# Update inference function to use fine-tuned model
@app.function(gpu="L40S")
def generate_ir_with_finetuned_model(prompt: str) -> IR:
    """Generate IR using fine-tuned model."""
    # Use loaded model with LoRA weights
    pass
```

**Deliverables**:
- Modified `lift_sys/inference/modal_app.py`
- Model versioning system (base vs. fine-tuned)
- A/B testing capability (compare models)
- Performance benchmarks (latency impact)

**Dependencies**: lift-sys-213

**Success Criteria**:
- Fine-tuned model loads correctly
- Inference works end-to-end
- Latency acceptable (<2s increase)
- Can switch between models

---

### lift-sys-215: Implement A/B Testing Framework
**Type**: task
**Priority**: 1 (important)
**Estimate**: 1 day

Allow comparing base model vs. fine-tuned model in production.

**Implementation**:
```python
# lift_sys/inference/ab_testing.py

class ModelABTest:
    """Compare base vs. fine-tuned model."""

    def __init__(self):
        self.base_model = "qwen3-30b-fp8-base"
        self.finetuned_model = "qwen3-30b-fp8-liftsys-v1"

    async def run_comparison(
        self,
        test_cases: list[str],
        model_a: str = None,
        model_b: str = None,
    ) -> ComparisonReport:
        """Run both models on test cases and compare."""
        results_a = []
        results_b = []

        for prompt in test_cases:
            # Run both models in parallel
            ir_a, ir_b = await asyncio.gather(
                self.generate_ir(prompt, model_a or self.base_model),
                self.generate_ir(prompt, model_b or self.finetuned_model),
            )

            results_a.append(ir_a)
            results_b.append(ir_b)

        # Compare results
        return self.compare_results(results_a, results_b)
```

**Deliverables**:
- `lift_sys/inference/ab_testing.py` (~200 lines)
- CLI for running comparisons
- Visualization of results
- Statistical significance testing

**Dependencies**: lift-sys-214

**Success Criteria**:
- Can compare any two models
- Clear winner identification
- Statistical rigor in comparisons

---

### lift-sys-216: Update Provider System for Fine-Tuned Model
**Type**: task
**Priority**: 1 (important)
**Estimate**: 0.5 days

Modify `lift_sys/providers/modal_provider.py` to use fine-tuned model by default.

**Changes**:
1. Add model version configuration
2. Update default to fine-tuned model
3. Keep base model as fallback option
4. Update documentation

**Deliverables**:
- Modified `lift_sys/providers/modal_provider.py`
- Configuration options for model selection
- Updated `docs/MODAL_REFERENCE.md`

**Dependencies**: lift-sys-214

**Success Criteria**:
- Fine-tuned model used by default
- Can easily switch models
- Backwards compatible

---

## Phase 6: Evaluation & Iteration

### lift-sys-217: Run Comprehensive Evaluation on Expanded Test Suite
**Type**: milestone
**Priority**: 0 (critical path)
**Estimate**: 4 hours

Execute complete evaluation: base vs. fine-tuned on 300+ test suite.

**Evaluation Plan**:
```bash
# Run Phase 2 tests (10 tests)
uv run python run_nontrivial_tests.py phase2 --model finetuned

# Run Phase 3 tests (18 tests)
uv run python run_nontrivial_tests.py phase3 --model finetuned

# Run synthetic tests (300+ tests)
uv run pytest tests/synthetic/phase_synthetic.py --model finetuned

# Compare all results vs. baseline
uv run python -m lift_sys.evaluation.compare_models \
  --baseline results/baseline.json \
  --finetuned results/finetuned.json \
  --output results/comparison_report.md
```

**Metrics**:
- Overall success rate (target: 95%+)
- Category-wise performance
- Difficulty-wise performance
- Improvement by error type
- Cost per request (fine-tuned vs. base)
- Latency (fine-tuned vs. base)

**Deliverables**:
- `results/comprehensive_evaluation.md`
- Success rate comparison charts
- Error analysis
- Cost/performance tradeoffs
- Recommendation for production

**Dependencies**: lift-sys-209 (test suite), lift-sys-216 (integration)

**Success Criteria**:
- 95%+ success rate achieved (target)
- Clear improvement over baseline
- No major regressions
- Acceptable cost/latency tradeoffs

---

### lift-sys-218: Analyze Failure Modes and Iterate
**Type**: task
**Priority**: 1 (important)
**Estimate**: 2 days

Deep dive into remaining failures, identify patterns, plan next iteration.

**Analysis**:
1. Categorize all failures
2. Identify common patterns
3. Determine root causes
4. Evaluate fixes:
   - More training data in weak areas?
   - Prompt engineering improvements?
   - Additional fine-tuning?
   - AST repair patterns?
   - IR interpreter validation?

**Deliverables**:
- `docs/FAILURE_MODE_ANALYSIS_V1.md`
- Categorized failure taxonomy
- Root cause analysis
- Next iteration plan
- Priority ranking for fixes

**Dependencies**: lift-sys-217

**Success Criteria**:
- All failures categorized
- Clear root causes identified
- Actionable improvement plan

---

### lift-sys-219: Document SWE-smith Integration Results
**Type**: task
**Priority**: 1 (important)
**Estimate**: 1 day

Comprehensive documentation of the entire integration process and results.

**Content**:
1. **Executive Summary**
   - What we built
   - Key results (success rate improvement)
   - Cost and effort
   - Lessons learned

2. **Methodology**
   - SWE-smith concepts applied
   - lift-sys adaptations
   - Pipeline architecture

3. **Results**
   - Quantitative metrics
   - Qualitative improvements
   - Comparison to baselines

4. **Integration Guide**
   - How to use fine-tuned model
   - How to regenerate data
   - How to retrain model

5. **Future Work**
   - Remaining challenges
   - Next improvements
   - Research directions

**Deliverables**:
- `docs/SWE_SMITH_INTEGRATION_RESULTS.md` (50+ pages)
- Training data generation guide
- Model fine-tuning guide
- Best practices document

**Dependencies**: lift-sys-217, lift-sys-218

**Success Criteria**:
- Comprehensive documentation
- Reproducible methodology
- Clear results communication

---

## Phase 7: Continuous Improvement Loop

### lift-sys-220: Implement Continuous Data Collection
**Type**: task
**Priority**: 2 (nice to have)
**Estimate**: 1.5 days

Set up system to continuously collect new training examples.

**Goal**: Keep training data fresh with new GitHub repositories and patterns

**Implementation**:
```python
# lift_sys/data_synthesis/continuous_collector.py

class ContinuousDataCollector:
    """Continuously collect new training examples."""

    def schedule_collection(self, frequency: str = "weekly"):
        """Run data collection on schedule."""
        # Use Modal cron jobs
        pass

    def collect_from_new_repos(self, min_date: datetime):
        """Collect from recently created/updated repos."""
        pass

    def identify_weak_areas(self):
        """Find categories with low success rates."""
        pass

    def targeted_collection(self, category: str, target: int = 100):
        """Collect examples for specific weak areas."""
        pass
```

**Deliverables**:
- `lift_sys/data_synthesis/continuous_collector.py` (~300 lines)
- Modal cron job configuration
- Automated retraining triggers
- Data drift detection

**Dependencies**: lift-sys-217

**Success Criteria**:
- Automated weekly data collection
- Targeted collection for weak areas
- Minimal manual intervention

---

### lift-sys-221: Implement Model Versioning and Registry
**Type**: task
**Priority**: 2 (nice to have)
**Estimate**: 1 day

Track model versions, performance, and enable easy rollback.

**Implementation**:
```python
# lift_sys/training/model_registry.py

class ModelRegistry:
    """Track model versions and performance."""

    def register_model(
        self,
        name: str,
        version: str,
        lora_weights_path: str,
        metrics: dict,
        training_config: dict,
    ):
        """Register new model version."""
        pass

    def compare_versions(self, v1: str, v2: str) -> ComparisonReport:
        """Compare two model versions."""
        pass

    def get_best_model(self, metric: str = "success_rate") -> str:
        """Get best performing model."""
        pass

    def rollback_to_version(self, version: str):
        """Rollback to previous model version."""
        pass
```

**Deliverables**:
- `lift_sys/training/model_registry.py` (~200 lines)
- Model metadata database
- Version comparison tools
- Rollback mechanism

**Dependencies**: lift-sys-216

**Success Criteria**:
- All models tracked
- Easy version comparison
- One-command rollback

---

### lift-sys-222: Set Up Retraining Pipeline
**Type**: task
**Priority**: 2 (nice to have)
**Estimate**: 1 day

Automate periodic retraining with new data.

**Implementation**:
```python
# lift_sys/training/retraining_pipeline.py

class RetrainingPipeline:
    """Automated model retraining."""

    def should_retrain(self) -> bool:
        """Determine if retraining is needed."""
        # Check: enough new data?
        # Check: performance degradation?
        # Check: time since last training?
        pass

    async def retrain(self):
        """Execute full retraining pipeline."""
        # 1. Prepare new training data
        # 2. Merge with existing data
        # 3. Train new model version
        # 4. Evaluate on test set
        # 5. Register if better than current
        # 6. Deploy if approved
        pass
```

**Deliverables**:
- `lift_sys/training/retraining_pipeline.py` (~300 lines)
- Automated retraining triggers
- Performance-based deployment
- Notification system

**Dependencies**: lift-sys-220, lift-sys-221

**Success Criteria**:
- Automated retraining when needed
- Performance-gated deployment
- Full audit trail

---

## Summary: Integration Points with Existing lift-sys Design

### Synergies with Current Architecture

**1. IR Design (Preserved & Enhanced)**
- SWE-smith data generation uses existing IR format
- Fine-tuned model better understands IR structure
- Real-world examples validate IR expressiveness
- **Impact**: IR becomes more robust through exposure to real code

**2. Modal Infrastructure (Extended)**
- Existing Modal setup handles training/inference
- LoRA fine-tuning deployed on Modal
- Data pipeline uses Modal for parallel processing
- **Impact**: Leverages existing infra investment

**3. XGrammar Constraints (Complementary)**
- Fine-tuned model still uses XGrammar for syntactic correctness
- Better base model + constraints = higher quality
- Semantic understanding + syntactic constraints = optimal
- **Impact**: Syntactic guarantees + semantic improvements

**4. Reverse Mode (Core Enabler)**
- Reverse mode enables SWE-smith-style data extraction
- Batch processing enhancement benefits all use cases
- **Impact**: Reverse mode becomes training data engine

**5. Validation Infrastructure (Leveraged)**
- Existing assertion checker validates training data
- AST repair patterns still useful post-training
- Execution validation shared between data gen and testing
- **Impact**: Validation investments pay double dividends

**6. Forward Mode Pipeline (Enhanced)**
- Fine-tuned model improves IR generation quality
- Code generation also improved through training
- End-to-end success rate increase
- **Impact**: Core value proposition strengthened

### What's New vs. What's Enhanced

**New Components (SWE-smith-Inspired)**:
- GitHub data scraper
- Batch lifter for parallel processing
- Prompt synthesis from code
- Execution-based validator
- LoRA fine-tuning infrastructure
- Model registry and versioning
- Continuous data collection
- Retraining pipeline

**Enhanced Components (lift-sys Existing)**:
- Reverse mode: batch processing, performance
- Modal setup: training workloads, larger models
- Test infrastructure: 300+ generated tests
- Validation: shared with data generation
- Providers: model versioning, A/B testing

### Success Metrics

**Data Generation**:
- ✅ 5,000-10,000 training examples (vs. 18 current)
- ✅ 300-500 test cases (vs. 18 current)
- ✅ Real-world code patterns from GitHub

**Model Performance**:
- 🎯 **Target: 95%+ success rate** (vs. 80-90% current)
- 🎯 +5-15% absolute improvement
- 🎯 SWE-smith precedent: +32% relative improvement

**Cost Efficiency**:
- Training: $200-500 one-time
- Inference: Similar or better (merged LoRA)
- Development velocity: 2-3x faster

**Timeline**:
- Phase 1-2: 2-3 weeks (data generation)
- Phase 3: 1 week (test expansion)
- Phase 4: 2 weeks (fine-tuning)
- Phase 5: 1 week (integration)
- Phase 6-7: 1-2 weeks (evaluation & iteration)
- **Total: 7-9 weeks** for complete implementation

### Risk Mitigation

**High-Risk Items**:
- lift-sys-206: Initial dataset generation (could fail if reverse mode quality low)
  - **Mitigation**: Small-scale pilot (100 examples) before full run
- lift-sys-212: LoRA fine-tuning (might not improve performance)
  - **Mitigation**: Validate on small dataset first, can abort
- lift-sys-217: Comprehensive evaluation (might not hit 95% target)
  - **Mitigation**: 90% still valuable, iterate in Phase 6

**Medium-Risk Items**:
- GitHub API rate limits
  - **Mitigation**: Use multiple tokens, spread collection over time
- Training costs exceed budget
  - **Mitigation**: Start with smaller model/dataset, scale if promising

**Low-Risk Items**:
- Most tasks leverage existing, proven infrastructure
- SWE-smith methodology has published success (+32%)
- Clear checkpoints allow early termination if not working

---

## Dependencies (Bead Chain)

```
Foundation Phase:
lift-sys-200 (design) → 201 (scraper) → 202 (batch lifter)
                                      → 203 (prompt synthesis)

Data Generation Phase:
[201, 202, 203] → 204 (pipeline) → 205 (validator) → 206 (MILESTONE: generate dataset)

Test Expansion Phase (parallel):
207 (design) → 208 (implement) → 209 (validate)

Fine-Tuning Phase:
206 → 210 (prep data) → 211 (modal setup) → 212 (MILESTONE: train) → 213 (validate)

Integration Phase:
213 → 214 (integrate lora) → 215 (a/b testing) → 216 (update providers)

Evaluation Phase:
[209, 216] → 217 (MILESTONE: comprehensive eval) → 218 (analyze failures) → 219 (document)

Continuous Improvement (optional):
217 → 220 (continuous collection) → 221 (model registry) → 222 (retraining)
```

---

## Estimated Timeline & Resources

**Week 1-2**: Foundation + Data Generation (lift-sys-200 to lift-sys-206)
- **Effort**: 8-10 days engineering
- **Cost**: $50-100 (GitHub API, Modal compute)
- **Deliverable**: 5,000-10,000 validated training examples

**Week 3**: Test Expansion (lift-sys-207 to lift-sys-209)
- **Effort**: 3-4 days engineering
- **Cost**: Minimal
- **Deliverable**: 300-500 test cases

**Week 4-5**: Fine-Tuning (lift-sys-210 to lift-sys-213)
- **Effort**: 5-6 days engineering + 8-24h training
- **Cost**: $200-500 (GPU training)
- **Deliverable**: Fine-tuned Qwen3-30B-FP8 model

**Week 6**: Integration (lift-sys-214 to lift-sys-216)
- **Effort**: 2-3 days engineering
- **Cost**: Minimal
- **Deliverable**: Deployed fine-tuned model

**Week 7**: Evaluation (lift-sys-217 to lift-sys-219)
- **Effort**: 4-5 days engineering
- **Cost**: $50-100 (evaluation runs)
- **Deliverable**: Comprehensive results & documentation

**Week 8-9** (optional): Continuous Improvement (lift-sys-220 to lift-sys-222)
- **Effort**: 3-4 days engineering
- **Cost**: Minimal
- **Deliverable**: Automated data collection & retraining

**Total**: 7-9 weeks, $300-700, 25-35 engineering days

---

## Conclusion

This plan integrates SWE-smith's proven synthetic data generation and fine-tuning methodologies with lift-sys's existing strengths:

**From SWE-smith**:
- Large-scale synthetic data generation (52k examples precedent)
- Execution-based validation (quality filtering)
- Model fine-tuning methodology (+32% improvement precedent)
- Programmatic test generation (task synthesis)

**From lift-sys** (preserved & enhanced):
- Formal IR specification language
- Modal inference infrastructure
- XGrammar constrained generation
- Reverse mode for code analysis
- Validation and assertion checking

**Expected Outcome**: Break through 80-90% plateau to achieve 95%+ success rate through specialized model training on real-world code patterns.

**Next Step**: Review plan, prioritize beads, begin with lift-sys-200 (architecture design).
