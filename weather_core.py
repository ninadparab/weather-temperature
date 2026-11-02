"""Core functions for the city temperature-variability tool.

Data: ERA5 reanalysis served by Open-Meteo (free, no API key).
Everything here is plain Python so it can also be imported from a notebook.
"""
import calendar
import time
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy import stats

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

GRID_START = 1980                       # first year of the fixed 5-year download grid
END_YEAR = date.today().year - 1        # last full year
CHUNK_YEARS = 5
CACHE_DIR = Path(".cache")              # downloaded chunks are saved here, so repeats are instant
BENCH_SWING_C = 10                      # threshold used when the benchmark summary.csv was made

BLUE, RED, ORANGE, GREEN, GRAY = "#1f77b4", "#d62728", "#ff7f0e", "#2ca02c", "#7f7f7f"


class DailyLimitReached(Exception):
    pass


# --------------------------------------------------------------------------- search

def geocode(name, count=8):
    """Look up a city name. Returns a list of {label, lat, lon, tz}."""
    r = requests.get(GEOCODE_URL, params={"name": name, "count": count, "language": "en", "format": "json"},
                     timeout=30)
    r.raise_for_status()
    out = []
    for x in r.json().get("results") or []:
        label = ", ".join(p for p in [x.get("name"), x.get("admin1"), x.get("country")] if p)
        out.append({"label": label, "lat": x["latitude"], "lon": x["longitude"],
                    "tz": x.get("timezone") or "UTC"})
    return out


# --------------------------------------------------------------------------- download

def year_chunks(start_year, end_year, size):
    y = start_year
    while y <= end_year:
        yield y, min(y + size - 1, end_year)
        y += size


def _fetch_chunk(lat, lon, y0, y1, max_retries=5):
    params = {"latitude": lat, "longitude": lon, "start_date": f"{y0}-01-01", "end_date": f"{y1}-12-31",
              "hourly": "temperature_2m", "timezone": "GMT", "models": "era5"}
    for attempt in range(max_retries):
        r = requests.get(ARCHIVE_URL, params=params, timeout=120)
        if r.status_code == 200:
            return r.json()
        reason = ""
        try:
            reason = r.json().get("reason", "")
        except Exception:
            pass
        if r.status_code == 429:
            if "daily" in reason.lower():
                raise DailyLimitReached(reason)
            time.sleep(20 * (attempt + 1))          # minute/hour limit: wait and retry
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {reason or r.text[:200]}")
    raise RuntimeError("Too many retries (rate limited). Try again in a few minutes.")


def fetch_hourly(lat, lon, start_year, end_year, progress=None):
    """Hourly temperature (UTC) for the years requested. progress(fraction, message) is optional."""
    CACHE_DIR.mkdir(exist_ok=True)
    chunks = [c for c in year_chunks(GRID_START, END_YEAR, CHUNK_YEARS) if c[1] >= start_year and c[0] <= end_year]
    frames = []
    for i, (y0, y1) in enumerate(chunks):
        path = CACHE_DIR / f"{lat:.2f}_{lon:.2f}_{y0}_{y1}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
        else:
            j = _fetch_chunk(lat, lon, y0, y1)
            df = pd.DataFrame({"time": pd.to_datetime(j["hourly"]["time"], utc=True),
                               "t": pd.Series(j["hourly"]["temperature_2m"], dtype="float64")})
            df.to_parquet(path, index=False)
        frames.append(df)
        if progress:
            progress((i + 1) / len(chunks), f"Downloaded {y0}-{y1}")
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- metrics

def build_daily(hourly, tz, start_year, end_year):
    """Hourly UTC -> local-day table (mean, high, low, range) and a month x hour average profile."""
    h = hourly.drop_duplicates("time").sort_values("time")
    local = h["time"].dt.tz_convert(tz)
    h = h.assign(date=local.dt.tz_localize(None).dt.normalize(), hour=local.dt.hour.values, month=local.dt.month.values)
    h = h[(h["date"].dt.year >= start_year) & (h["date"].dt.year <= end_year)]

    g = h.groupby("date")["t"]
    daily = pd.DataFrame({"n": g.count(), "tmean": g.mean(), "tmax": g.max(), "tmin": g.min()})
    daily = daily[daily["n"] >= 23].copy()                    # drop partial days (23/25 hours happen on DST days)
    daily["dtr"] = daily["tmax"] - daily["tmin"]              # diurnal temperature range
    daily = daily.reset_index()
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month

    profile = h.groupby(["month", "hour"])["t"].mean().unstack("hour")
    return daily, profile


def add_changes(daily):
    """Day-over-day and 2-day changes in the daily high and low (consecutive calendar days only)."""
    d = daily.sort_values("date").reset_index(drop=True).copy()
    gap1 = d["date"].diff().dt.days
    gap2 = d["date"].diff(2).dt.days
    for v in ("tmax", "tmin"):
        d[f"{v}_d1"] = d[v].diff().where(gap1 == 1)
        d[f"{v}_d2"] = (d[v] - d[v].shift(2)).where(gap2 == 2)
    return d


def annual_metrics(d, swing_c=10):
    big = (d["tmax_d2"].abs() >= swing_c) | (d["tmin_d2"].abs() >= swing_c)
    d = d.assign(big=big.astype(int), abs_tmax_d1=d["tmax_d1"].abs(), abs_tmin_d1=d["tmin_d1"].abs())
    annual = d.groupby("year").agg(
        dtr_mean=("dtr", "mean"),
        dod_abs_tmax=("abs_tmax_d1", "mean"),
        dod_abs_tmin=("abs_tmin_d1", "mean"),
        dod_p95_tmax=("abs_tmax_d1", lambda s: s.quantile(0.95)),
        swing48_days_any=("big", "sum"),
        tmean_p05=("tmean", lambda s: s.quantile(0.05)),
        tmean_p95=("tmean", lambda s: s.quantile(0.95)),
        tmax_year=("tmax", "max"),
        tmin_year=("tmin", "min"),
    ).reset_index()
    annual["annual_p95_p5"] = annual["tmean_p95"] - annual["tmean_p05"]
    annual["annual_extreme_range"] = annual["tmax_year"] - annual["tmin_year"]
    return annual


SUMMARY_COLS = ["dtr_mean", "dod_abs_tmax", "dod_abs_tmin", "dod_p95_tmax", "swing48_days_any",
                "annual_p95_p5", "annual_extreme_range"]


def summarize(annual):
    return {c: float(annual[c].mean()) for c in SUMMARY_COLS}


def trend_table(annual):
    """Theil-Sen slope per decade and Kendall p-value for the headline metrics."""
    labels = {"dtr_mean": "Daily range (high - low)", "dod_abs_tmax": "Avg day-to-day change in the high",
              "swing48_days_any": "Big-swing days per year", "annual_p95_p5": "Yearly spread (hot vs cold days)"}
    rows = []
    for m, label in labels.items():
        a = annual.dropna(subset=[m])
        if len(a) < 8:
            continue
        slope = stats.theilslopes(a[m].values, a["year"].values)[0]
        _, p = stats.kendalltau(a["year"].values, a[m].values)
        rows.append({"metric": label, "change_per_decade": round(slope * 10, 3), "p_value": round(p, 3),
                     "clear_trend": "yes" if p < 0.05 else "no"})
    return pd.DataFrame(rows)


def load_benchmark(path=None):
    """Optional: summary.csv exported from the 40-city notebook (index = city)."""
    path = Path(path) if path else Path(__file__).parent / "summary.csv"
    if not path.exists():
        return None
    b = pd.read_csv(path, index_col=0)
    return b if {"dtr_mean", "dod_abs_tmax", "annual_p95_p5"} <= set(b.columns) else None


def percentiles(bench, summ, include_swing=True):
    """Share of benchmark cities that are LESS variable than this city, per metric."""
    out = {}
    for m in ["dtr_mean", "dod_abs_tmax", "dod_p95_tmax", "annual_p95_p5", "annual_extreme_range"] + \
             (["swing48_days_any"] if include_swing else []):
        if m in bench.columns:
            out[m] = float((bench[m] < summ[m]).mean() * 100)
    return out


# --------------------------------------------------------------------------- plots

def _month_labels(ax):
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([calendar.month_abbr[i][0] for i in range(1, 13)])


def plot_dtr_by_month(daily):
    m = daily.groupby("month")["dtr"].mean().reindex(range(1, 13))
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(range(1, 13), m.values, color=ORANGE)
    _month_labels(ax)
    ax.set_ylabel("Average high minus low (°C)")
    ax.set_title("How big is the daily swing, month by month?")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_hourly_profiles(profile):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    for mth, c in {1: BLUE, 4: GREEN, 7: RED, 10: ORANGE}.items():
        if mth in profile.index:
            ax.plot(profile.columns, profile.loc[mth].values, label=calendar.month_abbr[mth], color=c, lw=2)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hour of day (local time)")
    ax.set_ylabel("Average temperature (°C)")
    ax.set_title("A typical day, in four months")
    ax.legend(title="Month")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_change_hist(d):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, v, name, c in zip(axes, ["tmax", "tmin"], ["daily high", "daily low"], [RED, BLUE]):
        x = d[f"{v}_d1"].dropna()
        p95 = x.abs().quantile(0.95)
        ax.hist(x, bins=np.arange(-25, 25.5, 1), color=c, alpha=0.8)
        ax.axvline(-p95, ls="--", color="black")
        ax.axvline(p95, ls="--", color="black")
        ax.set_xlim(-20, 20)
        ax.set_title(f"Change in the {name} from the day before\n(dashed: 1 day in 20 is more extreme)", fontsize=10)
        ax.set_xlabel("°C  (negative = cooler than yesterday)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Number of days")
    fig.tight_layout()
    return fig


def _trend_line(ax, x, y, color="black"):
    ok = ~np.isnan(y)
    if ok.sum() >= 8:
        slope, icpt = stats.theilslopes(y[ok], x[ok])[:2]
        ax.plot(x, icpt + slope * x, color=color, lw=2)
        return slope * 10
    return None


def plot_big_swings(annual, swing_c):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(annual["year"], annual["swing48_days_any"], color=ORANGE)
    s = _trend_line(ax, annual["year"].values, annual["swing48_days_any"].values.astype(float))
    ax.set_ylabel("Days per year")
    ax.set_title(f"Days when the high or low moved {swing_c} °C or more within 2 days")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_seasonal_band(d):
    doy = d["date"].dt.dayofyear - ((d["date"].dt.is_leap_year) & (d["date"].dt.month > 2)).astype(int)
    d = d.assign(doy=doy.clip(1, 365))
    q = d.groupby("doy")["tmean"].quantile([0.05, 0.5, 0.95]).unstack()

    def smooth(s, w=7):
        ext = pd.concat([s.iloc[-w:], s, s.iloc[:w]])
        return pd.Series(ext.rolling(w, center=True).mean().iloc[w:-w].values, index=s.index)

    lo, med, hi = smooth(q[0.05]), smooth(q[0.5]), smooth(q[0.95])
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.fill_between(q.index, lo, hi, color=BLUE, alpha=0.25, label="Middle 90% of years")
    ax.plot(q.index, med, color=BLUE, lw=2.5, label="Typical (median)")
    ax.set_xticks([1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
    ax.set_xticklabels(list("JFMAMJJASOND"))
    ax.set_ylabel("Daily mean temperature (°C)")
    ax.set_title("The seasons, and how much the weather on each date varies from year to year")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_trends(annual):
    specs = [("dtr_mean", "Daily range (high - low), °C"),
             ("dod_abs_tmax", "Avg day-to-day change in the high, °C"),
             ("swing48_days_any", "Big-swing days per year"),
             ("annual_p95_p5", "Yearly spread (hot vs cold days), °C")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharex=True)
    for ax, (m, title) in zip(axes.ravel(), specs):
        x, y = annual["year"].values, annual[m].values.astype(float)
        ax.plot(x, y, marker="o", ms=3, lw=1, color=GRAY)
        s = _trend_line(ax, x, y, color=RED)
        ax.set_title(title + (f"   ({s:+.2f} per decade)" if s is not None else ""), fontsize=10)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_fingerprint(bench, summ, label):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(bench["annual_p95_p5"], bench["dod_abs_tmax"], s=60, color="lightgray", edgecolor="white", label="40 benchmark cities")
    ax.scatter([summ["annual_p95_p5"]], [summ["dod_abs_tmax"]], s=260, marker="*", color=RED, edgecolor="black", zorder=3, label=label)
    ax.set_xlabel("Yearly swing: P95 - P5 of daily mean temperature (°C)")
    ax.set_ylabel("Day-to-day swing in the daily high (°C)")
    ax.set_title("Where does your city sit among the 40?")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig
