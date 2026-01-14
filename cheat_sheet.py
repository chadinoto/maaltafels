import pandas as pd
import numpy as np
import plotly.express as px




# DATA QUALITY

# (1) FILL MISSING DATES AND FILL WITH NAN ---- 
avg_time_table = (df_scores_vermenigvuldiging
                        .assign(DATE_START=lambda d: pd.to_datetime(d["DATE_START"]).dt.normalize())
                        .groupby("DATE_START", as_index=False)
                        .agg(gemiddelde_tijd_per_tafel = ("DURATION_TIME", "mean"))
)

full_date_range = pd.date_range(start=avg_time_table["DATE_START"].min(),
                                end=avg_time_table["DATE_START"].max())

avg_time_table = (
    avg_time_table.set_index("DATE_START")
    .reindex(full_date_range, fill_value=np.nan)
    .rename_axis("DATE_START")
    .reset_index()
)



# PLOTS

# (1) Simple line plot

fig = px.line(
    avg_time_table_filtered,
    x="DATE_START",
    y="gemiddelde_tijd_per_tafel",
    title="Gemiddelde tijd per maaltafel over tijd",
    labels={"DATE_START": "Datum", "AVG_TIME_PER_MAALTAFEL": "Gemiddelde tijd per maaltafel (sec)"},
    markers=True,
)