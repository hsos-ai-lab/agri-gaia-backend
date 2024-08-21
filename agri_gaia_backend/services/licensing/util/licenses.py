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

# See: https://api.github.com/licenses?featured=false&per_page=100&page=1
LICENSES = {
    frozenset({"MIT License", "MIT"}): "mit",
    frozenset(
        {
            "BSD",
            "BSD License",
            "BSD-2-Clause",
            "BSD 2",
            "BSD 2 Clause",
            "FreeBSD License",
            "FreeBSD",
        }
    ): "bsd-2-clause",
    frozenset(
        {"Apache", "Apache Software License", "Apache-2.0", "Apache License 2.0"}
    ): "apache-2.0",
    frozenset(
        {
            "GNU Library or Lesser General Public License (LGPL)",
            "LGPL",
            "LGPL v2.1",
            "LGPL 2.1",
            "LGPL 2",
            "Lesser General Public License",
        }
    ): "lgpl-2.1",
    frozenset(
        {
            "zlib License",
            "zlib",
        }
    ): "zlib",
    frozenset(
        {
            'BSD 3-Clause "New" or "Revised" License',
            "BSD 3-Clause",
            "BSD 3 Clause",
            "BSD 3",
        }
    ): "bsd-3-clause",
    frozenset(
        {
            "GNU Affero General Public License v3.0",
            "AGPL v3",
            "AGPL v3.0",
            "AGPL 3",
            "AGPL 3.0",
        }
    ): "agpl-3.0",
    frozenset(
        {
            "GNU General Public License v2.0",
            "GPL 2",
            "GPL 2.0",
            "GPL v2",
            "GPL v2.0",
        }
    ): "gpl-2.0",
    frozenset({"ISC", "ISC License", "OSI Approved", "OSI"}): "isc",
}
