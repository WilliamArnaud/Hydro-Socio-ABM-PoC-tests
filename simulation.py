# simulation.py
import random
import matplotlib.pyplot as plt

from climate import ClimateEngine
from hydrology import Parcel
from agents import Farmer, Village

# =====================================================================
# OPENMOLE INTERFACE (Inputs & Simulation Wrapper)
# =====================================================================

SCENARIO_INPUTS = {
    # Time & Environment
    "days_to_simulate": 710,
    "daily_evaporation": 1.0,
    
    # Climate Engine
    "humid_length": 180,
    "p_peak": 8.0,
    "p_base": 3.3,
    "rho": 0.6,
    "sigma": 3.0,
    
    # Parcel Physics
    "s_max": 400.0,
    "beta": 0.015,
    "k_erosion": 0.25,
    
    # Village Governance
    "village_demand": 7.0,
    "min_env_flow": 2.0,
    "humanitarian_threshold": 0.5,
    
    # Farmer Spatial Distribution
    "farmer_profiles": ["Expander", "Traditionalist", "Expander"]
}

def run_simulation(inputs, plot=False, seed=42):
    """Runs the ABM using the input dictionary and returns an output dictionary."""
    random.seed(seed)
    
    # 1. Initialize Objects using Inputs
    climate = ClimateEngine(
        humid_length=inputs["humid_length"], 
        p_peak=inputs["p_peak"], 
        p_base=inputs["p_base"],
        rho=inputs["rho"],
        sigma=inputs["sigma"]
    )
    
    parcels = [
        Parcel(0, inputs["s_max"], inputs["beta"], inputs["k_erosion"]), 
        Parcel(1, inputs["s_max"], inputs["beta"], inputs["k_erosion"]), 
        Parcel(2, inputs["s_max"], inputs["beta"], inputs["k_erosion"])
    ]
    
    farmers = [
        Farmer(0, inputs["farmer_profiles"][0], parcels[0]),       
        Farmer(1, inputs["farmer_profiles"][1], parcels[1]), 
        Farmer(2, inputs["farmer_profiles"][2], parcels[2])        
    ]
    
    mamoudzou = Village(
        demand=inputs["village_demand"], 
        min_env_flow=inputs["min_env_flow"], 
        humanitarian_threshold=inputs["humanitarian_threshold"]
    )

    history = {"days": [], "rain": [], "river": [], "pumped": [], "turbidity": [], "restriction": []}
    
    # 2. Main Simulation Loop
    for day in range(inputs["days_to_simulate"]):
        precip = climate.step()
        restriction_today = mamoudzou.upstream_restriction_active
        
        current_q_in = 0.0
        current_sed_in = 0.0
        current_turbidity = 0.0
        
        for i in range(len(parcels)):
            p = parcels[i]
            f = farmers[i]
            
            w_avail = p.get_available_water(precip, current_q_in, inputs["daily_evaporation"])
            pump = f.make_daily_decision(restriction_today, w_avail)
            
            q_out, total_sed, t_out = p.step_hydrology(precip, current_q_in, current_sed_in, inputs["daily_evaporation"], pump)
            current_q_in = q_out
            current_sed_in = total_sed
            current_turbidity = t_out
            
        v_pumped, flow_to_ocean, treatment_cost = mamoudzou.process_daily_water(current_q_in, current_turbidity)
        
        if plot:
            history["days"].append(day)
            history["rain"].append(precip)
            history["river"].append(current_q_in)
            history["pumped"].append(v_pumped)
            history["turbidity"].append(current_turbidity)
            history["restriction"].append(1 if mamoudzou.upstream_restriction_active else 0)

    # 3. Calculate Final Output Metrics
    yield_f0 = round(((inputs["days_to_simulate"] - farmers[0].stress_days) / inputs["days_to_simulate"]) * 100, 2)
    yield_f1 = round(((inputs["days_to_simulate"] - farmers[1].stress_days) / inputs["days_to_simulate"]) * 100, 2)
    yield_f2 = round(((inputs["days_to_simulate"] - farmers[2].stress_days) / inputs["days_to_simulate"]) * 100, 2)

    outputs = {
        "system_stress_days": mamoudzou.upstream_restriction_days,
        "eco_violations": mamoudzou.eco_violations,
        "economic_treatment_cost": round(mamoudzou.total_treatment_cost, 2),
        "village_thirst_days": mamoudzou.thirst_days,
        "yield_expander_top_pct": yield_f0,
        "yield_traditional_mid_pct": yield_f1,
        "yield_expander_bot_pct": yield_f2
    }
    
    # 4. Optional Plotting
    if plot:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        ax1.plot(history["days"], history["rain"], label='Precipitation', color='skyblue', alpha=0.7)
        ax1.plot(history["days"], history["river"], label='River Flow (Incoming)', color='blue', linewidth=2)
        ax1.plot(history["days"], history["pumped"], label='Village Pumped', color='green', linewidth=2)
        ax1.set_ylabel('Water Volume')
        ax1.set_title('Hydrological Dynamics')
        ax1.legend(loc='upper right')
        ax1.grid(True, linestyle='--', alpha=0.5)

        ax2.plot(history["days"], history["turbidity"], label='Turbidity at Village', color='brown', linewidth=1.5)
        ax2.fill_between(history["days"], 0, max(history["turbidity"]), where=[r == 1 for r in history["restriction"]], color='red', alpha=0.15, label='Restriction Active')
        ax2.set_xlabel('Day of Year')
        ax2.set_ylabel('Turbidity Level')
        ax2.set_title('Water Quality and Governance')
        ax2.legend(loc='upper right')
        ax2.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    return outputs

if __name__ == "__main__":
    final_results = run_simulation(SCENARIO_INPUTS, plot=True)
    print("\n--- OPENMOLE OUTPUT DICTIONARY ---")
    for key, value in final_results.items():
        print(f"{key}: {value}")