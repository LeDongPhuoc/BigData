"""Internal edge writer with explicit endpoint validation in the write transaction."""


def insert_relationship(db, collection, document):
    definitions = db.graph("jobReferralGraph").edge_definitions()
    definition = next((d for d in definitions if d["edge_collection"] == collection), None)
    if definition is None:
        raise ValueError("Edge collection is not part of jobReferralGraph")
    vertices = set(definition["from_vertex_collections"] + definition["to_vertex_collections"])
    for field, allowed in (
        ("_from", definition["from_vertex_collections"]),
        ("_to", definition["to_vertex_collections"]),
    ):
        endpoint = document.get(field)
        if not isinstance(endpoint, str) or endpoint.split("/")[0] not in allowed:
            raise ValueError(f"Invalid {field} collection for {collection}")
    if collection == "connections" and document["_from"] >= document["_to"]:
        raise ValueError("Connections require distinct, canonical endpoints")
    tx = db.begin_transaction(read=sorted(vertices), write=[collection], allow_implicit=False)
    try:
        if not all(tx.has_document(document[field]) for field in ("_from", "_to")):
            raise ValueError("Relationship endpoints must exist")
        result = tx.collection(collection).insert(document)
        tx.commit_transaction()
        return result
    except Exception:
        tx.abort_transaction()
        raise
