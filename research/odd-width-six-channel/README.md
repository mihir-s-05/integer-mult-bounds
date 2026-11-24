# One width-six carryless product recovers odd multiplication modulo 64

Two parties each encode one odd six-bit operand as a binary polynomial of degree at most five. The receiver sees the eleven coefficients of their single product in $\mathbb F_2[z]$. **Bits 4 and 5 of the ordinary product cost 23 AND and 42 XOR gates to decode.** The full residue modulo 64 costs two more XORs. Both decoders are fixed Boolean circuits. Six coordinates per side attain the width lower bound from Chris R’s [PR #7838](https://github.com/CrocSwap/integer-mult-bounds/pull/7838).

| Stage | Two-input AND | Two-input XOR |
|---|---:|---:|
| Left encoder | 8 | 16 |
| Right encoder | 8 | 16 |
| One schoolbook carryless product | 36 | 25 |
| Decoder for bits 4 and 5 | 23 | 42 |
| **Total for bits 4 and 5** | **75** | **99** |
| **Total for the full residue** | **75** | **101** |

Bit 0 is the least significant bit. Constants, wires and fan-out are free. Complementing a wire costs an XOR with one. Each side pays for all six encoded positions. The only cross-operand operation before decoding is the polynomial product. [Gate schedule](circuit.py)

## Construction

Interpret the bits of a polynomial mask as coefficients in increasing degree. Assign the following ordinary residues to polynomial irreducibles and extend the assignment multiplicatively modulo 64.

| Prime mask | 2 ($z$) | 3 ($1+z$) | 7 | 11 | 13 | 19 | 25 | 31 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Image | 31 | 5 | 45 | 53 | 57 | 21 | 17 | 13 |

The odd masks $R=1,3,\ldots,31$ have degree at most four and constant term one. Factoring them over $\mathbb F_2$ and using the table gives $5^t\bmod 64$, with the following exponents in mask order.

```text
0  1  2  7  8  5  10  3  4  13  14  11  12  9  6  15
```

These exponents cover all sixteen residues modulo 16. The powers of five give all units congruent to one modulo four. The unit 31 has order two and is three modulo four. Thus every odd input has a unique representative $E(x)=z^s R$, with $s\in\{0,1\}$ and $\deg E\le5$. Unique factorization ensures that equal raw channel returns have equal ordinary products modulo 64. For instance, $(5,61)$ and $(25,25)$ give the same polynomial $1+z^4$, whose image is 49. Even the unordered pair of operands is lost at this return.

### Evaluating the circuit

The encoder and decoder need no factorization or lookup at run time. For an odd operand $x$, the sign flag is bit 1. Multiplication by 31 sends $x$ to $32-x\pmod{64}$, complementing bits 1 through 4 and preserving bit 5. Normalizing the sign this way gives $31^s x$. The encoder computes its four variable polynomial coefficients and shifts by $s$. Its six output equations are in [circuit.py](circuit.py).

For a returned polynomial $P$, the exponent of $z$ is 0, 1 or 2. Its parity is the wire $o=(1+P_0)P_1$. Divide out this power of $z$ using the fixed shifts in the circuit and denote the remaining coefficients by $1,p_1,\ldots,p_8$. With addition and multiplication in $\mathbb F_2$, put $a=p_2+p_3$, $b=p_4+p_8$ and $c=p_3+p_4+p_5$. The two requested output wires are

$$
\begin{aligned}
h_4 &= p_2+p_4+p_1a+o,\\
h_5 &= p_3+b+p_1(p_2+b)+p_2(p_7+p_1c)+p_5(a+p_4)+p_6a.
\end{aligned}
$$

The four lower wires, in increasing order, are $1,o,p_1+o,p_2+o$. These identities can be checked on just 103 normalized products $R_xR_y$. To derive the nonlinear formulas, restrict squarefree monomials in the eight coefficients to those 103 rows and solve over $\mathbb F_2$ for the target bit of each factor label. The replay checks the displayed circuit on all three shifts. Every array index in the circuit is fixed by the wiring.

## Why five positions cannot suffice

The lower bound also has a short direct check at this width. Suppose two odd left operands have the same row of joint outputs as the right operand varies. Dividing one by the other in the unit group gives an odd $u$ such that $k$ and $ku\bmod64$ have the same two high bits for every odd $k$. Taking $k=1$ forces $u\le15$. If $3\le u\le15$, choose the smallest odd $k\ge16/u$. Then $k\le7$ while $16\le ku<16+2u<64$, so the two high bits differ. Thus $u=1$.

All 32 rows are distinct and each is nonconstant, since multiplying by an odd unit permutes the odd residues. An all-zero encoding would return zero on its entire row. This requires 32 nonzero encodings, and five positions provide only 31. Symmetry gives the same lower bound on the right. Chris R gives the general lower bound for two adjacent bits and a width-seven mixed construction at this operand size. [Pinned predecessor proof](https://github.com/CrocSwap/integer-mult-bounds/blob/cd9ce5a555977b469bd848199bc36025bd82fdcb/research/carryless-middle-bit-rank/ODD-WIDTH.md)

## Reproduction and scope

From the repository root with Python 3.12 and the standard library, run

```sh
python3 -B scripts/research_package.py --package research/odd-width-six-channel
```

The verifier constructs the inverse codebook by polynomial division, compares the channel gates with a shift-and-XOR polynomial multiplier, and checks both output modes against ordinary integer multiplication on all 1,024 ordered pairs. There are 309 distinct returns, of which 149 occur for more than one unordered pair. Omitting the sign tag aliases 31 with 1. Dropping just coefficient 10 aliases the returns for $(31,31)$ and $(47,47)$, whose ordinary residues are 1 and 33. A symbolic gate count replays each stage. [Verifier](verify.py)

This establishes a finite circuit and sharp input width on odd six-bit operands. The counts are exact for this schedule. Gate-count optimality is open. Extension to wider or unrestricted operands, tape and restoration costs, and a compatible recursive supplier bill remain open. The construction earns no $\kappa$ credit.

## Open next questions

Does the same factor assignment method give a single width-seven channel for odd **seven-bit** operands? The first test is to assign exponents modulo 32 to irreducibles through degree five so that the 32 odd polynomial masks below 64 receive distinct labels. A bijection would give the next width certificate. Pricing it would also require explicit encoder and decoder gates.

## Credit

This answers the specific handoff posted by Chris R / @Clear1nsight. His preceding work supplies the channel model, the width obstruction, a five-bit gate example and a width-seven field control. He credits Thathachar and Bryant for antecedents on middle-bit rank. PR #7839 treats a different problem involving two sibling products. Prepared for @mihir-s-05 with substantial OpenAI Codex assistance. Apache-2.0. [Handoff](https://github.com/CrocSwap/integer-mult-bounds/discussions/1166#discussioncomment-19769396) · [Related PR #7839](https://github.com/CrocSwap/integer-mult-bounds/pull/7839)
