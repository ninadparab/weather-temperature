import streamlit as st

import weather_core as wc

st.set_page_config(page_title="How much does your city's temperature swing?", layout="wide")

st.title("How much does your city's temperature swing?")
st.write("Type a city name to see how much the temperature varies **within a day**, **from day to day**, "
         "and **across the year**, and whether that has changed since 1980.")
st.caption("Data: ERA5 reanalysis from Open-Meteo. It is a weather model on a ~25 km grid, not a thermometer reading, "
           "so it slightly smooths the extremes of a single spot.")


@st.cache_data(ttl=3600, show_spinner=False)
def search_city(q):
    return wc.geocode(q)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Pick a city")
    query = st.text_input("City name", placeholder="e.g. Seattle, Mumbai, Toronto")
    matches = []
    if len(query.strip()) >= 2:
        try:
            matches = search_city(query.strip())
        except Exception as e:
            st.error(f"Search failed: {e}")
        if not matches:
            st.warning("No city found. Try another spelling.")
    idx = None
    if matches:
        idx = st.selectbox("Which one?", range(len(matches)), format_func=lambda i: matches[i]["label"])
    years = st.slider("Years to analyze", wc.GRID_START, wc.END_YEAR, (wc.GRID_START, wc.END_YEAR))
    swing_c = st.slider("What counts as a big swing? (°C change within 2 days)", 5, 20, wc.BENCH_SWING_C)
    go = st.button("Analyze", type="primary", disabled=idx is None)

# ------------------------------------------------------------------ download + prepare
if go and idx is not None:
    place = matches[idx]
    bar = st.progress(0.0, text="Starting download...")
    try:
        hourly = wc.fetch_hourly(place["lat"], place["lon"], years[0], years[1],
                                 progress=lambda frac, msg: bar.progress(frac, text=msg))
    except wc.DailyLimitReached:
        bar.empty()
        st.error("The free data service has hit its daily limit. Please try again tomorrow.")
        st.stop()
    except Exception as e:
        bar.empty()
        st.error(f"Could not download data: {e}")
        st.stop()
    bar.empty()
    daily, profile = wc.build_daily(hourly, place["tz"], years[0], years[1])
    st.session_state["result"] = {"place": place, "years": years,
                                  "daily": wc.add_changes(daily), "profile": profile}

res = st.session_state.get("result")
if res is None:
    st.info("Search for a city in the sidebar, pick the right match, and press **Analyze**.")
    st.stop()

place, d, profile = res["place"], res["daily"], res["profile"]
annual = wc.annual_metrics(d, swing_c)
summ = wc.summarize(annual)
bench = wc.load_benchmark()
pct = wc.percentiles(bench, summ, include_swing=(swing_c == wc.BENCH_SWING_C)) if bench is not None else {}


def rank_note(metric):
    if metric in pct:
        return f"More variable than {pct[metric]:.0f}% of the 40 benchmark cities"
    return None


# ------------------------------------------------------------------ headline numbers
st.subheader(f"{place['label']}  ·  {res['years'][0]}-{res['years'][1]}")
c1, c2, c3 = st.columns(3)
c1.metric("Within a day", f"{summ['dtr_mean']:.1f} °C",
          help="Average gap between the day's high and the day's low.")
c2.metric("From day to day", f"{summ['dod_abs_tmax']:.1f} °C",
          help="Average change in the daily high from one day to the next.")
c3.metric("Across the year", f"{summ['annual_p95_p5']:.1f} °C",
          help="Gap between a hot day and a cold day of the year (95th minus 5th percentile of daily mean temperature).")
for col, m in ((c1, "dtr_mean"), (c2, "dod_abs_tmax"), (c3, "annual_p95_p5")):
    note = rank_note(m)
    if note:
        col.caption(note)

tab_names = ["Within a day", "Day to day", "Across the year", "Has it changed?"]
if bench is not None:
    tab_names.append("Compare with 40 cities")
tabs = st.tabs(tab_names)

# ------------------------------------------------------------------ tab 1: within a day
with tabs[0]:
    st.write("**What this shows:** how far the temperature rises from the day's low (usually near dawn) "
             "to the day's high (usually mid-afternoon). A small number means a day feels about the same all day.")
    a, b = st.columns(2)
    a.pyplot(wc.plot_dtr_by_month(d))
    b.pyplot(wc.plot_hourly_profiles(profile))

# ------------------------------------------------------------------ tab 2: day to day
with tabs[1]:
    st.write("**What this shows:** how much the high or low temperature changes from one day to the next. "
             "A large number means you can't predict tomorrow's temperature from today's.")
    typical = d["tmax_d1"].abs().median()
    rough = d["tmax_d1"].abs().quantile(0.95)
    m1, m2, m3 = st.columns(3)
    m1.metric("Typical day-to-day change in the high", f"{typical:.1f} °C", help="Half of all days change by less than this.")
    m2.metric("A rough day (1 in 20)", f"{rough:.1f} °C", help="One day in twenty changes by more than this.")
    m3.metric(f"Big-swing days per year (≥{swing_c} °C in 2 days)", f"{summ['swing48_days_any']:.1f}",
              help="Days where the high or the low differs from two days earlier by at least the chosen amount.")
    st.pyplot(wc.plot_change_hist(d))
    st.pyplot(wc.plot_big_swings(annual, swing_c))

# ------------------------------------------------------------------ tab 3: across the year
with tabs[2]:
    st.write("**What this shows:** the seasonal cycle. The line is the typical temperature on each date; the shaded "
             "band shows where 90% of years fall, so a wide band means the weather on that date is unpredictable.")
    st.pyplot(wc.plot_seasonal_band(d))
    e1, e2 = st.columns(2)
    e1.metric("Typical gap, hot vs cold days of the year", f"{summ['annual_p95_p5']:.1f} °C")
    e2.metric("Hottest hour minus coldest hour in a year", f"{summ['annual_extreme_range']:.1f} °C",
              help="Average over the years analyzed.")

# ------------------------------------------------------------------ tab 4: trends
with tabs[3]:
    st.write("**What this shows:** each yearly number (grey) with a trend line (red) that ignores one-off extreme "
             "years. The title gives the change per decade. Weather varies a lot from year to year, so a short "
             "period may show no clear trend.")
    if len(annual) < 8:
        st.info("Pick at least 8 years to see trends.")
    else:
        st.pyplot(wc.plot_trends(annual))
        st.dataframe(wc.trend_table(annual), hide_index=True)
        st.caption("p-value below 0.05 means the trend is unlikely to be chance. Model-based data can also carry "
                   "small artificial trends, so treat these as indicative.")

# ------------------------------------------------------------------ tab 5: compare
if bench is not None:
    with tabs[4]:
        st.write("**What this shows:** where your city sits among the 40 benchmark cities from the main analysis.")
        names = {"dtr_mean": "Within a day (high - low)", "dod_abs_tmax": "Day to day (change in the high)",
                 "dod_p95_tmax": "A rough day (1 in 20)", "annual_p95_p5": "Across the year (hot vs cold)",
                 "annual_extreme_range": "Hottest vs coldest hour of the year",
                 "swing48_days_any": f"Big-swing days per year (≥{wc.BENCH_SWING_C} °C)"}
        rows = [{"Measure": names[m], "This city": round(summ[m], 1),
                 "Median of 40": round(float(bench[m].median()), 1),
                 "More variable than": f"{p:.0f}% of cities"} for m, p in pct.items() if m in names]
        st.dataframe(rows, hide_index=True)
        if swing_c != wc.BENCH_SWING_C:
            st.caption(f"Big-swing days are only compared when the threshold is {wc.BENCH_SWING_C} °C, "
                       "the value used for the 40-city benchmark.")
        st.pyplot(wc.plot_fingerprint(bench, summ, place["label"].split(",")[0]))

# ------------------------------------------------------------------ download
st.download_button("Download yearly numbers (CSV)", annual.to_csv(index=False).encode("utf-8"),
                   file_name="yearly_variability.csv", mime="text/csv")
