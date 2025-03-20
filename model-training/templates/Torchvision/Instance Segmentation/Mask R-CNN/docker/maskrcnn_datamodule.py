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

import os
import sys
import torch
import pytorch_lightning as pl
import torchvision.transforms as T

from pathlib import Path
from PIL import ImageDraw
from torch.utils.data import DataLoader
from maskrcnn_dataset import MaskRCNNDataset
from typing import Tuple, List, Dict, Optional


class MaskRCNNDataModule(pl.LightningDataModule):
    def __init__(
        self,
        images_dir: str,
        labels_dir: str,
        batch_size: int,
        img_size: int,
        num_workers: int = -1,
        check_data_path: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.batch_size = batch_size
        self.img_size = img_size
        self.num_workers = os.cpu_count() if num_workers <= 0 else num_workers
        self.check_data_path = check_data_path
        self.pin_memory = torch.cuda.is_available()

        self.train_split = None
        self.test_split = None

    """
        default_collate() extends any Numpy array or Tensor in '(images, targets) = batch' by the batch size.
        For any batch size N, we simply need ([image0, image1, ..., imageN], [target0, target1, ..., targetN]) = batch.
        See: https://pytorch.org/docs/stable/data.html#torch.utils.data.default_collate
    """

    @staticmethod
    def _collate_fn(batch: List) -> Tuple[List, List]:
        images, targets = map(list, zip(*batch))
        return images, targets

    def setup(self, stage: str) -> None:
        self.train_split = MaskRCNNDataset(
            root=os.path.join(self.images_dir, "train"),
            annFile=os.path.join(self.labels_dir, "train", "labels.json"),
            img_size=self.img_size,
        )

        self.test_split = MaskRCNNDataset(
            root=os.path.join(self.images_dir, "val"),
            annFile=os.path.join(self.labels_dir, "val", "labels.json"),
            img_size=self.img_size,
        )

        if self.check_data_path is not None:
            self.check_data_path = Path(self.check_data_path)
            self._create_segmentations_with_boxes()
            sys.exit()

    def _create_segmentations_with_boxes(self) -> None:
        assert len(self.train_split) > 0

        train_image, train_targets = self.train_split[0]
        self._save_segmentations_with_boxes(
            train_image, train_targets, filename_prefix="train"
        )

        test_image, test_targets = self.test_split[0]
        self._save_segmentations_with_boxes(
            test_image, test_targets, filename_prefix="test"
        )

    def _save_segmentations_with_boxes(
        self, image: torch.Tensor, targets: Dict, filename_prefix: str
    ) -> None:
        # image
        pil_image = T.ToPILImage()(image)
        pil_image.save(self.check_data_path.joinpath(f"{filename_prefix}_image.jpg"))

        # masks and boxes
        masks = targets["masks"]
        mask = torch.sum(masks, dim=0).to(torch.bool).to(torch.uint8) * 255
        pil_mask = T.ToPILImage()(mask)

        # draw bounding boxes into segmentation image
        boxes = targets["boxes"]
        draw = ImageDraw.Draw(pil_mask)
        for box in boxes:
            draw.rectangle(box.tolist(), outline="white", width=3)

        pil_mask.save(self.check_data_path.joinpath(f"{filename_prefix}_mask.png"))

    def train_dataloader(self) -> DataLoader:
        return DataLoader(
            self.train_split,
            num_workers=self.num_workers,
            collate_fn=self._collate_fn,
            batch_size=self.batch_size,
            shuffle=True,
            persistent_workers=True,
            pin_memory=self.pin_memory,
        )

    def test_dataloader(self) -> DataLoader:
        return DataLoader(
            self.test_split,
            num_workers=self.num_workers,
            collate_fn=self._collate_fn,
            persistent_workers=True,
            pin_memory=self.pin_memory,
        )
