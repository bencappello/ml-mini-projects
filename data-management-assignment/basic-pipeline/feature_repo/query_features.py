import pandas as pd
from feast import FeatureStore

# Initialize the FeatureStore (Assumes you're running this in the feature_repo directory)
store = FeatureStore(repo_path=".")

# Define the customer IDs for which we want to retrieve historical features
entity_df = pd.DataFrame.from_dict(
    {
        "customerID": [
            "7590-VHVEG",
            "5575-GNVDE",
            "3668-QPYBK",
            "7795-CFOCW",
            "9237-HQITU",
            "9305-CDSKC",
            "1452-KIOVK",
            "6713-OKOMC",
            "7892-POOKP",
            "6388-TABGU",
            "9763-GRSKD",
            "7469-LKBCI",
            "8091-TTVAX",
            "0280-XJGEX",
            "5129-JLPIS",
            "3655-SNQYZ",
            "8191-XWSZG",
            "9959-WOFKT",
            "4190-MFLUW",
        ]
    }
)

# Feast requires a timestamp column, so we generate arbitrary timestamps
entity_df["event_timestamp"] = pd.date_range(
    end=pd.Timestamp.now(),
    periods=len(entity_df),
    freq="D"
)

# Query historical features from the offline store
features = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "customer_features:TotalAddonServices",
        "customer_features:AvgMonthlyUsage",
        "customer_features:TenureGroup",
    ],
).to_df()

# Print the resulting dataframe
print("\n✅ Retrieved Features from Feast:")
print(features)