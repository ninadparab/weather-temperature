# City temperature variability tool

Type a city name and get its temperature variation at three time scales, plus charts:

- **Within a day**: average gap between the daily high and low, by month, and a typical day's temperature curve
- **From day to day**: how much the daily high and low change from one day to the next, a "rough day" (1 in 20) figure, and the number of big-swing days per year
- **Across the year**: the seasonal cycle with the spread between years, and the gap between hot and cold days
- **Has it changed?**: per-decade trends since 1980 (Theil-Sen slope with a Kendall p-value)
- **Compare** (optional): where the city sits among the 40 cities from the main analysis

Data comes from ERA5 (a weather model) via the free Open-Meteo API. No API key needed.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first run for a city downloads about 46 years of hourly data (a few seconds to a minute). Downloads are saved in `.cache/`, so repeating a city is instant. Add `.cache/` to your `.gitignore`.

## Enable the "Compare with 40 cities" tab (optional)

In the analysis notebook, after the city summary cell, run:

```python
summary.to_csv("summary.csv")
```

Put `summary.csv` next to `app.py`. The tab appears automatically. Big-swing days are only compared when the app's threshold slider is at 10 deg C, the value used in the notebook.

## Deploy for free

Push this folder to GitHub, then create an app on Streamlit Community Cloud pointing at `app.py`. Note that `.cache/` does not persist there, so each new city downloads fresh data.

## Files

- `app.py`: the Streamlit interface
- `weather_core.py`: data download, metrics, trends and charts (usable from a notebook too: `import weather_core as wc`)
- `requirements.txt`

## Limits to know about

- ERA5 is a ~25 km model grid, so it slightly understates the sharpest day-to-day swings and the diurnal range, especially in coastal and mountain cities.
- The free API has daily limits; if you hit one the app says so and works again the next day.
- Day-to-day numbers are raw changes (not seasonally adjusted).
