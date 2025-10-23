import datetime as dt

def View(df):
    from datawrangler import open_in_data_wrangler
    open_in_data_wrangler(df)
    
    

# (1) Loggers

def print_red(text, timestamp=True):
    color_code = "\033[91m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text}"
    print(f"{color_code}{text}\033[0m")

def print_green(text, timestamp=True):
    color_code = "\033[92m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text}"
    print(f"{color_code}{text}\033[0m")

def print_orange(text, timestamp=True):
    color_code = "\033[93m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text}"
    print(f"{color_code}{text}\033[0m")

def print_magenta(text, timestamp=True):
    color_code = "\033[95m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text}"
    print(f"{color_code}{text}\033[0m")
    
    
def print_white(text, timestamp=True):
    color_code = "\033[97m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text}"
    print(f"{color_code}{text}\033[0m")
    
def print_title(text, timestamp=False):
    color_code = "\033[1m\033[94m"
    if timestamp:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{now}] {text.upper()}"
    print(f"{color_code}{text.upper()} \033[0m")

