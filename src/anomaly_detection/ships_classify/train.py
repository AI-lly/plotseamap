#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/anomaly_detection/ships_classify/train.py

Trainiert ein LSTM-Modell zur Klassifikation, ob eine AIS-Sequenz zu einem Frachtschiff (Cargo) gehört.
Enthält ausführliche Kommentare zur Architektur, zum Trainings-Loop und zur Trainingsmetriken-Visualisierung.
"""
import os
import json
import logging
import click
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
from sklearn.metrics import roc_auc_score
import matplotlib.pyplot as plt

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


class LSTMClassifier(nn.Module):
    """
    Einfache LSTM-basierte Binär-Klassifikation:
    - Input: Sequenz von Feature-Vektoren (batch, seq_len, feature_dim)
    - LSTM verarbeitet die Sequenz, liefert finalen hidden state
    - Dense + Sigmoid auf hidden state → Wahrscheinlichkeit
    """
    def __init__(self, input_dim, hidden_dim=64, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            batch_first=True
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # x: (batch, seq_len, feature_dim)
        # mask NaNs (falls vorverarbeitet) → setze auf 0
        x = torch.nan_to_num(x, nan=0.0)
        # LSTM → out (ignored), (h_n, c_n)
        _, (h_n, _) = self.lstm(x)
        h = h_n.squeeze(0)  # (batch, hidden_dim)
        h = self.dropout(h)
        logits = self.fc(h)  # (batch, 1)
        return torch.sigmoid(logits).squeeze(1)  # (batch,)


@click.command()
@click.option(
    "--config", "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur JSON-Config (ships_classify.json)"
)
def main(config_path):
    # 1) Config laden
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    log.info(f"Config geladen: {config_path}")

    # 2) Pfade und Hyperparameter aus Config
    seq_dir       = cfg["output"]["sequences_dir"]
    training_plot = cfg["output"].get("training_plot",
                                      "output/plots/anomaly_detection/training_metrics.png")
    L             = cfg["sequence_length"]
    batch_size    = cfg.get("batch_size", 128)
    lr            = cfg.get("learning_rate", 1e-3)
    n_epochs      = cfg.get("n_epochs", 20)
    patience      = cfg.get("patience", 3)
    val_frac      = cfg.get("validation_split", 0.2)

    # 3) Sequenzen laden
    log.info("Lade Sequenzen…")
    X_train = np.load(os.path.join(seq_dir, "X_train.npy"))
    y_train = np.load(os.path.join(seq_dir, "y_train.npy"))
    X_test  = np.load(os.path.join(seq_dir, "X_test.npy"))
    y_test  = np.load(os.path.join(seq_dir, "y_test.npy"))
    log.info(f"→ Training: {X_train.shape[0]} Sequenzen, Test: {X_test.shape[0]} Sequenzen")

    # 4) Setup Device, Dataset und DataLoader
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Verwende Device: {device}")

    # TensorDataset für Training & Validierung
    full_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32)
    )
    n_val = int(val_frac * len(full_ds))
    n_trn = len(full_ds) - n_val
    train_ds, val_ds = random_split(full_ds, [n_trn, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds, batch_size=batch_size)
    test_loader  = DataLoader(
        TensorDataset(torch.tensor(X_test, dtype=torch.float32),
                      torch.tensor(y_test, dtype=torch.float32)),
        batch_size=batch_size
    )

    # 5) Modell, Loss und Optimizer
    n_features = X_train.shape[2]
    model = LSTMClassifier(input_dim=n_features).to(device)
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # 6) Trainings-Loop mit Early Stopping
    train_losses, val_losses, val_aucs, val_accs = [], [], [], []
    best_val_loss = float('inf')
    epochs_no_improve = 0

    for epoch in range(1, n_epochs+1):
        # -- Training --
        model.train()
        batch_losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            preds = model(xb)
            loss = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            batch_losses.append(loss.item())
        train_loss = np.mean(batch_losses)
        train_losses.append(train_loss)

        # -- Validierung --
        model.eval()
        batch_vloss, all_preds, all_targets = [], [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                preds = model(xb)
                batch_vloss.append(criterion(preds, yb).item())
                all_preds.append(preds.cpu().numpy())
                all_targets.append(yb.cpu().numpy())
        val_loss = np.mean(batch_vloss)
        val_losses.append(val_loss)
        preds = np.concatenate(all_preds)
        targets = np.concatenate(all_targets)
        val_auc = roc_auc_score(targets, preds)
        val_aucs.append(val_auc)
        val_hard = (preds >= 0.5).astype(int)
        val_acc = (val_hard == targets).mean()
        val_accs.append(val_acc)

        log.info(f"Epoch {epoch}: train_loss={train_loss:.4f}  "
                 f"val_loss={val_loss:.4f}  val_auc={val_auc:.4f}  val_acc={val_acc:.4f}")

        # Early Stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            torch.save(model.state_dict(), os.path.join(seq_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                log.info("→ Early stopping ausgelöst")
                break

    # 7) Test-Evaluation
    model.load_state_dict(torch.load(os.path.join(seq_dir, "best_model.pt")))
    model.eval()
    test_preds, test_targets = [], []
    with torch.no_grad():
        for xb, yb in test_loader:
            xb = xb.to(device)
            p = model(xb).cpu().numpy()
            test_preds.append(p)
            test_targets.append(yb.numpy())
    test_preds = np.concatenate(test_preds)
    test_targets = np.concatenate(test_targets).astype(int)

    test_loss = criterion(
        torch.tensor(test_preds, dtype=torch.float32),
        torch.tensor(test_targets, dtype=torch.float32)
    ).item()
    test_hard = (test_preds >= 0.5).astype(int)
    test_acc = (test_hard == test_targets).mean()
    test_auc = roc_auc_score(test_targets, test_preds)
    log.info(f"\n--- Test‑Evaluation ---\n"
             f"Test Loss:    {test_loss:.4f}\n"
             f"Test Accuracy: {test_acc:.4f}\n"
             f"Test AUC:      {test_auc:.4f}")

    # 8) Plot Trainingsverlauf (Loss & Accuracy)
    log.info("Erstelle Plot für Trainings‑Metriken …")
    epochs = np.arange(1, len(train_losses)+1)
    fig, ax1 = plt.subplots(figsize=(8,4))
    ax1.plot(epochs, train_losses, label='Train Loss')
    ax1.plot(epochs, val_losses,   label='Val Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax2 = ax1.twinx()
    ax2.plot(epochs, val_accs, color='green', label='Val Acc')
    ax2.set_ylabel('Accuracy')
    # Legende kombinieren
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines+lines2, labels+labels2, loc='best')
    plt.title('Training Verlauf: Loss & Accuracy')
    os.makedirs(os.path.dirname(training_plot), exist_ok=True)
    plt.tight_layout()
    plt.savefig(training_plot, dpi=300)
    log.info(f"Training‑Metriken‑Plot gespeichert: {training_plot}")

if __name__ == '__main__':
    main()


# python src/anomaly_detection/ships_classify/train.py --config config/ships_classify.json