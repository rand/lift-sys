# SWE-smith Integration Beads - Detailed Task List

## lift-sys-200: Design GitHub Data Collection Architecture
**Type**: task
**Priority**: 0
**Dependencies**:

Design the system for collecting training data from GitHub repositories. Define repository selection criteria, function extraction strategy, data storage format, rate limiting, and quality metrics.

**Deliverables**:
- docs/SYNTHETIC_DATA_ARCHITECTURE.md
- Schema definitions for training data format
- Repository selection criteria

**Estimate**: 4 hours

---

## lift-sys-201: Implement GitHub Repository Scraper
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-200

Create scraper that clones and analyzes top Python repositories from GitHub. Fetches repos with good licenses, clones them, extracts functions with metadata.

**Deliverables**:
- lift_sys/data_synthesis/github_scraper.py (~300 lines)
- Unit tests for scraper
- CLI command

**Estimate**: 1 day

---

## lift-sys-202: Enhance Reverse Mode for Batch Processing
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-201

Optimize reverse mode to process thousands of functions efficiently with parallelization and caching.

**Deliverables**:
- lift_sys/data_synthesis/batch_lifter.py (~400 lines)
- Parallel processing with asyncio
- Progress tracking and error handling
- Performance tests (100+ functions/minute target)

**Estimate**: 2 days

---

## lift-sys-203: Implement Prompt Synthesis from Code
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-201

Generate natural language prompts from function signatures, docstrings, and test cases.

**Deliverables**:
- lift_sys/data_synthesis/prompt_synthesizer.py (~300 lines)
- Support for common docstring formats
- Fallback strategies
- Examples of generated prompts

**Estimate**: 1 day

---

## lift-sys-204: Implement Training Data Pipeline
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-201,lift-sys-202,lift-sys-203

Orchestrate end-to-end pipeline from GitHub repos to training data. Combines scraping, lifting, prompt synthesis, and validation.

**Deliverables**:
- lift_sys/data_synthesis/pipeline.py (~500 lines)
- Progress tracking with rich console
- Checkpoint/resume capability
- Error reporting and statistics

**Estimate**: 2 days

---

## lift-sys-205: Implement SWE-smith-Style Execution Validator
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-204

Validate training examples through execution, keeping only working examples like SWE-smith does.

**Deliverables**:
- lift_sys/data_synthesis/execution_validator.py (~300 lines)
- Modal-based test execution
- Parallel validation (10+ examples/second)
- Detailed failure logging

**Estimate**: 1.5 days

---

## lift-sys-206: Run Initial Dataset Generation
**Type**: milestone
**Priority**: 0
**Dependencies**: lift-sys-205

Execute the pipeline to generate 5,000-10,000 validated training examples from GitHub.

**Deliverables**:
- training_data/synthetic_v1.jsonl (5,000-10,000 examples)
- training_data/generation_report.md
- Quality distribution analysis
- Error report

**Estimate**: 12 hours wall time

---

## lift-sys-207: Design Template-Based Test Generator
**Type**: task
**Priority**: 1
**Dependencies**:

Design systematic test generation following SWE-smith's task synthesis approach. Create template taxonomy and variation strategy.

**Deliverables**:
- docs/TEST_GENERATION_DESIGN.md
- Template taxonomy
- Variation strategy

**Estimate**: 0.5 days

---

## lift-sys-208: Implement Programmatic Test Generator
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-207

Implement test generator that creates 300-500 tests from templates.

**Deliverables**:
- lift_sys/testing/test_generator.py (~600 lines)
- 300-500 generated tests
- Test suite validation
- CLI command

**Estimate**: 2 days

---

## lift-sys-209: Validate and Integrate Generated Test Suite
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-208

Run generated tests, fix issues, integrate into CI pipeline.

**Deliverables**:
- tests/synthetic/phase_synthetic.py (300-500 tests)
- Validation report
- CI integration
- Baseline performance measurement

**Estimate**: 1 day

---

## lift-sys-210: Prepare Training Data for LoRA Fine-Tuning
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-206

Convert synthetic dataset to format required for LoRA fine-tuning. Split into train/val/test sets.

**Deliverables**:
- lift_sys/training/data_prep.py (~200 lines)
- training_data/train.jsonl (4,000 examples)
- training_data/val.jsonl (500 examples)
- training_data/test.jsonl (500 examples)
- Data statistics report

**Estimate**: 1 day

---

## lift-sys-211: Set Up Modal LoRA Training Infrastructure
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-210

Create Modal app for LoRA fine-tuning of Qwen3-30B-FP8 on A100/H100 GPU.

**Deliverables**:
- lift_sys/training/modal_lora_training.py (~400 lines)
- Modal volume setup scripts
- Training monitoring dashboard
- Cost estimation calculator

**Estimate**: 1.5 days

---

## lift-sys-212: Execute LoRA Fine-Tuning
**Type**: milestone
**Priority**: 0
**Dependencies**: lift-sys-211

Run the LoRA fine-tuning on Modal with A100/H100 GPU. Train for 3 epochs on synthetic dataset.

**Deliverables**:
- Trained LoRA weights in Modal volume
- Training logs and metrics
- Loss curves
- Final evaluation on validation set

**Estimate**: 8-24 hours wall time

---

## lift-sys-213: Validate Fine-Tuned Model Performance
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-212

Evaluate fine-tuned model vs base model on held-out test set. Compare success rates, error types, quality scores.

**Deliverables**:
- training_data/evaluation_report.md
- Performance comparison charts
- Error analysis
- Recommendation for deployment

**Estimate**: 1 day

---

## lift-sys-214: Integrate LoRA Weights with Modal Inference
**Type**: task
**Priority**: 0
**Dependencies**: lift-sys-213

Modify Modal inference app to load LoRA weights on top of base model for production inference.

**Deliverables**:
- Modified lift_sys/inference/modal_app.py
- Model versioning system
- A/B testing capability
- Performance benchmarks

**Estimate**: 1 day

---

## lift-sys-215: Implement A/B Testing Framework
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-214

Allow comparing base model vs fine-tuned model in production with statistical significance testing.

**Deliverables**:
- lift_sys/inference/ab_testing.py (~200 lines)
- CLI for running comparisons
- Visualization of results
- Statistical significance testing

**Estimate**: 1 day

---

## lift-sys-216: Update Provider System for Fine-Tuned Model
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-214

Modify modal provider to use fine-tuned model by default with easy model switching.

**Deliverables**:
- Modified lift_sys/providers/modal_provider.py
- Configuration options
- Updated docs/MODAL_REFERENCE.md

**Estimate**: 0.5 days

---

## lift-sys-217: Run Comprehensive Evaluation on Expanded Test Suite
**Type**: milestone
**Priority**: 0
**Dependencies**: lift-sys-209,lift-sys-216

Execute complete evaluation of base vs fine-tuned on 300+ test suite. Target 95%+ success rate.

**Deliverables**:
- results/comprehensive_evaluation.md
- Success rate comparison charts
- Error analysis
- Cost/performance tradeoffs
- Recommendation for production

**Estimate**: 4 hours

---

## lift-sys-218: Analyze Failure Modes and Iterate
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-217

Deep dive into remaining failures, identify patterns, plan next iteration.

**Deliverables**:
- docs/FAILURE_MODE_ANALYSIS_V1.md
- Categorized failure taxonomy
- Root cause analysis
- Next iteration plan

**Estimate**: 2 days

---

## lift-sys-219: Document SWE-smith Integration Results
**Type**: task
**Priority**: 1
**Dependencies**: lift-sys-217,lift-sys-218

Comprehensive documentation of entire integration process and results.

**Deliverables**:
- docs/SWE_SMITH_INTEGRATION_RESULTS.md (50+ pages)
- Training data generation guide
- Model fine-tuning guide
- Best practices document

**Estimate**: 1 day

---

## lift-sys-220: Implement Continuous Data Collection
**Type**: task
**Priority**: 2
**Dependencies**: lift-sys-217

Set up system to continuously collect new training examples from GitHub on a schedule.

**Deliverables**:
- lift_sys/data_synthesis/continuous_collector.py (~300 lines)
- Modal cron job configuration
- Automated retraining triggers
- Data drift detection

**Estimate**: 1.5 days

---

## lift-sys-221: Implement Model Versioning and Registry
**Type**: task
**Priority**: 2
**Dependencies**: lift-sys-216

Track model versions, performance, and enable easy rollback.

**Deliverables**:
- lift_sys/training/model_registry.py (~200 lines)
- Model metadata database
- Version comparison tools
- Rollback mechanism

**Estimate**: 1 day

---

## lift-sys-222: Set Up Retraining Pipeline
**Type**: task
**Priority**: 2
**Dependencies**: lift-sys-220,lift-sys-221

Automate periodic retraining with new data when performance degrades or enough new data collected.

**Deliverables**:
- lift_sys/training/retraining_pipeline.py (~300 lines)
- Automated retraining triggers
- Performance-based deployment
- Notification system

**Estimate**: 1 day
