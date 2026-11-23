# Socio-Hydrological Toy Model (PhD Proof-of-Concept)

A minimalist, coupled Agent-Based Model (ABM) and semi-distributed hydrological cascade designed as a fast, computationally cheap sandbox for a broader PhD research project. 

## Purpose of this Repository

Before deploying computationally expensive model exploration pipelines on the full-scale socio-hydrological model, this repository serves as a **testbed to prototype, benchmark, and validate state-of-the-art numerical methods**, including:
* **Global Sensitivity Analysis (GSA):** Sobol indices, Morris screening, Shapley effects, and time-varying sensitivity analysis.
* **Model Exploration & Scenario Discovery:** Latin Hypercube Sampling (LHS), adaptive sampling, OpenMOLE-style pattern space exploration, and tipping-point / regime-shift detection.
* **Meta-Modeling & Surrogate Emulation:** Gaussian Processes (Kriging), Polynomial Chaos Expansion (PCE), and neural surrogates for fast emulation of non-linear, threshold-driven socio-environmental dynamics.

---

## Model Overview

Inspired by socio-hydrological dynamics in tropical island catchments (such as Mayotte), this reduced model captures the competing pressures between upstream agricultural land-use change and downstream municipal water security over a 1-year (365-day) seasonal cycle.

### Core Dynamics
* **Hydrological Cascade (`Parcel`):** A 1D chain of sequentially linked spatial units separating local soil moisture storage (the "sponge" capacity) from passing river channel discharge.
* **Stochastic Seasonal Climate (`ClimateEngine`):** Generates daily precipitation driven by a sinusoidal monsoon wet season and a dry baseflow season using a Gamma distribution.
* **Heterogeneous Farmer Agents (`Farmer`):**
  * **Traditionalists:** Maintain agroforestry/forest cover, preserve soil retention capacity, and respect drought water restrictions.
  * **Expanders:** Continuously clear forest to expand agricultural land, degrading local soil infiltration capacity, increasing surface runoff and erosion, and largely ignoring water restrictions.
* **Downstream Municipality (`Village`):** Extracts river water to meet municipal demand. It suffers from **quantitative scarcity** (insufficient flow during the dry season) and **qualitative scarcity** (treatment plant shutdowns triggered by high sediment turbidity during wet-season storms).

---

## Experimental Design: Inputs & Outputs

The model is structured around a compact parameter space to facilitate rapid surrogate fitting and sensitivity testing:

### Key Input Parameters
1. **Drought Intensity ($\Delta P$):** Reduction in precipitation volume during the wet/dry cycle.
2. **Agent Composition:** Ratio of `Expander` vs. `Traditionalist` farmers in the catchment.
3. **Policy Enforcement:** Compliance rate / effectiveness of municipal drought pumping restrictions.
4. **Infrastructure Capacity:** Upstream reservoir storage volume buffering seasonal flows.

### Target Output Metrics
* **Municipal Water Security:** Total annual days of water shortage (`thirst_days`), decomposed into *quantitative drought days* vs. *turbidity shutdown days*.
* **Agricultural Yield:** End-of-year crop production accounting for non-linear cumulative and consecutive water stress.
* **Ecological / Hydrological Health:** Remaining catchment soil retention capacity ($S_{\max}$) and river discharge to the ocean ($Q_{\text{ocean}}$).

---

## Repository Structure

```text
├── src/
│   ├── climate.py          # Stochastic monsoon/dry season generator
│   ├── hydrology.py        # Parcel water balance, baseflow, and turbidity routing
│   ├── agents.py           # Farmer archetypes and downstream Village logic
│   └── simulation.py       # 365-day coupled simulation wrapper
├── experiments/
│   ├── sensitivity/        # GSA scripts (Sobol, Morris, etc.)
│   ├── exploration/        # Space-filling and regime-shift search
│   └── metamodels/         # Surrogate training and validation notebooks
└── README.md
