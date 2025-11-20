🚌 Transport Timetable Scheduler

Optimize Public Transport Timings Using the Chinese Remainder Theorem (CRT)

The Transport Timetable Scheduler is an interactive Streamlit application that generates, analyzes, and optimizes public transport timetables using modular arithmetic and the Chinese Remainder Theorem.
It allows planners, students, and researchers to experiment with headways, offsets, synchronizations, and visualize transport events across a full operating day.

🚀 Features
✔️ Mathematically Optimized Scheduling

Model each route as a congruence:

t ≡ offset (mod headway)


Detect exact synchronization times across multiple routes using Generalized CRT (supports non-coprime moduli).

✔️ Automatic Offset Adjustment

Optional brute-force optimization to slightly modify offsets.

Finds a set of offsets that create perfect synchronization.

Supports different objectives:

Minimize total shift

Minimize maximum shift

✔️ Full Timetable Generation

Generates events for all routes between a start and end time.

Computes:

Next event times

Average system waiting time

Merged event timelines

✔️ Visual Timeline

Clean Matplotlib scatter plot showing route activity across the day.

✔️ CSV Export

Download schedules for:

Original timetable

Optimized (adjusted) timetable

✔️ User-Friendly Interface

Built with Streamlit

Includes preset examples (Airport, Dense City, etc.)

Dynamic input handling with expandable route configuration

📦 Installation

Clone the repository

git clone https://github.com/yourusername/transport-timetable-scheduler.git
cd transport-timetable-scheduler


Install dependencies

pip install -r requirements.txt


Run the app

streamlit run app.py

🧠 How It Works
1. Route Modeling

Each route is defined by:

Headway: minutes between vehicles

Offset: first arrival timing mod headway

Name: route label

These form congruence equations:

t ≡ offset (mod headway)

2. Synchronization Check

The app uses a generalized Chinese Remainder Theorem to determine:

If all routes synchronize

The synchronization period (LCM)

First synchronization time

3. Event Generation

For each route:

Generate all event times between start and end of day

Merge into a single timeline for display and export

4. Optimization Module

If routes cannot synchronize:

A brute-force grid search adjusts offsets within ±max_shift

New offsets must satisfy the CRT

The best solution is selected based on chosen objective

📊 Outputs
1. Synchronization Result

CRT solution displayed clearly

All synchronization times (HH:MM format)

2. Timetable DataFrame

A pivoted table showing each route’s times

3. Event CSV Export

schedule_events.csv

adjusted_schedule_events.csv (if optimized)

4. Timeline Visualization

Scatter plot representing each route over the horizon

5. Performance Metrics

Average passenger wait time

Horizon length (in minutes)

🧪 Example Use Cases

✔️ Smart city transit planning
✔️ Airport shuttle coordination
✔️ Metro–bus intermodal synchronization
✔️ University transport system design
✔️ Mathematical demonstration of CRT

⚠️ Limitations

Brute-force optimization grows exponentially:

(2 * max_shift + 1) ** n_lines


Recommended:

Use ≤6 routes if optimization is enabled

Keep max_shift between 1–5 minutes

Not designed for real-time operations; intended for planning/simulation.

🗂️ Project Structure
│── app.py                   # Main Streamlit application
│── requirements.txt         # List of dependencies
│── README.md                # Project documentation
│── /assets                  # (Optional) images or logos

🤝 Contributing

Pull requests are welcome!
If you want to add features (e.g., route maps, optimization heuristics), feel free to contribute.

📄 License

This project can be used for academic and personal purposes.
For commercial licensing, contact the author.
