
import math
import random

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
