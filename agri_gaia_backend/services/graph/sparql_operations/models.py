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

import os

from rdflib.namespace import RDF, DCTERMS
from rdflib import Namespace
from rdflib import Graph
from rdflib import Literal, URIRef

from . import util

import logging

FUSEKI_ENDPOINT = os.environ.get("FUSEKI_ENDPOINT")
SPARQL_UPDATE_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/update"
SPARQL_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/sparql"

logger = logging.getLogger("api-logger")


def query_for_concepts(concepts):
    for concept in concepts:
        concept = "<" + concept + ">"
    concept_string = ",".join(concepts)
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?iri WHERE {{
            ?iri a <http://w3id.org/gaia-x/gax-trust-framework#SoftwareResource> .
            ?iri <http://www.w3.org/ns/dcat#keyword> ?obj .
            filter (?obj IN ({concept_string}))
        }}"""

    return util.send_query(SPARQL_QUERY_ENDPOINT, query)


def query_for_keyword(keyword):
    query = f"""SELECT ?iri WHERE {{
            ?iri a <http://w3id.org/gaia-x/gax-trust-framework#SoftwareResource> .
            ?iri <http://www.w3.org/ns/dcat#keyword> <{keyword}> .
        }}"""

    return util.send_query(SPARQL_QUERY_ENDPOINT, query)


def delete_model(model_id):
    model_id_splitted = model_id.split("#")
    model_id_splitted[-1] = "_Distribution"
    distribution_id = "#".join(model_id_splitted)

    query = f"""
        DELETE{{  ?id ?p ?o }}
            WHERE{{   
                {{
                    FILTER (?id = <{model_id}>)
                    ?id ?p ?o
                }}
                UNION
                {{
                    FILTER (?id = <{distribution_id}>)
                    ?id ?p ?o
                }}
                
            }}"""

    return util.send_update(SPARQL_UPDATE_ENDPOINT, query)


# Returns a default graph for a model, that is located inside a bucket on a server located at the passed url
#
# minio_server: the location of the minio instance
# bucket:       the bucket name
# model:      the model name


def get_default_graph(minio_server: str, bucket: str, model_name: str, model_id: int):
    graph = Graph()
    dcat = Namespace("http://www.w3.org/ns/dcat#")
    # gaiax_core = Namespace("http://w3id.org/gaia-x/core#")
    # gaiax_resource = Namespace("http://w3id.org/gaia-x/resource#")
    gax_trust_framework = Namespace("http://w3id.org/gaia-x/gax-trust-framework#")

    graph.bind("dcat", dcat)
    graph.bind("gax-trust-framework", gax_trust_framework)
    # graph.bind("gaiax-core", gaiax_core)
    # graph.bind("gaiax_resource", gaiax_resource)
    graph.bind("dct", DCTERMS)
    id_string = "https://" + minio_server + "/" + bucket + "/models/" + str(model_id)
    accessURL = URIRef(id_string)
    modelid = URIRef(id_string + "#_Model")
    distributionid = URIRef(id_string + "#_Distribution")
    graph.add((modelid, dcat.title, Literal(model_name)))
    # graph.add((modelid, dcat.creator, Literal(bucket)))
    graph.add((modelid, dcat.publisher, Literal(bucket)))
    graph.add((modelid, RDF.type, gax_trust_framework.SoftwareResource))
    graph.add((modelid, dcat.distribution, distributionid))
    graph.add((distributionid, dcat.accessURL, accessURL))
    return graph, id_string


# Returns a graph for a model, that is located inside a bucket on a server located at the passed url.
# The model has to be annotated with information on used labels, the creator and the creation date.
#
# labels:       the used labels for annotation
# minio_server: the location of the minio instance
# bucket:       the bucket name
# model:      the model name
# description:  the model description


def create_graph(
    uris,
    minio_server: str,
    bucket: str,
    model_name: str,
    model_id: int,
    description: str,
):
    (graph, id_string) = get_default_graph(minio_server, bucket, model_name, model_id)
    dcat = Namespace("http://www.w3.org/ns/dcat#")

    modelid = URIRef(id_string + "#_Model")
    for uri in uris:
        graph.add((modelid, dcat.keyword, uri))
    graph.add((modelid, dcat.description, Literal(description)))
    return graph, modelid
