from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonVirtualenvOperator
from datetime import datetime, timedelta
import os

# Load repository path from environment variable
DATA_REPO_NAME = os.environ['DATA_REPO_NAME']
RAW_DATA_LOCAL_PATH = f'/opt/airflow/{DATA_REPO_NAME}/WA_Fn-UseC_-Telco-Customer-Churn.csv'
TRANSFORMED_DATA_LOCAL_PATH = f'/opt/airflow/{DATA_REPO_NAME}/Telco-Customer-Churn-Transformed.csv'
PARQUET_DATA_LOCAL_PATH = TRANSFORMED_DATA_LOCAL_PATH.replace(".csv", ".parquet")

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_REGION = "us-east-1"
S3_URL = f"s3://{S3_BUCKET_NAME}"

# Function to perform feature engineering
def transform_dataset(raw_data_path, transformed_data_path):
    import pandas as pd
    
    # Read the raw dataset
    df = pd.read_csv(raw_data_path)

    df_temp = df[['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 
              'TechSupport', 'StreamingTV', 'StreamingMovies']].copy()

    for col in df_temp:
        df_temp[col] = df_temp[col].map({'Yes': 1, 'No': 0, 'No internet service': 0, 'No phone service': 0}).fillna(0)

    df['TotalAddonServices'] = df_temp.sum(axis=1)
    
    # Convert TotalCharges to numeric (handling missing values)
    df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
    df['tenure'] = pd.to_numeric(df['tenure'], errors='coerce')
    
    # Calculate AvgMonthlyUsage safely
    df['AvgMonthlyUsage'] = df['TotalCharges'] / df['tenure']
    df['AvgMonthlyUsage'].fillna(0, inplace=True)
    
    # Create TenureGroup feature
    df['TenureGroup'] = pd.cut(df['tenure'], bins=[0, 12, 24, 48, 60, 100], 
                               labels=["0-12", "12-24", "24-48", "48-60", "60+"])
    
    # Save the transformed dataset
    df.to_csv(transformed_data_path, index=False)

# Function to convert CSV to Parquet
def convert_to_parquet(transformed_data_path, parquet_data_path):
    import pandas as pd
    
    # Read the transformed dataset
    df = pd.read_csv(transformed_data_path)
    
    # Save as Parquet
    df.to_parquet(parquet_data_path, index=False)

# Default DAG arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 2, 13),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define DAG
dag = DAG(
    "download_dataset",
    default_args=default_args,
    description="Download and transform Telco Customer Churn dataset",
    schedule_interval="@daily",
    catchup=False
)

# Task to download dataset using Kaggle CLI
download_task = BashOperator(
    task_id="download_dataset",
    bash_command=f"kaggle datasets download -d blastchar/telco-customer-churn -p /opt/airflow/{DATA_REPO_NAME} --unzip",
    dag=dag,
)

# Ensure the dataset exists
verify_task = BashOperator(
    task_id="verify_dataset",
    bash_command=f"ls -lh {RAW_DATA_LOCAL_PATH}",
    dag=dag,
)

# Task to perform feature engineering
transform_task = PythonVirtualenvOperator(
    task_id="transform_dataset",
    python_callable=transform_dataset,
    requirements=["pandas"],
    system_site_packages=False,
    op_args=[RAW_DATA_LOCAL_PATH, TRANSFORMED_DATA_LOCAL_PATH],
    dag=dag,
)

# Task to convert CSV to Parquet
convert_to_parquet_task = PythonVirtualenvOperator(
    task_id="convert_to_parquet",
    python_callable=convert_to_parquet,
    requirements=["pandas", "pyarrow"],
    system_site_packages=False,
    op_args=[TRANSFORMED_DATA_LOCAL_PATH, PARQUET_DATA_LOCAL_PATH],
    dag=dag,
)

# Task to commit and push data files to Git/DVC repository
commit_push_task = BashOperator(
    task_id="commit_push_dvc",
    bash_command="""
    cd /opt/airflow/$DATA_REPO_NAME

    # Ensure DVC is initialized
    if [ ! -d .dvc ]; then
        dvc init
    fi

    # Ensure DVC remote is set only if it doesn't exist
    if ! dvc remote list | grep -q "origin"; then
        dvc remote add -d origin $S3_URL
    fi

    # Configure Git User
    git config --global user.email "bencappello@gmail.com"
    git config --global user.name "Ben Cappello"

    # Add files to DVC tracking
    dvc add Telco-Customer-Churn-Transformed.csv
    dvc add Telco-Customer-Churn-Transformed.parquet

    # Ensure Git tracks DVC metadata files
    git add .gitignore
    if [ -f Telco-Customer-Churn-Transformed.csv.dvc ]; then git add Telco-Customer-Churn-Transformed.csv.dvc; fi
    if [ -f Telco-Customer-Churn-Transformed.parquet.dvc ]; then git add Telco-Customer-Churn-Transformed.parquet.dvc; fi
    if [ -f dvc.yaml ]; then git add dvc.yaml; fi
    if [ -f dvc.lock ]; then git add dvc.lock; fi

    # Commit changes to Git
    git commit -m "Add transformed dataset and Parquet file" || echo "No changes to commit"

    # Ensure correct Git branch and push
    git branch -M main
    git push origin main

    # Push dataset files to DVC remote storage (S3)
    dvc push
    """,
    env={'DATA_REPO_NAME': DATA_REPO_NAME, 'S3_URL': S3_URL, 'AWS_ACCESS_KEY_ID': os.environ['AWS_ACCESS_KEY_ID'], 'AWS_SECRET_ACCESS_KEY': os.environ['AWS_SECRET_ACCESS_KEY']},
    append_env=True,  # Set to True to append to existing environment variables
    dag=dag,
)

# Task dependencies
download_task >> verify_task >> transform_task >> convert_to_parquet_task >> commit_push_task