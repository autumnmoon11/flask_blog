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

def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0, []
    
    search = current_app.elasticsearch.search(
        index=index,
        body={
            'query': {
                'multi_match': {
                    'query': query, 
                    'fields': ['title^3', 'content'], # Title is 3x more important
                    'fuzziness': 'AUTO' 
                }
            },
            'highlight': {
                'fields': {
                    'title': {},
                    'content': {}
                }
            },
            'from': (page - 1) * per_page,
            'size': per_page
        }
    )
    
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    total = search['hits']['total']['value']
    hits = search['hits']['hits'] # This contains the highlights
    
    return ids, total, hits