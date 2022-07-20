"""add_impact_score.

Revision ID: c76670622e1e
Revises: e3cb5f234bbf
Create Date: 2022-07-13 15:11:52.699325

"""
import json
import warnings

import pandas as pd
import sqlalchemy as sa
from alembic import op

warnings.filterwarnings("ignore")

# revision identifiers, used by Alembic.
revision = "c76670622e1e"
down_revision = "e3cb5f234bbf"
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade anomaly_data_output to add impact column."""
    # ### commands auto generated by Alembic - please adjust! ###

    conn = op.get_bind()

    df = pd.read_sql("SELECT * from anomaly_data_output;", conn)
    df["data_datetime"] = pd.to_datetime(df["data_datetime"])
    df["series_type"] = df["series_type"].apply(
        lambda series: json.dumps(series) if series else None
    )
    df_with_metrics = pd.DataFrame()

    kpi_ids = df["kpi_id"].unique()
    for kpi_id in kpi_ids:
        # split data based on kpi id
        df_kpi = df.loc[df["kpi_id"] == kpi_id].reset_index(drop=True)
        # fetch anomaly period from kpi table
        anom_period_query_result = conn.execute(
            f"SELECT anomaly_params ->> 'anomaly_period' FROM kpi WHERE id={kpi_id}"
        )
        for row in anom_period_query_result:
            anom_period = int(row[0])

        df_kpi_with_metric = _calculate_metric(df_kpi, anom_period)
        df_with_metrics = df_with_metrics.append(df_kpi_with_metric, ignore_index=True)

    conn.execute("TRUNCATE TABLE anomaly_data_output;")
    op.add_column(
        "anomaly_data_output",
        sa.Column("impact", sa.Float(), autoincrement=False, nullable=True),
    )
    df_with_metrics.to_sql("anomaly_data_output", conn, if_exists="append", index=False)
    # ### end Alembic commands ###


def downgrade():
    """Downgrade anomaly_data_output to drop impact column."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("anomaly_data_output", "impact")
    # ### end Alembic commands ###


def _calculate_metric(df, period):
    """Caclulate metrics and impact."""
    df_with_metric = pd.DataFrame()

    for series in ["overall", "subdim", "dq"]:
        subgroup_list = df.loc[df["anomaly_type"] == series]["series_type"].unique()
        for subgroup in subgroup_list:
            if series == "overall":
                df_sub = df.loc[(df["anomaly_type"] == series)].reset_index(drop=True)
                df_sub = _calculate_for_series(df_sub, period)
                deviation_from_mean_df = pd.DataFrame(
                    {
                        "data_datetime": df_sub["data_datetime"],
                        "deviation_from_mean_overall": df_sub["deviation_from_mean"],
                    }
                )
                df_with_metric = df_with_metric.append(df_sub, ignore_index=True)
            else:
                df_sub = df.loc[
                    (df["anomaly_type"] == series)
                    & (df["series_type"] == subgroup).reset_index(drop=True)
                ]
                df_sub = _calculate_for_series(df_sub, period)
                if series == "subdim":
                    df_sub = df_sub.merge(deviation_from_mean_df, how="left", on="data_datetime")
                    df_sub.loc[df_sub["deviation_from_mean_overall"] != 0, "impact"] = (
                        (
                            df_sub["deviation_from_mean"] / df_sub["deviation_from_mean_overall"]
                        )
                        * df_sub["zscore"]
                    ).abs()
                    df_sub = df_sub.drop("deviation_from_mean_overall", axis=1)
                df_with_metric = df_with_metric.append(df_sub, ignore_index=True)

    df_with_metric = df_with_metric.drop(["zscore", "deviation_from_mean"], axis=1)

    return df_with_metric


def _calculate_for_series(df_sub, period):
    df_sub = df_sub.sort_values(by=["data_datetime"]).reset_index(drop=True)
    df_sub["mean"], df_sub["std_dev"] = 0.0, 0.0
    df_sub.iloc[0:period]["mean"] = df_sub.iloc[0:period]["y"].mean()
    df_sub.iloc[0:period]["std_dev"] = df_sub.iloc[0:period]["y"].std()
    for i in range(period, len(df_sub)):
        df_sub["mean"][i] = df_sub.iloc[i - period : i]["y"].mean()
        df_sub["std_dev"][i] = df_sub.iloc[i - period : i]["y"].std()
    df_sub["deviation_from_mean"] = df_sub["y"] - df_sub["mean"]

    df_sub["zscore"] = 0.0
    df_sub.loc[df_sub["is_anomaly"] == 1, "zscore"] = (
        df_sub["y"] - df_sub["yhat_upper"]
    ) / df_sub["std_dev"]
    df_sub.loc[df_sub["is_anomaly"] == -1, "zscore"] = (
        df_sub["yhat_lower"] - df_sub["y"]
    ) / df_sub["std_dev"]
    df_sub["impact"] = 0.0
    df_sub = df_sub.drop(["mean", "std_dev"], axis=1)

    return df_sub
