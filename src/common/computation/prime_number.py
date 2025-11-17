

def compute_prime_numbers_in_range(start: int, end: int):
    """
    Check for prime numbers in the range from start to end (inclusive) and return a list of those prime numbers.
    """
    
    primes = []

    for x in range(start, end + 1):
        for k in range(2, x):
            if x % k == 0:
                break
        else:
            primes.append(x)

    return primes


def compute_prime_numbers(n: int):
    """
    Compute all prime numbers up to n (inclusive) and return them as a list.
    """
    return compute_prime_numbers_in_range(1, n)

