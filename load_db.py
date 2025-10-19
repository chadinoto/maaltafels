# pip install pandas supabase python-dateutil numpy python-dotenv
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from supabase import create_client


# 1️⃣ Load Supabase credentials
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
sb = create_client(url, key)

# 2️⃣ Load your data
df = pd.read_excel("scores.xlsx")  # or: pd.read_csv("scores.csv", sep=";")

# make all column names lowercase
df.columns = [col.lower() for col in df.columns]

# 3️⃣ Parse datetime / date / time correctly
df["datetime_start"] = pd.to_datetime(
    df["datetime_start"], dayfirst=True, errors="coerce"
)
df["date_start"] = pd.to_datetime(
    df["date_start"], dayfirst=True, errors="coerce"
).dt.date
df["time_start"] = pd.to_datetime(df["time_start"].astype(str), errors="coerce").dt.time

# 4️⃣ Convert everything to JSON-serializable types

# 4️⃣ Convert everything to JSON-serializable types
df["datetime_start"] = df["datetime_start"].dt.strftime("%Y-%m-%d %H:%M:%S")
df["date_start"] = df["date_start"].astype(str)
df["time_start"] = df["time_start"].astype(str)

for c in ["exercise_idx", "tafel", "rand_num"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c] = df[c].where(~df[c].isna(), None)
    df[c] = df[c].apply(lambda x: int(x) if x is not None else None)

for c in ["score", "duration_time", "model_score", "probability"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c] = df[c].where(~df[c].isna(), None)

for c in ["user_answer", "name"]:
    df[c] = df[c].astype(str).replace({"nan": None, "": None})

# 5️⃣ Build JSON records for Supabase
cols = [
    "name",
    "datetime_start",
    "date_start",
    "time_start",
    "exercise_idx",
    "tafel",
    "rand_num",
    "user_answer",
    "score",
    "duration_time",
    "model_score",
    "probability",
]
records = df[cols].to_dict(orient="records")

# 6️⃣ Insert in batches
BATCH = 500
for i in range(0, len(records), BATCH):
    chunk = records[i : i + BATCH]
    sb.table("results").insert(chunk).execute()

print(f"✅ Inserted {len(records)} rows into 'results'")
