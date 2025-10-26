
# (0) INIT ENVIRONMENT ----
%load_ext autoreload
%autoreload 2

import pandas as pd
from functions import *
import random
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import re
from supabase import create_client, Client



url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)


starttime = df.iloc[0,3]

# (1) READ DATA ----
df = read_score_df("Raphael")
df = read_score_df_updated_db("Raphael")

df_filtered = df.query("DATETIME_START=='2025-10-26T12:09:48+00:00'")
df["SCORE"] = df["SCORE"] if df["SCORE"]==1 else 0

# change score to 0 if score is not 1
df["SCORE"] = df["SCORE"].astype(int)
df["SCORE"] = df["SCORE"].apply(lambda x: 0 if x != 1 else x)

df.groupby(["DATETIME_START","TAFELS_IN_OEF"]).agg({"DURATION_TIME":"sum","SCORE":"sum","DATETIME_START":"count"}).rename(columns={"DATETIME_START":"COUNT"}).query("SCORE==20 and COUNT==20")



df.groupby(["NAME","DATE_START","TIME_START","TAFELS_IN_OEF","DIFFICULTY_LEVEL"],set_index=False).agg("SCORE":"sum","COUNT":"count")
df
# get df number of rows
len(df)

# (2) DATABASE MANIPULATION ----

# remove all lines where user is Mama and datetime is today in the supabase database
