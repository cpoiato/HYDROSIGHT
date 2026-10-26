"""HYDROSIGHT — Figures only. Calculations and output paths belong to the EDA runner."""
from pathlib import Path
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx


def visualize_water_breaks(x, y, xlabel, ylabel, title, output_file: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    try:
        ax.bar(x, y)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if len(x) > 35:
            ax.tick_params(axis="x", labelrotation=90, labelsize=6)
        fig.tight_layout()
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"\nChart saved: {output_file}")
    finally:
        plt.show()
        plt.close(fig)


def visualize_spatial_distribution(df, title, output_file: Path) -> None:
    spatial = df.dropna(subset=["longitude", "latitude"])
    if spatial.empty:
        raise ValueError(f"No valid coordinate records for {title}")
    geo = gpd.GeoDataFrame(spatial, geometry=gpd.points_from_xy(spatial.longitude, spatial.latitude), crs="EPSG:4326").to_crs(epsg=3857)
    fig, ax = plt.subplots(figsize=(10, 10))
    try:
        geo.plot(ax=ax, markersize=3, alpha=0.4)
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldGrayCanvas)
        except Exception as exc:
            print(f"WARNING: Basemap unavailable; geographic points still saved: {exc}")
        ax.set_title(title)
        ax.set_axis_off()
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"\nSpatial chart saved: {output_file}")
    finally:
        plt.show()
        plt.close(fig)

def visualize_monthly_comparison(monthly_counts, title, output_file):
    fig, ax = plt.subplots(figsize=(12, 6))

    for year in monthly_counts.columns:
        ax.plot(
            monthly_counts.index,
            monthly_counts[year],
            marker="o",
            label=str(year)
        )

    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Mois")
    ax.set_ylabel("Nombre de ruptures")
    ax.set_title(title)
    ax.legend(title="Année")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")

    plt.show()
    plt.close(fig)

