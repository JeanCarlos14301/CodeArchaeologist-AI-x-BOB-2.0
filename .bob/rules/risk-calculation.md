# Risk Calculation Rules

Rules governing quantitative risk metrics and effort estimations across all CodeArchaeologist agents.

## Mandatory Risk Principles

1. **Calculated by Code, Not Fabricated by LLM**
   - Agents must never output arbitrary risk percentages, dollar costs, or arbitrary complexity numbers.
   - All scores must be mathematically derived using the established formulas.

2. **The Risk Equation**
   $$Risk = Impact \times Uncertainty$$
   - $Impact$ is determined by module blast radius, write vs read nature, and business criticality.
   - $Uncertainty$ is determined by lack of test coverage, untyped parameters, and dynamic imports.

3. **PERT Three-Point Estimation Requirement**
   - Single-point estimates ("this will take 8 hours") are forbidden.
   - Every estimate must provide:
     - $O$: Optimistic duration
     - $M$: Most likely duration
     - $P$: Pessimistic duration
     - $E = \frac{O + 4M + P}{6}$: Expected PERT duration
     - Confidence interval: $[E - 2\sigma, E + 2\sigma]$ where $\sigma = \frac{P - O}{6}$.

4. **Deterministic Blast Radius**
   - $\text{Blast Radius} = \frac{\text{Direct \& Transitive Downstream Modules}}{\text{Total Codebase Modules}} \times 100\%$
   - Must be verified against the module import graph extracted by `legacy-dependency-tracer`.

5. **Explicit Assumptions**
   - Every pessimistic ($P$) estimate must explicitly state the failure modes assumed (e.g. database schema lock, unhandled circular import).
