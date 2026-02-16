from flask import render_template, request, Blueprint, current_app, url_for
from flaskblog.models import Post
from flaskblog import db

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template("home.html", posts=posts)

@main.route("/about")
def about():
    return render_template("about.html", title="About")

@main.route("/search")
def search():
    # Retrieve query and page number from URL parameters
    q = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('POSTS_PER_PAGE', 5)

    if not q:
        return render_template('search.html', title='Search', posts=[], total=0)

    # Execute search via the Mixin
    ids, total, hits = Post.search(q, page, per_page)
    
    # Query database for the full objects based on IDs returned by Elasticsearch
    if total > 0:
        # Fetch posts and maintain the relevance order from Elasticsearch
        posts = db.session.execute(
            db.select(Post).filter(Post.id.in_(ids))
        ).scalars().all()
        posts.sort(key=lambda x: ids.index(x.id))

        # Match the highlight snippets from 'hits' to the 'posts' objects
        for i, post in enumerate(posts):
            # look for the hit that matches this post ID
            # In most cases, it's hits[i], but searching by ID is safer
            hit = next((h for h in hits if int(h['_id']) == post.id), None)
            if hit and 'highlight' in hit:
                post.highlights = hit['highlight']
            else:
                post.highlights = {}
    else:
        posts = []

    # Calculate pagination URLs
    next_url = url_for('main.search', q=q, page=page + 1) \
        if total > page * per_page else None
    prev_url = url_for('main.search', q=q, page=page - 1) \
        if page > 1 else None

    return render_template('search.html', title='Search Results', posts=posts, total=total, q=q, next_url=next_url, prev_url=prev_url)