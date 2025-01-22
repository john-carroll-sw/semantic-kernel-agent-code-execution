import random

def estimate_pi(num_samples: int):
    inside_circle = 0

    for _ in range(num_samples):
        x, y = random.uniform(0, 1), random.uniform(0, 1)
        if x**2 + y**2 <= 1:
            inside_circle += 1

    return (inside_circle / num_samples) * 4

# Estimate π using 1,000,000 samples
# estimate_pi(1000000)
print("Estimated π:", estimate_pi(1000000))