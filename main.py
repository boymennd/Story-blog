from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from functools import wraps
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import (
    UserMixin,
    login_user,
    LoginManager,
    login_required,
    current_user,
    logout_user,
)
from forms import CreatePostForm, CreateUserForm, CreateLoginForm, CreateCommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config["SECRET_KEY"] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(
    app,
    size=100,
    rating="g",
    default="retro",
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None,
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.__init__(app)


@login_manager.user_loader
def user_load(user_id):
    return User.query.get(user_id)


def admin_only(f):
    @wraps(f)
    def decorate_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorate_function


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="user")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="blog")


class Comment(db.Model):
    __tablename__ = "blog_comment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog = relationship("BlogPost", back_populates="comments")
    user = relationship("User", back_populates="comments")
    comment_text = db.Column(db.Text, nullable=False)


db.create_all()


@app.route("/")
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template(
        "index.html", all_posts=posts, logged_in=current_user.is_authenticated
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    users = User.query.all()
    form = CreateUserForm()
    if form.validate_on_submit():
        for user in users:
            if user.email == form.email.data:
                flash("The email you entered already exists, please enter it again")
                return redirect(url_for("register"))
        new_user = User(
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            name=form.name.data,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(
            url_for("get_all_posts", logged_in=current_user.is_authenticated)
        )
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = CreateLoginForm()
    users = User.query.all()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        for user in users:
            if user.email == email:
                if check_password_hash(user.password, password):
                    login_user(user)
                    return redirect(
                        url_for(
                            "get_all_posts", logged_in=current_user.is_authenticated
                        )
                    )
                else:
                    flash("The password you entered is incorrect")
                    return redirect(url_for("login"))
            else:
                flash("The email you entered is incorrect or does not exist!")
                return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(blog_id=post_id).all()
    form = CreateCommentForm()
    if form.validate_on_submit():
        if logout_user():
            flash("Please login to comment")
            return redirect(url_for("login"))
        else:
            new_comment = Comment(
                comment_text=form.comment.data, user=current_user, blog=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
    return render_template(
        "post.html",
        post=requested_post,
        logged_in=current_user.is_authenticated,
        form=form,
        comments=comments,
        current_user=current_user,
    )


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template(
        "make-post.html",
        form=form,
        logged_in=current_user.is_authenticated,
        current_user=current_user,
    )


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body,
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template(
        "make-post.html", form=edit_form, logged_in=current_user.is_authenticated
    )


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("get_all_posts"))


if __name__ == "__main__":
    app.run(debug=True)
