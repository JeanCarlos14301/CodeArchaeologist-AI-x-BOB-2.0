---
name: legacy-risk-assessment
description: >
  Mathematical risk calculation, blast radius analysis, and PERT effort 
  estimation for legacy codebase modernization projects.
metadata:
  origin: CodeArchaeologist
---

# Legacy Risk Assessment & PERT Estimation

A quantitative methodology for computing migration risk scores, module blast radius, and three-point PERT effort estimates without guesswork.

## When to Use

- When evaluating migration options in `migration-architect`.
- When calculating effort ranges for the executive board memo.
- When running the `/legacy-risk` command.
- To provide engineering leadership with defensible, probabilistic estimates.

## The Mathematical Risk Model

$$Risk = Impact \times Uncertainty$$

### 1. Calculating Impact (0.0 to 1.0)
Impact measures the potential systemic damage if a component fails during migration:
- **Blast Radius Weight (40%)**: Ratio of dependent modules affected if this module changes.
  $$\text{Blast Radius} = \frac{\text{Direct \& Transitive Downstream Modules}}{\text{Total Codebase Modules}}$$
- **Criticality Weight (30%)**: Does this module handle payments, authentication, or primary revenue flows?
- **Data Mutation Weight (30%)**: Does this module execute write/delete transactions vs read-only queries?

### 2. Calculating Uncertainty (0.0 to 1.0)
Uncertainty measures the lack of verified knowledge regarding the module's behavior:
- **Test Coverage Deficit (35%)**: $1.0 - \text{test\_coverage\_ratio}$ (e.g. 0% coverage = 1.0 uncertainty).
- **Type Annotations Deficit (25%)**: Percentage of un-annotated function parameters and returns.
- **Dynamic Coupling (20%)**: Presence of `getattr`, `eval`, or dynamic `importlib` calls.
- **Documentation & Age (20%)**: Absence of schema definitions or outdated dependencies.

## Three-Point PERT Effort Estimation

Never provide a single-number estimate. Use the Program Evaluation and Review Technique (PERT) to generate a realistic probability distribution.

### The PERT Equations
- **Expected Duration ($E$)**:
  $$E = \frac{O + 4M + P}{6}$$
- **Standard Deviation ($\sigma$)**:
  $$\sigma = \frac{P - O}{6}$$
- **95% Confidence Interval**:
  $$[E - 2\sigma, \; E + 2\sigma]$$

Where:
- $O$ = **Optimistic Estimate** (Everything goes perfectly, zero unexpected bugs, instant tests).
- $M$ = **Most Likely Estimate** (Normal development pace with standard minor obstacles).
- $P$ = **Pessimistic Estimate** (Hidden dependencies surface, database locks, subtle race conditions).

### Worked Example: Extracting a User Endpoint
- $O = 4$ hours
- $M = 8$ hours
- $P = 18$ hours
- Expected: $E = \frac{4 + 4(8) + 18}{6} = \frac{54}{6} = 9.0$ hours
- Standard Deviation: $\sigma = \frac{18 - 4}{6} = 2.33$ hours
- 95% Confidence Range: $[4.34, \; 13.66]$ hours (reported as 5 to 14 hours).

## Risk Matrix Classification

| Impact \ Uncertainty | Low Uncertainty (< 0.3) | Moderate Uncertainty (0.3–0.6) | High Uncertainty (> 0.6) |
|---|---|---|---|
| **High Impact (> 0.6)** | **MEDIUM RISK** (Manage via staging) | **HIGH RISK** (Characterization tests required) | **CRITICAL RISK** (Do not touch as first cut) |
| **Moderate Impact (0.3–0.6)** | **LOW RISK** (Standard PR) | **MEDIUM RISK** (Pair programming) | **HIGH RISK** (Isolate before migration) |
| **Low Impact (< 0.3)** | **MINIMAL RISK** (Prime first cut) | **LOW RISK** (Ideal quick win) | **MEDIUM RISK** (Spike recommended) |

## Best Practices

- **Show the Work**: Always document $O$, $M$, $P$, and the specific assumptions that justify $P$.
- **Ground Blast Radius in the Graph**: Blast radius must be calculated directly from the dependency tree produced by `legacy-dependency-tracer`.
- **Never Promise Exact Dates**: Present estimates as probability windows to prevent premature commitments.
