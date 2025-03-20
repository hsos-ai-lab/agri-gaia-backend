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
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-

import json
import torchvision
import pytorch_lightning as pl

from pathlib import Path
from torchmetrics import MetricCollection
from typing import Optional, Union, TYPE_CHECKING, Dict
from maskrcnn_datamodule import MaskRCNNDataModule
from torchvision.models.detection.mask_rcnn import (
    MaskRCNN as TMaskRCNN,
    MaskRCNN_ResNet50_FPN_Weights,
    MaskRCNN_ResNet50_FPN_V2_Weights,
)
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from pytorch_lightning.callbacks import StochasticWeightAveraging
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from pytorch_lightning.strategies import DDPStrategy, DDPSpawnStrategy

if TYPE_CHECKING:
    from maskrcnn import MaskRCNN


# See: https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html#finetuning-from-a-pretrained-save_model
def get_model(backbone: str, pretrained: bool, num_classes: int) -> TMaskRCNN:
    if backbone == "resnet50_fpn":
        weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT if pretrained else None
        model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=weights)
    elif backbone == "resnet50_fpn_v2":
        weights = MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT if pretrained else None
        model = torchvision.models.detection.maskrcnn_resnet50_fpn_v2(weights=weights)
    else:
        raise ValueError(f"Unsupported backbone architecture: '{backbone}'")

    in_features = model.roi_heads.box_predictor.cls_score.in_features

    """
        num_classes (int): number of output classes of the model (including the background).
    """
    model.roi_heads.box_predictor = FastRCNNPredictor(
        in_features, num_classes=num_classes + 1
    )

    return model


def train_and_test_model(
    mask_rcnn: "MaskRCNN",
    epochs: int,
    data: MaskRCNNDataModule,
    swa_lrs: Optional[float],
    auto_lr_find: bool,
    auto_batch_size: bool,
    patience: Optional[int],
    strategy: Optional[str],
):
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
        # Run early stopping on train epoch end because MaskRCNN does not provide validation metrics.
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
        trainer.tune(model=mask_rcnn, datamodule=data)
        if trainer.auto_lr_find:
            print("Automatically determined learning rate:", mask_rcnn.learning_rate)

    trainer.fit(model=mask_rcnn, datamodule=data)

    trainer = pl.Trainer(devices=1, num_nodes=1, accelerator="auto")
    trainer.test(model=mask_rcnn, datamodule=data)

    return mask_rcnn


def get_num_classes(labels_filepath: str) -> int:
    with open(labels_filepath, "r") as fh:
        return len(json.load(fh)["categories"])


def configure_strategy(
    strategy: Optional[str],
) -> Union[DDPStrategy, DDPSpawnStrategy, Optional[str]]:
    if strategy == "ddp":
        return DDPStrategy(find_unused_parameters=False)

    if strategy == "ddp_spawn":
        return DDPSpawnStrategy(find_unused_parameters=False)

    return strategy


def get_sync_dist(strategy: Optional[str]) -> bool:
    return strategy is not None and (
        strategy.startswith("ddp") or strategy.startswith("dp")
    )


def create_metrics(strategy: Optional[str]) -> Union[MetricCollection, Dict]:
    dist_sync_on_step = strategy == "dp"

    # Issue with mAP iou_type="segm": https://github.com/Lightning-AI/metrics/issues/1239
    """
    return MetricCollection(
        {
            "bbox": MeanAveragePrecision(
                iou_type="bbox", dist_sync_on_step=dist_sync_on_step
            ),
            "segm": MeanAveragePrecision(
                iou_type="segm", dist_sync_on_step=dist_sync_on_step
            ),
        },
        prefix="test",
    )
    """
    return {
        "bbox": MeanAveragePrecision(
            iou_type="bbox", dist_sync_on_step=dist_sync_on_step
        ),
        "segm": MeanAveragePrecision(
            iou_type="segm", dist_sync_on_step=dist_sync_on_step
        ),
    }


def create_model_filepath(output_dir: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return str(output_path.joinpath("model.pt"))


def save_model(trained_mask_rcnn: "MaskRCNN", model_filepath: str) -> None:
    trained_mask_rcnn.to_torchscript(file_path=model_filepath)
