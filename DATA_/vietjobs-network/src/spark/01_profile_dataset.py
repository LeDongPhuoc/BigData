import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure Java 17 LTS if JAVA_HOME is not set
if not os.environ.get("JAVA_HOME"):
    candidate_jdk = r"C:\Program Files\Java\jdk-17.0.19"
    if Path(candidate_jdk).exists():
        os.environ["JAVA_HOME"] = candidate_jdk

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

DATA_PATH = "data/raw/vietjobs/VietJobs.csv"

def create_spark():
    return (
        SparkSession.builder
        .appName("VietJobs-Data-Profiling")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )

def main():
    print(f"Loading dataset from: {DATA_PATH} ...")
    spark = create_spark()
    spark.sparkContext.setLogLevel("WARN")

    df = (
        spark.read
        .option("header", True)
        .option("multiLine", True)
        .option("quote", '"')
        .option("escape", '"')
        .option("inferSchema", True)
        .csv(DATA_PATH)
    )

    print("\n" + "=" * 25 + " ROOT SCHEMA " + "=" * 25)
    df.printSchema()

    total_records = df.count()
    print("\n" + "=" * 25 + " TOTAL RECORDS " + "=" * 25)
    print(f"Total Rows: {total_records:,}")
    print(f"Total Columns: {len(df.columns)}")

    print("\n" + "=" * 25 + " NULL COUNT PER COLUMN " + "=" * 25)
    null_exprs = [
        F.count(
            F.when(
                F.col(c).isNull() | 
                (F.trim(F.col(c).cast("string")) == "") | 
                (F.trim(F.col(c).cast("string")).isin("null", "None", "NaN")), 
                c
            )
        ).alias(c)
        for c in df.columns
    ]
    null_df = df.select(null_exprs)
    null_row = null_df.collect()[0].asDict()
    for col_name, null_cnt in null_row.items():
        pct = (null_cnt / total_records) * 100
        print(f" - {col_name:25s}: {null_cnt:6,d} ({pct:5.2f}%)")

    print("\n" + "=" * 25 + " CATEGORY COUNT " + "=" * 25)
    df.groupBy("category").count().orderBy(F.desc("count")).show(50, truncate=False)

    print("\n" + "=" * 25 + " COUNTRY COUNT " + "=" * 25)
    df.groupBy("country").count().orderBy(F.desc("count")).show(20, truncate=False)

    print("\n" + "=" * 25 + " CONTRACT TYPE " + "=" * 25)
    df.groupBy("contract_type").count().orderBy(F.desc("count")).show(20, truncate=False)

    print("\n" + "=" * 25 + " EXPERIENCE REQUIRED " + "=" * 25)
    df.groupBy("experience_required").count().orderBy(F.desc("count")).show(30, truncate=False)

    print("\n" + "=" * 25 + " SALARY SUMMARY " + "=" * 25)
    df.select("salary_min", "salary_max", "salary_avg").describe().show()

    print("\n" + "=" * 25 + " SAMPLE RECORD PREVIEW " + "=" * 25)
    sample_row = df.limit(1).collect()[0].asDict()
    for k, v in sample_row.items():
        val_str = str(v)
        if len(val_str) > 80:
            val_str = val_str[:77] + "..."
        print(f"{k:25s}: {val_str}")

    spark.stop()

if __name__ == "__main__":
    main()
