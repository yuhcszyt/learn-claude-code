"""Calculator module providing basic arithmetic operations."""

VERSION = "1.0.0"


def add(a, b):
    """Return the sum of a and b.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum of a and b.
    """
    return a + b


def subtract(a, b):
    """Return the difference of a and b.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The result of a minus b.
    """
    return a - b


def multiply(a, b):
    """Return the product of a and b.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The product of a and b.
    """
    return a * b


def divide(a, b):
    """Return the quotient of a divided by b.

    Args:
        a: Dividend.
        b: Divisor.

    Returns:
        The result of a divided by b, or an error message if b is zero.
    """
    if b == 0:
        return "Error: Division by zero"
    return a / b


def main():
    """Demonstrate all calculator operations with sample values and print results."""
    x, y = 10, 5

    print(f"add({x}, {y}) = {add(x, y)}")
    print(f"subtract({x}, {y}) = {subtract(x, y)}")
    print(f"multiply({x}, {y}) = {multiply(x, y)}")
    print(f"divide({x}, {y}) = {divide(x, y)}")

    # Also demonstrate division by zero
    print(f"divide({x}, 0) = {divide(x, 0)}")


if __name__ == "__main__":
    main()