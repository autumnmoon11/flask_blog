from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from flaskblog import db
from flaskblog.models import Post
from flaskblog.posts.forms import PostForm

posts = Blueprint('posts', __name__)


@posts.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user, category=form.category.data)
        db.session.add(post)
        db.session.commit()

        from flaskblog.tasks import summarize_post_task
        summarize_post_task.delay(post.id)
        
        flash('Your post has been created! AI is summarizing your post...', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html', title='New Post', form=form, legend="New Post")


@posts.route("/post/<int:post_id>")
def post(post_id):
    post = db.get_or_404(Post, post_id)
    return render_template('post.html', title=post.title, post=post)


@posts.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = db.get_or_404(Post, post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.category = form.category.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.category.data = post.category
    return render_template('create_post.html', title='Update Post', form=form, legend="Update Post")


@posts.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.home'))

@posts.route("/post/<int:post_id>/status")
def post_status(post_id):
    post = Post.query.get_or_404(post_id)
    if post.summary:
        return render_template('partials/_summary_content.html', post=post)
    
    return render_template('partials/_summary_loading.html', post=post)

@posts.route("/post/<int:post_id>/summarize", methods=['POST'])
@login_required
def trigger_summary(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    # Reset summary to None to trigger the "Loading" state in the UI
    post.summary = None
    db.session.commit()
    
    from flaskblog.tasks import summarize_post_task
    summarize_post_task.delay(post.id)
    
    return render_template('partials/_summary_loading.html', post=post)