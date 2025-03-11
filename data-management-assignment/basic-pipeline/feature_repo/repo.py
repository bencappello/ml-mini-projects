import pandas as pd
from feast import Entity, FeatureView, FileSource, Field
from feast.types import Float32, Int32, String

PARQUET_FILE_PATH = "../Telco-Customer-Churn-Transformed.parquet"

# Read Parquet file and add a timestamp column if needed
data_df = pd.read_parquet(PARQUET_FILE_PATH)
if "event_timestamp" in data_df.columns:
    data_df = data_df.drop(columns=["event_timestamp"])
timestamps = pd.date_range(
    end=pd.Timestamp.now(),
    periods=len(data_df),
    freq="D"
).to_frame(name="event_timestamp", index=False)
data_df = pd.concat([data_df, timestamps], axis=1)
data_df.to_parquet(PARQUET_FILE_PATH, index=False)

# Define Feature Store Schema
customer = Entity(name="customer", join_keys=["customerID"])

customer_features = FeatureView(
    name="customer_features",
    entities=[customer],
    ttl=None,
    schema=[
        Field(name="TotalAddonServices", dtype=Int32),
        Field(name="AvgMonthlyUsage", dtype=Float32),
        Field(name="TenureGroup", dtype=String),
    ],
    source=FileSource(path=PARQUET_FILE_PATH, event_timestamp_column="event_timestamp")
)