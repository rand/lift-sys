def filter_even_numbers(input_list: list[int]) -> list[int]:
    """Create a function that returns a new list containing only the even numbers from the input list.

    The function should filter out odd numbers and return a list of even numbers.

    Args:
        input_list: The list of integers to be filtered.

    Returns:
        list[int]
    """
    # Algorithm: The function iterates over the input list, checks if each number is even, and if so, appends it to a new list. The new list is then returned.

    # Initialize an empty list to store even numbers
    filtered_list = []
    # Iterate over each number in the input list
    for number in input_list:
    # Check if the number is even
    if number % 2 == 0:
        # Add the even number to the filtered list
        filtered_list.append(number)
    # Return the list of even numbers
    return filtered_list
