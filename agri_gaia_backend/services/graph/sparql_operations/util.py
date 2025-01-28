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

import requests
import os

from rdflib import URIRef
from typing import Dict, List
from base64 import b64encode


import logging
import json

FUSEKI_ADMIN_USER = os.environ.get("FUSEKI_ADMIN_USER")
FUSEKI_ADMIN_PASSWORD = os.environ.get("FUSEKI_ADMIN_PASSWORD")

FUSEKI_ENDPOINT = os.environ.get("FUSEKI_ENDPOINT")
UPLOAD_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/data"
SHAPES_ENDPOINT_GET = f"{FUSEKI_ENDPOINT}shapes/get"
ONTOLOGIES_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}ontologies/sparql"
AGROVOC_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}agrovoc/sparql"
GEONAMES_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}geonames/sparql"
DATASET_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/sparql"

logger = logging.getLogger("api-logger")


predef_ns = {
    "cc": "http://creativecommons.org/ns#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "gax-contract": "http://w3id.org/gaia-x/contract#",
    "gax-core": "http://w3id.org/gaia-x/core#",
    "gax-participant": "http://w3id.org/gaia-x/participant#",
    "gax-resource": "http://w3id.org/gaia-x/resource#",
    "gax-service": "http://w3id.org/gaia-x/service#",
    "gax-node": "http://w3id.org/gaia-x/node#",
    "ids": "<https://w3id.org/idsa/core/>",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema": "http://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "sh": "http://www.w3.org/ns/shacl#",
    "vcard": "https://www.w3.org/2006/vcard/ns#",
    "void": "http://rdfs.org/ns/void#",
    "vann": "http://purl.org/vocab/vann/",
    "voaf": "http://purl.org/vocommons/voaf#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "agri-gaia-asset": "http://w3id.org/agri-gaia-x/asset#",
}


def _create_auth_header() -> Dict[str, str]:
    basic = b64encode(
        f"{FUSEKI_ADMIN_USER}:{FUSEKI_ADMIN_PASSWORD}".encode("utf-8")
    ).decode("utf-8")
    return {"Authorization": f"Basic {basic}"}


def query_possible_classes():
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?s
    WHERE 
    {
        { ?s a owl:Class }
    UNION 
        { ?s a rdfs:Class }
    }"""
    return send_query(ONTOLOGIES_QUERY_ENDPOINT, query)


def query_possible_data_ressource_labels():
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ag: <http://w3id.org/agri-gaia-x/asset#>
    SELECT ?label WHERE {
        {?sub rdfs:subClassOf* ag:AgriDataResource .
        ?sub rdfs:label ?label .
        Filter(lang(?label)='en')}
        MINUS
        {?sub rdfs:subClassOf* <http://w3id.org/agri-gaia-x/asset#AgriApiDescription>}
    }
    """
    result = send_query(ONTOLOGIES_QUERY_ENDPOINT, query)
    list = result["results"]["bindings"]
    labels = set()
    for i in list:
        labels.add(i["label"]["value"])
    return labels


def query_possible_data_ressources():
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
 
    Select ?resType
    Where
    {
    {?resType rdfs:subClassOf* <http://w3id.org/agri-gaia-x/asset#AgriDataResource>}
    MINUS
    {?resType rdfs:subClassOf* <http://w3id.org/agri-gaia-x/asset#AgriApiDescription>}
    }
    """
    result = send_query(ONTOLOGIES_QUERY_ENDPOINT, query)
    list = result["results"]["bindings"]
    classes = set()
    for i in list:
        classes.add(i["resType"]["value"])
    return classes


def query_attributes_for_class(class_name):
    prefix, iri_name = class_name.split(":")
    class_name = predef_ns[prefix] + iri_name
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?prop ?label ?range
    WHERE
    {{
    <{class_name}> rdfs:subClassOf* ?superclass .  
    ?prop rdfs:domain ?superclass .
    ?prop <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    ?prop <http://www.w3.org/2000/01/rdf-schema#range> ?range
    Filter(lang(?label)='en')
    }}"""
    return send_query(ONTOLOGIES_QUERY_ENDPOINT, query)


def send_update(endpoint, update):
    return requests.post(
        endpoint,
        data=update,
        headers={
            **_create_auth_header(),
            **{"Content-Type": "application/sparql-update"},
        },
    )


def get_labels_for_uri(uri: str):
    query = f"""Select ?obj WHERE {{
        <{uri}> <http://www.w3.org/ns/dcat#keyword> ?obj
    }}"""

    response = send_query(DATASET_QUERY_ENDPOINT, query)["results"]["bindings"]
    labels = []
    if len(response) > 0:
        for entry in response:
            labels.append(entry["obj"]["value"])
    return labels


def get_locations_for_uri(uri: str):
    query = f"""Select ?obj WHERE {{
        <{uri}> <http://purl.org/dc/terms/spatial> ?obj
    }}"""

    response = send_query(DATASET_QUERY_ENDPOINT, query)["results"]["bindings"]
    locations = []
    if len(response) > 0:
        for entry in response:
            locations.append(entry["obj"]["value"])
    return locations


def get_description_for_uri(uri: str):
    query = f"""Select ?obj WHERE {{
        <{uri}> <http://www.w3.org/ns/dcat#description> ?obj
    }}"""

    response = send_query(DATASET_QUERY_ENDPOINT, query)["results"]["bindings"]
    description = ""
    if len(response) > 0:
        description = response[0]["obj"]["value"]
    return description


def get_metadata_information_for_uri(uri: str):
    query = f"""Construct {{
                    ?sub ?pred ?obj
                }} 
                WHERE {{
                    ?sub ?pred ?obj
                    Filter(?sub = <{uri}>)}}
            """

    response = send_graph_query(DATASET_QUERY_ENDPOINT, query)
    return response


def get_metadata_information_for_uris(uris: List[str]):
    query = f"""Construct {{
                    ?sub ?pred ?obj
                }} 
                WHERE {{
                    ?sub ?pred ?obj
                    Filter(?sub IN (<{">, <".join(uris)}>))}}
            """

    response = send_graph_query(DATASET_QUERY_ENDPOINT, query)
    return response


# TODO: this function might leak memory..
# Sends a SparQL query to the Fuseki query endpoint and returns the result as json
#
# endpoint: the fuseki query endpoint
# query:    the query, to be executed
def send_query(endpoint, query: str):
    response = requests.post(
        endpoint,
        data=query.encode("utf-8"),
        headers={
            **_create_auth_header(),
            **{"Content-Type": "application/sparql-query"},
        },
    )
    result = response.json()
    return result


def send_graph_query(endpoint, query):
    response = requests.post(
        endpoint,
        data=query.encode("utf-8"),
        headers={
            **_create_auth_header(),
            **{
                "Content-Type": "application/sparql-query",
                "Accept": "application/ld+json",
            },
        },
    )
    return json.loads(response.content.decode("utf8").replace("'", '"'))


def store_graph(graph, fuseki_dataset: str = "ds"):
    """
    Stores a graph to the triple store located using the given endpoint.

    Args:
        graph: The Metadata, which should be stored in the RDF storage.
        fuseki_dataset: The Dataset identifier in Fuseki, where the metadata should be stored. Defaults to "ds".

    Returns:
        The response object returned by Fuseki.
    """
    return requests.post(
        UPLOAD_ENDPOINT.replace("ds", fuseki_dataset),
        data=graph.serialize(format="turtle"),
        headers={**_create_auth_header(), **{"Content-Type": "text/turtle"}},
    )


def store_json(metadata, fuseki_dataset: str = "ds"):
    """
    Stores metadata to the triple store located using the given endpoint.

    Args:
        metadata: The Metadata, which should be stored in the RDF storage.
        fuseki_dataset: The Dataset identifier in Fuseki, where the metadata should be stored. Defaults to "ds".

    Returns:
        The response object returned by Fuseki.
    """
    return requests.post(
        UPLOAD_ENDPOINT.replace("ds", fuseki_dataset),
        data=metadata,
        headers={**_create_auth_header(), **{"Content-Type": "application/ld+json"}},
    )


def get_shapes():
    return _get_graph(SHAPES_ENDPOINT_GET)


def delete_graph(graphname):
    return requests.delete(
        FUSEKI_ENDPOINT + "$/datasets/" + graphname, headers=_create_auth_header()
    )


def createFusekiDataset(object_name):
    f = open(os.path.join("fuseki", "dataset_create.ttl"))
    assembler = f.read()
    assembler = assembler.replace("DATASET_NAME", object_name, 1)

    response = requests.post(
        FUSEKI_ENDPOINT + "$/datasets",
        data=assembler,
        headers={**_create_auth_header(), **{"Content-Type": "text/turtle"}},
    )
    return response


def shacl_validate(dataset_name, shape):
    return requests.post(
        FUSEKI_ENDPOINT + dataset_name + "/shacl?graph=default",
        data=shape,
        headers={
            **_create_auth_header(),
            **{"Content-Type": "text/turtle", "Accept": "application/ld+json"},
        },
    ).json()


def get_additional_information(
    concept: str, language: str, type: str, endpoint: str = AGROVOC_QUERY_ENDPOINT
):
    if type.lower() != "broader" and type.lower() != "narrower":
        return

    additional_information = _get_additional_keywords(
        endpoint, concept, type.lower(), language
    )

    result = set()
    for res in additional_information:
        result.add(res["obj"]["value"])

    return result


def get_language(uri: str, endpoint: str = AGROVOC_QUERY_ENDPOINT):
    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> 
    
            SELECT lang(?obj) WHERE {{
            <{uri}> skosxl:literalForm ?obj .
            }}"""
    return send_query(endpoint, query)["results"]["bindings"][0]


def query_narrower_concepts(concept_uri):
    """Queries the Agrovoc Graph in the RDF storage for all concepts, which are narrower versiosn of the given concept.

    Args:
        concept_uri: The concept URI, for which narrower concepts should be found.

    Returns:
        A list of all concepts, which are narrower than the given concept.
    """
    query = f"""SELECT ?obj WHERE{{
    	<{concept_uri}> <http://www.w3.org/2004/02/skos/core#narrower>* ?obj
    }}"""
    response = send_query(AGROVOC_QUERY_ENDPOINT, query)
    concepts = []
    if len(response) > 0:
        for entry in response["results"]["bindings"]:
            concepts.append(f"<{entry['obj']['value']}>")
    return concepts


def get_possible_languages_for_keyword(
    keyword: str, endpoint: str = AGROVOC_QUERY_ENDPOINT
):
    concept, lang = _get_concept_of_keyword(endpoint, keyword, "")

    languages = _get_languages_for_concept(endpoint, concept)

    result = set()
    for res in languages:
        result.add(res[".0"]["value"])

    return result, lang


def check_keyword(keyword: str, endpoint: str = AGROVOC_QUERY_ENDPOINT):
    uri = _get_localized_uri(endpoint, keyword)
    if len(uri) == 0:
        return (None, None)

    concept = _get_concept(endpoint, uri["sub"]["value"])
    return URIRef(concept["sub"]["value"]), URIRef(uri["sub"]["value"])


def check_location(location: str, endpoint: str = GEONAMES_QUERY_ENDPOINT):
    concept = _get_geoname_uri(endpoint, location)
    return URIRef(concept["sub"]["value"])


def get_possible_keywords(language: str, endpoint: str = AGROVOC_QUERY_ENDPOINT):
    keywords = set()

    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> 

        SELECT DISTINCT ?obj WHERE
        {{
            ?sub skosxl:literalForm ?obj 
            Filter(lang(?obj)='{language}')
        }}"""

    result = send_query(endpoint, query)

    for obj in result["results"]["bindings"]:
        keywords.add(obj["obj"]["value"])

    return keywords


def get_possible_locations(endpoint: str = GEONAMES_QUERY_ENDPOINT):
    locations = set()

    query = f"""PREFIX geo: <http://www.geonames.org/ontology#> 

        SELECT DISTINCT ?obj WHERE
        {{
            ?sub geo:name ?obj 
        }}"""

    result = send_query(endpoint, query)

    for obj in result["results"]["bindings"]:
        locations.add(obj["obj"]["value"])

    return locations


def convert_to_URI(uri: str):
    return URIRef(uri)


def _get_localized_uri(endpoint: str, keyword: str):
    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> 

            SELECT ?sub WHERE
            {{
                ?sub skosxl:literalForm ?obj 
                Filter(LCASE(STR(?obj))=LCASE('{keyword}'))
            }}
        """

    result = send_query(endpoint, query)["results"]["bindings"]
    if not result:
        return []
    return result[0]


def _get_geoname_uri(endpoint: str, location: str):
    query = f"""PREFIX geo: <http://www.geonames.org/ontology#>  

            SELECT ?sub WHERE
            {{
                ?sub geo:name ?obj 
                Filter(LCASE(STR(?obj))=LCASE('{location}'))
            }}
        """

    result = send_query(endpoint, query)["results"]["bindings"]
    if not result:
        return []
    return result[0]


def _get_concept(endpoint: str, uri: str):
    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>
    
            SELECT ?sub WHERE {{
                {{
                    ?sub skosxl:prefLabel <{uri}>
                }}Union{{
                    ?sub skosxl:altLabel <{uri}>
                }}
            }}
            """

    return send_query(endpoint, query)["results"]["bindings"][0]


def _get_languages_for_concept(endpoint: str, concept: str):
    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>
                PREFIX skoscore: <http://www.w3.org/2004/02/skos/core#>
                    
                SELECT lang(?obj) WHERE 
                {{
                {{
                    <{concept}> skosxl:prefLabel/skosxl:literalForm ?obj
                }}
                Union
                {{
                    <{concept}> skosxl:altLabel/skosxl:literalForm ?obj
                }}
                Union
                {{
                    <{concept}> skoscore:prefLabel ?obj
                }}
                Union
                {{
                    <{concept}> skoscore:altLabel ?obj
                }}
                }}
            """

    return send_query(endpoint, query)["results"]["bindings"]


def _get_additional_keywords(endpoint: str, concept: str, pred: str, language: str):
    query = f"""PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>
                PREFIX skoscore: <http://www.w3.org/2004/02/skos/core#>
                    
                SELECT DISTINCT ?obj WHERE 
                {{
                {{
                    <{concept}> skoscore:{pred}/skosxl:prefLabel/skosxl:literalForm ?obj
                    filter(lang(?obj)='{language}')
                }}
                Union
                {{
                    <{concept}> skoscore:{pred}/skosxl:altLabel/skosxl:literalForm ?obj
                    filter(lang(?obj)='{language}')
                }}
                Union
                {{
                    <{concept}> skoscore:{pred}/skoscore:prefLabel ?obj
                    filter(lang(?obj)='{language}')
                }}
                Union
                {{
                    <{concept}> skoscore:{pred}/skoscore:altLabel ?obj
                    filter(lang(?obj)='{language}')
                }}
                }}
            """

    return send_query(endpoint, query)["results"]["bindings"]


def _get_concept_of_keyword(endpoint: str, keyword: str, language: str):
    result = _get_localized_uri(endpoint, keyword)
    if len(result) == 0:
        return

    if language == "":
        language = get_language(result["sub"]["value"], endpoint)[".0"]["value"]
    concept = _get_concept(endpoint, result["sub"]["value"])["sub"]["value"]

    return concept, language


def _get_graph(endpoint):
    resp = requests.get(
        endpoint,
        headers={**_create_auth_header(), **{"Accept": "text/turtle; charset=utf-8"}},
    )
    return resp.content
