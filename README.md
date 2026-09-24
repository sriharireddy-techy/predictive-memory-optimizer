# Predictive Memory Pressure Management and Process-Aware Resource Optimization

An Operating Systems project designed to monitor process memory dynamics, detect increasing memory pressure, assess process impact, predict future pressure trends, and generate safe resource-management recommendations.

---

## 1. Project Overview

Modern operating systems execute many concurrent processes sharing limited physical memory (RAM). While standard task managers show static snapshots of instantaneous memory consumption, they do not answer key behavioral questions:
- Is a process consuming memory steadily, or is its footprint continuously growing over time?
- Is overall system memory pressure rising toward dangerous saturation thresholds?
- Which specific processes are driving current memory pressure?
- How much time remains before available physical memory becomes critically depleted if existing trends persist?

This project builds an end-to-end, modular, and explainable OS resource-monitoring and prediction engine implemented in Python on a laptop environment.

---

## 2. Core Architecture

The system is structured as a unidirectional analysis pipeline:

```
                  HOST LAPTOP (OS & Hardware)
                              |
                              v
                   PROCESS DATA COLLECTOR
                              |
                              v
                      HISTORICAL STORAGE
                              |
                              v
                   MEMORY TREND ANALYZER
                              |
                    +---------+---------+
                    |                   |
                    v                   v
             ABNORMAL GROWTH      MEMORY PRESSURE
                DETECTOR              ANALYZER
                    |                   |
                    +---------+---------+
                              |
                              v
                    PROCESS IMPACT SCORE
                              |
                              v
                    PRESSURE PREDICTOR
                              |
                              v
                 RESOURCE RECOMMENDATION
                       ENGINE
                              |
                              v
                         DASHBOARD
                              |
                              v
                      EVALUATION SUITE
```

---

## 3. Key Operating Systems Concepts

- **Virtual vs. Physical Memory**: Distinction between virtual address space allocations and physical frames in Resident Set Size (RSS).
- **Resident Set Size (RSS)**: Actual physical RAM occupied by a process.
- **Process States & Control**: Process ID (PID), process execution states, CPU utilization, thread count, and process lifecycle events.
- **Memory Pressure**: System-wide scarcity of free/available physical memory leading to paging, swapping, or thrashing.
- **Explainable Heuristics vs. Premature ML**: Accurate statistical baselines (rate of change, persistence, moving slopes) before introducing complex models.

---

## 4. Safety Principles

Safety is a core requirement of this project:
- **No Unsafe Interventions**: The system does not terminate, kill, or suspend processes automatically.
- **No Modification of Critical OS Processes**: Core operating system tasks are protected and never interfered with.
- **Advisory Recommendations**: Output is provided as informative warnings, risk prioritization, and simulated mitigation plans.
- **Accurate Terminology**: High memory usage is not conflated with a memory leak. Phenomena are accurately termed *sustained memory growth*, *abnormal memory growth*, or *memory pressure*.

---

## 5. Phased Roadmap

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Project Planning, Workspace Setup & Architecture Specification | Completed |
| **Phase 1** | Process and Memory Monitoring (psutil snapshots) | Completed |
| **Phase 2** | Historical Memory Storage (SQLite time-series) | Completed |
| **Phase 3** | Memory Behaviour & Growth Analysis (growth rate, persistence) | Completed |
| **Phase 4** | Memory Pressure & Process Impact Scoring | Completed |
| **Phase 5** | Predictive Memory Pressure Analysis (trend forecasting) | In Progress (Next) |
| **Phase 6** | Safe Resource Recommendation Engine | Pending |
| **Phase 7** | Interactive Monitoring Dashboard (Streamlit) | Pending |
| **Phase 8** | Controlled Experiments & Evaluation (workload benchmarks) | Pending |
| **Phase 9** | Final Documentation, Demo & Viva Preparation | Pending |

---

## 6. Directory Structure

```
predictive-memory-optimizer/
├── README.md              # Project overview and roadmap
├── PROJECT_SPEC.md        # Detailed requirements and technical specifications
├── ARCHITECTURE.md        # Architectural decisions and dataflow diagrams
├── requirements.txt       # Project dependencies
├── .gitignore             # Ignored runtime and generated files
├── src/
│   ├── collector/         # Phase 1: Real-time process & system metrics collection
│   ├── storage/           # Phase 2: SQLite database storage & query interface
│   ├── analysis/          # Phase 3: Time-series growth & trend calculations
│   ├── detection/         # Phase 4: System pressure & abnormal growth detection
│   ├── prediction/        # Phase 5: Explainable trend projection & forecasting
│   ├── optimization/      # Phase 6: Safe recommendation engine
│   └── dashboard/         # Phase 7: Streamlit visual monitoring interface
├── tests/                 # Modular unit & integration test suites
├── experiments/           # Phase 8: Controlled workload scripts & benchmark logs
├── data/                  # Local SQLite database files & test traces (git-ignored)
└── docs/                  # Phase 9: Reports, presentations, and viva preparation
```

---

## 7. Setup & Verification

1. **Prerequisites**: Python 3.11+
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Phase Verification Tests**:
   ```bash
   pytest tests/
   ```
