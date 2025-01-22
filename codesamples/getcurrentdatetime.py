from datetime import datetime
import pytz

# Get the current time in UTC
utc_now = datetime.now(pytz.utc)

# Convert to Eastern Standard Time (EST)
est_now = utc_now.astimezone(pytz.timezone('US/Eastern'))

# Print the current date and time in EST
print(est_now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))