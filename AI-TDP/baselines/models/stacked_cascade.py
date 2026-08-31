"""Experimental stacked cascade: LSTM-AE → USAD → TranAD with latent context."""

from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn

from baselines.models.lstm_ae import LSTMAE
from baselines.models.tranad import TranAD
from baselines.models.usad import USAD


def inject_context(x: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
    """
    Broadcast latent ``z`` (B, D) across time and concat on feature dim.

    x: (B, T, F) → out: (B, T, F+D)
    """
    if z.dim() != 2:
        raise ValueError(f"z must be (B, D), got {tuple(z.shape)}")
    if x.dim() != 3:
        raise ValueError(f"x must be (B, T, F), got {tuple(x.shape)}")
    T = x.size(1)
    z_t = z.unsqueeze(1).expand(-1, T, -1)
    return torch.cat([x, z_t], dim=-1)


class StackedCascade(nn.Module):
    """
    Experimental stacked AD cascade (not the official hierarchy).

    net → LSTM-AE → z1
    proto∥z1 → USAD → z2
    phys∥z2 → TranAD → z3 (unified)
    """

    def __init__(self, lstm: LSTMAE, usad: USAD, tranad: TranAD):
        super().__init__()
        self.lstm = lstm
        self.usad = usad
        self.tranad = tranad

    @property
    def latent_dim(self) -> int:
        return int(self.tranad.latent_dim)

    def encode_stages(
        self,
        net: torch.Tensor,
        proto: torch.Tensor,
        phys: torch.Tensor,
        *,
        detach_prev: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z1 = self.lstm.encode(net)
        if detach_prev:
            z1 = z1.detach()
        x_proto = inject_context(proto, z1)
        z2 = self.usad.encode(x_proto)
        if detach_prev:
            z2 = z2.detach()
        x_phys = inject_context(phys, z2)
        z3 = self.tranad.encode(x_phys)
        return z1, z2, z3

    def forward_z(
        self, net: torch.Tensor, proto: torch.Tensor, phys: torch.Tensor
    ) -> torch.Tensor:
        """Return unified latent z3."""
        _, _, z3 = self.encode_stages(net, proto, phys, detach_prev=True)
        return z3

    def freeze_lstm(self) -> None:
        self.lstm.eval()
        for p in self.lstm.parameters():
            p.requires_grad = False

    def freeze_usad(self) -> None:
        self.usad.eval()
        for p in self.usad.parameters():
            p.requires_grad = False


def build_cascade(
    *,
    n_net: int = 7,
    n_proto: int = 122,
    n_phys: int = 65,
    latent_dim: int = 32,
    hidden_dim: int = 64,
    lstm_layers: int = 1,
    lstm_dropout: float = 0.0,
    d_model: int = 64,
    nhead: int = 4,
    tranad_layers: int = 2,
    dim_feedforward: int = 128,
    tranad_dropout: float = 0.1,
) -> StackedCascade:
    """Fresh models sized for domain + context dims."""
    lstm = LSTMAE(
        n_features=n_net,
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
        num_layers=lstm_layers,
        dropout=lstm_dropout,
    )
    usad = USAD(
        n_features=n_proto + latent_dim,
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
    )
    tranad = TranAD(
        n_features=n_phys + latent_dim,
        d_model=d_model,
        nhead=nhead,
        num_layers=tranad_layers,
        dim_feedforward=dim_feedforward,
        dropout=tranad_dropout,
        latent_dim=latent_dim,
    )
    return StackedCascade(lstm, usad, tranad)
