# PRODUCT.md

> Product vision, UX architecture and implementation guidance for the AI-powered software modernization platform.

---

# 1. Purpose of this document

This document defines **what we are building and how the product should behave**.

It is intended to be consumed by Claude Code, coding agents, design agents and implementation agents working on this repository.

This document is NOT the visual design system.

Visual implementation must follow:

```text
DESIGN.md
```

When `DESIGN.md` exists, it is the **single source of truth for visual decisions**, including:

- colors
- typography
- spacing
- radius
- shadows
- borders
- CSS variables
- Tailwind v4 tokens
- component styling
- responsive behavior
- interaction states
- motion
- light/dark themes

Do not invent visual styles that conflict with `DESIGN.md`.

---

# 2. Product vision

Build a premium **AI-powered Software Modernization Workspace**.

The platform helps developers and engineering teams understand an existing software project, analyze its architecture and dependencies, identify technical and security risks, plan technology migrations, and interact with an AI assistant that understands the repository.

The product must NOT feel like:

- a generic SaaS dashboard
- an admin template
- a collection of cards
- a ChatGPT clone
- a marketing site with an AI chat attached
- an AI-generated UI
- a CRUD application with prettier styling

It should feel like a serious **developer tool**.

Conceptually, the experience sits somewhere between:

```text
IDE
+
Architecture Explorer
+
Migration Planner
+
Risk Analysis Platform
+
AI Engineering Assistant
```

The AI is not the product interface.

The AI is an **intelligence layer embedded throughout the product**.

---

# 3. Core product philosophy

The interface should answer four questions continuously:

```text
┌───────────────────────────────────────────────┐
│                                               │
│  1. What does this project contain?           │
│                                               │
│  2. How does this project work?               │
│                                               │
│  3. What could break?                         │
│                                               │
│  4. How should we modernize it safely?        │
│                                               │
└───────────────────────────────────────────────┘
```

Every major screen should contribute to answering at least one of these questions.

---

# 4. Primary user

Primary users:

- Software Engineers
- Backend Engineers
- Full-stack Engineers
- Software Architects
- DevOps Engineers
- Technical Leads
- Engineering teams modernizing legacy systems

Users are technically sophisticated.

Do not oversimplify technical information.

Prefer:

```text
Clear + dense + structured
```

over:

```text
Large + decorative + empty
```

The UI should make complex engineering information understandable without removing useful technical depth.

---

# 5. Core workflow

The primary product journey is:

```text
                         ┌─────────────────┐
                         │   ENTRY POINT   │
                         └────────┬────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Connect Repository    │
                    │                         │
                    │ GitHub / Local Project  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Repository Scan      │
                    │                         │
                    │ Files                   │
                    │ Dependencies            │
                    │ Frameworks              │
                    │ Infrastructure          │
                    │ Architecture            │
                    └────────────┬────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │          PROJECT WORKSPACE         │
              └─────────────────┬──────────────────┘
                                │
             ┌──────────────────┼────────────────────┐
             │                  │                    │
             ▼                  ▼                    ▼
      Architecture        Dependencies           Risks
       Explorer             Explorer            Analysis
             │                  │                    │
             └──────────────────┼────────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Migration Strategy  │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  Migration Plan     │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ AI-assisted changes │
                     └─────────────────────┘
```

The AI assistant remains context-aware throughout this workflow.

---

# 6. Information architecture

The application should conceptually contain:

```text
Platform
│
├── Home / Projects
│
├── Repository Connection
│   ├── GitHub
│   └── Local Project
│
└── Project Workspace
    │
    ├── Overview
    │
    ├── Architecture
    │
    ├── Repository
    │
    ├── Dependencies
    │
    ├── Risks
    │
    ├── Modernization
    │   ├── Target Technology
    │   ├── Compatibility Analysis
    │   ├── Migration Strategy
    │   └── Migration Plan
    │
    ├── Reports
    │
    └── AI Assistant
```

Do not treat every item as necessarily requiring an independent page.

Some functionality may work better as:

- panels
- inspectors
- tabs
- drawers
- command interfaces
- contextual overlays

Choose interaction patterns based on usability.

---

# 7. Application shell

The workspace should feel closer to an engineering tool than a traditional website.

Conceptual structure:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Project / Repository                       Branch      Status        │
├──────────────┬───────────────────────────────────────┬──────────────┤
│              │                                       │              │
│ Navigation   │                                       │ AI Context   │
│              │                                       │ Panel        │
│ Overview     │                                       │              │
│ Architecture │          Main Workspace               │ Ask about    │
│ Repository   │                                       │ this project │
│ Dependencies │                                       │              │
│ Risks        │                                       │              │
│ Migration    │                                       │              │
│ Reports      │                                       │              │
│              │                                       │              │
├──────────────┴───────────────────────────────────────┴──────────────┤
│ Context / analysis status / background operations                  │
└─────────────────────────────────────────────────────────────────────┘
```

This diagram is conceptual.

Do NOT reproduce it literally if `DESIGN.md` suggests a better visual solution.

---

# 8. Project connection experience

The first meaningful action is connecting a software project.

Supported conceptual sources:

## GitHub repository

User should be able to:

1. Connect GitHub
2. Choose repository
3. Choose branch
4. Configure analysis
5. Start repository scan

## Local project

The architecture must allow a future local-project workflow.

Potential mechanisms may include:

- folder selection
- CLI companion
- local agent
- uploaded archive

Do not fake local filesystem capabilities in a browser if the technical implementation does not support them.

---

# 9. Repository analysis

After connection, the system analyzes the codebase.

The analysis model should conceptually discover:

### Languages

Examples:

```text
Java
TypeScript
Python
SQL
YAML
Dockerfile
```

### Frameworks

Examples:

```text
Spring Boot
React
Next.js
FastAPI
Express
```

### Infrastructure

Examples:

```text
Docker
GitHub Actions
Azure
AWS
Kubernetes
Terraform
```

### Databases

Examples:

```text
PostgreSQL
MySQL
MongoDB
Redis
```

### Architecture

Examples:

```text
Monolith
Modular Monolith
Microservices
Layered Architecture
Hexagonal Architecture
Event-driven Architecture
```

### Project relationships

The system should attempt to understand:

```text
Controller
    │
    ▼
Service
    │
    ▼
Repository
    │
    ▼
Database
```

and more complex relationships when available.

---

# 10. Project overview

The Overview screen should answer:

> "What kind of system am I looking at?"

Possible information:

```text
Repository
Branch
Primary language
Framework
Architecture
Database
Build system
Deployment environment
Repository size
Detected services
Dependencies
Detected risks
Modernization opportunities
```

Avoid turning all of these into individual cards.

Use hierarchy.

For example:

```text
my-platform/backend
Spring Boot · Java 21 · PostgreSQL

Architecture
Modular Monolith

──────────────────────────────────────

Health                         Analysis

Dependencies                   126
Outdated                        18
Critical risks                   3
Architecture findings            7

──────────────────────────────────────

Modernization readiness

████████████████░░░░

Several dependencies require migration before
the framework can be upgraded safely.
```

Values above are illustrative only.

Never present mock values as actual analysis results.

---

# 11. Architecture Explorer

Architecture visualization is one of the signature experiences.

It should allow users to understand relationships between major components.

Conceptual example:

```text
                        ┌──────────────┐
                        │   Frontend   │
                        │    React     │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ API Gateway  │
                        └──────┬───────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌────────────┐  ┌────────────┐  ┌────────────┐
        │   Users    │  │  Orders    │  │ Payments   │
        │  Service   │  │  Service   │  │  Service   │
        └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
              │               │               │
              ▼               ▼               ▼
        ┌────────────────────────────────────────────┐
        │                 PostgreSQL                 │
        └────────────────────────────────────────────┘
```

Nodes should potentially expose:

- technology
- dependencies
- risk status
- files
- incoming relationships
- outgoing relationships
- modernization impact

Selecting a node should reveal contextual information.

Architecture visualization should support exploration, not just decoration.

---

# 12. Dependency Explorer

Dependencies must be treated as relationships, not just a package list.

Example:

```text
spring-boot
│
├── spring-web
│
├── spring-data-jpa
│
├── spring-security
│
└── jackson
```

For each dependency, the product may expose:

```text
Current version
Latest compatible version
Usage
Affected files
Known incompatibilities
Migration impact
Risk
```

Useful states:

```text
Healthy
Update available
Deprecated
Breaking change
Security risk
Unknown
```

Do not rely solely on color to communicate these states.

---

# 13. Risk analysis

Risk analysis is a first-class feature.

Risk categories:

```text
Security
Compatibility
Dependencies
Architecture
Performance
Deployment
Database
API
Configuration
```

Each risk should contain:

```text
Title

Severity
Confidence
Category

Affected components
Affected files

Why this matters

Evidence

Potential impact

Recommended action
```

Example conceptual hierarchy:

```text
CRITICAL
│
├── Vulnerable dependency
│
└── Authentication incompatibility

HIGH
│
├── Deprecated API
│
├── Database migration issue
│
└── Breaking framework change

MEDIUM
│
└── Configuration migration

LOW
│
└── Cleanup opportunities
```

Risk visualization must emphasize **reasoning and evidence**, not fear.

Avoid alarmist UX.

---

# 14. Modernization Center

This is one of the core product experiences.

Users should be able to define a transformation.

Example:

```text
CURRENT

Spring Boot 2.7
Java 11

        │
        │ Modernize
        ▼

TARGET

Spring Boot 4.x
Java 25
```

The exact versions are user/project dependent.

The system should then analyze the transformation.

---

# 15. Migration analysis

The migration engine should conceptually evaluate:

```text
                    TARGET MIGRATION
                          │
                          ▼
                ┌───────────────────┐
                │ Compatibility     │
                │ Analysis          │
                └─────────┬─────────┘
                          │
       ┌──────────────────┼────────────────────┐
       │                  │                    │
       ▼                  ▼                    ▼
 Dependencies         Source Code         Configuration
       │                  │                    │
       ▼                  ▼                    ▼
 Compatibility       Deprecated APIs       Properties
 Breaking Changes    Language Changes      Environment
 Vulnerabilities     Framework Changes     Infrastructure
       │                  │                    │
       └──────────────────┼────────────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │    Risk Model     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Migration Plan    │
                └───────────────────┘
```

---

# 16. Migration Plan

Migration should NOT be represented as a generic checklist.

It should communicate dependency between steps.

Example:

```text
Migration Plan

01
Update runtime
Java 11 → Java 17+
       │
       ▼
02
Update core dependencies
       │
       ├───────────────┐
       ▼               ▼
03                  04
Security            Persistence
migration           migration
       │               │
       └───────┬───────┘
               ▼
05
Framework upgrade
               │
               ▼
06
Resolve deprecated APIs
               │
               ▼
07
Run test suite
               │
               ▼
08
Deployment validation
```

Each migration step should potentially expose:

```text
Why
Files affected
Dependencies
Risk
Estimated complexity
Required previous steps
Suggested changes
Validation strategy
```

---

# 17. Change impact analysis

A major product principle is:

> Never recommend a change without showing its possible impact.

Example:

```text
Upgrade spring-security

             │
             ▼

       Impact Analysis
             │
      ┌──────┼────────┐
      │      │        │
      ▼      ▼        ▼

 AuthConfig  Filters   Tests
     │          │        │
     └──────────┼────────┘
                ▼

          Deployment
```

Users should be able to ask:

> What could break if I make this change?

The system should explain:

- affected files
- affected components
- dependent systems
- confidence
- reasoning

---

# 18. AI Assistant

The assistant is contextual.

It understands the active:

```text
User
  │
  ▼
Project
  │
  ├── Repository
  ├── Branch
  ├── Architecture
  ├── Dependencies
  ├── Risks
  ├── Migration
  └── Current UI context
             │
             ▼
       AI Assistant
```

The assistant should know what the user is currently inspecting.

Examples:

```text
Why is this dependency marked as high risk?

Which files depend on this service?

What should I migrate first?

Explain this architecture.

What could break if I update Spring Security?

Show me where this deprecated API is used.

Why did you recommend this migration order?

What tests should I run after this change?
```

---

# 19. AI interaction model

Avoid a giant permanent chatbot occupying the product.

AI can appear through:

### Contextual assistant

A collapsible side panel.

### Inline actions

Examples:

```text
Explain
Analyze impact
Suggest migration
Find usages
Generate plan
Explain risk
```

### Command interface

Potential command palette:

```text
⌘ K

> Analyze repository
> Explain architecture
> Find security risks
> Plan migration
> Ask about current file
```

### Contextual prompts

When examining a risk:

```text
Ask AI about this risk
```

When examining a dependency:

```text
Analyze upgrade impact
```

The assistant must feel connected to the object currently being viewed.

---

# 20. Evidence-first AI

AI output must distinguish between:

```text
Detected fact
Inference
Recommendation
Unknown
```

Whenever possible, recommendations should expose evidence.

Example:

```text
HIGH RISK

Spring Security configuration requires migration.

Evidence

src/main/java/.../SecurityConfig.java

The project uses an API that is deprecated in the
target framework version.

Affected

3 files
2 tests

Confidence

High
```

Avoid presenting model speculation as repository truth.

---

# 21. Progressive disclosure

Do not show every technical detail simultaneously.

Use:

```text
Summary
   │
   ▼
Finding
   │
   ▼
Evidence
   │
   ▼
Affected code
   │
   ▼
Recommended action
```

This keeps the UI powerful without becoming overwhelming.

---

# 22. Repository Explorer

The repository browser should support technical exploration.

Conceptually:

```text
backend/
│
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/
│   │   │       └── project/
│   │   │           ├── controller/
│   │   │           ├── service/
│   │   │           ├── repository/
│   │   │           └── config/
│   │   │
│   │   └── resources/
│   │       └── application.yml
│   │
│   └── test/
│
├── Dockerfile
├── pom.xml
└── README.md
```

The repository tree should integrate with analysis.

Files may display indicators for:

```text
Risk
Migration impact
Deprecated usage
Security finding
Modified state
```

---

# 23. Code inspection

When viewing code, the experience should support contextual analysis.

Conceptual layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ SecurityConfig.java                                         │
├───────────────────────────────────────┬──────────────────────┤
│                                       │                      │
│                                       │ Findings             │
│             CODE                      │                      │
│                                       │ ⚠ Deprecated API     │
│                                       │                      │
│                                       │ Migration impact     │
│                                       │ High                 │
│                                       │                      │
│                                       │ [Explain]            │
│                                       │ [Plan fix]           │
└───────────────────────────────────────┴──────────────────────┘
```

The code is the primary content.

AI controls must not overwhelm it.

---

# 24. Product visual character

Detailed styling comes from `DESIGN.md`.

However, the product should conceptually communicate:

```text
ENGINEERING
PRECISION
INTELLIGENCE
CONTROL
TRUST
CLARITY
```

Not:

```text
FLASHY
PLAYFUL
GIMMICKY
CRYPTO
SCI-FI
GENERIC AI
```

Avoid excessive:

- gradients
- glowing borders
- glassmorphism
- floating cards
- huge border radius
- meaningless metrics
- decorative charts
- excessive animation
- giant hero typography inside the application
- purple AI aesthetic

---

# 25. Information density

This is a professional engineering application.

Reasonable density is desirable.

Prefer:

```text
┌────────────────────────────────────┐
│ Dependency                         │
│ spring-security  6.x               │
│                                    │
│ Risk       HIGH                    │
│ Usage      14 files                │
│ Impact     Authentication          │
└────────────────────────────────────┘
```

over enormous cards with little information.

Spacing should create hierarchy, not emptiness.

---

# 26. Interaction philosophy

Every interaction should answer:

> What will happen if I click this?

Actions must have explicit labels.

Prefer:

```text
Analyze migration impact
```

instead of:

```text
Analyze
```

Prefer:

```text
View affected files
```

instead of:

```text
Details
```

Prefer:

```text
Generate migration plan
```

instead of:

```text
Continue
```

---

# 27. Status model

Long-running AI/repository operations need clear status.

Potential states:

```text
Queued
Scanning
Analyzing
Generating architecture
Evaluating dependencies
Analyzing risks
Building migration plan
Complete
Failed
Cancelled
```

Avoid fake progress.

If actual percentage progress is unavailable, use stage-based progress.

Example:

```text
Analyzing repository

✓ Repository indexed
✓ Technologies detected
● Analyzing dependencies
○ Mapping architecture
○ Evaluating risks
```

---

# 28. Empty states

Empty states should help users act.

Bad:

```text
No data available.
```

Better:

```text
No migration analysis yet.

Choose a target technology to evaluate compatibility,
breaking changes and migration risks.

[Choose migration target]
```

---

# 29. Error states

Errors must communicate:

```text
What happened
Why it matters
What the user can do
```

Example:

```text
Repository analysis could not complete.

The dependency manifest could not be parsed.

pom.xml
Line 84

[View error]
[Retry analysis]
```

---

# 30. Responsive behavior

This is primarily a desktop engineering tool.

Priority:

```text
Desktop
   ↓
Laptop
   ↓
Tablet
   ↓
Mobile
```

Do not destroy desktop information architecture merely to make mobile implementation easier.

On smaller screens:

- collapse secondary panels
- prioritize primary workspace
- convert inspectors to drawers
- collapse navigation
- preserve core actions

---

# 31. Accessibility

Minimum expectations:

- semantic HTML
- keyboard navigation
- visible focus states
- sufficient contrast
- screen-reader labels
- reduced-motion support
- no color-only status communication
- usable zoom behavior
- accessible dialogs
- accessible tooltips
- accessible forms

Developer tooling does not justify poor accessibility.

---

# 32. Design system integration

The implementation will use:

```text
Tailwind CSS v4
CSS Variables
Design Tokens
```

Claude must NOT scatter arbitrary values throughout components.

Avoid:

```text
text-[#8B5CF6]
bg-[#111827]
rounded-[13px]
shadow-[...]
```

when an equivalent semantic token exists.

Prefer semantic abstractions such as:

```text
bg-background
bg-surface
bg-surface-elevated

text-foreground
text-muted

border-border
border-subtle

text-risk-critical
text-risk-warning
text-success
```

Exact names must follow `DESIGN.md`.

---

# 33. Token philosophy

Tokens should represent meaning rather than arbitrary visual values.

Conceptually:

```text
Primitive Tokens
        │
        ▼
Semantic Tokens
        │
        ▼
Component Tokens
        │
        ▼
UI
```

Example:

```text
gray-950
   │
   ▼
surface-primary
   │
   ▼
workspace-background
```

Do not tightly couple business components to primitive color values.

---

# 34. Component philosophy

Before creating a component, ask:

```text
Is this reusable?

Is this a UI primitive?

Is this domain-specific?

Does an equivalent component already exist?

Should this behavior belong to a composable primitive?
```

Potential domain components:

```text
RepositoryTree
ArchitectureGraph
DependencyInspector
RiskFinding
RiskBadge
MigrationTimeline
MigrationStep
ImpactGraph
CodeViewer
AnalysisStatus
AIContextPanel
TechnologyBadge
EvidencePanel
ProjectSwitcher
```

Do not prematurely create abstractions for trivial markup.

---

# 35. Motion

Motion should explain state changes.

Good:

```text
Panel opens
Node expands
Analysis progresses
Inspector changes context
Migration step changes state
```

Bad:

```text
Everything fades in
Cards float on hover
Random glowing animation
Constant gradient movement
```

Animation must serve understanding.

---

# 36. Agent instructions

This repository may contain specialized Claude Code agents and skills.

USE THEM.

Before implementing a substantial feature:

1. Inspect available agents.
2. Inspect available skills.
3. Determine which are relevant.
4. Delegate specialized analysis when useful.
5. Consolidate findings before implementation.

Potential responsibilities include:

```text
UI/UX analysis
Design-system enforcement
Frontend architecture
Accessibility review
Security review
Code quality review
Testing
Performance analysis
Repository exploration
```

Do not invoke agents mechanically.

Use them when their specialization improves the result.

---

# 37. Design implementation workflow

When implementing UI from a provided design/reference:

```text
REFERENCE DESIGN
       │
       ▼
Analyze visual language
       │
       ├── Layout
       ├── Typography
       ├── Color
       ├── Spacing
       ├── Radius
       ├── Borders
       ├── Shadows
       ├── Density
       ├── Motion
       └── Components
       │
       ▼
Read DESIGN.md
       │
       ▼
Map design → tokens
       │
       ▼
Define primitives
       │
       ▼
Build application shell
       │
       ▼
Build domain components
       │
       ▼
Compose screens
       │
       ▼
Visual review
       │
       ▼
Accessibility review
       │
       ▼
Responsive review
       │
       ▼
Refine
```

Do NOT jump directly from screenshot/reference to random JSX.

---

# 38. Reference design rule

If reference screenshots or inspiration are provided:

DO:

- study hierarchy
- study proportions
- study density
- study typography
- study navigation patterns
- study interaction patterns
- extract reusable principles

DO NOT:

- blindly clone branding
- copy logos
- reproduce proprietary assets
- copy text
- mechanically reproduce every pixel

The objective is:

> Capture the quality and design principles while creating an original product identity.

---

# 39. Anti-generic UI rule

Before accepting a screen, evaluate whether it could belong to any random SaaS.

If replacing the product name would make the screen indistinguishable from:

```text
CRM
Analytics dashboard
Finance SaaS
Marketing dashboard
Generic AI wrapper
```

then the design is not specific enough.

The interface should visibly communicate:

```text
software
repositories
architecture
dependencies
migration
engineering
risk
AI-assisted analysis
```

---

# 40. Avoid card soup

Do not solve every layout problem using:

```text
<Card>
<Card>
<Card>
<Card>
<Card>
<Card>
```

Use:

- sections
- tables
- trees
- graphs
- timelines
- split panes
- inspectors
- lists
- code surfaces
- command interfaces
- contextual panels
- structured text

Cards should represent actual conceptual objects, not merely containers.

---

# 41. AI-generated UI smell test

Reject or revise a design if it contains too many of these patterns:

```text
Huge gradient headline
Purple/blue glow
Three statistic cards
Four feature cards
Everything rounded-xl
Glass panels everywhere
Sparkle icon beside every AI feature
Random charts
Generic sidebar
Generic dashboard grid
Chat bubble floating bottom-right
```

The product must feel intentionally designed.

---

# 42. Screen hierarchy

Every screen needs:

```text
PRIMARY OBJECT

What is the user examining?

        │
        ▼

PRIMARY QUESTION

What are they trying to understand?

        │
        ▼

PRIMARY ACTION

What is the most likely next action?

        │
        ▼

SECONDARY CONTEXT

What information helps that decision?
```

Do not give every element equal visual importance.

---

# 43. Example: Risk screen

Primary object:

```text
Repository risks
```

Primary question:

```text
What could prevent or complicate modernization?
```

Primary action:

```text
Inspect / resolve a finding
```

Possible structure:

```text
Risks                                      12 findings

Critical  2    High  3    Medium  5    Low  2

────────────────────────────────────────────────────────

Security                                      Critical

Authentication configuration incompatible
with target framework.

src/main/.../SecurityConfig.java

3 affected files · High confidence

[Inspect finding]

────────────────────────────────────────────────────────

Compatibility                                  High

Deprecated persistence API detected.

8 usages across 4 files.

[View usages]
```

Values are illustrative.

---

# 44. Example: Migration workspace

```text
Modernization

Spring Boot 2.7                        Spring Boot 4.x
Java 11                               Java 25

CURRENT                               TARGET

─────────────────────────────────────────────────────────

Migration readiness

Dependencies        ███████████░░
Source compatibility████████░░░░░
Configuration       ██████████░░░
Tests               ███████░░░░░░

─────────────────────────────────────────────────────────

Migration sequence

01 Runtime
      │
02 Dependencies
      │
      ├───────────┐
03 Security     04 Persistence
      └─────┬─────┘
            │
05 Framework
            │
06 Validation

─────────────────────────────────────────────────────────

3 blocking risks
7 affected modules
24 files require review
```

All numbers are placeholders until real analysis exists.

---

# 45. Example: AI contextual interaction

Instead of:

```text
┌─────────────────────┐
│ Chat with AI        │
│                     │
│ Ask anything...     │
└─────────────────────┘
```

Prefer contextual intelligence:

```text
SecurityConfig.java

⚠ Migration finding

SecurityFilterChain configuration requires review.

[Explain]
[Analyze impact]
[Suggest migration]

                              ┌───────────────────────────┐
                              │ AI                       │
                              │                           │
                              │ Context                  │
                              │ SecurityConfig.java      │
                              │ Spring Security          │
                              │ Migration #04            │
                              │                           │
                              │ Ask about this finding…  │
                              └───────────────────────────┘
```

---

# 46. Trust model

This product may recommend modifications to software.

Therefore trust is essential.

Never imply:

```text
"This change is safe."
```

without evidence.

Prefer:

```text
No known blocking incompatibilities were detected
in the analyzed files.

Confidence: High

Recommended validation:
• Unit tests
• Integration tests
• Authentication flow
```

The product assists engineering judgment.

It does not replace it.

---

# 47. Security principles

Treat repository data as sensitive.

Design architecture assuming repositories may contain:

- proprietary source code
- credentials accidentally committed
- infrastructure configuration
- API definitions
- business logic
- secrets
- internal URLs

Never intentionally expose sensitive repository information to unrelated users.

Security architecture should consider:

```text
Authentication
Authorization
Repository access scopes
Tenant isolation
Secret management
Encryption
Auditability
Input validation
Rate limiting
Secure API boundaries
Prompt injection from repository content
Tool permissions
AI context isolation
```

AI-generated code must not bypass security controls for convenience.

---

# 48. Multi-agent / AI architecture principle

If multiple agents are used internally, the UI should not force users to understand internal orchestration.

Conceptually:

```text
USER
 │
 ▼
AI EXPERIENCE
 │
 ▼
ORCHESTRATION
 │
 ├── Repository Analysis
 ├── Architecture Analysis
 ├── Dependency Analysis
 ├── Security Analysis
 ├── Migration Planning
 └── Code Reasoning
```

Users care about results, evidence and actions.

Internal agent complexity should remain behind the product boundary unless exposing it creates real value.

---

# 49. Implementation priority

When building from scratch, prioritize:

```text
1. Design tokens
2. Core UI primitives
3. Application shell
4. Project navigation
5. Repository connection
6. Project overview
7. Repository explorer
8. Architecture explorer
9. Risk analysis
10. Migration workspace
11. AI contextual assistant
12. Reports
13. Advanced interactions
```

Do not implement twenty incomplete screens simultaneously.

Build vertical slices with production-quality interaction.

---

# 50. Quality gate

Before considering a feature complete, verify:

### Product

- Does the feature solve a real user task?
- Is the primary action obvious?
- Does it expose useful engineering information?
- Does AI provide context rather than decoration?

### Design

- Does it follow `DESIGN.md`?
- Does it use design tokens?
- Is hierarchy clear?
- Is information density appropriate?
- Does it avoid generic SaaS patterns?

### Engineering

- Is the component architecture maintainable?
- Are states modeled explicitly?
- Are loading/error/empty states handled?
- Is business logic separated from presentation?
- Are types strict?
- Are tests appropriate?

### Accessibility

- Keyboard usable?
- Focus visible?
- Semantic HTML?
- Contrast sufficient?
- Screen-reader labels?
- Reduced motion respected?

### Security

- Inputs validated?
- Permissions respected?
- Sensitive data protected?
- AI/tool actions bounded?
- Repository content treated as untrusted input?

### Performance

- Avoid unnecessary rerenders?
- Large repository trees virtualized when necessary?
- Heavy graphs loaded appropriately?
- Expensive operations deferred?
- Bundle impact considered?

---

# 51. Final instruction to Claude Code

When asked to design or implement a feature in this product:

DO NOT immediately start coding.

First:

```text
UNDERSTAND
    ↓
Inspect PRODUCT.md
    ↓
Inspect DESIGN.md
    ↓
Inspect relevant agents / skills
    ↓
Inspect existing architecture
    ↓
Identify reusable components
    ↓
Understand feature requirements
    ↓
Plan implementation
    ↓
IMPLEMENT
    ↓
Visual validation
    ↓
Accessibility validation
    ↓
Security validation
    ↓
REFINE
```

When ambiguity exists, prefer consistency with the established product and design system over inventing new patterns.

Do not redesign established patterns without a concrete reason.

Do not add dependencies merely because they simplify a small implementation.

Do not create generic placeholder UI when a domain-specific representation would communicate the information better.

Do not optimize for "looks impressive in a screenshot."

Optimize for:

```text
USEFUL
PRECISE
COHERENT
FAST
ACCESSIBLE
SECURE
TRUSTWORTHY
BEAUTIFULLY ENGINEERED
```

---

# 52. North Star

The final product should create this feeling:

> "I connected my repository, and now I can actually understand how this system is built, what is risky, what needs to change, why it needs to change, and how to modernize it safely."

Not:

> "I uploaded my repository and got another AI chat."

That distinction should guide every product, UX and engineering decision.