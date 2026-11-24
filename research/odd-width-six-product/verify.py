#!/usr/bin/env python3
"""Exhaust the finite contract and meter the literal two-input circuit."""

from collections import Counter
from functools import reduce
from operator import xor
from pathlib import Path
import sys

# The registered command also works with an isolated interpreter.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from circuit import channel, decode, encode


ODDS = range(1, 64, 2)
# X, followed by all constant-one irreducibles of degrees one through four.
# Each pair is (coefficient mask, odd residue modulo 64).
FACTORS = ((2, 33), (3, 5), (7, 19), (11, 11), (13, 7),
           (19, 53), (25, 47), (31, 45))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bits(value, width):
    return [(value >> i) & 1 for i in range(width)]


def polynomial_product(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        b >>= 1
    return result


def polynomial_divmod(a, b):
    quotient = 0
    while a.bit_length() >= b.bit_length():
        shift = a.bit_length() - b.bit_length()
        quotient ^= 1 << shift
        a ^= b << shift
    return quotient, a


def label(p):
    require(p > 0, "zero has no unit label")
    residue = 1
    for factor, value in FACTORS:
        while True:
            quotient, remainder = polynomial_divmod(p, factor)
            if remainder:
                break
            p = quotient
            residue = (residue * value) % 64
    require(p == 1, f"unlabelled residual polynomial {p}")
    return residue


def reference_codes():
    irreducibles = []
    for p in range(2, 32):
        degree = p.bit_length() - 1
        trial_factors = range(2, 1 << (degree // 2 + 1))
        if all(polynomial_divmod(p, q)[1] for q in trial_factors):
            irreducibles.append(p)
    require(irreducibles == [p for p, _ in FACTORS], "factor inventory differs")
    power = 1
    for exponent in range(8):
        for sign in (0, 1):
            core = polynomial_product(power, 1 | (sign << 3)) & 31
            expected = ((-1) ** sign * 5 ** exponent) % 32
            require(label(core) % 32 == expected, f"unit group lift at core {core}")
        power = polynomial_product(power, 3) & 31

    codes = {}
    for core in range(1, 32, 2):
        for shift in (0, 1):
            word = core << shift
            codes[label(word)] = word
    require(set(codes) == set(ODDS), "the factor labels must cover all odd residues")
    return codes


def direct_bit(left, right, top):
    """Ordinary schoolbook columns for odd operands, truncated at bit top.

    left and right hold variable bits 1..5. A 3-to-2 counter consumes three
    same-column bits and sends its carry to the next column. The last column needs
    only a parity. All list operations here select wires at construction time.
    """
    carries = []
    for k in range(1, top + 1):
        column = [left[k - 1], right[k - 1], *carries]
        column.extend(left[i - 1] & right[k - i - 1] for i in range(1, k))
        if k == top:
            return reduce(xor, column)
        carries = []
        while len(column) >= 3:
            a, b, c = column[:3]
            pair = a ^ b
            carries.append((a & b) ^ (pair & c))
            rest = column[3:]
            column = [*rest, pair ^ c] if rest else []
        if len(column) == 2:
            carries.append(column[0] & column[1])


class Meter:
    """Count gate applications on a fixed topology, without Boolean simplifications."""

    def __init__(self):
        self.ands = 0
        self.xors = 0

    def __and__(self, other):
        self.ands += 1
        return self

    def __xor__(self, other):
        self.xors += 1
        return self


def cost(build):
    meter = Meter()
    build(meter)
    return meter.ands, meter.xors


def main():
    codes = reference_codes()
    encoded = {a: encode(bits(a >> 1, 5), 1) for a in ODDS}
    for a in ODDS:
        require(encoded[a] == bits(codes[a], 6), f"encoder at {a}")

    returns = {}
    rows = set()
    shifts = Counter()
    for a in ODDS:
        left = bits(a >> 1, 5)
        row = []
        for b in ODDS:
            right = bits(b >> 1, 5)
            expected = (a * b) % 64
            raw = channel(encoded[a], encoded[b])
            key = polynomial_product(codes[a], codes[b])
            require(raw == bits(key, 11), f"convolution at {a},{b}")
            require(returns.setdefault(key, expected) == expected, f"conflict at return {key}")
            require(label(key) == expected, f"factor label at {key}")
            require(decode(raw, 1) == tuple(bits(expected >> 4, 2)), f"adjacent bits at {key}")
            require(decode(raw, 1, full=True) == tuple(bits(expected, 6)), f"full decoder at {key}")
            for top in (4, 5):
                require(direct_bit(left, right, top) == ((expected >> top) & 1),
                        f"direct reference bit {top} at {a},{b}")
            shifts[(key & -key).bit_length() - 1] += 1
            row.append(expected >> 4)
        require(len(set(row)) > 1, f"constant joint-output row at {a}")
        rows.add(tuple(row))
    require(len(rows) == 32, "joint-output row separation")
    require(len(returns) == 309 and shifts == {0: 256, 1: 512, 2: 256}, "return coverage")

    # Equal mixed returns really occur. Losing the high tag or truncating the
    # raw polynomial creates conflicts at the requested outputs.
    def ret(a, b):
        return polynomial_product(codes[a], codes[b])

    require(ret(1, 25) == ret(5, 5) and returns[ret(5, 5)] == 25, "mixed collision control")
    require(codes[33] == codes[1] << 1 and (returns[ret(33, 1)] ^ returns[ret(1, 1)]) == 32,
            "high-bit tag control")
    short, long = ret(1, 43), ret(3, 25)
    require(short == 22 and long == 150 and short == (long & 63)
            and returns[short] >> 4 != returns[long] >> 4, "truncation control")

    encoder = cost(lambda w: encode([w] * 5, w))
    convolution = cost(lambda w: channel([w] * 6, [w] * 6))
    decoder = cost(lambda w: decode([w] * 11, w))
    full_decoder = cost(lambda w: decode([w] * 11, w, full=True))
    total = tuple(2 * e + c + d for e, c, d in zip(encoder, convolution, decoder))
    require((encoder, convolution, decoder, full_decoder, total) ==
            ((9, 17), (36, 25), (24, 40), (24, 42), (78, 99)), "gate invoice")
    direct = [cost(lambda w: direct_bit([w] * 5, [w] * 5, top)) for top in (4, 5)]
    require(direct == [(15, 16), (26, 27)], "ordinary reference invoice")
    print(f"32 nonconstant distinct rows, {len(returns)} raw returns, 1024 ordered pairs")
    print(f"AND/XOR counts for each encoder {encoder}, channel {convolution}, decoder {decoder}, total {total}")
    print(f"Full-residue decoder {full_decoder}, direct bit 4 and bit 5 references {direct}")
    print("PASS width-six odd product modulo 64")


if __name__ == "__main__":
    main()
