"""Human-written TypeScript code baselines for quality comparison.

These baselines represent idiomatic, high-quality TypeScript code written by
experienced developers. They serve as the gold standard for comparing
generated code quality.

Each baseline includes:
- Well-documented functions with TSDoc comments
- Proper type annotations
- Modern TypeScript syntax (const/let, arrow functions, etc.)
- Idiomatic patterns and best practices
- Clear, concise implementations
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TypeScriptBaseline:
    """A human-written TypeScript code sample with metadata."""

    id: str
    category: str
    description: str
    code: str
    complexity_score: int  # Cyclomatic complexity
    lines_of_code: int
    features: list[str]  # Notable TypeScript features used


# ============================================================================
# BASIC OPERATIONS - Simple arithmetic and boolean logic
# ============================================================================

BASELINE_ADD = TypeScriptBaseline(
    id="add",
    category="basic",
    description="Add two numbers",
    code="""/**
 * Adds two numbers together.
 *
 * @param a - The first number
 * @param b - The second number
 * @returns The sum of a and b
 */
export function add(a: number, b: number): number {
  return a + b;
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "type_annotations", "export", "arrow_return"],
)

BASELINE_IS_EVEN = TypeScriptBaseline(
    id="isEven",
    category="basic",
    description="Check if number is even",
    code="""/**
 * Checks if a number is even.
 *
 * @param n - The number to check
 * @returns True if n is divisible by 2, false otherwise
 */
export function isEven(n: number): boolean {
  return n % 2 === 0;
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "type_annotations", "boolean_return", "modulo"],
)

BASELINE_MAX = TypeScriptBaseline(
    id="max",
    category="basic",
    description="Find maximum of two numbers",
    code="""/**
 * Returns the maximum of two numbers.
 *
 * @param a - The first number
 * @param b - The second number
 * @returns The larger of a and b
 */
export function max(a: number, b: number): number {
  return a > b ? a : b;
}
""",
    complexity_score=2,
    lines_of_code=3,
    features=["tsdoc", "ternary_operator", "comparison"],
)

BASELINE_ABS = TypeScriptBaseline(
    id="abs",
    category="basic",
    description="Calculate absolute value",
    code="""/**
 * Returns the absolute value of a number.
 *
 * @param n - The number
 * @returns The absolute value (distance from zero)
 */
export function abs(n: number): number {
  return n < 0 ? -n : n;
}
""",
    complexity_score=2,
    lines_of_code=3,
    features=["tsdoc", "ternary_operator", "negation"],
)

BASELINE_CLAMP = TypeScriptBaseline(
    id="clamp",
    category="basic",
    description="Clamp number to range",
    code="""/**
 * Clamps a number between a minimum and maximum value.
 *
 * @param value - The value to clamp
 * @param min - The minimum allowed value
 * @param max - The maximum allowed value
 * @returns The clamped value
 */
export function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}
""",
    complexity_score=3,
    lines_of_code=5,
    features=["tsdoc", "multiple_conditions", "early_return"],
)

# ============================================================================
# ARRAY OPERATIONS - Collections and iteration
# ============================================================================

BASELINE_SUM = TypeScriptBaseline(
    id="sum",
    category="arrays",
    description="Sum array of numbers",
    code="""/**
 * Calculates the sum of an array of numbers.
 *
 * @param numbers - Array of numbers to sum
 * @returns The sum of all numbers
 */
export function sum(numbers: Array<number>): number {
  return numbers.reduce((acc, n) => acc + n, 0);
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "array_type", "reduce", "arrow_function"],
)

BASELINE_FILTER_POSITIVE = TypeScriptBaseline(
    id="filterPositive",
    category="arrays",
    description="Filter positive numbers",
    code="""/**
 * Filters an array to include only positive numbers.
 *
 * @param numbers - Array of numbers to filter
 * @returns Array containing only positive numbers
 */
export function filterPositive(numbers: Array<number>): Array<number> {
  return numbers.filter(n => n > 0);
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "array_type", "filter", "arrow_function"],
)

BASELINE_CONTAINS = TypeScriptBaseline(
    id="contains",
    category="arrays",
    description="Check if array contains value",
    code="""/**
 * Checks if an array contains a specific value.
 *
 * @param arr - The array to search
 * @param value - The value to find
 * @returns True if value is found, false otherwise
 */
export function contains<T>(arr: Array<T>, value: T): boolean {
  return arr.includes(value);
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "generics", "array_type", "includes"],
)

BASELINE_REVERSE_ARRAY = TypeScriptBaseline(
    id="reverseArray",
    category="arrays",
    description="Reverse array",
    code="""/**
 * Returns a reversed copy of an array.
 *
 * @param arr - The array to reverse
 * @returns A new array with elements in reverse order
 */
export function reverseArray<T>(arr: Array<T>): Array<T> {
  return [...arr].reverse();
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "generics", "spread_operator", "reverse"],
)

# ============================================================================
# ASYNC OPERATIONS - Promises and async/await
# ============================================================================

BASELINE_DELAY = TypeScriptBaseline(
    id="delay",
    category="async",
    description="Delay execution",
    code="""/**
 * Creates a promise that resolves after a specified delay.
 *
 * @param ms - Number of milliseconds to delay
 * @returns Promise that resolves after delay
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "promise", "settimeout", "arrow_function"],
)

BASELINE_FETCH_DATA = TypeScriptBaseline(
    id="fetchData",
    category="async",
    description="Async fetch with error handling",
    code="""/**
 * Fetches data from a URL with error handling.
 *
 * @param url - The URL to fetch from
 * @returns Promise resolving to the fetched data
 * @throws Error if fetch fails
 */
export async function fetchData(url: string): Promise<Record<string, any>> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    throw new Error(`Failed to fetch data: ${error}`);
  }
}
""",
    complexity_score=4,
    lines_of_code=11,
    features=["tsdoc", "async_await", "error_handling", "fetch", "template_literal"],
)

# ============================================================================
# STRING OPERATIONS - Text manipulation
# ============================================================================

BASELINE_CAPITALIZE = TypeScriptBaseline(
    id="capitalize",
    category="strings",
    description="Capitalize first letter",
    code="""/**
 * Capitalizes the first letter of a string.
 *
 * @param str - The string to capitalize
 * @returns String with first letter capitalized
 */
export function capitalize(str: string): string {
  if (str.length === 0) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}
""",
    complexity_score=2,
    lines_of_code=4,
    features=["tsdoc", "string_methods", "concatenation", "guard_clause"],
)

BASELINE_COUNT_VOWELS = TypeScriptBaseline(
    id="countVowels",
    category="strings",
    description="Count vowels in string",
    code="""/**
 * Counts the number of vowels in a string.
 *
 * @param str - The string to analyze
 * @returns Number of vowels (a, e, i, o, u)
 */
export function countVowels(str: string): number {
  const vowels = new Set(['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U']);
  return [...str].filter(char => vowels.has(char)).length;
}
""",
    complexity_score=2,
    lines_of_code=4,
    features=["tsdoc", "set", "spread_operator", "filter", "arrow_function"],
)

BASELINE_IS_PALINDROME = TypeScriptBaseline(
    id="isPalindrome",
    category="strings",
    description="Check if string is palindrome",
    code="""/**
 * Checks if a string is a palindrome.
 *
 * @param str - The string to check
 * @returns True if string reads the same forwards and backwards
 */
export function isPalindrome(str: string): boolean {
  const cleaned = str.toLowerCase().replace(/[^a-z0-9]/g, '');
  return cleaned === cleaned.split('').reverse().join('');
}
""",
    complexity_score=2,
    lines_of_code=4,
    features=["tsdoc", "regex", "string_methods", "method_chaining"],
)

# ============================================================================
# OBJECT OPERATIONS - Type manipulation
# ============================================================================

BASELINE_MERGE_OBJECTS = TypeScriptBaseline(
    id="mergeObjects",
    category="objects",
    description="Merge two objects",
    code="""/**
 * Merges two objects, with properties from the second object
 * overwriting those from the first.
 *
 * @param obj1 - The first object
 * @param obj2 - The second object
 * @returns A new merged object
 */
export function mergeObjects<T extends Record<string, any>>(
  obj1: T,
  obj2: Partial<T>
): T {
  return { ...obj1, ...obj2 };
}
""",
    complexity_score=1,
    lines_of_code=3,
    features=["tsdoc", "generics", "spread_operator", "type_constraints"],
)

BASELINE_PICK_KEYS = TypeScriptBaseline(
    id="pickKeys",
    category="objects",
    description="Pick specific keys from object",
    code="""/**
 * Creates a new object with only the specified keys from the original object.
 *
 * @param obj - The source object
 * @param keys - Array of keys to pick
 * @returns A new object with only the specified keys
 */
export function pickKeys<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: Array<K>
): Pick<T, K> {
  const result: any = {};
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}
""",
    complexity_score=3,
    lines_of_code=9,
    features=["tsdoc", "generics", "utility_types", "for_of", "in_operator"],
)


# ============================================================================
# ALL BASELINES - Registry
# ============================================================================

ALL_BASELINES: dict[str, TypeScriptBaseline] = {
    "add": BASELINE_ADD,
    "isEven": BASELINE_IS_EVEN,
    "max": BASELINE_MAX,
    "abs": BASELINE_ABS,
    "clamp": BASELINE_CLAMP,
    "sum": BASELINE_SUM,
    "filterPositive": BASELINE_FILTER_POSITIVE,
    "contains": BASELINE_CONTAINS,
    "reverseArray": BASELINE_REVERSE_ARRAY,
    "delay": BASELINE_DELAY,
    "fetchData": BASELINE_FETCH_DATA,
    "capitalize": BASELINE_CAPITALIZE,
    "countVowels": BASELINE_COUNT_VOWELS,
    "isPalindrome": BASELINE_IS_PALINDROME,
    "mergeObjects": BASELINE_MERGE_OBJECTS,
    "pickKeys": BASELINE_PICK_KEYS,
}


def get_baseline(function_name: str) -> TypeScriptBaseline | None:
    """
    Get human baseline for a function by name.

    Args:
        function_name: Name of the function

    Returns:
        TypeScriptBaseline if found, None otherwise
    """
    return ALL_BASELINES.get(function_name)


def get_baselines_by_category(category: str) -> list[TypeScriptBaseline]:
    """
    Get all baselines in a specific category.

    Args:
        category: Category name (basic, arrays, async, strings, objects)

    Returns:
        List of baselines in that category
    """
    return [b for b in ALL_BASELINES.values() if b.category == category]


def list_all_baselines() -> list[str]:
    """
    Get list of all baseline function names.

    Returns:
        List of function names with baselines
    """
    return list(ALL_BASELINES.keys())
