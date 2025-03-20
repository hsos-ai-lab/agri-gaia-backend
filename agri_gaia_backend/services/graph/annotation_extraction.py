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

from xml.etree import ElementTree as ET


def get_label_list(xml_doc):
    labelLst = []
    labels = []
    try:
        labels = xml_doc.find("meta").find("task").find("labels").findall("label")
    except (ValueError, AttributeError):
        return labelLst

    for label in labels:
        labelLst.append(label.find("name").text)

    return labelLst


def get_dataset_creator(xml_doc):
    for child in xml_doc.find("meta").find("task").findall("owner"):
        user = child.find("username").text
    return user


def get_created_date(xml_doc):
    for date in xml_doc.find("meta").findall("task"):
        crDate = date.find("created").text
    return crDate


def get_metadata(file):
    xml_doc = ET.parse(file).getroot()

    labels, creator, date = (
        get_label_list(xml_doc),
        get_dataset_creator(xml_doc),
        get_created_date(xml_doc),
    )

    # file is not closed by ET.parse()
    # leads to empty file being uploaded to Minio as File cursor
    # is placed at the end of file after parsing the XML.
    file.seek(0)

    return labels, creator, date
