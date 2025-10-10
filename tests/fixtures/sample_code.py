"""Sample Python code for testing reverse mode lifting."""


def factorial(n):
    """Calculate factorial of n recursively."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def is_prime(n):
    """Check if n is a prime number."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def binary_search(arr, target):
    """Perform binary search on sorted array."""
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def validate_input(data):
    """Validate input data with security checks."""
    if data is None:
        raise ValueError("Data cannot be None")

    if not isinstance(data, (list, tuple)):
        raise TypeError("Data must be a list or tuple")

    if len(data) == 0:
        raise ValueError("Data cannot be empty")

    return True
