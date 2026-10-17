if __package__:
    from .edit_demo import add
else:
    from edit_demo import add


cases = [
    (2, 3, 5),
    (-2, 3, 1),
    (0, 0, 0),
]

for a, b, expected in cases:
    actual = add(a, b)

    if actual != expected:
        raise AssertionError(
            print(f"add({a}, {b}): expected {expected}, got {actual}")
        )
    print(f"add({a}, {b}): expected {expected}, got {actual}")

print("All 3 addition checks passed.")