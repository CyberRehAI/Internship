"""Seq2seq LSTM Autoencoder for window reconstruction baselines."""

from __future__ import annotations

import torch
import torch.nn as nn


class LSTMAE(nn.Module):
    """
    Encoder LSTM → latent bottleneck → Decoder LSTM.

    Input / reconstruction shape: (B, T, F).
    Latent embedding ``z`` shape: (B, latent_dim).
    """

    def __init__(
        self,
        n_features: int = 7,
        hidden_dim: int = 64,
        latent_dim: int = 32,
        num_layers: int = 1,
        dropout: float = 0.0,
    ):
        super().__init__()
        if num_layers < 1:
            raise ValueError("num_layers must be >= 1")
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.num_layers = num_layers

        enc_dropout = dropout if num_layers > 1 else 0.0
        self.encoder = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=enc_dropout,
        )
        self.to_latent = nn.Linear(hidden_dim, latent_dim)
        self.from_latent = nn.Linear(latent_dim, hidden_dim)

        dec_dropout = dropout if num_layers > 1 else 0.0
        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dec_dropout,
        )
        self.out_proj = nn.Linear(hidden_dim, n_features)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Return bottleneck embedding ``z`` of shape (B, latent_dim)."""
        _, (h_n, _) = self.encoder(x)
        return self.to_latent(h_n[-1])

    def decode(self, z: torch.Tensor, T: int) -> torch.Tensor:
        """Reconstruct sequence of length T from latent ``z``."""
        h0 = self.from_latent(z)
        h0 = h0.unsqueeze(0).repeat(self.num_layers, 1, 1)
        c0 = torch.zeros_like(h0)
        dec_in = h0[-1].unsqueeze(1).repeat(1, T, 1)
        out, _ = self.decoder(dec_in, (h0, c0))
        return self.out_proj(out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return reconstruction with same shape as ``x``."""
        z = self.encode(x)
        return self.decode(z, T=x.size(1))

    def anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """Per-window MSE reconstruction score, shape (B,)."""
        recon = self.forward(x)
        return ((recon - x) ** 2).mean(dim=(1, 2))
