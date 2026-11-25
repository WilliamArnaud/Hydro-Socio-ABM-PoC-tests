
import math
import random

class ClimateEngine:
    def __init__(self, humid_length=180, p_peak=25.0, p_base = 5.0, rho=0.6, sigma=3.0):
        self.humid_length = humid_length
        self.p_peak = p_peak     # Max average rainfall in peak wet season (mm)
        self.p_base = p_base     # Baseline rain during the dry season (mm)
        self.rho = rho           # AR1 memory coefficient (0 to 1)
        self.sigma = sigma       # AR1 volatility
        self.epsilon = 0.0       # Initial noise
        self.t = 0               # Day counter

    def step(self):
        day_of_year = self.t % 365
        
        # Calculate seasonal mean
        if day_of_year < self.humid_length:
            mu = self.p_base + self.p_peak * math.sin(math.pi * day_of_year / self.humid_length)
        else:
            mu = self.p_base
            
        # AR1 Noise generation
        random_shock = random.gauss(0, self.sigma)
        self.epsilon = self.rho * self.epsilon + random_shock
        
        # Final precipitation (>=0)
        precip = max(0.0, mu + self.epsilon)
        self.t += 1
        return precip


class Parcel:
    def __init__(self, parcel_id, s_max=400.0, beta=0.015, k_erosion=0.2):
        self.id = parcel_id
        self.s_max = s_max           # Max soil water retention
        self.beta = beta             # Subsurface flow coefficient
        self.k_erosion = k_erosion   # Sensitivity to erosion
        self.storage = s_max * 0.7   # Initial soil moisture (70% full)
        
        # Land use (will be dynamically changed by Farmers later)
        self.monoculture_ratio = 0.5 

    def get_available_water(self, precip, q_in, evap):
        """Calculates total water available to the farmer (soil moisture + river channel)"""
        soil_avail = max(0.0, self.storage + precip - evap)
        return soil_avail + q_in

    def step_hydrology(self, precip, q_in, sed_in, evap, pumped):
        # 1. Soil infiltration after ET
        soil_water = max(0.0, self.storage + precip - evap)
        
        # 2. Surface runoff & retained soil
        surface_runoff = max(0.0, soil_water - self.s_max)
        retained_soil = min(soil_water, self.s_max)
        
        # 3. Subsurface baseflow (slow leak)
        baseflow = self.beta * retained_soil
        
        # 4. River channel routing (upstream + local runoff + local baseflow - pumping)
        gross_river_flow = q_in + surface_runoff + baseflow
        q_out = max(0.0, gross_river_flow - pumped)
        
        # 5. Final soil storage (subtract baseflow, and any deficit pumping from soil)
        self.storage = retained_soil - baseflow
        if pumped > gross_river_flow:
            deficit = pumped - gross_river_flow
            self.storage = max(0.0, self.storage - deficit)
        
        # 6. Calculate Turbidity (Sediments)
        sed_gen = self.k_erosion * self.monoculture_ratio * (precip ** 2)
        total_sed = sed_in + sed_gen
        t_out = total_sed / max(1.0, q_out) 
        
        return q_out, total_sed, t_out




import math
import random


class Farmer:
    def __init__(self, agent_id, profile, parcel):
        self.id = agent_id
        self.profile = profile  # "Expander" or "Traditionalist"
        self.parcel = parcel    # The physical land this farmer occupies
        self.stress_days = 0    # Tracks crop health (higher = worse yield)
        
        # Profile specific parameters
        if self.profile == "Expander":
            self.demand = 2.0              # High water need
            self.compliance_rate = 0.3     # Only respects restrictions 20% of the time
            self.expansion_rate = 0.001    # Daily rate of clearing land
            self.sponge_loss = 0.3         # Daily loss of soil retention capacity
            self.parcel.monoculture_ratio = 0.6
        else: # Traditionalist
            self.demand = 1.0              # Low water need
            self.compliance_rate = 0.95    # Respects restrictions 95% of the time
            self.expansion_rate = 0.0      # Does not expand
            self.sponge_loss = 0.0         # Maintains soil health
            self.parcel.monoculture_ratio = 0.1
    

    def make_daily_decision(self, restriction_active, w_available):
        # 1. Decide Intended Pumping
        intended_pump = self.demand
        
        if restriction_active:
            # Roll a random number between 0 and 1
            if random.random() < self.compliance_rate:
                intended_pump = 0.0 # Complies and shuts off the pump
                
        # 2. Calculate Actual Pumping (cannot pump more than is available)
        actual_pump = min(intended_pump, w_available)
        
        # 3. Assess Crop Stress (Did they get the water they needed?)
        # If they needed water and didn't get it (due to compliance or dry soil)
        if actual_pump < self.demand:
            self.stress_days += 1
            
        # 4. Land Expansion Feedback
        if self.profile == "Expander":
            # Increase monoculture ratio (caps at 1.0)
            self.parcel.monoculture_ratio = min(1.0, self.parcel.monoculture_ratio + self.expansion_rate)
            # Degrade the soil's capacity to hold water (bottoms out at 50.0)
            self.parcel.s_max = max(80.0, self.parcel.s_max - self.sponge_loss)
            
        return actual_pump


class Village:
    def __init__(self, demand=10.0, min_env_flow=2.0, t_critical=20.0, humanitarian_threshold=0.5):
        self.demand = demand
        self.min_env_flow = min_env_flow
        self.t_critical = t_critical      
        self.humanitarian_threshold = humanitarian_threshold # e.g., 0.5 means 50% of demand
        
        # Tracking metrics
        self.upstream_restriction_active = False 
        self.upstream_restriction_days = 0       
        self.village_restriction_days = 0        
        self.thirst_days = 0                     
        self.total_treatment_cost = 0.0          
        self.eco_violations = 0                  

    def process_daily_water(self, q_in, t_in):
        # 1. Calculate how much water is SAFE to take
        q_safe_to_pump = max(0.0, q_in - self.min_env_flow)
        
        # 2. Check the treatment plant limits
        if t_in > self.t_critical:
            actual_pump = 0.0
            daily_cost = 0.0
        else:
            actual_pump = min(self.demand, q_safe_to_pump)
            daily_cost = 5.0 + 0.1 * (t_in ** 1.5)
            
        self.total_treatment_cost += daily_cost
        
        # 3. Assess Village Restrictions
        if actual_pump < self.demand:
            self.thirst_days += 1
            self.village_restriction_days += 1  
            
        # 4. Final flow to the ocean
        flow_to_ocean = max(0.0, q_in - actual_pump)
        
        # 5. GOVERNANCE: The Dual-Trigger Restriction System
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


# simulation.py
import random
import matplotlib.pyplot as plt

# =====================================================================
# INTERFACE (Inputs & Simulation Wrapper)
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