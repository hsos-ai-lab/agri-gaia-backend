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

import torch
import torchvision.transforms as T

from torch import Tensor
from PIL.Image import Image
from typing import Tuple, List, Dict
from torch.utils.data import Dataset
from torchvision.datasets.coco import CocoDetection


class EfficientNetDataset(Dataset):
    def __init__(
        self,
        root: str,
        annFile: str,
        img_size: int,
    ) -> None:
        self.coco_dataset = CocoDetection(root=root, annFile=annFile)
        self.instance_targets = self._create_instance_targets()
        self.img_size = img_size

    def _create_instance_targets(self) -> List[Tuple[int, int]]:
        image_index = 0
        instance_targets = []
        for _, targets in self.coco_dataset:
            for target_index in range(len(targets)):
                instance_targets.append((image_index, target_index))
            image_index += 1
        return instance_targets

    def _transforms(self, image: Image, target: Dict) -> Tuple[Tensor, Tensor]:
        image = T.Compose(
            [T.Resize(size=[self.img_size, self.img_size]), T.ToTensor()]
        )(image)

        # COCO category_ids start at 1 insted of 0
        class_index = torch.tensor(target["category_id"] - 1)
        return image, class_index

    def __getitem__(self, index: int) -> Tuple[Tensor, Tensor]:
        image_index, target_index = self.instance_targets[index]
        image, targets = self.coco_dataset[image_index]
        target = targets[target_index]

        # Extract instances from image if bounding box is present in COCO labels.
        if "bbox" in target:
            minx, miny, bbox_width, bbox_height = target["bbox"]
            maxx, maxy = minx + bbox_width, miny + bbox_height
            image = image.crop((minx, miny, maxx, maxy))

        image, target = self._transforms(image, target)

        return image, target

    def __len__(self) -> int:
        return len(self.instance_targets)
