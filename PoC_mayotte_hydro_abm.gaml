/**
* Name: PoCmayottehydroabm
* PoC for eXmodelo OpenMole training. 
* Author: williamarnaud
* Tags: 
*/


/* Notes de prise en main
 * 
 * In Python, ClimateEngine & Main Loop become a global {} in GAML. 
 * The global block is the world agent. Its 'init' sets up the board, 
 * and its 'reflex' runs every step. 
 * 
 * Class Parcel in python becomes species parcel {} in gaml. 
 * Instead of class, GAMA uses species. Every parcel is a spatial a
 * agent with a shape and color on a map. 
 * 
 * Class Farmer becomes species farmer {}. 
 * A second species can sit directly on top of a parcel and 
 * real / modify its variables. 
 * 
 * Class Village : species village 
 * A thirs species at the bottom of watershed.
 * 
 * For days in range (710) -> reflex step_name{}
 * There is no for loop here. Every reflex inside global or a species
 * automatically executes once per simulation cycle. 
 * 
 * the plots are declared at the bottom of the gapl file. 
 * experiment my_exp type : gui { output {...} }
 */

model PoCmayottehydroabm


global {
    // =====================================================================
    // 1. SCENARIO INPUTS (Exposed to GUI & OpenMOLE)
    // =====================================================================
    int days_to_simulate <- 710;
    float daily_evaporation <- 1.0;

    // Climate Engine
    int humid_length <- 180;
    float p_peak <- 8.0;
    float p_base <- 3.3;
    float rho <- 0.6;
    float sigma <- 3.0;

    // Parcel Physics
    float init_s_max <- 400.0;
    float init_beta <- 0.015;
    float init_k_erosion <- 0.25;

    // Village Governance
    float village_demand <- 7.0;
    float min_env_flow <- 2.0;
    float humanitarian_threshold <- 0.5;
    float t_critical <- 20.0;

    // Farmer Spatial Distribution (Top -> Middle -> Bottom)
    list<string> farmer_profiles <- ["Expander", "Traditionalist", "Expander"];

    // =====================================================================
    // 2. GLOBAL STATE & OUTPUT KPIs
    // =====================================================================
    float epsilon <- 0.0;
    float precip <- 0.0;
    
    // Live tracking variables for charts
    float incoming_river_flow <- 0.0;
    float incoming_turbidity <- 0.0;
    float village_pumped_today <- 0.0;

    // Ordered references
    list<parcel> parcels <- [];
    list<farmer> farmers <- [];
    village mamoudzou;

    // OpenMOLE KPIs (updated continuously)
    int system_stress_days <- 0;
    int eco_violations <- 0;
    float economic_treatment_cost <- 0.0;
    int village_thirst_days <- 0;
    float yield_expander_top_pct <- 100.0;
    float yield_traditional_mid_pct <- 100.0;
    float yield_expander_bot_pct <- 100.0;

    // =====================================================================
    // 3. INITIALIZATION
    // =====================================================================
    init {
        // 1. Create 3 cascaded parcels and attach 1 farmer to each
        loop i from: 0 to: 2 {
            create parcel number: 1 {
                id <- i;
                s_max <- init_s_max;
                beta <- init_beta;
                k_erosion <- init_k_erosion;
                storage <- s_max * 0.7;
                
                location <- {50.0, 16.0 + (i * 25.0)};
                shape <- rectangle(68.0, 19.0);
            }
            
            parcel current_p <- parcel last_with (each.id = i);
            
            create farmer number: 1 {
                id <- i;
                profile <- farmer_profiles[i];
                my_parcel <- current_p;
                do setup_profile;
                
                // Position farmer icon inside the right side of their parcel
                location <- current_p.location + {22.0, 0.0};
            }
        }

        parcels <- parcel sort_by (each.id);
        farmers <- farmer sort_by (each.id);

        // 2. Create the downstream Village
        create village number: 1 {
            demand <- village_demand;
            min_flow <- min_env_flow;
            hum_threshold <- humanitarian_threshold;
            turb_critical <- t_critical;
            
            location <- {50.0, 91.0};
            shape <- rectangle(68.0, 12.0);
        }
        mamoudzou <- first(village);
    }

    // =====================================================================
    // 4. MAIN DAILY SIMULATION LOOP
    // =====================================================================
    reflex daily_step {
        // A. Climate Engine Step
        int day_of_year <- cycle mod 365;
        float mu <- p_base;
        if (day_of_year < humid_length) {
            mu <- p_base + p_peak * sin(180.0 * day_of_year / humid_length);
        }
        epsilon <- rho * epsilon + gauss(0.0, sigma);
        precip <- max(0.0, mu + epsilon);

        // B. Today's governance signal (decided at the end of yesterday)
        bool restriction_today <- mamoudzou.upstream_restriction_active;

        float current_q_in <- 0.0;
        float current_sed_in <- 0.0;
        float current_turbidity <- 0.0;

        // C. Cascaded Top-to-Bottom Loop
        loop i from: 0 to: length(parcels) - 1 {
            parcel p <- parcels[i];
            farmer f <- farmers[i];

            float w_avail <- p.get_available_water(precip, current_q_in, daily_evaporation);
            float pump <- f.make_daily_decision(restriction_today, w_avail);

            ask p {
                do step_hydrology(precip, current_q_in, current_sed_in, daily_evaporation, pump);
                current_q_in <- q_out;
                current_sed_in <- total_sed;
                current_turbidity <- t_out;
            }
        }

        incoming_river_flow <- current_q_in;
        incoming_turbidity <- current_turbidity;

        // D. Downstream Village Processing
        ask mamoudzou {
            do process_daily_water(current_q_in, current_turbidity);
            village_pumped_today <- actual_pump;
        }

        // E. Update OpenMOLE KPIs
        int elapsed_days <- cycle + 1;
        system_stress_days <- mamoudzou.upstream_restriction_days;
        eco_violations <- mamoudzou.eco_violations;
        economic_treatment_cost <- mamoudzou.total_treatment_cost with_precision 2;
        village_thirst_days <- mamoudzou.thirst_days;

        yield_expander_top_pct <- (((elapsed_days - farmers[0].stress_days) / elapsed_days) * 100.0) with_precision 2;
        yield_traditional_mid_pct <- (((elapsed_days - farmers[1].stress_days) / elapsed_days) * 100.0) with_precision 2;
        yield_expander_bot_pct <- (((elapsed_days - farmers[2].stress_days) / elapsed_days) * 100.0) with_precision 2;

        // F. Stop condition & Console Summary
        if (elapsed_days >= days_to_simulate) {
            write "--- SIMULATION COMPLETE (" + elapsed_days + " days) ---";
            write "System Stress Days (Restrictions): " + system_stress_days;
            write "Eco Violations (Flow < Min): " + eco_violations;
            write "Economic Treatment Cost: " + economic_treatment_cost;
            write "Village Thirst Days: " + village_thirst_days;
            write "Yield Expander Top (%): " + yield_expander_top_pct;
            write "Yield Traditional Mid (%): " + yield_traditional_mid_pct;
            write "Yield Expander Bot (%): " + yield_expander_bot_pct;
            do pause;
        }
    }
}

// =====================================================================
// SPECIES 1: PARCEL
// =====================================================================
species parcel {
    int id;
    float s_max;
    float beta;
    float k_erosion;
    float storage;
    float monoculture_ratio <- 0.5;

    float q_out <- 0.0;
    float total_sed <- 0.0;
    float t_out <- 0.0;

    float get_available_water(float p_rain, float q_in, float evap) {
        float soil_avail <- max(0.0, storage + p_rain - evap);
        return soil_avail + q_in;
    }

    action step_hydrology(float p_rain, float q_in, float sed_in, float evap, float pumped) {
        float soil_water <- max(0.0, storage + p_rain - evap);
        float surface_runoff <- max(0.0, soil_water - s_max);
        float retained_soil <- min(soil_water, s_max);

        float baseflow <- beta * retained_soil;
        float gross_river_flow <- q_in + surface_runoff + baseflow;
        q_out <- max(0.0, gross_river_flow - pumped);

        storage <- retained_soil - baseflow;
        if (pumped > gross_river_flow) {
            float deficit <- pumped - gross_river_flow;
            storage <- max(0.0, storage - deficit);
        }

        float sed_gen <- k_erosion * monoculture_ratio * (p_rain ^ 2);
        total_sed <- sed_in + sed_gen;
        t_out <- total_sed / max(1.0, q_out);
    }

    aspect default {
        float saturation <- storage / s_max;
        rgb soil_color <- blend(#sienna, #dodgerblue, saturation);
        draw shape color: soil_color border: #black;
        
        draw "Parcel " + id + " (Mono: " + (monoculture_ratio with_precision 2) + ")" +
             "\nSoil: " + round(storage) + "/" + round(s_max) +
             "\nQ_out: " + (q_out with_precision 1) + " | Turb: " + (t_out with_precision 1)
             color: #white font: font("Arial", 10, #bold) at: location - {32.0, 2.0};
    }
}

// =====================================================================
// SPECIES 2: FARMER
// =====================================================================
species farmer {
    int id;
    string profile;
    parcel my_parcel;
    int stress_days <- 0;

    float demand;
    float compliance_rate;
    float expansion_rate;
    float sponge_loss;
    float last_pumped <- 0.0;

    action setup_profile {
        if (profile = "Expander") {
            demand <- 2.0;
            compliance_rate <- 0.3;
            expansion_rate <- 0.001;
            sponge_loss <- 0.3;
            my_parcel.monoculture_ratio <- 0.6;
        } else {
            demand <- 1.0;
            compliance_rate <- 0.95;
            expansion_rate <- 0.0;
            sponge_loss <- 0.0;
            my_parcel.monoculture_ratio <- 0.1;
        }
    }

    float make_daily_decision(bool restriction_active, float w_available) {
        float intended_pump <- demand;
        if (restriction_active and flip(compliance_rate)) {
            intended_pump <- 0.0;
        }

        float actual_pump <- min(intended_pump, w_available);
        last_pumped <- actual_pump;

        if (actual_pump < demand) {
            stress_days <- stress_days + 1;
        }

        if (profile = "Expander") {
            my_parcel.monoculture_ratio <- min(1.0, my_parcel.monoculture_ratio + expansion_rate);
            my_parcel.s_max <- max(80.0, my_parcel.s_max - sponge_loss);
        }

        return actual_pump;
    }

    aspect default {
        rgb agent_color <- (profile = "Expander") ? #orangered : #forestgreen;
        draw circle(3.5) color: agent_color border: #white;
        draw profile + "\nPump: " + (last_pumped with_precision 1)
             color: #white font: font("Arial", 9, #bold) at: location - {6.0, -5.5};
    }
}

// =====================================================================
// SPECIES 3: VILLAGE & GOVERNANCE
// =====================================================================
species village {
    float demand;
    float min_flow;
    float hum_threshold;
    float turb_critical;

    bool upstream_restriction_active <- false;
    int upstream_restriction_days <- 0;
    int village_restriction_days <- 0;
    int thirst_days <- 0;
    float total_treatment_cost <- 0.0;
    int eco_violations <- 0;

    float actual_pump <- 0.0;
    float flow_to_ocean <- 0.0;

    action process_daily_water(float q_in, float t_in) {
        float q_safe_to_pump <- max(0.0, q_in - min_flow);
        float daily_cost <- 0.0;

        if (t_in > turb_critical) {
            actual_pump <- 0.0;
            daily_cost <- 0.0;
        } else {
            actual_pump <- min(demand, q_safe_to_pump);
            daily_cost <- 5.0 + 0.1 * (t_in ^ 1.5);
        }

        total_treatment_cost <- total_treatment_cost + daily_cost;

        if (actual_pump < demand) {
            thirst_days <- thirst_days + 1;
            village_restriction_days <- village_restriction_days + 1;
        }

        flow_to_ocean <- max(0.0, q_in - actual_pump);

        bool eco_failure <- flow_to_ocean < min_flow;
        bool humanitarian_failure <- actual_pump < (demand * hum_threshold);

        if (eco_failure) {
            eco_violations <- eco_violations + 1;
        }

        if (eco_failure or humanitarian_failure) {
            upstream_restriction_active <- true;
            upstream_restriction_days <- upstream_restriction_days + 1;
        } else {
            upstream_restriction_active <- false;
        }
    }

    aspect default {
        rgb status_color <- upstream_restriction_active ? #firebrick : #seagreen;
        draw shape color: status_color border: #black;
        
        string status_txt <- upstream_restriction_active ? "RESTRICTION ACTIVE" : "NORMAL";
        draw "MAMOUZDOU VILLAGE [" + status_txt + "]" +
             "\nPumped: " + (actual_pump with_precision 1) + "/" + demand +
             " | Ocean Flow: " + (flow_to_ocean with_precision 1)
             color: #white font: font("Arial", 10, #bold) at: location - {32.0, 1.5};
    }
}

// =====================================================================
// EXPERIMENT & VISUALIZATION
// =====================================================================
experiment Run_PoC type: gui {
    // Expose Inputs in the UI
    parameter "Simulation Days" var: days_to_simulate category: "Simulation";
    parameter "Daily Evaporation" var: daily_evaporation category: "Environment";
    
    parameter "Humid Season Length" var: humid_length category: "Climate";
    parameter "Peak Rainfall" var: p_peak category: "Climate";
    parameter "Dry Season Base Rain" var: p_base category: "Climate";
    parameter "AR1 Memory (rho)" var: rho category: "Climate";
    parameter "AR1 Volatility (sigma)" var: sigma category: "Climate";

    parameter "Max Soil Capacity (S_max)" var: init_s_max category: "Parcel";
    parameter "Baseflow Coeff (beta)" var: init_beta category: "Parcel";
    parameter "Soil Erodibility (k)" var: init_k_erosion category: "Parcel";

    parameter "Village Demand" var: village_demand category: "Governance";
    parameter "Min Environmental Flow" var: min_env_flow category: "Governance";
    parameter "Humanitarian Threshold" var: humanitarian_threshold category: "Governance";
    parameter "Critical Turbidity Limit" var: t_critical category: "Governance";

    output {
        // 1. Interactive Spatial Map
        display "Mayotte Watershed" {
            species parcel aspect: default;
            species farmer aspect: default;
            species village aspect: default;
        }

        // 2. Hydrology Time-Series Chart
        display "Hydrology Dynamics" {
            chart "Rainfall, River Flow & Village Pumping" type: series {
                data "Precipitation" value: precip color: #skyblue;
                data "Incoming River Flow" value: incoming_river_flow color: #blue;
                data "Village Pumped" value: village_pumped_today color: #green;
            }
        }

        // 3. Water Quality & Governance Chart
        display "Water Quality & Governance" {
            chart "Turbidity & Upstream Restrictions" type: series {
                data "Turbidity at Village" value: incoming_turbidity color: #brown;
                data "Restriction Active (20=Yes)" value: mamoudzou.upstream_restriction_active ? 20.0 : 0.0 color: #red;
            }
        }

        // 4. OpenMOLE Output KPIs in Live Monitors
        monitor "Day" value: cycle;
        monitor "System Stress Days" value: system_stress_days;
        monitor "Eco Violations" value: eco_violations;
        monitor "Treatment Cost" value: economic_treatment_cost;
        monitor "Village Thirst Days" value: village_thirst_days;
        monitor "Yield Expander Top (%)" value: yield_expander_top_pct;
        monitor "Yield Traditional Mid (%)" value: yield_traditional_mid_pct;
        monitor "Yield Expander Bot (%)" value: yield_expander_bot_pct;
    }
}












