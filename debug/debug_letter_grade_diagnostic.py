def get_letter_grade(score: int) -> str:
    """Create a function that returns a letter grade based on a numeric score.

    This function will help in converting numeric scores to letter grades, which is a common task in educational systems and performance evaluations.

    Args:
        score: The numeric score to convert to a letter grade

    Returns:
        str
    """
    assert score >= 90, "Assertion from specification"
    assert 80 <= score < 90, "Assertion from specification"
    assert 70 <= score < 80, "Assertion from specification"
    assert 60 <= score < 70, "Assertion from specification"
    assert score < 60, "Assertion from specification"

    # Algorithm: The function get_letter_grade takes an integer score as input and returns a string representing the letter grade. The function uses a series of if-elif-else statements to determine the letter grade based on the score. If the score is 90 or above, the function returns 'A'. If the score is between 80 and 89, the function returns 'B'. If the score is between 70 and 79, the function returns 'C'. If the score is between 60 and 69, the function returns 'D'. If the score is below 60, the function returns 'F'.

    # Check if the score is 90 or above
    if score >= 90:
        # Return 'A' if the score is 90 or above
        return "A"
    # Check if the score is between 80 and 89
    elif 80 <= score < 90:
        # Return 'B' if the score is between 80 and 89
        return "B"
    # Check if the score is between 70 and 79
    elif 70 <= score < 80:
        # Return 'C' if the score is between 70 and 79
        return "C"
    # Check if the score is between 60 and 69
    elif 60 <= score < 70:
        # Return 'D' if the score is between 60 and 69
        return "D"
    # Check if the score is below 60
    else:
        # Return 'F' if the score is below 60
        return "F"
