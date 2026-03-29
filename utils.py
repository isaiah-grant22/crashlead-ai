import geopandas as gpd
from shapely.geometry import Point
import pandas as pd


# Default center: Columbia City, Indiana
COLUMBIA_CITY = Point(-85.4883, 41.1589)


def filter_by_radius(
    df: pd.DataFrame, center: Point = COLUMBIA_CITY, radius_km: int = 80
) -> pd.DataFrame:
    """Filter crash DataFrame to rows within `radius_km` of `center`."""
    if df.empty or "Latitude" not in df.columns or "Longitude" not in df.columns:
        return df

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"])
    )
    dist = gdf.geometry.distance(center)
    return df[dist <= (radius_km / 111)].copy()


def simple_lead_score(row) -> int:
    """Compute a 0-100+ lead score based on crash text fields."""
    score = 0
    text = (
        str(row.get("Nature", ""))
        + str(row.get("Injury", ""))
        + str(row.get("CrashType", ""))
    ).lower()

    if any(w in text for w in ["injury", "injured", "hurt"]):
        score += 40
    if any(w in text for w in ["serious", "severe", "fatal", "death"]):
        score += 50
    if "truck" in text or "semi" in text:
        score += 25
    if any(w in text for w in ["dui", "alcohol", "drunk", "dwi"]):
        score += 30

    return score
