#!/usr/bin/env python

# SPDX-FileCopyrightText: 2024 Osnabrück University of Applied Sciences
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

import torch
import inspect
import pytorch_lightning as pl

from torch import Tensor
from util import get_sync_dist, create_metrics
from typing import Tuple, List, Dict, Optional
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torchvision.models.detection.mask_rcnn import MaskRCNN as TMaskRCNN


class MaskRCNN(pl.LightningModule):
    def __init__(
        self,
        model: TMaskRCNN,
        epochs: int = 200,
        batch_size: int = 2,
        optimizer: str = "SGD",
        learning_rate: float = 0.2,
        momentum: float = 0.9,
        weight_decay: float = 0.0001,
        test_threshold: float = 0.5,
        strategy: str = Optional[None],
    ):
        super().__init__()
        self.model = model
        self.epochs = epochs
        self.batch_size = batch_size
        self.optimizer = optimizer
        self.learning_rate = learning_rate
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.test_threshold = test_threshold
        self.strategy = strategy
        self.sync_dist = get_sync_dist(strategy)

        # See: https://torchmetrics.readthedocs.io/en/stable/detection/mean_average_precision.html
        self.test_metrics = create_metrics(strategy)

    def _threshold_predictions(self, predictions: List[Dict]) -> List[Dict]:
        for prediction in predictions:
            prediction["masks"] = (
                prediction["masks"].squeeze(dim=1) >= self.test_threshold
            )
        return predictions

    def forward(
        self, images: List[Tensor], targets: Optional[List[Dict[str, Tensor]]] = None
    ):
        return self.model(images, targets)

    """
    No validation_step implemented because MaskRCNN model does not produce 'loss_dict' after model.eval().
    See: https://github.com/pytorch/vision/issues/1350
    """

    def training_step(self, batch: Tuple[List, List], batch_idx: int) -> float:
        images, targets = batch
        loss_dict = self.model(images, targets)
        train_loss = sum([loss for loss in loss_dict.values()])
        loss_dict["train_loss"] = train_loss
        self.log_dict(
            loss_dict,
            on_step=False,
            on_epoch=True,
            prog_bar=True,
            batch_size=self.batch_size,
            sync_dist=self.sync_dist,
        )
        return train_loss

    """
    During inference, the model requires only the input tensors, and returns the
    post-processed predictions as a List[Dict[Tensor]], one for each input image.
    The fields of the Dict are as follows, where N is the number of detected instances:

    boxes (FloatTensor[N, 4]): the predicted boxes in [x1, y1, x2, y2] format.
    labels (Int64Tensor[N]): the predicted labels for each instance
    scores (Tensor[N]): the scores or each instance
    masks (UInt8Tensor[N, 1, H, W]): the predicted masks for each instance, in 0-1 range.
        In order to obtain the final segmentation masks, the soft masks
        can be thresholded, generally with a value of 0.5 (mask >= 0.5)

    See: https://pytorch.org/vision/master/models/generated/torchvision.models.detection.maskrcnn_resnet50_fpn.html
    """

    def test_step(self, batch: Tuple[List, List], batch_idx: int) -> Dict:
        images, targets = batch
        predictions = self._threshold_predictions(self.model(images, targets=None))
        return {"predictions": predictions, "targets": targets}

    def test_step_end(self, outputs: Dict) -> None:
        # self.test_metrics(outputs["predictions"], outputs["targets"])
        for iou_type in self.test_metrics.keys():
            self.test_metrics[iou_type].update(
                outputs["predictions"], outputs["targets"]
            )

    def test_epoch_end(self, outputs) -> None:
        for iou_type in self.test_metrics.keys():
            test_metrics = {
                f"{iou_type}_{map_type}": map_value
                for map_type, map_value in self.test_metrics[iou_type].compute().items()
                if float(map_value) >= 0
            }

            self.log_dict(
                test_metrics,
                on_step=False,
                on_epoch=True,
                prog_bar=True,
                batch_size=1,
                sync_dist=self.sync_dist,
            )

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
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": ReduceLROnPlateau(optimizer),
                "interval": "epoch",
                "frequency": 1,
                "monitor": "train_loss",
                "strict": True,
                "name": None,
            },
        }
