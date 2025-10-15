# Comprehensive Test Plan - Week 2, Day 3/4

**Purpose**: Validate lift-sys with non-trivial, realistic test cases
**Goal**: Measure success rates across different complexity levels and categories

---

## Test Categories

### Category 1: Control Flow Variations (Priority 1)
**Rationale**: Just fixed indentation bug - need thorough validation

1. **if-elif-else chain** ⭐ HIGH PRIORITY
   - Prompt: "Create a function that returns letter grade (A/B/C/D/F) based on numeric score"
   - Tests: `grade(95)→A`, `grade(85)→B`, `grade(75)→C`, `grade(65)→D`, `grade(55)→F`
   - Complexity: Medium
   - Tests: Multiple elif statements

2. **nested if statements**
   - Prompt: "Create a function that checks if a number is positive, negative, or zero, and if positive whether it's even or odd"
   - Tests: `classify(10)→"positive even"`, `classify(7)→"positive odd"`, `classify(-5)→"negative"`, `classify(0)→"zero"`
   - Complexity: Medium-Hard
   - Tests: Nested control flow

3. **early return pattern**
   - Prompt: "Create a function that validates a password: must be at least 8 chars, contain a number, and contain uppercase. Return error message or 'valid'"
   - Tests: `validate_password("abc")→"too short"`, `validate_password("abcdefgh")→"no number"`, `validate_password("abcdefg1")→"no uppercase"`, `validate_password("Abcdefg1")→"valid"`
   - Complexity: Medium
   - Tests: Multiple early returns

### Category 2: List Operations (Priority 1)
**Rationale**: Core Python functionality, common in real code

4. **list filtering** ⭐ HIGH PRIORITY
   - Prompt: "Create a function that returns only the even numbers from a list"
   - Tests: `filter_even([1,2,3,4,5,6])→[2,4,6]`, `filter_even([1,3,5])→[]`, `filter_even([])→[]`
   - Complexity: Medium
   - Tests: List comprehension or iteration

5. **list aggregation**
   - Prompt: "Create a function that calculates the average of a list of numbers, returning 0 for empty list"
   - Tests: `average([1,2,3,4,5])→3.0`, `average([10])→10.0`, `average([])→0`
   - Complexity: Medium
   - Tests: Loop + division + edge case

6. **list search**
   - Prompt: "Create a function that finds the index of a value in a list, returning -1 if not found"
   - Tests: `find_index([10,20,30], 20)→1`, `find_index([10,20,30], 40)→-1`, `find_index([], 10)→-1`
   - Complexity: Medium
   - Tests: Iteration with early return

### Category 3: String Manipulation (Priority 2)
**Rationale**: Very common in real applications

7. **string parsing** ⭐ HIGH PRIORITY
   - Prompt: "Create a function that counts the number of words in a string (split by spaces)"
   - Tests: `count_words("hello world")→2`, `count_words("one")→1`, `count_words("")→0`, `count_words("  spaces  ")→1`
   - Complexity: Easy-Medium
   - Tests: String methods + edge cases

8. **string transformation**
   - Prompt: "Create a function that capitalizes the first letter of each word in a string"
   - Tests: `title_case("hello world")→"Hello World"`, `title_case("a")→"A"`, `title_case("")→""`
   - Complexity: Medium
   - Tests: String iteration + transformation

9. **string validation**
   - Prompt: "Create a function that checks if a string is a valid email (contains @ and . after @)"
   - Tests: `is_email("user@example.com")→True`, `is_email("user@example")→False`, `is_email("userexample.com")→False`
   - Complexity: Medium
   - Tests: String searching + validation logic

### Category 4: Mathematical Operations (Priority 2)
**Rationale**: Test numeric handling and algorithms

10. **factorial**
    - Prompt: "Create a function that calculates the factorial of a non-negative integer"
    - Tests: `factorial(5)→120`, `factorial(0)→1`, `factorial(1)→1`, `factorial(3)→6`
    - Complexity: Medium
    - Tests: Loop or recursion

11. **fibonacci**
    - Prompt: "Create a function that returns the nth Fibonacci number (0-indexed)"
    - Tests: `fibonacci(0)→0`, `fibonacci(1)→1`, `fibonacci(5)→5`, `fibonacci(10)→55`
    - Complexity: Medium-Hard
    - Tests: Iteration or recursion

12. **prime checker**
    - Prompt: "Create a function that checks if a number is prime"
    - Tests: `is_prime(7)→True`, `is_prime(4)→False`, `is_prime(1)→False`, `is_prime(2)→True`
    - Complexity: Medium
    - Tests: Loop with early termination

### Category 5: Type Operations (Priority 3)
**Rationale**: Type conversion and checking

13. **type conversion**
    - Prompt: "Create a function that converts a string to an integer, returning 0 if conversion fails"
    - Tests: `safe_int("123")→123`, `safe_int("abc")→0`, `safe_int("")→0`
    - Complexity: Medium
    - Tests: Try/except or validation

14. **type checking**
    - Prompt: "Create a function that returns the type of a value as a string ('int', 'str', 'list', or 'other')"
    - Tests: `get_type(5)→"int"`, `get_type("hi")→"str"`, `get_type([1,2])→"list"`, `get_type(3.14)→"other"`
    - Complexity: Medium
    - Tests: isinstance checks

### Category 6: Data Structure Operations (Priority 3)
**Rationale**: Working with dictionaries and complex structures

15. **dictionary manipulation**
    - Prompt: "Create a function that merges two dictionaries, with values from the second overwriting the first"
    - Tests: `merge_dicts({'a':1}, {'b':2})→{'a':1,'b':2}`, `merge_dicts({'a':1}, {'a':2})→{'a':2}`
    - Complexity: Medium
    - Tests: Dictionary operations

16. **min/max finding**
    - Prompt: "Create a function that returns both the minimum and maximum values from a list as a tuple"
    - Tests: `min_max([1,5,3])→(1,5)`, `min_max([7])→(7,7)`, `min_max([3,1,4,1,5])→(1,5)`
    - Complexity: Medium
    - Tests: Tuple return + iteration

### Category 7: Edge Case Handling (Priority 2)
**Rationale**: Robustness testing

17. **null/empty handling** ⭐ HIGH PRIORITY
    - Prompt: "Create a function that returns the first element of a list, or None if the list is empty"
    - Tests: `first([1,2,3])→1`, `first([])→None`, `first(["a"])→"a"`
    - Complexity: Easy
    - Tests: Edge case handling

18. **boundary conditions**
    - Prompt: "Create a function that clamps a value between a min and max (inclusive)"
    - Tests: `clamp(5, 0, 10)→5`, `clamp(-5, 0, 10)→0`, `clamp(15, 0, 10)→10`
    - Complexity: Medium
    - Tests: Multiple comparisons

---

## Test Suite Organization

### Suite 1: Quick Validation (5 tests, ~80s)
**Purpose**: Rapid smoke test after fixes

1. Letter grade (if-elif-else)
2. Filter even (list operations)
3. Count words (string manipulation)
4. Null/empty handling (edge cases)
5. Max of two (regression test)

**Expected success**: 90%+ (4-5/5)

### Suite 2: Medium Coverage (10 tests, ~160s)
**Purpose**: Comprehensive validation

- All from Suite 1 +
- Nested if statements
- List search
- Title case
- Factorial
- Type checking

**Expected success**: 80%+ (8-10/10)

### Suite 3: Full Coverage (18 tests, ~290s)
**Purpose**: Complete validation

- All tests above
- Expected success: 75%+ (14-18/18)

---

## Success Criteria

### By Category
| Category | Tests | Expected Success |
|----------|-------|------------------|
| Control Flow | 3 | 90%+ (if-elif-else crucial) |
| List Operations | 3 | 85%+ |
| String Manipulation | 3 | 85%+ |
| Mathematical | 3 | 80%+ |
| Type Operations | 2 | 75%+ |
| Data Structures | 2 | 70%+ |
| Edge Cases | 2 | 90%+ |

### By Complexity
| Complexity | Tests | Expected Success |
|------------|-------|------------------|
| Easy | 4 | 95%+ |
| Medium | 11 | 80%+ |
| Medium-Hard | 3 | 70%+ |

### Overall Target
**80% overall success rate** (14+/18 tests)

---

## Priorities for Day 3/4

### Phase 1: High Priority Tests (⭐ 5 tests)
Run these first to validate critical functionality:
1. Letter grade (if-elif-else)
2. Filter even (list ops)
3. Count words (string)
4. Null/empty handling (edge case)
5. Nested if (control flow)

**Time**: ~80 seconds
**Decision point**: If <80% success, investigate before continuing

### Phase 2: Medium Coverage (+5 tests)
Expand to 10 tests total:
6. List search
7. Title case
8. Factorial
9. Type checking
10. Boundary conditions (clamp)

**Time**: ~80 seconds
**Decision point**: If <75% success on new tests, pause and analyze

### Phase 3: Full Coverage (+8 tests)
Complete all 18 tests
**Time**: ~130 seconds

---

## Test Implementation Plan

### Step 1: Create test definitions file
File: `test_cases_nontrivial.py`
- Define all 18 test cases
- Include function names, prompts, test inputs/outputs
- Organize by category

### Step 2: Create test runner
File: `run_nontrivial_tests.py`
- Run tests in phases (5 → 10 → 18)
- Collect metrics per category
- Generate detailed report

### Step 3: Run Phase 1 (5 tests)
- Quick validation of critical functionality
- ~80 seconds

### Step 4: Analyze and Continue
- If Phase 1 ≥80% → Continue to Phase 2
- If Phase 1 <80% → Investigate failures

### Step 5: Complete Full Suite
- Run all 18 tests
- Generate comprehensive report

---

## Expected Findings

### Likely to Work Well
- Simple control flow (if-elif-else)
- Basic list operations (filter, search)
- String methods (split, capitalize)
- Edge case handling

### Likely to Have Issues
- Nested control flow (if inside if)
- Complex loops (fibonacci with iteration)
- Try/except blocks (not in schema)
- Dictionary operations (less common in simple prompts)

### Discovery Opportunities
- Which complexity level causes success rate to drop?
- Do certain categories consistently fail?
- Are there patterns in LLM-generated code quality?

---

## Documentation Plan

After running tests, create:
1. `TEST_RESULTS_NONTRIVIAL.md` - Detailed results by category
2. Update `PERFORMANCE_METRICS.md` - Add non-trivial test data
3. `KNOWN_LIMITATIONS.md` - Document failure patterns

---

## Timeline

- **Hour 1**: Create test definitions + runner (~60 min)
- **Hour 2**: Run Phase 1 (5 tests) + analyze (~30 min)
- **Hour 2**: Run Phase 2 (10 tests) + analyze (~30 min)
- **Hour 3**: Run Phase 3 (18 tests) + document (~60 min)

**Total**: ~3 hours for complete validation

---

## Success Metrics

At end of testing, we should know:
- ✅ Real-world success rate on non-trivial prompts
- ✅ Which categories work well vs. struggle
- ✅ Which complexity level is the limit
- ✅ Whether our fixes generalize beyond simple tests
- ✅ Confidence level for Week 3 demo

**Target**: 80% overall success rate (14+/18 tests)
**Acceptable**: 70% overall (13+/18 tests)
**Needs work**: <70% (analyze and fix issues)
