#!/usr/bin/env python

# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import torch
import inspect
import pytorch_lightning as pl
import torch.nn.functional as F

from torch import Tensor
from typing import Tuple, Dict, Optional
from util import create_metrics, get_sync_dist
from torch.optim.lr_scheduler import ReduceLROnPlateau, StepLR


class EfficientNet(pl.LightningModule):
    def __init__(
        self,
        model,
        num_classes: int,
        epochs: int = 100,
        batch_size: int = 32,
        optimizer: str = "AdamW",
        learning_rate_scheduler: str = "ReduceLROnPlateau",
        learning_rate_step_size: int = 40,
        learning_rate: float = 0.001,
        momentum: float = 0.9,
        weight_decay: float = 0.01,
        metrics_average: str = "micro",
        strategy: Optional[str] = None,
        label_smoothing: float = 0,
    ):
        super().__init__()
        self.model = model
        self.epochs = epochs
        self.batch_size = batch_size
        self.optimizer = optimizer
        self.learning_rate_scheduler = learning_rate_scheduler
        self.learning_rate_step_size = learning_rate_step_size
        self.learning_rate = learning_rate
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.num_classes = num_classes
        self.strategy = strategy
        self.sync_dist = get_sync_dist(strategy)
        self.label_smoothing = label_smoothing

        metrics = create_metrics(
            num_classes=num_classes, average=metrics_average, strategy=strategy
        )
        self.train_metrics = metrics.clone()
        self.test_metrics = metrics.clone()

    def forward(self, images: Tensor):
        return self.model(images)

    def training_step(self, batch: Tuple[Tensor, Tensor], batch_idx: int) -> Dict:
        images, targets = batch
        logits = self.model(images)
        class_probabilities = F.softmax(logits, dim=1)
        train_loss = F.cross_entropy(
            logits, targets, label_smoothing=self.label_smoothing
        )
        self.log(
            "train_loss",
            train_loss,
            on_step=False,
            on_epoch=True,
            prog_bar=True,
            sync_dist=self.sync_dist,
        )
        return {
            "loss": train_loss,
            "class_probabilities": class_probabilities,
            "targets": targets,
        }

    def training_step_end(self, outputs: Dict) -> None:
        self.train_metrics(outputs["class_probabilities"], outputs["targets"])

    def training_epoch_end(self, outputs: Dict) -> None:
        self.log_dict(
            self.train_metrics,
            on_step=False,
            on_epoch=True,
            prog_bar=True,
            sync_dist=self.sync_dist,
        )

    def test_step(self, batch: Tuple[Tensor, Tensor], batch_idx: int) -> Dict:
        images, targets = batch
        logits = self.model(images)
        class_probabilities = F.softmax(logits, dim=1)
        return {"class_probabilities": class_probabilities, "targets": targets}

    def test_step_end(self, outputs: Dict) -> None:
        self.test_metrics(outputs["class_probabilities"], outputs["targets"])

    def test_epoch_end(self, outputs) -> None:
        self.log_dict(self.test_metrics, sync_dist=self.sync_dist)

    def configure_optimizers(self):
        optimizer = eval(f"torch.optim.{self.optimizer}")
        supported_optimizer_args = set(
            inspect.signature(optimizer.__init__).parameters.keys()
        )
        optimizer_args = {
            k: v
            for k, v in {
                "lr": self.learning_rate,
                "momentum": self.momentum,
                "weight_decay": self.weight_decay,
            }.items()
            if v is not None and k in supported_optimizer_args
        }
        optimizer = optimizer(self.parameters(), **optimizer_args)

        if self.learning_rate_scheduler == "ReduceLROnPlateau":
            learning_rate_scheduler = ReduceLROnPlateau(optimizer)
            self.learning_rate_step_size = None
        elif self.learning_rate_scheduler == "StepLR":
            learning_rate_scheduler = StepLR(
                optimizer, step_size=self.learning_rate_step_size
            )
        else:
            raise ValueError(
                f"Unsupported learning rate scheduler '{self.learning_rate_scheduler}'."
            )

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": learning_rate_scheduler,
                "interval": "epoch",
                "frequency": 1,
                "monitor": "train_loss",
                "strict": True,
                "name": None,
            },
        }
