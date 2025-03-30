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
import numpy as np
import torchvision.transforms.functional as F

from PIL import Image, ImageDraw
import torchvision.transforms as T
from torch.utils.data import Dataset
from typing import Tuple, Dict, List
from shapely.geometry import Polygon
from PIL.Image import Image as PILImage
from torchvision.datasets.coco import CocoDetection


class MaskRCNNDataset(Dataset):
    def __init__(self, root: str, annFile: str, img_size: int) -> None:
        self.coco_dataset = CocoDetection(
            root=root,
            annFile=annFile,
            transforms=self._transforms,
        )
        self.img_size = img_size

    """
    The input to the model is expected to be a list of tensors, each of shape [C, H, W], 
    one for each image, and should be in 0-1 range. Different images can have different sizes.

    boxes (FloatTensor[N, 4]): the ground-truth boxes in [x1, y1, x2, y2] format.
    labels (Int64Tensor[N]): the class label for each ground-truth box
    masks (UInt8Tensor[N, H, W]): the segmentation binary masks for each instance

    See: https://pytorch.org/vision/master/models/generated/torchvision.models.detection.maskrcnn_resnet50_fpn.html
    """

    def _coco_to_maskrcnn(
        self, image: torch.Tensor, target: List[Dict]
    ) -> Tuple[torch.Tensor, Dict]:
        _, height, width = image.shape

        boxes, labels, masks = [], [], []
        for annotation in target:
            minx, miny, bbox_width, bbox_height = annotation["bbox"]
            maxx, maxy = minx + bbox_width, miny + bbox_height

            boxes.append([minx, miny, maxx, maxy])

            assert (
                annotation["category_id"] > 0
            ), "An object label cannot be less or equal to zero."
            labels.append(annotation["category_id"])

            segmentation = (
                np.asarray(annotation["segmentation"])
                .round()
                .astype(int)
                .flatten()
                .tolist()
            )

            mask = Image.new("L", (width, height), 0)
            draw = ImageDraw.Draw(mask)
            draw.polygon(
                segmentation,
                outline=1,
                fill=1,
            )
            mask = F.pil_to_tensor(mask).squeeze()
            masks.append(mask)

        boxes, labels, masks = (
            torch.as_tensor(boxes, dtype=torch.float64),
            torch.as_tensor(labels, dtype=torch.int64),
            torch.stack(masks).to(torch.uint8),
        )

        N = len(target)
        assert boxes.shape == (N, 4), f"{boxes.shape}"
        assert labels.shape == (N,), f"{labels.shape}"
        assert masks.shape == (N, height, width), f"{masks.shape}"

        return image, {"boxes": boxes, "labels": labels, "masks": masks}

    @staticmethod
    def _scale_point(
        point, orig_size: Tuple[int, int], new_size: Tuple[int, int]
    ) -> np.ndarray:
        return np.asarray(point) / (np.asarray(orig_size) / np.asarray(new_size))

    def _transforms(
        self, image: PILImage, target: List[Dict]
    ) -> Tuple[torch.Tensor, List[Dict]]:
        width, height = image.size

        # Resize and convert PIL image to tensor
        image = T.Compose([T.Resize(size=[self.img_size]), T.ToTensor()])(image)
        _, new_height, new_width = image.shape

        target = list(filter(lambda t: len(t["segmentation"]) > 2, target))

        # If resize changed the original image size
        if (new_width, new_height) != (width, height):
            # Resize bounding boxes and segmentations according to image
            for i in range(len(target)):
                minx, miny, bbox_width, bbox_height = target[i]["bbox"]
                maxx, maxy = minx + bbox_width, miny + bbox_height

                minx, miny, maxx, maxy = np.apply_along_axis(
                    self._scale_point,
                    axis=1,
                    arr=[[minx, miny], [maxx, maxy]],
                    orig_size=(width, height),
                    new_size=(new_width, new_height),
                ).flatten()

                target[i]["bbox"] = torch.as_tensor(
                    [minx, miny, maxx - minx, maxy - miny]
                )
                segmentation = np.apply_along_axis(
                    self._scale_point,
                    axis=1,
                    arr=target[i]["segmentation"],
                    orig_size=(width, height),
                    new_size=(new_width, new_height),
                )
                target[i]["segmentation"] = segmentation
                target[i]["area"] = Polygon(segmentation).area

        return image, target

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, Dict]:
        image, target = self.coco_dataset[index]
        image, target = self._coco_to_maskrcnn(image, target)
        return image, target

    def __len__(self):
        return len(self.coco_dataset)
