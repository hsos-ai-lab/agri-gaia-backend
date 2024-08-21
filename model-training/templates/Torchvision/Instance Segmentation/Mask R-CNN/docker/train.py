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

import os

from args import get_args
from maskrcnn import MaskRCNN
from maskrcnn_datamodule import MaskRCNNDataModule
from torchvision.models.detection.mask_rcnn import MaskRCNN as TMaskRCNN
from util import (
    get_model,
    train_and_test_model,
    save_model,
    get_num_classes,
    create_model_filepath,
)

from export import export_model

if __name__ == "__main__":
    ARGS = get_args()

    num_classes = get_num_classes(os.path.join(ARGS.labels_dir, "val", "labels.json"))

    mask_rcnn_data: MaskRCNNDataModule = MaskRCNNDataModule(
        images_dir=ARGS.images_dir,
        labels_dir=ARGS.labels_dir,
        batch_size=ARGS.batch_size,
        img_size=ARGS.img_size,
        check_data_path=ARGS.check_data_path,
    )

    model: TMaskRCNN = get_model(
        backbone=ARGS.backbone, pretrained=ARGS.pretrained, num_classes=num_classes
    )

    mask_rcnn: MaskRCNN = MaskRCNN(
        model=model,
        epochs=ARGS.epochs,
        batch_size=ARGS.batch_size,
        optimizer=ARGS.optimizer,
        learning_rate=ARGS.learning_rate,
        momentum=ARGS.momentum,
        weight_decay=ARGS.weight_decay,
        test_threshold=ARGS.test_threshold,
        strategy=ARGS.strategy,
    )

    trained_mask_rcnn: MaskRCNN = train_and_test_model(
        mask_rcnn=mask_rcnn,
        epochs=ARGS.epochs,
        data=mask_rcnn_data,
        swa_lrs=ARGS.swa_learning_rate,
        auto_lr_find=ARGS.auto_learning_rate,
        auto_batch_size=ARGS.auto_batch_size,
        patience=ARGS.patience,
        strategy=ARGS.strategy,
    )

    model_filepath = create_model_filepath(output_dir=ARGS.output_dir)

    export_model(
        model=trained_mask_rcnn,
        model_filepath=model_filepath,
        model_format="pytorch",
        default_model_export_func=save_model,
    )
