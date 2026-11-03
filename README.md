# The Weather App Test: temperature swings in 40 cities, 1980-2025

How much does the temperature jump around within a day, from one day to the next, and across the year? This project measures all three for 40 cities using 46 years of data, shows how the cities compare, checks whether the swings have grown since 1980, and includes an interactive app where you can look up any city in the world.

- Live app: [temperature-variations.streamlit.app](https://temperature-variations.streamlit.app/)
- Blog post: [Read it on Medium](https://ninadparab.medium.com/do-you-need-a-weather-app-4bcd13e9ef4f)
- Author: Ninad Parab ([GitHub](https://github.com/ninadparab))

## Contents

1. [Why this project](#1-why-this-project)
2. [What is in this repo](#2-what-is-in-this-repo)
3. [Key findings](#3-key-findings)
4. [The app](#4-the-app)
5. [Methodology](#5-methodology)
6. [Reproduce the analysis](#6-reproduce-the-analysis)
7. [Charts produced](#7-charts-produced)
8. [Limitations](#8-limitations)
9. [Glossary](#9-glossary)
10. [Data sources, credits and citation](#10-data-sources-credits-and-citation)

## 1. Why this project

Weather comparisons usually focus on averages: how hot, how cold, how rainy. But what makes a place inconvenient to plan around is often the *swings*. 

Yearly swings are something you can prepare for. Daily and day-to-day swings are harder: they decide what you wear when you leave in the morning, and whether you can plan a trip a few weeks ahead. So this project measures three kinds of variation separately:

| Time scale | Question | Measure (short name) |
|---|---|---|
| Within a day | How far does it warm up from the morning low to the afternoon high? | Daily range |
| From day to day | How much does today's high differ from yesterday's? | Day-to-day change |
| Across the year | How far apart are a hot day and a cold day of the year? | Yearly spread |

These are measures of *variation*, not of absolute temperature. London and Mumbai can have similar daily ranges while sitting at very different average temperatures.

## 2. What is in this repo

```
app.py                              Streamlit app (interface)
weather_core.py                     Data download, metrics, trends and charts used by the app
requirements.txt                    Python dependencies
weather_variability_simple.ipynb    Main analysis notebook (raw day-over-day changes)
weather_variability.ipynb           Same analysis with seasonally adjusted day-over-day changes
summary.csv                         (optional) 40-city summary exported from the notebook, enables the app's Compare tab
data/                               Created when you run the notebook (not committed)
figures/                            Charts saved by the notebook
```

File names may differ slightly in your copy. The two notebooks share the same structure and differ only in how day-to-day change is measured (see [5.5](#55-two-versions-of-the-day-to-day-metric)).

## 3. Key findings

These come from the 1980-2025 run of the notebook. Re-running with a different end year or swing threshold will change the numbers slightly. See the blog post for the charts.

- **Mumbai** is among the steadiest cities on both day-to-day change and daily range, which matches the experience that motivated the project. Singapore, Lagos, Jakarta and Manila are similarly steady.
- **Denver, Toronto, Minneapolis and Chicago** sit in the top right of the fingerprint chart, with large day-to-day and yearly swings. **Moscow, Beijing and Seoul** are close behind, which is a less obvious result.
- **Highland cities near the equator** (Mexico City, Nairobi, Bangalore) combine small day-to-day and yearly swings with a sizeable gap between day and night.
- Across cities there is a **broadly linear relationship between day-to-day and yearly variation**, while daily range does not follow the same pattern. Phoenix, for example, has one of the largest daily ranges without extreme yearly swings.
- **London and Seattle** are near-twins on all three measures.
- In **Mumbai**, the monsoon months (June to September) are cooler and have a much smaller daily range.
- Variability has **not shown a consistent trend since 1980** across cities: some cities show slightly larger swings, others slightly smaller. Absolute temperatures, in contrast, have trended upward.

## 4. The app

Type a city name and the app returns its three kinds of variation with charts and plain-language explanations. It works for any city in the world, not just the 40.

**What it shows**

- **Headline numbers:** daily range, day-to-day change and yearly spread for the city.
- **Within a day tab:** the daily range for each month, and a typical day's temperature curve for January, April, July and October.
- **Day to day tab:** a histogram of how much the high and low change from the previous day, the typical change, a "rough day" figure (1 day in 20 is larger), and the number of big-swing days per year. A slider sets what counts as a big swing.
- **Across the year tab:** the seasonal cycle with the 5th-95th percentile band across years.
- **Has it changed tab:** yearly values with trend lines and the change per decade for four headline metrics, with p-values.
- **Compare tab (optional):** where the city ranks among the 40 benchmark cities, with a fingerprint chart marking the city with a star.
- A download button for the yearly numbers as CSV.

**Run it locally**

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first lookup of a city downloads about 46 years of hourly data (seconds to a minute). Downloads are cached in `.cache/`, so repeating a city is instant. Add `.cache/` to `.gitignore`.

**Enable the Compare tab**

In the notebook, after the city summary cell, run:

```python
summary.to_csv("summary.csv")
```

and place `summary.csv` next to `app.py`. The app only compares big-swing days when its slider is at the same threshold used for the notebook (10 C by default).

**Deploy on Streamlit Community Cloud**

Push the repo to GitHub and create an app pointing at `app.py`. `requirements.txt` must be in the same folder as `app.py`. `scipy` is optional: the app uses numpy fallbacks if it is not installed. Cached downloads do not persist between visits on the free tier.

## 5. Methodology

### 5.1 Data

- **Source:** ERA5 reanalysis (Copernicus Climate Change Service / ECMWF), accessed through the free [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) with `models=era5`.
- **Variable:** hourly 2-metre air temperature (the notebook also downloads apparent temperature, used only for a "feels-like" extreme-range variant).
- **Period:** 1 January 1980 to 31 December 2025 (46 full years, about 403,000 hourly values per city).
- **Why ERA5:** one model, one method, every city and every year. Comparisons are not distorted by different instruments, station moves or data gaps, and the record is continuous. The trade-off is that it is a model, not a thermometer (see [limitations](#8-limitations)).
- **Download:** one request per city per 5-year chunk, saved as Parquet in `data/raw/`. Runs are resumable and skip files already downloaded.

### 5.2 Cities

40 cities were chosen to cover the world's largest metropolitan areas and most climate types. The list started from consensus top-25 metro rankings (sources disagree on exact order), plus contrast cities with well-known weather character. Three near-duplicates were dropped (Shenzhen, Tianjin, Lahore, which sit close to Guangzhou, Beijing and Delhi in ERA5's grid).

| Climate group | Cities |
|---|---|
| Tropical | Mumbai, Singapore, Lagos, Kinshasa, Dhaka, Kolkata, Manila, Jakarta, Rio de Janeiro |
| Highland | Nairobi, Mexico City, Bangalore |
| Arid | Dubai, Phoenix, Cairo, Karachi |
| Humid subtropical | Delhi, Tokyo, Osaka, Shanghai, Guangzhou, Chongqing, Sao Paulo, Buenos Aires, Sydney, Istanbul, Dallas |
| Maritime temperate | Seattle, London, Los Angeles, Cape Town |
| Continental | New York, Toronto, Chicago, Minneapolis, Denver, Moscow, Beijing, Seoul |
| Subpolar | Reykjavik |

Climate groups are a rough, hand-assigned label used for colouring and grouping charts, not a formal Koppen classification. Each city is a single point (its centre coordinates), so the result describes that location, not the whole metro area.

### 5.3 From hourly data to a daily table

1. Request hourly data in **UTC** and convert to each city's **local time** using its IANA timezone. This puts "hour of day" in local time and prevents duplicated or missing hours at daylight-saving changes.
2. Group by **local calendar day** and compute the daily mean (`tmean`), high (`tmax`), low (`tmin`) and range (`dtr = tmax - tmin`).
3. Keep only days with at least 23 hourly values (DST days have 23 or 25 hours). This drops only the partial first and last days created by the timezone shift.

Every city has more than 99.9% of the 16,802 days in 1980-2025 after this step.

### 5.4 Metrics: three scales

All metrics are computed per city per year and then averaged over the years (or trended, see 5.7).

| Scale | Metric | Definition |
|---|---|---|
| Within a day | **Daily range** (`dtr_mean`) | Mean of (daily high - daily low) |
| Day to day | **Day-to-day change** (`dod_abs_tmax`, `dod_abs_tmin`) | Mean of the absolute change in the daily high (or low) from the previous day |
| Day to day | **Rough day** (`dod_p95_tmax`) | 95th percentile of that absolute change: 1 day in 20 is larger |
| Day to day | **Big-swing days** (`swing48_days_any`) | Days per year where the high **or** the low differs from two days earlier by at least `SWING_C` (default 10 C) |
| Across the year | **Yearly spread** (`annual_p95_p5`) | 95th minus 5th percentile of daily mean temperature within the year |
| Across the year | **Extreme range** (`annual_extreme_range`) | Hottest hour of the year minus coldest hour of the year |
| Across the year | **Feels-like extreme range** | Same, using apparent temperature (approximates wind chill and heat index) |

**Why highs and lows instead of the daily mean:** a warm afternoon and a cool night average out, so the daily mean hides the swings people actually feel ("30 C today, 15 C two days later" is about the high). Tracking highs and lows separately also shows whether a city's swings come from its days or its nights.

**Why 2 days for big swings:** it matches the planning problem (a weather change within a couple of days), and it avoids counting a single-day blip. Windows overlap, so one event can count on consecutive days.

**Why percentiles for the yearly spread:** P95 minus P5 ignores a few freak days, while the extreme range captures them. Both are reported.

### 5.5 Two versions of the day-to-day metric

Day-over-day change on raw temperatures includes a small amount of normal seasonal drift (spring warm-up, autumn cool-down). Two notebooks handle this differently:

- **Simple version** (`weather_variability_simple.ipynb`): uses raw changes. Easier to explain. The drift adds a similar small amount to every city, so comparisons and the big-swing counts are largely unaffected.
- **Anomaly version** (`weather_variability.ipynb`): first subtracts each calendar day's long-term normal and measures changes in the result. The normal is the 1980-2025 average for that day of the year, computed separately for highs and lows and smoothed with a 31-day circular window. This isolates true weather swings and matters most in mild climates and in spring and autumn.

Big-swing counts use raw two-day changes in both versions, because the question is what people actually experience, and over two days the seasonal drift is typically under a degree.

### 5.6 Choosing the big-swing threshold

`SWING_C` is a judgement call. The notebook includes a sensitivity table that counts big-swing days for 5, 8, 10, 12 and 15 C. A good threshold separates cities usefully: if most cities show zero, it is too high, and if every continental city has nearly 100 such days a year, it is too low.

### 5.7 Has variability changed since 1980?

For each city and metric there is one value per year (46 points). Two simple measures of change:

- **Theil-Sen slope:** the median of all pairwise slopes. It is a trend line that a few extreme years cannot drag around. Reported per decade.
- **Kendall rank correlation p-value:** tests whether the values tend to rise or fall with time at all. p < 0.05 is flagged as a clear trend.
- **Early vs late:** mean of 1980-1989 compared with mean of 2016-2025.

With 40 cities and several metrics there are over 200 tests, so about 5% will look significant by chance alone. Read the results as patterns across many cities, not as single hits.

### 5.8 Absolute temperature trends

A companion chart shows, per city, the yearly hottest hour, yearly average, and coldest hour with Theil-Sen trend lines and slopes per decade. Comparing the three slopes shows where warming is concentrated (for example, winters warming faster than summers shrinks the yearly range).

### 5.9 Validation against weather stations

ERA5 is a model, so the notebook cross-checks it against real observations: NOAA GHCN-Daily highs and lows (quality-flagged values only) for eight US stations: Seattle-Tacoma, Dallas/Fort Worth, New York Central Park, Chicago O'Hare, Denver, Phoenix Sky Harbor, Minneapolis-St Paul and Los Angeles.

- Days where the station has no value are removed from both series, so the comparison is like-for-like.
- Reported: ERA5 bias for highs and lows (ERA5 minus station), correlation, and the percentage by which ERA5 over- or understates daily range, day-to-day change, big-swing days and extreme range.
- **Expected result:** ERA5 slightly *understates* variability, because its daily high is the highest *hourly* value and its grid cell smooths local extremes. What matters is whether the gap is similar across cities. If it is, city rankings and trends hold even if absolute values are slightly low.

Station IDs were entered by hand. If a download fails or the bias looks wrong, check the ID in NOAA's `ghcnd-stations.txt`.


## 6. Reproduce the analysis

1. `pip install -r requirements.txt` (plus `jupyter` if you use the notebooks). Python 3.10 or newer is recommended.
2. Open `weather_variability_simple.ipynb` and run cells top to bottom.
3. The fetch step downloads about 400 requests of data. The free Open-Meteo API has per-minute, per-hour and per-day limits, so the fetch is resumable: if the daily limit is hit it stops cleanly, and re-running the cell later continues where it left off.
4. Outputs: `data/daily/` (daily and annual tables as Parquet) and `figures/` (PNG charts).

Section order in the notebook: configuration, city list, cached fetch, hourly-to-daily table, sanity check, metrics, city summary, threshold sensitivity, visuals, trends, station validation.

## 7. Charts produced

- **Variability fingerprint:** yearly spread (x) against day-to-day change (y), bubble size = daily range, colour = climate group or average yearly temperature. All 40 cities are labelled, with automatic label placement that avoids overlaps.
- **Temperature carpets:** hour of day against day of year, coloured by temperature, averaged over 2010-2025, on a shared colour scale.
- **Day-to-day change charts:** several alternatives: a tail (exceedance) plot, a typical-day-versus-rough-day dot plot, a "days per year with a big jump" bar chart, a box plot of signed changes, and a stretch of real weather for a few cities.
- **Seasonal cycle with spread:** median daily temperature with a 5th-95th percentile band across years.
- **Diurnal range by month:** heatmap for all cities.
- **Trend charts:** per-city yearly series with Theil-Sen lines, and a city-by-metric heatmap of change between 1980-1989 and 2016-2025.
- **Absolute temperature trends:** hottest, average and coldest temperature per year.
- **Validation scatter:** ERA5 against station values per metric.
- **World map (optional):** interactive Plotly map of the 40 cities, coloured by a selectable metric.

## 8. Limitations

- **Model, not thermometer.** ERA5 is a reanalysis on a roughly 25 km grid. It smooths local extremes, so it tends to understate the daily range and the sharpest swings, especially in coastal and mountain cities (for example Mumbai, Los Angeles, Denver). The station check quantifies this for eight US cities only.
- **Daily highs and lows come from hourly values**, so they slightly understate true peaks.
- **Possible artificial trends.** ERA5 assimilates different observations over time (many more satellites after about 2000), which can introduce small artificial changes in variability. Trends are indicative, not definitive.
- **Multiple testing.** See 5.7.
- **One point per city.** Large metros have microclimates (coast vs inland, urban heat), and the chosen point may not match where you live.
- **Air temperature only.** Humidity, wind chill, rain, snow and storms are not included, except for the optional feels-like variant. A hot but steady city counts as low variation.
- **City selection.** 40 large cities are not a sample of the world. Empty regions on the map mean "not sampled", not "no variability".
- **Local day definition.** ERA5 days follow the local clock (including daylight saving), while some station networks use fixed local standard time, which can shift individual highs and lows slightly in the validation.
- **Raw day-to-day changes** in the simple notebook include a little seasonal drift (see 5.5).
- **API limits.** The free data service has daily limits, and the app reports them when hit.

## 9. Glossary

- **Diurnal (daily) range:** the gap between the day's highest and lowest temperature.
- **Day-to-day change:** how much the daily high (or low) differs from the previous day's.
- **Percentile (P5, P95):** the value below which 5% (or 95%) of observations fall. P95 minus P5 spans the middle 90%.
- **Anomaly:** a value minus what is normal for that calendar day.
- **Reanalysis:** a weather model that is repeatedly corrected with real observations to produce a consistent historical record.
- **Theil-Sen slope:** a robust trend slope, the median of all pairwise slopes.
- **Kendall p-value:** the probability of seeing a trend this strong in randomly ordered data. Small values suggest the trend is not chance.
- **Apparent temperature:** a "feels-like" temperature that blends air temperature with humidity and wind.

## 10. Data sources, credits and citation

- **ERA5:** Hersbach, H., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146, 1999-2049. Contains modified Copernicus Climate Change Service information.
- **Open-Meteo:** historical weather API, [open-meteo.com](https://open-meteo.com/). Please keep the attribution if you reuse the data, and check their terms for non-commercial use limits.
- **NOAA GHCN-Daily:** Menne, M. J., et al. (2012). An overview of the Global Historical Climatology Network-Daily database. *Journal of Atmospheric and Oceanic Technology*, 29, 897-910.
- **Method inspiration:** a post on comfortable-weather days in India, which in turn followed similar work for the US.

If you use this work, please link back to this repository and the accompanying blog post.

**License:** `[add a license, for example MIT, before publishing]`