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

import argparse


def get_args():
    parser = argparse.ArgumentParser(
        description="Train a Torchvision Mask R-CNN model using PyTorch."
    )
    parser.add_argument(
        "--backbone",
        default="resnet50_fpn",
        choices=["resnet50_fpn", "resnet50_fpn_v2"],
        help="Mask R-CNN's backbone architecture.",
    )
    parser.add_argument(
        "--check-data-path",
        type=str,
        default=None,
        help="Save segmentation mask with bounding boxes for an input image and exit.",
    )
    parser.add_argument(
        "--pretrained",
        default=False,
        action="store_const",
        const=True,
        help="Use a pretrained Mask R-CNN model for training.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=200,
        help="Number of epochs to train Mask R-CNN for.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Size of a training batch.",
    )
    parser.add_argument(
        "--auto-batch-size",
        default=False,
        action="store_const",
        const=True,
        help="Automatically determine optimal batch size.",
    )
    parser.add_argument(
        "--img-size",
        type=int,
        default=600,
        help="Size used for resizing input images.",
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        default="AdamW",
        help="Optimization algorithm used while training.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.02,
        help="Learning rate used while training.",
    )
    parser.add_argument(
        "--auto-learning-rate",
        default=False,
        action="store_const",
        const=True,
        help="Automatically find a suitable learning rate.",
    )
    parser.add_argument(
        "--swa-learning-rate",
        type=float,
        default=None,
        help="Stochastic Weight Averaging values for each parameter group of the optimizer.",
    )
    parser.add_argument(
        "--momentum",
        type=float,
        default=None,
        help="Momentum for SGD optimizer.",
    )
    parser.add_argument(
        "--weight-decay",
        type=float,
        default=None,
        help="Weight decay for optimizer.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=None,
        help="Patience in epochs for early stopping.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["dp", "ddp", "ddp_spawn", "ddp_notebook"],
        default=None,
        help="Model distribution strategy.",
    )
    parser.add_argument(
        "--test-threshold",
        type=float,
        default=0.5,
        help="Threshold value applied to soft prediction masks while testing.",
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        required=True,
        help="Directory containing training and validation images.",
    )
    parser.add_argument(
        "--labels-dir",
        type=str,
        required=True,
        help="Directory containing training and validation labels in COCO format.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for the trained Mask R-CNN model.",
    )
    return parser.parse_args()
