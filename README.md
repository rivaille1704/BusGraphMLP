<h1 align="center">BusRouteDelay-MLP  
Intelligent Bus Route Decision Support System using GTFS & Multilayer Perceptrons</h1>

---

<h2>Overview</h2>

This project implements a Decision Support System for bus route planning in Hanoi using:

- GTFS (General Transit Feed Specification) data  
- A Multilayer Perceptron (MLP) model for travel-time prediction  
- A dynamically weighted directed graph  
- A custom Time-Dependent Dijkstra algorithm  
- A full web-based visualization interface  

The system predicts real-world delays under multiple traffic scenarios, then uses these predictions to compute the fastest route—not just the shortest one.

---

<h2>Highlights</h2>

Build a complete GTFS-based bus network graph  
Simulate realistic traffic delay scenarios  
Train an MLP model to predict edge travel time  
Integrate dynamic weights into a routing algorithm  
Create a web app for real-time route visualization  

---

<h2>Dataset & Preprocessing</h2>

GTFS files used:

- <code>stops.txt</code> – bus stop coordinates  
- <code>routes.txt</code> – route metadata  
- <code>trips.txt</code> – trip schedules  
- <code>stop_times.txt</code> – per-stop time information  
- <code>calendar.txt</code> – service availability  

The data pipeline includes:

- Merging GTFS tables into a unified spatio-temporal dataset  
- Ordering stop sequences per trip  
- Computing geographic distances via Haversine  
- Generating delay labels using three traffic scenarios  

<h3>Dataset Illustration</h3>


<p align="center"><img alt="image" src="https://github.com/user-attachments/assets/d0710058-8a09-46a3-93d4-347326e24002" width="80%"></p>

---

<h2>Graph Construction</h2>

The bus network is modeled as a **directed graph**, where:

- Nodes = bus stops  
- Edges = consecutive stops within the same trip  
- Extra walking edges = connect nearby stops to ensure full connectivity  

Walking edges are generated using **BallTree radius queries**, linking stops within 300 meters.

<h3>Graph Connectivity Visualization</h3>

<p align="center"><img alt="image" src="https://github.com/user-attachments/assets/d6f58e3c-0522-41e6-b34a-0a3e8f24fee9" width="80%"></p>

---

<h2>🧠 MLP Model for Travel-Time Prediction</h2>

A custom MLP is trained to predict dynamic travel time from:

- Distance  
- Estimated traffic lights  
- Hour of day (encoded via embedding)  

**Architecture (PyTorch)**:

Hour → Embedding(24, 4)
↓
Concat[distance, lights, embedding]
↓
Linear(6 → 64) + ReLU
↓
Linear(64 → 32) + ReLU
↓
Linear(32 → 1) → Predicted travel time


The model is trained on synthetic traffic scenarios:

1. **Normal** – standard congestion rules  
2. **Hard** – random “traffic traps” (linear anomalies)  
3. **Extreme** – nonlinear gridlock behavior  

<h3>📸 MLP Architecture Illustration</h3>


<p align="center"><img alt="image" src="https://github.com/user-attachments/assets/d5db9f36-b1e3-4e67-99bd-561ed32228b1" width="80%"></p>

---

<h2>🛣 Routing Algorithm</h2>

The routing engine uses a **Time-Dependent Dijkstra**:

- The edge weight is calculated dynamically using predicted/heuristic travel time.  
- Bus edges include:
  - Waiting time based on bus schedules  
  - Travel time based on traffic state  
- Walking edges have fixed cost (distance / walking speed).  

This produces **real-time fastest routes**, not just shortest-distance routes.

---

<h2>🌐 Web Application</h2>

The web app features:

- Interactive map (Leaflet.js)  
- Click-to-select origin/destination  
- Color-coded segments (walk, bus, transfer)  
- Route step visualization with icons  
- Auto-zoom to full route  

<h3>📸 Demo Results</h3>


<p align="center"><img alt="image" src="https://github.com/user-attachments/assets/e4f3014b-3a7f-496e-bc9b-e9086ea25bdf" width="80%"></p>

---

<h2>📈 Experimental Results</h2>

Performance of the MLP across the three scenarios:

- **Normal:** R² > 0.95  
- **Hard:** R² ≈ 0.85–0.90  
- **Extreme:** R² ≈ 0.80–0.85  

The system:

- Outperforms linear regression and SVM  
- Avoids congested areas even when shortest-distance routes are slower  
- Responds under ~1 second per query  

<h2>🚀 Future Improvements</h2>

- Integrating real-time GPS bus data  
- Using advanced routing (A*, contraction hierarchies)
- Personalizing routes using user travel history  
