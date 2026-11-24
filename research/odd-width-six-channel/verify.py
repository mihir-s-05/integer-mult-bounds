"""Exhaust the finite interface against factorization and ordinary multiplication."""
from collections import defaultdict
from itertools import product

from circuit import carryless_product, decode, encode


ODDS = range(1, 64, 2)
# (binary polynomial, odd residue mod 64). The first entry carries the sign.
PRIME_IMAGES = ((2, 31), (3, 5), (7, 45), (11, 53), (13, 57),
                (19, 21), (25, 17), (31, 13))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bits(value, width):
    return tuple((value >> i) & 1 for i in range(width))


def pack(coefficients):
    return sum(bit << i for i, bit in enumerate(coefficients))


def divmod_poly(value, divisor):
    quotient = 0
    while value.bit_length() >= divisor.bit_length():
        shift = value.bit_length() - divisor.bit_length()
        quotient ^= 1 << shift
        value ^= divisor << shift
    return quotient, value


def image(value):
    """Multiply the assigned images of all factors in the word."""
    require(value > 0, "zero has no multiplicative label")
    residue = 1
    for prime, unit in PRIME_IMAGES:
        quotient, remainder = divmod_poly(value, prime)
        while remainder == 0:
            residue = residue * unit % 64
            value = quotient
            quotient, remainder = divmod_poly(value, prime)
    require(value == 1, "unlabelled polynomial factor")
    return residue


def reference_product(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        b >>= 1
    return result


class GateCount:
    """Symbolic inputs count each gate invocation; wiring and fan-out are free."""

    def __init__(self):
        self.ands = 0
        self.xors = 0

    def __and__(self, other):
        self.ands += 1
        return self

    def __xor__(self, other):
        self.xors += 1
        return self

    def __bool__(self):
        raise TypeError("a circuit wire cannot control the gate schedule")


def price(operation, *widths, **options):
    meter = GateCount()
    operation(*((meter,) * width for width in widths), **options)
    return meter.ands, meter.xors


def verify():
    # Every reducible polynomial has a monic divisor of at most half its degree.
    labelled_primes = {p for p, _ in PRIME_IMAGES}
    for mask in range(2, 32):
        degree = mask.bit_length() - 1
        small_divisors = range(2, 1 << (degree // 2 + 1))
        irreducible = all(divmod_poly(mask, d)[1] for d in small_divisors)
        require(irreducible == (mask in labelled_primes), f"factor alphabet at {mask}")

    # Independent inverse of the encoder, built solely from polynomial labels.
    reference = {image(r << sign): r << sign
                 for r in range(1, 32, 2) for sign in (0, 1)}
    require(reference.keys() == set(ODDS), "six-bit representatives miss a unit")
    encodings = {x: encode(bits(x, 6)[1:]) for x in ODDS}
    for x, code in encodings.items():
        require(len(code) == 6 and pack(code) == reference[x], f"encoder mismatch at {x}")

    returns = {}
    unordered_pairs = defaultdict(set)
    for x, y in product(ODDS, repeat=2):
        received = carryless_product(encodings[x], encodings[y])
        raw = pack(received)
        expected = x * y % 64
        require(len(received) == 11 and raw == reference_product(reference[x], reference[y]),
                f"convolution mismatch at {(x, y)}")
        require(returns.setdefault(raw, expected) == expected, f"conflict at return {raw}")
        require(pack(decode(received)) == expected >> 4, f"adjacent bits at {(x, y)}")
        require(pack(decode(received, full_residue=True)) == expected, f"residue at {(x, y)}")
        unordered_pairs[raw].add(tuple(sorted((x, y))))

    require(all(image(raw) == expected for raw, expected in returns.items()), "factor labels")
    ambiguous = sum(len(pairs) > 1 for pairs in unordered_pairs.values())
    require((len(returns), ambiguous) == (309, 149), "collision census")
    require({(5, 61), (25, 25)} <= unordered_pairs[17] and returns[17] == 49,
            "distinct factorizations must share this return")

    # All 32 distinct nonconstant rows rule out five coordinates, including zero.
    rows = {tuple((x * y % 64) >> 4 for y in ODDS) for x in ODDS}
    require(len(rows) == 32 and all(len(set(row)) == 4 for row in rows), "width lower bound")

    # Remove the sign tag, or drop only the top coefficient of the return.
    signless = reference[31] >> 1
    require(signless == reference[1] and pack(decode(bits(signless, 11))) != (31 >> 4),
            "erasing the sign should fail on (31, 1)")
    low = reference_product(reference[31], reference[31])
    high = reference_product(reference[47], reference[47])
    require((low, high) == (4, 1028) and low == (high & 1023)
            and returns[low] >> 4 != returns[high] >> 4, "top coefficient control")

    costs = (price(encode, 5), price(carryless_product, 6, 6),
             price(decode, 11), price(decode, 11, full_residue=True))
    require(costs == ((8, 16), (36, 25), (23, 42), (23, 44)), f"gate schedule: {costs}")
    print(f"PASS: 1024 ordered pairs, {len(returns)} returns, {ambiguous} with multiple unordered pairs")
    print("Controls: erasing the sign loses (31, 1); dropping degree 10 confuses (31, 31) and (47, 47)")
    print(f"AND/XOR per encoder, convolution, two-bit and full decoder: {costs}")
    for name, decoder_cost in zip(("bits 4 and 5", "full residue"), costs[2:]):
        ands, xors = (2 * e + c + d for e, c, d in zip(costs[0], costs[1], decoder_cost))
        print(f"{name}, both encoders included: {ands} AND / {xors} XOR")


if __name__ == "__main__":
    verify()
