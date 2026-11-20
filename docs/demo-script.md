# GapScout 3-Minute Live Demo Script

**Target Audience:** Recruiters, Engineering Managers, Hackathon Judges  
**Time:** Exactly 3 Minutes  
**Demo Workspace:** `GapScout Demo` (`demo@gapscout.test` / `DemoPassword123!`)

---

## Act 1: The Problem (0:00 - 0:30)
> *"Every week, thousands of local agencies, freelancers, and entrepreneurs pitch local businesses. They waste hours on Google Maps manually checking listings, guessing which businesses actually need help, and spraying generic cold emails that get marked as spam.*
> 
> *Meanwhile, founders opening new retail shops guess where to locate, often picking oversaturated blocks next to fierce competitors.*
> 
> *Meet **GapScout**: a map-based market intelligence and lead ranking engine powered by Uber H3 spatial indexing and active-learning ML."*

---

## Act 2: Spatial Intelligence & The Gap Map (0:30 - 1:15)
1. **Navigate to Gap Map:** Open `http://localhost:3000/gap/b44a4ddf-7246-4af3-80be-c51d8073dc6b` (or click on the completed Indiranagar & Koramangala Cafe scan in Dashboard).
2. **Explain the H3 Hexagonal Grid:**
   > *"Here is Bangalore's commercial corridor partitioned into H3 resolution-8 hexagons (~460m edge length). Every hex computes an opportunity score from 0 to 100 by analyzing competitor density, ratings, and commercial footfall anchors.*
   > 
   > *Green hexagons highlight underserved pockets—areas with massive footfall but low specialty cafe supply. Red hexagons show saturated clusters like 100ft Road.*
   > 
   > *Clicking on any hexagon brings up the Hex Drawer with immediate supply-demand metrics and top reasons."*

---

## Act 3: Lead Scorer & "Why This Score" (1:15 - 1:55)
1. **Navigate to Leads Pipeline:** Click **Leads** in the top navigation.
2. **Review Ranked Leads:**
   > *"Every business inside the scanned hexes is automatically extracted, enriched, and scored. Here are our top prospects ranked by blended conversion potential.*
   > 
   > *Let's click on our top lead: **Araku Coffee Indiranagar** (Score: 84.5)."*
3. **Inspect the "Why This Score" Panel:**
   > *"Notice this isn't a black box. The drawer breaks down the score across five transparent dimensions: Pain, Fit, Timing, Reachability, and Evidence. When our ML model is active, it also surfaces the top-3 SHAP feature contributions showing exactly why the algorithm prioritized this business."*

---

## Act 4: Grounded Outreach Draft & Zero Auto-Send (1:55 - 2:30)
1. **Generate Outreach Draft:** Click **Generate Cold Email Draft**.
2. **Highlight Safety & Grounding:**
   > *"GapScout strictly enforces human-in-the-loop safety. It NEVER sends messages autonomously. It drafts them.*
   > 
   > *Notice the copy: strict length cap under 120 words, zero hallucinated claims, grounded in real customer reviews, with an automatic opt-out line at the bottom.*
   > 
   > *With one click, the user can copy or open their native mail client via mailto link."*
3. **Log Contact:** Click **Mark Contacted**.

---

## Act 5: The Model Learns from Real Outcomes (2:30 - 3:00)
1. **Log Outcome:**
   > *"Two days later, the owner replies! We click **Log Reply**.*
   > 
   > *GapScout freezes the lead's feature snapshot at contact time to eliminate data leakage. Every outcome becomes a training label."*
2. **Show Model Insights Page:** Navigate to **Models**.
   > *"Because we have logged over 150 real outcomes, GapScout's automated tournament unlocked our machine learning challenger. We can inspect our active ROC-AUC (0.84), precision@10, calibration curves, and feature importance.*
   > 
   > *And over in **Active Learning**, the engine queues uncertain leads between 0.35 and 0.65 probability to help the agency gather maximum information value next week.*
   > 
   > *That's GapScout: from spatial raw data to closing high-converting local deals."*
