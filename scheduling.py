# app.py
import streamlit as st
import pandas as pd
import numpy as np
from math import gcd
from datetime import datetime, timedelta
import itertools
import io
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Transport Timetable Scheduler", page_icon="🚌")

st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    .stSuccess, .stWarning, .stError {
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------
# Math helpers
# --------------------
def extended_gcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = extended_gcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)

def crt_pair(a1, m1, a2, m2):
    """
    Solve:
        x ≡ a1 (mod m1)
        x ≡ a2 (mod m2)
    Returns (x mod lcm, lcm) or (None, None) if no solution.
    Works when moduli possibly non-coprime.
    """
    g, s, t = extended_gcd(m1, m2)
    if (a2 - a1) % g != 0:
        return (None, None)
    l = m1 // g * m2
    mod = m2 // g
    x = (a1 + (((a2 - a1) // g) * s % mod) * m1) % l
    return (x, l)

def crt(a_list, m_list):
    """Generalized CRT for list of congruences. Returns (x0, period) or (None, None)."""
    if not a_list:
        return (0, 1)
    x, m = a_list[0] % m_list[0], m_list[0]
    for ai, mi in zip(a_list[1:], m_list[1:]):
        x, m = crt_pair(x, m, ai % mi, mi)
        if x is None:
            return (None, None)
    return (x % m, m)

def lcm(a, b):
    return a // gcd(a, b) * b

def lcm_list(lst):
    from functools import reduce
    return reduce(lcm, lst, 1)

# --------------------
# Scheduling helpers
# --------------------
def minutes_to_time(start_dt, minutes):
    return (start_dt + timedelta(minutes=minutes)).strftime("%H:%M")

def generate_timetable(lines, day_start="06:00", day_end="22:00"):
    """
    lines: list of dicts {"name","headway","offset"} with offsets in minutes
    returns: dict with per-line minute lists, CRT result, and all events merged
    """
    start_dt = datetime.strptime(day_start, "%H:%M")
    end_dt = datetime.strptime(day_end, "%H:%M")
    horizon = int((end_dt - start_dt).total_seconds() // 60)
    a_list = [line["offset"] % line["headway"] for line in lines]
    m_list = [int(line["headway"]) for line in lines]
    x0, period = crt(a_list, m_list)
    result = {"common_sync_time": None, "period_lcm": None, "lines": {}, "all_events": []}
    if x0 is not None:
        result["common_sync_time"] = x0
        result["period_lcm"] = period
    # generate per-line times (minutes after start)
    merged = []
    
    for line in lines:
        times = []
        t = line["offset"] % line["headway"]
        while t <= horizon:
            times.append(int(t))
            merged.append({"time_min": int(t), "line": line["name"]})
            t += line["headway"]
        result["lines"][line["name"]] = sorted(times)
    # sort merged events
    merged = sorted(merged, key=lambda x: x["time_min"])
    result["all_events"] = merged
    return result, start_dt, horizon

def compute_average_wait(result, horizon):
    # build sorted set of all event times (minutes)
    events = sorted({e["time_min"] for e in result["all_events"]})
    if not events:
        return None
    total_wait = 0
    for minute in range(horizon + 1):
        # find next event >= minute
        next_event = None
        # binary search
        lo, hi = 0, len(events)-1
        while lo <= hi:
            mid = (lo+hi)//2
            if events[mid] >= minute:
                next_event = events[mid]
                hi = mid-1
            else:
                lo = mid+1
        if next_event is None:
            wait = float(horizon - minute)
        else:
            wait = next_event - minute
        total_wait += wait
    return total_wait / (horizon + 1)

# --------------------
# Optimization: small adjustments to offsets to attempt consistency
# --------------------
def find_adjusted_offsets(lines, max_shift=3, objective="min_total_shift", max_combinations=300000):
    """
    Try shifting each line offset by an integer in [-max_shift, +max_shift]
    to find a set of offsets that yields a CRT solution.
    objective: "min_total_shift" or "min_max_shift"
    Returns (best_offsets_list, crt_solution_x0, period, total_shift) or (None, None, None, None)
    Warning: combinatorial; number of combinations = (2*max_shift+1) ** n.
    """
    n = len(lines)
    choices_per_line = [list(range(-max_shift, max_shift + 1)) for _ in lines]
    total_combinations = (2*max_shift + 1) ** n
    if total_combinations > max_combinations:
        return (None, None, None, None, f"Too many combinations ({total_combinations}) - increase max_shift or reduce lines.")
    m_list = [int(l["headway"]) for l in lines]
    orig_offsets = [l["offset"] for l in lines]
    best = None
    best_obj = None
    best_shifts = None
    # iterate
    for comb in itertools.product(*choices_per_line):
        candidate_offsets = [(o + s) % m for o, s, m in zip(orig_offsets, comb, m_list)]
        x0, period = crt(candidate_offsets, m_list)
        if x0 is not None:
            # compute objective
            shifts = [abs(s) for s in comb]
            total_shift = sum(shifts)
            max_shift_used = max(shifts) if shifts else 0
            if objective == "min_total_shift":
                obj = total_shift
            else:
                obj = max_shift_used
            if best is None or obj < best_obj:
                best = candidate_offsets
                best_obj = obj
                best_shifts = comb
                best_period = period
                best_x0 = x0
                # if perfect (zero shift) found, break
                if obj == 0:
                    break
    if best is None:
        return (None, None, None, None, "No adjustment within given shift bound produced a consistent CRT solution.")
    else:
        return (best, best_x0, best_period, sum(abs(s) for s in best_shifts), None)

# --------------------
# Streamlit UI
# --------------------
st.title("🚌 Transport Timetable Scheduler")
st.markdown("### Optimize Public Transit Schedules with Mathematical Precision")
st.write("""
Welcome to the Transport Timetable Scheduler! This advanced tool leverages the Chinese Remainder Theorem (CRT) to analyze and optimize public transport schedules.

**Key Features:**
- Model routes as linear congruences: `t ≡ offset (mod headway)`
- Find exact synchronization times for multiple routes
- Automatically adjust offsets to achieve perfect coordination
- Visualize timetables and download schedules

Configure your routes below and generate optimized timetables.
""")

with st.sidebar:
    st.header("Global settings")
    day_start = st.time_input("Day start", value=datetime.strptime("06:00", "%H:%M").time())
    day_end = st.time_input("Day end", value=datetime.strptime("22:00", "%H:%M").time())
    day_start_str = day_start.strftime("%H:%M")
    day_end_str = day_end.strftime("%H:%M")
    st.markdown("---")
    st.info("Set number of lines and their headways/offsets below. Keep number of lines small (<7) if using optimization.")

with st.expander("🛤️ Configure Routes", expanded=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        n_lines = st.number_input("Number of routes/lines", min_value=1, max_value=12, value=4, step=1)
    with col2:
        default_example = st.selectbox("Load example set", ["Custom", "Airport example (4 lines)", "Dense city (5 lines)", "Simple 2-line sync"], index=0)

    # default presets
    presets = {
        "Airport example (4 lines)": [
            {"name":"Airport Express", "headway":20, "offset":5},
            {"name":"City Loop", "headway":15, "offset":10},
            {"name":"Suburb Shuttle", "headway":12, "offset":2},
            {"name":"Intercity", "headway":30, "offset":5},
        ],
        "Dense city (5 lines)": [
            {"name":"Line 1", "headway":10, "offset":0},
            {"name":"Line 2", "headway":12, "offset":3},
            {"name":"Line 3", "headway":15, "offset":7},
            {"name":"Line 4", "headway":20, "offset":10},
            {"name":"Line 5", "headway":30, "offset":5},
        ],
        "Simple 2-line sync": [
            {"name":"A", "headway":15, "offset":5},
            {"name":"B", "headway":20, "offset":5},
        ]
    }

    # Inputs for each line
    lines = []
    preset_loaded = presets.get(default_example) if default_example != "Custom" else None

    for i in range(n_lines):
        st.markdown(f"**Route {i+1}**")
        c1, c2, c3 = st.columns([2,1,1])
        if preset_loaded and i < len(preset_loaded):
            default = preset_loaded[i]
            name = c1.text_input("Name", value=default["name"], key=f"name_{i}")
            headway = c2.number_input("Headway (min)", min_value=1, value=int(default["headway"]), key=f"h_{i}")
            offset = c3.number_input("Offset (min)", min_value=0, value=int(default["offset"]), key=f"o_{i}")
        else:
            name = c1.text_input("Name", value=f"Line {i+1}", key=f"name_{i}")
            headway = c2.number_input("Headway (min)", min_value=1, value=15, key=f"h_{i}")
            offset = c3.number_input("Offset (min)", min_value=0, value=0, key=f"o_{i}")
        lines.append({"name": name.strip() or f"Line {i+1}", "headway": int(headway), "offset": int(offset)})

    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        if st.button("🚀 Generate timetable & analyze"):
            run_now = True
        else:
            run_now = False
    with colB:
        do_opt = st.checkbox("🔧 Try small offset adjustment to achieve synchronization (optimization)", value=False)
        if do_opt:
            max_shift = st.slider("Max shift in minutes (±)", 0, 15, 3)
            objective = st.selectbox("Objective", ["min_total_shift", "min_max_shift"], index=0)
            max_combinations = st.number_input("Max combinations for brute force", min_value=1000, max_value=1000000, value=300000, step=1000)

# Auto-run when parameters changed
if run_now or st.session_state.get("auto_run", True):
    st.markdown("## 📊 Analysis Results")
    # ensure valid times
    try:
        result, start_dt, horizon = generate_timetable(lines, day_start=day_start_str, day_end=day_end_str)
    except Exception as e:
        st.error(f"Error generating timetable: {e}")
        st.stop()

    ### 🔄 Synchronization Status
    col1, col2 = st.columns([2,1])
    with col1:
        if result["common_sync_time"] is not None:
            st.success(f"✅ Exact CRT solution found: t ≡ {result['common_sync_time']} (mod {result['period_lcm']}).")
            # show first few sync times in HH:MM
            sync_times = []
            t = result["common_sync_time"]
            while t <= horizon:
                sync_times.append(minutes_to_time(start_dt, t))
                t += result["period_lcm"]
            st.write("**Synchronous times (first few):**", ", ".join(sync_times[:8]))
        else:
            st.warning("⚠️ No exact CRT solution exists for the provided offsets/headways.")
    with col2:
        # metrics
        avg_wait = compute_average_wait(result, horizon)
        if avg_wait is not None:
            st.metric("⏱️ Estimated average wait (min)", f"{avg_wait:.2f}")
        st.write(f"🕒 Time window: **{day_start_str}** — **{day_end_str}** ({horizon} minutes)")

    st.markdown("### 📅 Timetable (per route)")
    # build DataFrame per line (first N)
    max_show = 30
    df_rows = []
    for name, times in result["lines"].items():
        for t in times:
            hhmm = minutes_to_time(start_dt, t)
            df_rows.append({"time_min": t, "time_hhmm": hhmm, "line": name})
    df_all = pd.DataFrame(df_rows).sort_values(["time_min", "line"]).reset_index(drop=True)
    # table view with pivot
    if not df_all.empty:
        pivot = df_all.pivot_table(index="time_hhmm", columns="line", values="time_min", aggfunc="first")
        st.dataframe(pivot.head(max_show), height=300)
    else:
        st.write("No events generated.")

    # CSV download
    csv_buffer = io.StringIO()
    df_all.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode()
    st.download_button("Download events CSV", data=csv_bytes, file_name="schedule_events.csv", mime="text/csv")

    # plot timeline
    st.markdown("### 📈 Visual Timeline of Events")
    fig, ax = plt.subplots(figsize=(12, 2 + max(0, len(lines)*0.2)))
    labels = []
    for i, (name, times) in enumerate(result["lines"].items()):
        ys = np.full(len(times), i)
        xs = np.array(times)
        ax.scatter(xs, ys, marker="|", s=200)
        labels.append(name)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Minutes since {day_start_str}")
    ax.set_ylim(-1, len(labels))
    ax.grid(axis="x", linestyle="--", linewidth=0.5)
    st.pyplot(fig)



    # If no solution and user opted for optimization, attempt adjustment
    if result["common_sync_time"] is None and do_opt:
        st.markdown("---")
        st.markdown("## 🔧 Optimization: Adjust Offsets for Synchronization")
        if n_lines > 7 and (2*max_shift+1)**n_lines > max_combinations:
            st.warning("Optimization may be infeasible for many lines and large shift. Reduce number of lines or max shift.")
        with st.spinner("Searching for feasible adjusted offsets..."):
            best, best_x0, best_period, tot_shift, error = find_adjusted_offsets(lines, max_shift=max_shift, objective=objective, max_combinations=max_combinations)
        if error:
            st.error(error)
        elif best is None:
            st.info("No feasible adjusted solution found within the given shift bounds.")
        else:
            st.success(f"Found adjusted offsets with total shift = {tot_shift} minutes that yield CRT solution.")
            st.write(f"Adjusted offsets (minutes mod headway):")
            for line, new_off in zip(lines, best):
                st.write(f"- {line['name']}: headway={line['headway']}, original offset={line['offset']} → adjusted offset = {new_off}")
            st.write(f"CRT solution: t ≡ {best_x0} (mod {best_period})")
            # show the new schedule
            new_lines = []
            for line, new_off in zip(lines, best):
                new_lines.append({"name":line["name"], "headway":line["headway"], "offset":int(new_off)})
            new_result, new_start_dt, new_horizon = generate_timetable(new_lines, day_start=day_start_str, day_end=day_end_str)
            new_avg_wait = compute_average_wait(new_result, new_horizon)
            st.metric("Estimated average wait after adjustment (min)", f"{new_avg_wait:.2f}")
            # show small table
            df_rows2 = []
            for name, times in new_result["lines"].items():
                for t in times:
                    df_rows2.append({"time_min": t, "time_hhmm": minutes_to_time(new_start_dt, t), "line": name})
            df2 = pd.DataFrame(df_rows2).sort_values(["time_min","line"]).reset_index(drop=True)
            st.dataframe(df2.pivot_table(index="time_hhmm", columns="line", values="time_min", aggfunc="first").head(40), height=300)
            csv_buf2 = io.StringIO()
            df2.to_csv(csv_buf2, index=False)
            st.download_button("Download adjusted events CSV", data=csv_buf2.getvalue().encode(), file_name="adjusted_schedule_events.csv", mime="text/csv")

st.markdown("---")
st.markdown("### ℹ️ About This Tool")
st.write("""
This Transport Timetable Scheduler leverages advanced mathematics to optimize public transit coordination.

**How it works:**
- Models each route as a linear congruence equation
- Uses the Chinese Remainder Theorem to find common synchronization points
- Calculates average waiting times and provides visual timelines
- Offers optimization to adjust offsets for better coordination

**Technical Notes:** The optimization uses brute-force search for offset adjustments. For large numbers of routes, keep shift bounds conservative. The app handles non-coprime moduli using generalized CRT with GCD checks.

Built with ❤️ using Streamlit, Python, and mathematical algorithms.
""")
st.caption("For best performance, limit routes to <7 when using optimization. Large combinatorial spaces may require increased max combinations.")
