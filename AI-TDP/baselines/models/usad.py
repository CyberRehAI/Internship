"""USAD-style dual autoencoder baseline (Audibert et al., simplified)."""

from __future__ import annotations

import torch
import torch.nn as nn


class _Encoder(nn.Module):
    def __init__(self, n_features: int, hidden_dim: int, latent_dim: int):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, latent_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h_n, _) = self.lstm(x)
        return self.fc(h_n[-1])


class _Decoder(nn.Module):
    def __init__(self, n_features: int, hidden_dim: int, latent_dim: int):
        super().__init__()
        self.fc = nn.Linear(latent_dim, hidden_dim)
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.out = nn.Linear(hidden_dim, n_features)

    def forward(self, z: torch.Tensor, T: int) -> torch.Tensor:
        h = self.fc(z)
        h0 = h.unsqueeze(0)
        c0 = torch.zeros_like(h0)
        dec_in = h.unsqueeze(1).repeat(1, T, 1)
        out, _ = self.lstm(dec_in, (h0, c0))
        return self.out(out)


class USAD(nn.Module):
    """
    Shared encoder + two decoders.

    Training uses AE and adversarial-style losses (see train_usad).
    Anomaly score: 0.5 * ||x - AE1(x)||^2 + 0.5 * ||x - AE2(AE1(x))||^2
    averaged over T×F per window.
    """

    def __init__(
        self,
        n_features: int = 194,
        hidden_dim: int = 64,
        latent_dim: int = 32,
    ):
        super().__init__()
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.encoder = _Encoder(n_features, hidden_dim, latent_dim)
        self.decoder1 = _Decoder(n_features, hidden_dim, latent_dim)
        self.decoder2 = _Decoder(n_features, hidden_dim, latent_dim)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward_ae1(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        return self.decoder1(z, T=x.size(1))

    def forward_ae2(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        return self.decoder2(z, T=x.size(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Primary reconstruction (AE1)."""
        return self.forward_ae1(x)

    def anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """USAD combined per-window score, shape (B,)."""
        w1 = self.forward_ae1(x)
        w2 = self.forward_ae2(w1)
        e1 = ((x - w1) ** 2).mean(dim=(1, 2))
        e2 = ((x - w2) ** 2).mean(dim=(1, 2))
        return 0.5 * e1 + 0.5 * e2
