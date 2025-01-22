def fibonacci(n):
    fib_sequence = [0, 1]
    while len(fib_sequence) < n:
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence

# Calculate the first 100 Fibonacci numbers
first_100_fib = fibonacci(100)
print(first_100_fib)