"""Compact TranAD-style transformer reconstruction baseline."""

from __future__ import annotations

import math

import torch
import torch.nn as nn


class _PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class TranAD(nn.Module):
    """
    Transformer encoder → linear projection reconstruction.

    Minimal window-level TranAD-style baseline: reconstruct (B, T, F),
    anomaly score = per-window MSE.
    """

    def __init__(
        self,
        n_features: int = 194,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
        latent_dim: int = 32,
    ):
        super().__init__()
        if d_model % nhead != 0:
            raise ValueError("d_model must be divisible by nhead")
        self.n_features = n_features
        self.d_model = d_model
        self.latent_dim = latent_dim

        self.input_proj = nn.Linear(n_features, d_model)
        self.pos = _PositionalEncoding(d_model)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.to_latent = nn.Linear(d_model, latent_dim)
        self.out_proj = nn.Linear(d_model, n_features)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        h = self.pos(self.input_proj(x))
        h = self.encoder(h)
        return self.to_latent(h.mean(dim=1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.pos(self.input_proj(x))
        h = self.encoder(h)
        return self.out_proj(h)

    def anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        recon = self.forward(x)
        return ((recon - x) ** 2).mean(dim=(1, 2))
