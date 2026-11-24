"""Boolean circuit for one width-six channel on odd six-bit operands.

Tuples are in increasing bit/degree order. Only XOR, AND, constants and
static wiring act on their elements. The optional output width is fixed
when constructing the circuit, independently of the operand values.
"""
from functools import reduce
from operator import xor


def encode(bits):
    """Input bits 1 through 5. Bit 0 is hardwired to one."""
    sign, x2, x3, x4, x5 = bits
    # The positive component is 31**sign * x mod 64.
    a, b, c = x2 ^ sign, x3 ^ sign, x4 ^ sign
    ac = a & c
    common = b ^ c ^ (ac & b)
    r3 = common ^ ac ^ x5
    r4 = common ^ (a & x5)

    # R has coefficients (1, a, b, r3, r4). Emit z**sign * R.
    return (
        sign ^ 1,
        x2 ^ (sign & a),
        b ^ (sign & (a ^ b)),
        r3 ^ (sign & (b ^ r3)),
        r4 ^ (sign & (r3 ^ r4)),
        sign & r4,
    )


def carryless_product(left, right):
    """All eleven coefficients of a six-by-six binary polynomial product."""
    return tuple(
        reduce(xor, (left[i] & right[k - i]
                     for i in range(max(0, k - 5), min(k, 5) + 1)))
        for k in range(11)
    )


def decode(product, *, full_residue=False):
    """Receive only the eleven product coefficients."""
    # The number of leading zero coefficients is 0, 1 or 2.
    no_constant = product[0] ^ 1
    odd_shift = no_constant & product[1]
    double_shift = no_constant ^ odd_shift

    # p_i is coefficient i after dividing out that power of z.
    differences = [product[i] ^ product[i + 1] for i in range(1, 10)]
    p1, p2, p3, p4, p5, p6, p7, p8 = (
        product[i + 1] ^ (product[0] & differences[i - 1])
        ^ (double_shift & differences[i])
        for i in range(1, 9)
    )
    p23 = p2 ^ p3
    p48 = p4 ^ p8
    p345 = p3 ^ p4 ^ p5
    bit4 = p2 ^ p4 ^ (p1 & p23) ^ odd_shift
    bit5 = (p3 ^ p48 ^ (p1 & (p2 ^ p48)) ^ (p2 & (p7 ^ (p1 & p345)))
            ^ (p5 & (p23 ^ p4)) ^ (p6 & p23))
    if full_residue:
        return 1, odd_shift, p1 ^ odd_shift, p2 ^ odd_shift, bit4, bit5
    return bit4, bit5
