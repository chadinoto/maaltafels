# auto reload on save
# %%
%load_ext autoreload
%autoreload 2

import pandas as pd
import functions as f

#%%
df = f.read_score_df()

#%%
f.generate_prob_table(df)

# %%
