from flask import current_app

def add_to_index(index, model):
    # Check if Elasticsearch is configured
    if not current_app.elasticsearch:
        return
    payload = {}
    # Loop through the searchable fields defined in the model
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id, document=payload)

def remove_from_index(index, model):
    # Remove document from index when a post is deleted
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)