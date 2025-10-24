
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

df.groupby(["NAME","DATE_START","TIME_START","TAFELS_IN_OEF","DIFFICULTY_LEVEL"],set_index=False).agg("SCORE":"sum","COUNT":"count")
df
# get df number of rows
len(df)

# (2) DATABASE MANIPULATION ----

# remove all lines where user is Mama and datetime is today in the supabase database
