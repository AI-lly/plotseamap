#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anomaly Detection & Mapping of AIS Δt-Intervals with GMM
======================================================

1. Load filtered AIS CSV and compute Δt per MMSI
2. Clean Δt (remove zeros, trim extremes)
3. Fit a 3-component Gaussian Mixture Model
4. Mark anomalies via low log-likelihood
5. Plot:
   • Δt histogram + KDE + quantile cutoffs
   • Δt distribution with GMM density + anomaly rugplot
   • Example ship trajectory over the Fehmarnbelt basemap
"""
import os
import json
from pathlib import Path

import click
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.mixture import GaussianMixture
from shapely.geometry import Point, box

# Logging
import logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def save_hist_kde(df_filtered, q_low, q_high, out_path):
    """Histogramm + KDE + Quantil-Linien speichern."""
    xs = np.linspace(df_filtered['delta_t'].min(),
                     df_filtered['delta_t'].max(), 1000)
    kde = gaussian_kde(df_filtered['delta_t'])

    fig, ax = plt.subplots(figsize=(8,5))
    ax.hist(df_filtered['delta_t'],
            bins=100, density=True, alpha=0.7,
            edgecolor='black', label='Δt (bereinigt)')
    ax.plot(xs, kde(xs), lw=2, label='KDE')
    ax.axvline(q_low, linestyle='--', color='red',
               label=f'0.5%-Quantil ({q_low:.1f}s)')
    ax.axvline(q_high, linestyle='--', color='red',
               label=f'99.5%-Quantil ({q_high:.1f}s)')
    ax.set_title('Histogramm und KDE der Δt-Intervalle')
    ax.set_xlabel('Δt (Sekunden)')
    ax.set_ylabel('Dichte')
    ax.legend()
    plt.tight_layout()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    log.info(f"Δt‐Histogramm + KDE gespeichert: {out_path}")


def save_gmm_density(df_filtered, gmm, xs, out_path):
    """Δt-Verteilung mit GMM-Dichte + Anomalie-Rugplot speichern."""
    # Normal vs. Anomalie
    normal = df_filtered.loc[~df_filtered['anomaly'], 'delta_t']
    anom   = df_filtered.loc[df_filtered['anomaly'],  'delta_t']
    pdf    = np.exp(gmm.score_samples(xs.reshape(-1,1)))

    fig, ax = plt.subplots(figsize=(10,4))
    ax.hist(normal, bins=100, density=True,
            alpha=0.6, edgecolor='black', label='Normal')
    ax.plot(xs, pdf, lw=2, label='GMM-Dichte')
    ax.plot(anom, np.full_like(anom, -0.002), '|',
            color='red', label='Anomalie')
    ax.set_title('Δt-Verteilung mit GMM-Dichte und Anomalien')
    ax.set_xlabel('Δt (Sekunden)')
    ax.set_ylabel('Dichte')
    ax.set_ylim(bottom=-0.005)
    ax.legend()
    plt.tight_layout()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    log.info(f"GMM‐Dichte‐Plot gespeichert: {out_path}")


def plot_trajectory_on_basemap(traj_df, anomalies, map_cfg, ais_cfg):
    """Zeichnet eine einzelne AIS-Trajektorie inkl. Anomalien auf die Basemap."""
    base_png     = map_cfg["output_base_map"]
    bbox_geojson = map_cfg["output_buffer_geojson"]
    # benutzerdefiniertes Ausgabe‐Muster
    example_mmsi = traj_df['MMSI'].iloc[0]
    out_png      = Path("output/plots/anomaly_detection") / f"trajectory_{example_mmsi}.png"

    # Extent aus Buffer-GeoJSON (in WebMercator)
    buf = gpd.read_file(bbox_geojson).to_crs(epsg=3857)
    minx, miny, maxx, maxy = buf.total_bounds

    # Bild laden
    img = plt.imread(base_png)

    # GeoDataFrame reprojizieren
    gdf = gpd.GeoDataFrame(
        traj_df,
        geometry=gpd.points_from_xy(traj_df.lon, traj_df.lat),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    # Plot
    fig, ax = plt.subplots(figsize=ais_cfg["plot"].get("figsize", [10,8]))
    ax.imshow(img, extent=(minx, maxx, miny, maxy), zorder=0)
    ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy)
    ax.axis("off")

    normal = gdf[~anomalies]
    ax.plot(normal.geometry.x, normal.geometry.y,
            color=ais_cfg["plot"].get("track_color","orange"),
            linewidth=ais_cfg["plot"].get("track_width",1),
            alpha=0.7, zorder=1, label="Normal")

    anom = gdf[anomalies]
    ax.scatter(anom.geometry.x, anom.geometry.y,
               color="red", marker="x", s=50,
               zorder=2, label="Anomalie")

    ax.legend(loc="lower left")
    ax.set_title(f"Trajektorie MMSI {example_mmsi}")
    plt.tight_layout()

    os.makedirs(out_png.parent, exist_ok=True)
    fig.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close(fig)
    log.info(f"AIS-Trajektorie mit Anomalien gespeichert: {out_png}")


@click.command()
@click.option(
    "--map-config", "map_config_path", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur Map-Config JSON (fehmarnbelt.json)"
)
@click.option(
    "--ais-config", "ais_config_path", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur AIS-Filter-Config JSON (ais_filters.json)"
)
def main(map_config_path, ais_config_path):
    # 0) Configs einlesen
    with open(map_config_path) as f:
        map_cfg = json.load(f)
    with open(ais_config_path) as f:
        ais_cfg = json.load(f)
    log.info("Configs geladen")

    # 1) Δt berechnen
    ais_csv = ais_cfg["output_csv"]
    df = pd.read_csv(ais_csv, parse_dates=["# Timestamp"])
    df.rename(columns={"Latitude":"lat","Longitude":"lon"}, inplace=True, errors="ignore")
    df = df.sort_values(['MMSI', '# Timestamp'])
    df['delta_t'] = df.groupby('MMSI')['# Timestamp'].diff().dt.total_seconds()
    deltas = df['delta_t'].dropna()
    log.info(f"Δt berechnet: {len(deltas):,} Intervalle")

    # 2) Clean & trim
    deltas_clean = deltas[deltas > 0]
    q_low, q_high = deltas_clean.quantile([0.005, 0.995])
    mask = (
        (df['delta_t'] > 0) &
        (df['delta_t'] >= q_low) &
        (df['delta_t'] <= q_high)
    )
    df_filtered = df.loc[mask].copy()
    log.info(f"Δt gereinigt: {len(df_filtered):,} Intervalle")

    # 3) Histogramm + KDE
    save_hist_kde(
        df_filtered=df_filtered,
        q_low=q_low, q_high=q_high,
        out_path="output/plots/anomaly_detection/delta_t_hist_kde.png"
    )

    # 4) GMM-Fit & Dichte-Plot
    X = df_filtered['delta_t'].values.reshape(-1,1)
    gmm = GaussianMixture(n_components=3,
                          covariance_type='full',
                          random_state=42)
    gmm.fit(X)
    log.info(f"GMM fit (AIC={gmm.aic(X):.0f}, BIC={gmm.bic(X):.0f})")

    xs = np.linspace(df_filtered['delta_t'].min(),
                     df_filtered['delta_t'].max(), 1000)
    df_filtered['log_lik'] = gmm.score_samples(X)
    tau = np.percentile(df_filtered['log_lik'], 1)
    df_filtered['anomaly'] = df_filtered['log_lik'] < tau
    log.info(f"Anomalien: {df_filtered['anomaly'].sum():,} / {len(df_filtered):,}")

    save_gmm_density(
        df_filtered=df_filtered,
        gmm=gmm,
        xs=xs,
        out_path="output/plots/anomaly_detection/delta_t_gmm_density.png"
    )

    # 5) Beispiel-Trajektorie
    example_mmsi = df_filtered['MMSI'].value_counts().idxmax()
    traj = df_filtered[df_filtered['MMSI']==example_mmsi].reset_index(drop=True)
    plot_trajectory_on_basemap(traj, traj['anomaly'], map_cfg, ais_cfg)


if __name__ == "__main__":
    main()