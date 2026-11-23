#Updated 2026-11-23
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