# Project Specification: Predictive Memory Pressure Management

## 1. Problem Statement

On multi-tasking operating systems, physical memory is finite. When multiple processes run concurrently, memory pressure can climb rapidly due to:
1. High baseline allocation by memory-intensive software.
2. Sustained memory accumulation caused by inefficient resource lifecycle management, unreleased caches, or unbounded buffer growth.
3. System-wide contention when aggregate memory demand approaches total available physical RAM, inducing severe page swapping, thrashing, and system unresponsiveness.

Traditional OS tools (e.g., Windows Task Manager, Linux top/htop) provide instantaneous snapshots of memory usage. However, static views fail to communicate:
- Rate of change ($\Delta M / \Delta t$)
- Persistence of growth across time windows
- Predictive warnings before system thrashing begins
- Explainable attribution of which processes are primarily responsible for imminent exhaustion.

## 2. Core Objectives

1. **System & Process Telemetry**: Reliably sample system RAM metrics and individual process attributes without notable overhead.
2. **Persistent Historical Records**: Record structured time-series snapshots into a lightweight SQLite database.
3. **Behavioral Growth Modeling**: Compute growth rate, persistence of expansion, and distinguish transient spikes from sustained accumulation.
4. **Holistic Pressure & Impact Scoring**: Formulate an explainable composite index combining memory volume, growth velocity, and persistence.
5. **Short-Term Predictive Forecasting**: Project short-term pressure trajectories using transparent trend analysis.
6. **Safe Advisory Optimization**: Generate risk-prioritized, explainable recommendations without taking unverified or disruptive termination actions.
7. **Interactive Visualization & Empirical Validation**: Provide a live dashboard and test against reproducible synthetic workloads.

## 3. Scope and Boundaries

### What the System DOES:
- Observes process memory metrics (Resident Set Size, Virtual Memory, percentage share).
- Evaluates temporal behavior over consecutive sampling intervals.
- Detects sustained accumulation patterns.
- Projects near-future memory pressure states (e.g., Stable, Increasing, Potentially Critical).
- Identifies high-impact candidate processes contributing to memory strain.
- Recommends actionable, human-in-the-loop remediation steps.

### What the System DOES NOT DO:
- **No Definitive "Leak" Labels**: We do not claim proof of code-level memory leaks from external monitoring alone. Legitimate caches or buffers may grow over time; our analysis describes observed behavioral growth.
- **No Auto-Kill or Auto-Termination**: The system will never autonomously issue SIGKILL / TerminateProcess calls to processes.
- **No Machine Learning Hype**: We avoid black-box neural networks or complex deep learning early on. A transparent mathematical and statistical baseline is established first.

## 4. Key Mathematical Formulations

### 4.1 Instantaneous Growth Rate
For a process $i$ sampled at time $t$ and previous sample $t-1$:
$$G_i(t) = \frac{M_i(t) - M_i(t-1)}{\Delta t}$$
where $M_i(t)$ represents memory consumption (typically Resident Set Size in MB) and $\Delta t = t - (t-1)$ in seconds.

### 4.2 Growth Persistence
Persistence measures the consistency of positive growth across $W$ consecutive sampling intervals:
$$P_i(W) = \frac{\sum_{k=0}^{W-1} \mathbb{I}(G_i(t-k) > \epsilon)}{W}$$
where $\mathbb{I}(\cdot)$ is an indicator function yielding $1$ if true, and $\epsilon \ge 0$ is a noise threshold.

### 4.3 Composite Process Impact Score
To identify processes disproportionately driving memory stress:
$$\text{Impact}_i = w_1 \cdot \widehat{M}_i + w_2 \cdot \widehat{G}_i + w_3 \cdot P_i$$
where:
- $\widehat{M}_i \in [0, 1]$ is normalized current memory usage relative to total RAM or peak process usage.
- $\widehat{G}_i \in [0, 1]$ is normalized positive growth velocity.
- $P_i \in [0, 1]$ is the persistence factor.
- $w_1, w_2, w_3$ are transparent configurable weights ($w_1 + w_2 + w_3 = 1.0$).

## 5. Technology Stack & Justification

- **Language**: Python 3.11+ — High developer velocity, rich OS interaction libraries, cross-platform standard modules.
- **OS Telemetry**: `psutil` — Industry-standard, battle-tested system and process monitoring library.
- **Data Store**: `SQLite` — Zero-configuration, serverless, relational engine with ACID guarantees; ideal for local edge storage.
- **Unit Testing**: `pytest` — Clear assertions, modular fixtures, and comprehensive test discovery.
- **Visualization**: `Streamlit` — Fast, decoupled web UI for interactive live dashboards.
