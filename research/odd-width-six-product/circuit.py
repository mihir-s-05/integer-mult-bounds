"""Straight-line Boolean circuit. Coefficients are in increasing degree order."""

from functools import reduce
from operator import xor


def encode(digits, one):
    """Encode the five variable bits (bits 1 through 5) of an odd operand."""
    sign, a2, a3, a4, a5 = digits
    b1 = a2 ^ sign
    b2 = a3 ^ sign
    b3 = sign ^ (b1 & b2)
    b4 = (a4 ^ a3) ^ (b1 & sign)
    core_high = b4 ^ ((b1 & b3) & (b2 ^ b4))
    shift = a5 ^ core_high

    core = [one, b1, b2, b3, b4]
    return [
        one ^ shift,
        *(core[i] ^ (shift & (core[i - 1] ^ core[i])) for i in range(1, 5)),
        shift & b4,
    ]


def channel(left, right):
    """All eleven coefficients of the one unreduced 6-by-6 polynomial product."""
    return [
        reduce(xor, (left[i] & right[k - i]
                     for i in range(max(0, k - 5), min(k, 5) + 1)))
        for k in range(11)
    ]


def normalize(raw, one):
    """Remove X^q, q in {0,1,2}. Only the eight nonconstant core wires are needed."""
    shifted = one ^ raw[0]          # q >= 1
    odd_shift = shifted & raw[1]    # q == 1
    twice = shifted ^ odd_shift     # q == 2
    delta = [raw[i] ^ raw[i + 1] for i in range(1, 10)]
    core = [raw[i] ^ (shifted & delta[i - 1]) ^ (twice & delta[i])
            for i in range(1, 9)]
    return core, odd_shift


def decode(raw, one, *, full=False):
    """The keyword selects output wires at circuit construction time."""
    b, odd_shift = normalize(raw, one)
    b1, b2, b3, b4, b5, b6, b7, b8 = b
    sign = b3 ^ (b1 & b2)
    pair24 = b2 ^ b4
    bit4 = pair24 ^ (sign ^ (b1 & sign))
    high = (b4 ^ b8
            ^ ((b1 & b3) & pair24)
            ^ (b5 & (one ^ b1 ^ b3))
            ^ (b6 & (b1 ^ b2))
            ^ (b1 & b7))
    bit5 = high ^ odd_shift
    if full:
        return one, sign, b1 ^ sign, b2 ^ sign, bit4, bit5
    return bit4, bit5
