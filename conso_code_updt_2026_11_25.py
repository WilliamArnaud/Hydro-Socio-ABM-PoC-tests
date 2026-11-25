import math
import random


class ClimateEngine:
    def __init__(self, humid_length=180, p_peak=25.0, p_base=5.0, rho=0.6, sigma=3.0):
        self.humid_length = humid_length
        self.p_peak = p_peak
        self.p_base = p_base
        self.rho = rho
        self.sigma = sigma
        self.epsilon = 0.0
        self.t = 0

    def step(self):
        day_of_year = self.t % 365
        if day_of_year < self.humid_length:
            mu = self.p_base + self.p_peak * math.sin(math.pi * day_of_year / self.humid_length)
        else:
            mu = self.p_base

        random_shock = random.gauss(0, self.sigma)
        self.epsilon = self.rho * self.epsilon + random_shock
        precip = max(0.0, mu + self.epsilon)
        self.t += 1
        return precip


class Parcel:
    def __init__(self, parcel_id, s_max=400.0, beta=0.015, k_erosion=0.2):
        self.id = parcel_id
        self.s_max = s_max
        self.beta = beta
        self.k_erosion = k_erosion
        self.storage = s_max * 0.7
        self.monoculture_ratio = 0.5

    def get_available_water(self, precip, q_in, evap):
        soil_avail = max(0.0, self.storage + precip - evap)
        return soil_avail + q_in

    def step_hydrology(self, precip, q_in, sed_in, evap, pumped):
        soil_water = max(0.0, self.storage + precip - evap)
        surface_runoff = max(0.0, soil_water - self.s_max)
        retained_soil = min(soil_water, self.s_max)

        baseflow = self.beta * retained_soil
        gross_river_flow = q_in + surface_runoff + baseflow
        q_out = max(0.0, gross_river_flow - pumped)

        self.storage = retained_soil - baseflow
        if pumped > gross_river_flow:
            deficit = pumped - gross_river_flow
            self.storage = max(0.0, self.storage - deficit)

        sed_gen = self.k_erosion * self.monoculture_ratio * (precip ** 2)
        total_sed = sed_in + sed_gen
        t_out = total_sed / max(1.0, q_out)
        return q_out, total_sed, t_out


class Farmer:
    def __init__(self, agent_id, profile, parcel):
        self.id = agent_id
        self.profile = profile
        self.parcel = parcel
        self.stress_days = 0

        if self.profile == "Expander":
            self.demand = 2.0
            self.compliance_rate = 0.3
            self.expansion_rate = 0.001
            self.sponge_loss = 0.3
            self.parcel.monoculture_ratio = 0.6
        else:
            self.demand = 1.0
            self.compliance_rate = 0.95
            self.expansion_rate = 0.0
            self.sponge_loss = 0.0
            self.parcel.monoculture_ratio = 0.1

    def make_daily_decision(self, restriction_active, w_available):
        intended_pump = self.demand
        if restriction_active and random.random() < self.compliance_rate:
            intended_pump = 0.0

        actual_pump = min(intended_pump, w_available)
        if actual_pump < self.demand:
            self.stress_days += 1

        if self.profile == "Expander":
            self.parcel.monoculture_ratio = min(1.0, self.parcel.monoculture_ratio + self.expansion_rate)
            self.parcel.s_max = max(80.0, self.parcel.s_max - self.sponge_loss)

        return actual_pump


class Village:
    def __init__(self, demand=10.0, min_env_flow=2.0, t_critical=20.0, humanitarian_threshold=0.5):
        self.demand = demand
        self.min_env_flow = min_env_flow
        self.t_critical = t_critical
        self.humanitarian_threshold = humanitarian_threshold

        self.upstream_restriction_active = False
        self.upstream_restriction_days = 0
        self.village_restriction_days = 0
        self.thirst_days = 0
        self.total_treatment_cost = 0.0
        self.eco_violations = 0

    def process_daily_water(self, q_in, t_in):
        q_safe_to_pump = max(0.0, q_in - self.min_env_flow)

        if t_in > self.t_critical:
            actual_pump = 0.0
            daily_cost = 0.0
        else:
            actual_pump = min(self.demand, q_safe_to_pump)
            daily_cost = 5.0 + 0.1 * (t_in ** 1.5)

        self.total_treatment_cost += daily_cost

        if actual_pump < self.demand:
            self.thirst_days += 1
            self.village_restriction_days += 1

        flow_to_ocean = max(0.0, q_in - actual_pump)
        eco_failure = flow_to_ocean < self.min_env_flow
        humanitarian_failure = actual_pump < (self.demand * self.humanitarian_threshold)

        if eco_failure:
            self.eco_violations += 1

        if eco_failure or humanitarian_failure:
            self.upstream_restriction_active = True
            self.upstream_restriction_days += 1
        else:
            self.upstream_restriction_active = False

        return actual_pump, flow_to_ocean, daily_cost


def run_simulation(inputs, seed=42):
    random.seed(int(seed))

    climate = ClimateEngine(
        humid_length=int(inputs["humid_length"]),
        p_peak=float(inputs["p_peak"]),
        p_base=float(inputs["p_base"]),
        rho=float(inputs["rho"]),
        sigma=float(inputs["sigma"])
    )

    parcels = [
        Parcel(0, float(inputs["s_max"]), float(inputs["beta"]), float(inputs["k_erosion"])),
        Parcel(1, float(inputs["s_max"]), float(inputs["beta"]), float(inputs["k_erosion"])),
        Parcel(2, float(inputs["s_max"]), float(inputs["beta"]), float(inputs["k_erosion"]))
    ]

    farmers = [
        Farmer(0, inputs["farmer_profiles"][0], parcels[0]),
        Farmer(1, inputs["farmer_profiles"][1], parcels[1]),
        Farmer(2, inputs["farmer_profiles"][2], parcels[2])
    ]

    mamoudzou = Village(
        demand=float(inputs["village_demand"]),
        min_env_flow=float(inputs["min_env_flow"]),
        t_critical=float(inputs["t_critical"]),
        humanitarian_threshold=float(inputs["humanitarian_threshold"])
    )

    days = int(inputs["days_to_simulate"])
    evap = float(inputs["daily_evaporation"])

    for _ in range(days):
        precip = climate.step()
        restriction_today = mamoudzou.upstream_restriction_active

        current_q_in = 0.0
        current_sed_in = 0.0
        current_turbidity = 0.0

        for i in range(len(parcels)):
            p = parcels[i]
            f = farmers[i]
            w_avail = p.get_available_water(precip, current_q_in, evap)
            pump = f.make_daily_decision(restriction_today, w_avail)
            q_out, total_sed, t_out = p.step_hydrology(precip, current_q_in, current_sed_in, evap, pump)
            current_q_in = q_out
            current_sed_in = total_sed
            current_turbidity = t_out

        mamoudzou.process_daily_water(current_q_in, current_turbidity)

    return {
        "system_stress_days": int(mamoudzou.upstream_restriction_days),
        "eco_violations": int(mamoudzou.eco_violations),
        "economic_treatment_cost": float(round(mamoudzou.total_treatment_cost, 2)),
        "village_thirst_days": int(mamoudzou.thirst_days),
        "yield_expander_top_pct": float(round(((days - farmers[0].stress_days) / days) * 100.0, 2)),
        "yield_traditional_mid_pct": float(round(((days - farmers[1].stress_days) / days) * 100.0, 2)),
        "yield_expander_bot_pct": float(round(((days - farmers[2].stress_days) / days) * 100.0, 2))
    }


# =====================================================================
# OPENMOLE INTERFACE (Fallback defaults if run standalone without OpenMOLE)
# =====================================================================
if "days_to_simulate" not in globals():
    days_to_simulate = 710
    daily_evaporation = 1.0
    humid_length = 180
    p_peak = 8.0
    p_base = 3.3
    rho = 0.6
    sigma = 3.0
    init_s_max = 400.0
    init_beta = 0.015
    init_k_erosion = 0.25
    village_demand = 7.0
    min_env_flow = 2.0
    humanitarian_threshold = 0.5
    t_critical = 20.0
    seed = 55

_inputs = {
    "days_to_simulate": days_to_simulate,
    "daily_evaporation": daily_evaporation,
    "humid_length": humid_length,
    "p_peak": p_peak,
    "p_base": p_base,
    "rho": rho,
    "sigma": sigma,
    "s_max": init_s_max,
    "beta": init_beta,
    "k_erosion": init_k_erosion,
    "village_demand": village_demand,
    "min_env_flow": min_env_flow,
    "humanitarian_threshold": humanitarian_threshold,
    "t_critical": t_critical,
    "farmer_profiles": ["Expander", "Traditionalist", "Expander"]
}

_res = run_simulation(_inputs, seed=seed)

# Expose output variables at top level for OpenMOLE PythonTask
system_stress_days = _res["system_stress_days"]
eco_violations = _res["eco_violations"]
economic_treatment_cost = _res["economic_treatment_cost"]
village_thirst_days = _res["village_thirst_days"]
yield_expander_top_pct = _res["yield_expander_top_pct"]
yield_traditional_mid_pct = _res["yield_traditional_mid_pct"]
yield_expander_bot_pct = _res["yield_expander_bot_pct"]