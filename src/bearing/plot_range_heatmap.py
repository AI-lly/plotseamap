#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_range_heatmap.py

Erzeugt Polar-Heatmaps
  • P(r | θ, ω∈[ω_i,ω_{i+1}))
  • P(r | θ) global über alle ω
  • P(r) global über θ und ω

und speichert alle Grafiken unter plots/range_heatmaps/.
"""
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
import click

@click.command()
@click.option(
    "--lut", "lut_path",
    default="src/bearing/processed_data/range_lut.pkl",
    show_default=True,
    help="Pfad zur Lookup-Tabelle (Pickle)"
)
@click.option(
    "--outdir", "out_dir",
    default="src/bearing/plots/range_heatmaps",
    show_default=True,
    help="Ausgabe-Verzeichnis für die PNGs"
)
def main(lut_path: str, out_dir: str):
    # LUT laden
    with open(lut_path, "rb") as f:
        lut = pickle.load(f)

    params     = lut["params"]
    prob_cube  = lut["prob_cube"]         # shape = (n_az, n_rate, n_r)
    az_deg     = params["az_bin_deg"]
    rate_edges = params["rate_edges"]     # z.B. [0, 0.01, 0.03, …]
    range_vec  = np.array(params["range_vec"])  # z.B. [250, 750, …]

    # Kanten für pcolormesh
    az_edges = np.deg2rad(np.arange(0, 360+az_deg, az_deg))
    dr       = np.diff(range_vec).mean()
    r_edges  = np.concatenate((
        [0.0],
        (range_vec[:-1] + range_vec[1:]) / 2,
        [range_vec[-1] + dr/2]
    ))

    # Meshgrid
    R, A = np.meshgrid(r_edges, az_edges)

    # Ordner anlegen
    os.makedirs(out_dir, exist_ok=True)

    n_rate = prob_cube.shape[1]

    # 1) Heatmaps je Rate-Bin
    for ri in range(n_rate):
        Z = prob_cube[:, ri, :]  # (n_az, n_r)
        nonzero = Z.sum(axis=0) > 0
        max_r = r_edges[:-1][nonzero].max() if nonzero.any() else r_edges[-1]

        fig, ax = plt.subplots(figsize=(6,6), subplot_kw={"projection":"polar"})
        pcm = ax.pcolormesh(A, R, Z, shading="flat", cmap="viridis")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_ylim(0, max_r)
        ax.set_title(f"P(r|θ,ω∈[{rate_edges[ri]:.3f},{rate_edges[ri+1]:.3f}))\nmax≈{max_r:.0f} m")
        cbar = fig.colorbar(pcm, ax=ax, pad=0.1)
        cbar.set_label("Wahrscheinlichkeit")
        fname = f"range_heatmap_rate_{ri:02d}.png"
        fig.savefig(f"{out_dir}/{fname}", dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"→ Saved {out_dir}/{fname}")

    # 2) P(r | θ) marginalisiert über ω
    Z_marg = prob_cube.sum(axis=1)  # shape (n_az, n_r)
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw={"projection":"polar"})
    pcm = ax.pcolormesh(A, R, Z_marg, shading="flat", cmap="plasma")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("P(r | θ) marginalisiert über ω")
    cbar = fig.colorbar(pcm, ax=ax, pad=0.1)
    cbar.set_label("Wahrscheinlichkeit")
    out = f"{out_dir}/range_heatmap_marginal_rate.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"→ Saved {out}")

    # 3) P(r) global über θ und ω
    pr = prob_cube.sum(axis=(0,1))                # (n_r,)
    pr /= pr.sum()                                # normieren
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(range_vec, pr, marker="o")
    ax.set_xlabel("Radius r [m]")
    ax.set_ylabel("P(r)")
    ax.set_title("Globale Radiale Verteilung P(r)")
    out = f"{out_dir}/radial_distribution_global.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"→ Saved {out}")

if __name__ == "__main__":
    main()