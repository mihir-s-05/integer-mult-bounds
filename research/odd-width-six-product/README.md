# One width-six carryless product recovers an odd product modulo 64

For any two odd six-bit integers, each encoder emits six coefficients in
$\mathbb F_2[X]$. Multiplying those polynomials once gives eleven coefficients
from which a fixed Boolean circuit recovers the ordinary product modulo 64.
The decoder sees only the product coefficients. Bits 4 and 5 together cost
**24 AND and 40 XOR gates to decode**, or **78 AND and 99 XOR** including both
encoders and the channel. Bits are numbered from zero.

Six is the minimum width on each side, even for just the two adjacent bits.
Chris R's #7838 proved this lower bound and supplied a width-seven joint
construction for the full odd residue. This construction attains six with
one symmetric channel and a table-free encoder and decoder.
[Predecessor proof at cd9ce5a](https://github.com/CrocSwap/integer-mult-bounds/blob/cd9ce5a555977b469bd848199bc36025bd82fdcb/research/carryless-middle-bit-rank/ODD-WIDTH.md) · [Six-bit handoff](https://github.com/CrocSwap/integer-mult-bounds/discussions/1166#discussioncomment-19769396)

## Why six coefficients suffice

Use the sixteen polynomials $B$ of degree at most four with constant term one.
Modulo $X^5$ these form a group. Every member is uniquely
$(1+X)^t(1+X^3)^s$, with $0\le t<8$ and $0\le s<2$. The first generator has
order eight. Its only element of order two is $1+X^4$, so the second generator
gives an independent factor of order two. The corresponding ordinary units
$5^t(-1)^s$ run through all odd residues modulo 32.

Lift this correspondence to a multiplicative label $L$ modulo 64 by assigning
a label to each irreducible polynomial that can divide a codeword. The table
uses coefficient masks, so 3 denotes $1+X$ and 25 denotes $1+X^3+X^4$.
The odd-mask entries reduce modulo 32 to the group correspondence above.
Either lift of each entry gives the width construction. These particular lifts
admit the short high-bit formula below.

| Irreducible mask | 2 ($X$) | 3 | 7 | 11 | 13 | 19 | 25 | 31 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Label modulo 64 | 33 | 5 | 19 | 11 | 7 | 53 | 47 | 45 |

Unique factorization defines $L$ on every product of these factors. For an
odd input $a$, take the unique core $B$ with $L(B)=a\pmod{32}$. Use $B$ itself
if its label equals $a$ modulo 64, and $XB$ otherwise. Multiplication by
$L(X)=33$ toggles exactly bit 5 of every odd residue modulo 64. Thus both
choices fit in six coefficients and the raw product has label $ab\pmod{64}$.
Different unordered operand pairs can give the same polynomial. For example,
$(1,25)$ and $(5,5)$ both return $1+X^2$.

For the lower bound, consider the row of bit pairs produced by each odd left
input as the right input ranges over all units. Equal rows for $a$ and $a'$
would make their quotient preserve the two output bits at every unit. Those
quotients form a subgroup. Every nontrivial subgroup of this order-32 group
contains an involution. The three nonidentity involutions are 31, 33 and 63.
Each changes the output at 1. Hence all 32 rows differ. Every row is
nonconstant because multiplication by a unit permutes the units. A zero
codeword would make its entire row constant. Five coefficients give only 31
nonzero words. Commutativity gives the same lower bound for the right encoder,
even if the two encoders differ.

## Table-free circuit and price

Write the raw product as $X^q C$, where $C(0)=1$. Each encoder introduced at
most one $X$, so $q$ is 0, 1 or 2. The first two raw coefficients distinguish
these three cases. For $C=1+\sum_{i=1}^8 b_i X^i$, put
$s=b_3+b_1b_2$ and $d=b_2+b_4$. In the following expressions addition is XOR
and multiplication is AND. The two requested bits are

$$
\begin{aligned}
z_4 &= d+s+b_1s,\\
z_5 &= (q\bmod 2)+b_4+b_8+b_1 b_3 d
       +b_5(1+b_1+b_3)+b_6(b_1+b_2)+b_1 b_7 .
\end{aligned}
$$

The lower four output bits, from least significant upwards, are
$1,s,b_1+s,b_2+s$. The high-bit polynomial is a finite interpolation on
products of the sixteen cores. The checker verifies it against the factor
labels on every reachable return. On a single core, $b_5$ through $b_8$ vanish.
The same expression gives the bit that decides whether the encoder inserts
$X$. The circuit implements all three possible shifts with two-input gates.
[Circuit](circuit.py) · [Independent factor-label check and gate counter](verify.py)

| Component | AND | XOR |
|---|---:|---:|
| One encoder (used twice) | 9 | 17 |
| One full six-by-six carryless convolution | 36 | 25 |
| Decoder for bits 4 and 5 | 24 | 40 |
| **Total for bits 4 and 5** | **78** | **99** |
| **Total for the full residue** | **78** | **101** |

Wiring, fan-out and hardwired constants are free. XOR with one is charged.
For comparison, two separately executed ordinary truncated schoolbook circuits
in the checker use 15 AND / 16 XOR for bit 4 and 26 AND / 27 XOR for bit 5.
Together they are cheaper and use direct access to the operands. The result
settles joint-channel width. Gate minimization under that interface is open.

## Reproduce

From the repository root on Linux with Python 3.12 and its standard library, run

```sh
python3 -B scripts/research_package.py --package research/odd-width-six-product
```

The check covers all 1,024 ordered odd input pairs, 32 distinct nonconstant
joint-output rows and 309 different raw returns with zero conflicting residues.
An independent reference divides each polynomial by the listed irreducibles.
Ordinary integer multiplication supplies the expected outputs. Truncating the
return to six low coefficients conflates masks 22 and 150, produced by
$(1,43)$ and $(3,25)$ respectively. Their ordinary residues are 43 and 11.
The package also checks the lost high bit when the $X$ tag is removed.

## Open next questions

How many gates does a decoder need for these fixed encoders? A smaller circuit
could close part of the gap to direct computation. Start with the 309 required
eleven-bit returns, leave the other inputs unconstrained, then replay all
1,024 pairs and count gates with the same free-fan-out convention. A global
optimum would also have to consider other encoders. Even operands, wider
products and use in a recursive supplier require additional constructions.
This finite result earns zero $\kappa$ credit. [Task and source context](TASK.json)

## Credit

Chris R (@Clear1nsight) posed the single-channel problem and proved the lower
bound in #7838, crediting Thathachar and Bryant for earlier middle-bit rank
arguments. The factor labels, circuit and checks here were prepared for
Mihir Srivastava (@mihir-s-05) with substantial OpenAI Codex assistance.
Apache-2.0. [Predecessor package](https://github.com/CrocSwap/integer-mult-bounds/tree/cd9ce5a555977b469bd848199bc36025bd82fdcb/research/carryless-middle-bit-rank)
