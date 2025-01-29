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

import json
import torchvision
import pytorch_lightning as pl

from torch import nn
from pathlib import Path
from efficientnet_datamodule import EfficientNetDataModule
from torchvision.models.efficientnet import EfficientNet as TEfficientNet

from typing import Optional, Union, TYPE_CHECKING
from pytorch_lightning.callbacks import StochasticWeightAveraging
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from pytorch_lightning.strategies import DDPStrategy, DDPSpawnStrategy
from torchmetrics import MetricCollection, Accuracy, Precision, Recall, F1Score

if TYPE_CHECKING:
    from efficientnet import EfficientNet


def get_weights_name(architecture: str) -> str:
    _, version = architecture.split("_", maxsplit=1)
    return f"EfficientNet_{version.upper()}_Weights"


def get_model(
    architecture: str,
    pretrained: bool,
    num_classes: int,
) -> TEfficientNet:
    weights_name = get_weights_name(architecture)
    weights = f"torchvision.models.{weights_name}.DEFAULT" if pretrained else None

    model = eval(f"torchvision.models.{architecture}(weights={weights})")
    num_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_features, num_classes)

    return model


def train_and_test_model(
    efficientnet: "EfficientNet",
    epochs: int,
    data: EfficientNetDataModule,
    swa_lrs: Optional[float],
    auto_lr_find: bool,
    auto_batch_size: bool,
    patience: Optional[int],
    strategy: Optional[str],
) -> "EfficientNet":
    auto_scale_batch_size = False
    if auto_batch_size:
        auto_scale_batch_size = "binsearch"
        print(
            f"Automatically determining batch size using '{auto_scale_batch_size}' method."
        )

    callbacks = []
    if swa_lrs:
        assert swa_lrs > 0, "SWA learning rate has to be positive."

        # See: https://github.com/Lightning-AI/lightning/issues/14755
        auto_lr_find = False
        auto_scale_batch_size = False
        print(
            "Disabled auto learning rate and batch size finders as they are currently incompatible with SWA."
        )
        callbacks.append(StochasticWeightAveraging(swa_lrs=swa_lrs))
        print("Using Stochastic Weight Averaging with learning rate:", swa_lrs)
    else:
        print("Stochastic Weight Averaging is disabled.")

    if patience:
        assert patience > 0, "Early stopping patience has to be positive."
        callbacks.append(
            EarlyStopping(
                monitor="train_loss",
                mode="min",
                patience=patience,
                check_on_train_epoch_end=True,
            )
        )
    else:
        print("Early Stopping is disabled.")

    trainer = pl.Trainer(
        max_epochs=epochs,
        accelerator="auto",
        devices="auto",
        limit_val_batches=0,
        log_every_n_steps=1,
        auto_lr_find=auto_lr_find,
        auto_scale_batch_size=auto_scale_batch_size,
        strategy=configure_strategy(strategy),
        callbacks=callbacks,
    )

    if not trainer.auto_lr_find:
        print("Auto learning rate finder is disabled.")

    if not trainer.auto_scale_batch_size:
        print("Auto batch size finder is disabled")

    if trainer.auto_lr_find or trainer.auto_scale_batch_size:
        trainer.tune(model=efficientnet, datamodule=data)
        if trainer.auto_lr_find:
            print("Automatically determined learning rate:", efficientnet.learning_rate)

    trainer.fit(model=efficientnet, datamodule=data)

    trainer = pl.Trainer(devices=1, num_nodes=1, accelerator="auto")
    trainer.test(model=efficientnet, datamodule=data)

    return efficientnet


def configure_strategy(
    strategy: Optional[str],
) -> Union[DDPStrategy, DDPSpawnStrategy, Optional[str]]:
    if strategy == "ddp":
        return DDPStrategy(find_unused_parameters=False)

    if strategy == "ddp_spawn":
        return DDPSpawnStrategy(find_unused_parameters=False)

    return strategy


def get_num_classes(labels_filepath: str) -> int:
    with open(labels_filepath, "r") as fh:
        return len(json.load(fh)["categories"])


def get_sync_dist(strategy: Optional[str]) -> bool:
    return strategy is not None and (
        strategy.startswith("ddp") or strategy.startswith("dp")
    )


def create_metrics(
    num_classes: int, average: str, strategy: Optional[str]
) -> MetricCollection:
    dist_sync_on_step = strategy == "dp"

    metric_params = {
        "num_classes": num_classes,
        "average": average,
        "dist_sync_on_step": dist_sync_on_step,
    }

    return MetricCollection(
        [
            Accuracy(**metric_params),
            Precision(**metric_params),
            Recall(**metric_params),
            F1Score(**metric_params),
        ]
    )


def create_model_filepath(output_dir: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return str(output_path.joinpath("model.pt"))


def save_model(trained_efficientnet: "EfficientNet", model_filepath: str) -> None:
    trained_efficientnet.to_torchscript(file_path=model_filepath)
