def gcd(a, b):
    """Computes the greatest common divisor of integers a and b using
        Euclid's Algorithm.
    """
    while True:
        if b == 0:
            return a
        a, b = b, a % b


print(gcd(23424, 5654))
