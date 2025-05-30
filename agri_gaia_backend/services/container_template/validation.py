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

from pathlib import Path


class ContainerTemplateValidationException(Exception):
    pass


class ContainerTemplateValidator:

    def validate(template_dir: Path) -> None:
        pass


class InferenceContainerTemplateValidator(ContainerTemplateValidator):

    def validate(self, template_dir: Path) -> None:
        dockerfile_path = template_dir / Path("Dockerfile")
        if not dockerfile_path.is_file():
            raise ContainerTemplateValidationException(
                "Container template does not contain a Dockerfile"
            )
