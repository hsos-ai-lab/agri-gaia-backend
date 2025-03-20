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


class ServiceInput:
    type = "text"
    pattern = ""
    selectProps = []
    id = "0"
    label = ""
    name = ""
    required = False
    select = None
    value = ""
    description = ""

    def __iter__(self):
        return [
            self.type,
            self.pattern,
            self.selectProps,
            self.id,
            self.label,
            self.name,
            self.required,
            self.select,
            self.value,
            self.description,
        ]

    def __repr__(self):
        return (
            "(ServiceInput: "
            + self.selectProps
            + self.id
            + self.name
            + self.label
            + self.pattern
            + self.label
            + self.type
            + self.required
            + self.select
            + self.value
            + self.description
            + ")"
        )
