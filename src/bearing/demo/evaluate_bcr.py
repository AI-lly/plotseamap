import numpy as np
import pandas as pd
import pickle
from scipy.spatial.distance import jensenshannon  # JS-Divergenz

def evaluate_segment(df_seg, lut):
    """
    df_seg: DataFrame mit Spalten ['# Timestamp','bearing','bearing_rate',...]
    lut: geladenes Dict mit params, prob_rate_cube, rate_edges
    """
    params         = lut["params"]
    prob_rate_cube = lut["prob_rate_cube"]    # shape (n_az, n_rate)
    edges          = np.array(params["rate_edges"])
    az_deg         = params["az_bin_deg"]

    # 1) hole arrays
    thetas = df_seg["bearing"].values
    omegas = df_seg["bearing_rate"].values
    N = len(df_seg)

    log_likes = []
    brier_scores = []
    # für distribution-Vergleich
    counts_true = np.zeros(len(edges)-1)
    sum_pred    = np.zeros_like(counts_true, dtype=float)

    for θ, ω in zip(thetas, omegas):
        # az-Bin
        az_i = int((θ % 360)//az_deg)
        # rate-Bin für ground truth
        rate_i = np.searchsorted(edges, abs(ω), side="right") - 1
        if rate_i<0 or rate_i>=len(counts_true): 
            continue

        p_vec = prob_rate_cube[az_i]   # shape (n_rate,)
        p_vec = p_vec/ p_vec.sum()     # sicherheitshalber normalisieren

        # accumulate for distrib-comparison
        counts_true[rate_i] += 1
        sum_pred += p_vec

        # log-likelihood
        log_likes.append(np.log(p_vec[rate_i] + 1e-12))

        # Brier
        one_hot = np.zeros_like(p_vec)
        one_hot[rate_i] = 1
        brier_scores.append(np.sum((p_vec - one_hot)**2))

    # 2) metrics
    avg_ll     = np.mean(log_likes)
    avg_brier  = np.mean(brier_scores)

    # empirical & predicted dist:
    q_true = counts_true / counts_true.sum()
    p_pred = sum_pred    / sum_pred.sum()

    # JS-distance as summary
    jsd = jensenshannon(q_true, p_pred)

    return {
      "n":            N,
      "avg_loglik":  avg_ll,
      "avg_brier":   avg_brier,
      "js_distance": jsd,
      "bins":        list(zip(edges[:-1],edges[1:])),
      "q_true":      q_true,
      "p_pred":      p_pred
    }


# Beispiel über alle Segmente:
with open("src/bearing/demo/lut.pkl","rb") as f:
    lut = pickle.load(f)

df = pd.read_csv("src/bearing/processed_data/05_distance.csv", parse_dates=["# Timestamp"])
results = []
for (mmsi, seg_id), group in df.groupby(["MMSI","segment_idx"]):
    res = evaluate_segment(group, lut)
    res["MMSI"] = mmsi
    res["segment"] = seg_id
    results.append(res)

# in DataFrame packen
df_metrics = pd.DataFrame(results)
print(df_metrics[["MMSI","segment","n","avg_loglik","avg_brier","js_distance"]])