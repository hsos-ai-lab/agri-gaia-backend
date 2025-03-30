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

import argparse


def get_args():
    parser = argparse.ArgumentParser(
        description="Train a Torchvision EfficientNet model using PyTorch."
    )
    parser.add_argument(
        "--architecture",
        default="efficientnet_b0",
        choices=[
            "efficientnet_b0",
            "efficientnet_b1",
            "efficientnet_b2",
            "efficientnet_b3",
            "efficientnet_b4",
            "efficientnet_b5",
            "efficientnet_b6",
            "efficientnet_b7",
            "efficientnet_v2_s",
            "efficientnet_v2_m",
            "efficientnet_v2_l",
        ],
        help="EfficientNet architecture (version and size) to train.",
    )
    parser.add_argument(
        "--pretrained",
        default=False,
        action="store_const",
        const=True,
        help="Use a pretrained (ImageNet-1K) EfficientNet for training.",
    )
    parser.add_argument(
        "--metrics-average",
        type=str,
        default="micro",
        choices=["micro", "macro", "weighted", "none", "samples"],
        help="Averaging method used for calculating metrics.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of epochs to train EfficientNet for.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
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
        default=300,
        help="Size used for resizing input images.",
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        default="AdamW",
        help="Optimization algorithm used while training.",
    )
    parser.add_argument(
        "--lr-scheduler",
        default="ReduceLROnPlateau",
        choices=[
            "ReduceLROnPlateau",
            "StepLR",
        ],
        help="Learning rate scheduler used while training.",
    )
    parser.add_argument(
        "--lr-step-size",
        type=int,
        default=40,
        help="Period of learning rate decay used while training with StepLR learning rate scheduler.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
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
        default=0.01,
        help="Weight decay for optimizer.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=None,
        help="Patience in epochs for early stopping.",
    )
    parser.add_argument(
        "--label-smoothing",
        type=float,
        default=0,
        help="Label smoothing",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["dp", "ddp", "ddp_spawn", "ddp_notebook"],
        default=None,
        help="Model distribution strategy.",
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
        help="Output directory for the trained EfficientNet model.",
    )
    return parser.parse_args()
