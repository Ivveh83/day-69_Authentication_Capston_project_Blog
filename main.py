from __future__ import annotations
from datetime import date
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from forms import CreatePostForm, RegisterForm, CommentForm, LoginForm
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Integer, String, ForeignKey, Text
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, fresh_login_required
from argon2 import PasswordHasher
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from argon2.exceptions import VerifyMismatchError
from typing import List
from bs4 import BeautifulSoup
import os

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
Bootstrap5(app)

login_manager = LoginManager()
app.config['SESSION_PERMANENT'] = False #Sessionen är tillfällig och kommer att tas bort när webbläsaren stängs.
login_manager.init_app(app)

ph = PasswordHasher()


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db' #Innehåller både blogposts och användare
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///blog.db")

db = SQLAlchemy(model_class=Base)
db.init_app(app)



#PARENT to BlogPost and Comment
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    pwhash: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(1000))
    posts: Mapped[List["BlogPost"]] = relationship("BlogPost", back_populates="author") #Parent to Blogpost
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="author_of_comment")  #Parent to Comment

    def __init__(self, email: str, pwhash: str, name: str):
        self.email = email
        self.pwhash = pwhash
        self.name = name


#CHILD to User and PARENT to Comment
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id")) #Child to User
    author: Mapped["User"] = relationship("User", back_populates="posts") #Child to User
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_post")#Parent to Comment

#CHILD to User AND CHILD to BlogPost
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)

    author_of_comment_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))  # Child to User
    author_of_comment: Mapped["User"] = relationship("User", back_populates="comments")  # Child to User

    blogpost_id: Mapped[int] = mapped_column(Integer, ForeignKey("blog_posts.id"))  # Child to BlogPost
    parent_post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="comments") # Child to BlogPost


with app.app_context():
    db.create_all()


@app.after_request
def apply_csp(response):
    response.headers['Content-Security-Policy'] = (
        "script-src 'self' 'unsafe-inline' https://use.fontawesome.com https://cdn.jsdelivr.net https://cdn.ckeditor.com; "  # Tillåter skript från Font Awesome och jsDelivr
        "style-src 'self' 'unsafe-inline' https://use.fontawesome.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # Tillåter stilar från Font Awesome, Google Fonts och jsDelivr
        "font-src 'self' 'unsafe-inline' https://use.fontawesome.com https://fonts.gstatic.com; "  # Tillåter font-filer från Font Awesome och Google Fonts
        "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.ckeditor.com; "
    )
    return response



def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # print(kwargs['post_id'])
        print(current_user.id)
        post = db.get_or_404(BlogPost, kwargs['post_id'])
        print(post.author_id)
        if current_user.id != 1 and current_user.id != post.author_id:
            return redirect("https://i.pinimg.com/736x/48/8c/7f/488c7f0fb8f6b046889775edaa5a6fa1.jpg")
        return f(*args, **kwargs)
    return decorated_function

def delete_accepted(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # print(kwargs['comment_id'])
        # print(current_user.id)
        comment = db.get_or_404(Comment, kwargs['comment_id'])
        # print(comment.author_of_comment_id)
        if current_user.id != comment.author_of_comment_id:
            return redirect("https://i.pinimg.com/736x/48/8c/7f/488c7f0fb8f6b046889775edaa5a6fa1.jpg")
        return f(*args, **kwargs)
    return decorated_function








@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'GET':
        return render_template("register.html", form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            hashed_password = ph.hash(form.password.data)
            # print(hashed_password)
            try:
                new_user = User(
                    email=form.email.data,
                    name=form.name.data,
                    pwhash=hashed_password,
                    )
                db.session.add(new_user)
                db.session.commit()
            except IntegrityError:
                flash("Email already in use. Log in instead.")
            finally:
                return redirect(url_for('login'))
        # return redirect(url_for('register'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar_one_or_none()
        if user:
            try:
                ph.verify(user.pwhash, form.password.data)
                login_user(user)
                return redirect(url_for('get_all_posts'))
            except VerifyMismatchError:
                flash("Not a valid password")
                return redirect(url_for('login', form=form))
        flash("Not a valid username")
        return redirect(url_for('login', form=form))
    return render_template("login.html", form=form)



@app.route('/logout')
def logout():
    logout_user()
    print("user logged out")
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)



@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    users = db.session.execute(db.select(User)).scalars().all()
    requested_post = db.get_or_404(BlogPost, post_id)
    with app.app_context():
        all_comments_on_post = db.session.execute(db.select(Comment).where(Comment.blogpost_id == post_id)).scalars().all()
    if request.method == 'POST':
        if form.validate_on_submit():
            plain_text = BeautifulSoup(form.body.data, "html.parser").get_text()
            comment = Comment(
                text=plain_text,
                author_of_comment_id=current_user.id,
                blogpost_id=post_id
            )
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=requested_post.id))
    return render_template("post.html", users=users, post=requested_post, form=form, comments_list=all_comments_on_post)



@app.route("/new-post", methods=["GET", "POST"])
@fresh_login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)



@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)



@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    comments_to_delete = db.session.execute(db.select(Comment).where(Comment.blogpost_id == post_id)).scalars().all()
    for comment in comments_to_delete:
        comment_to_delete = db.get_or_404(Comment, comment.id)
        db.session.delete(comment_to_delete)
        db.session.commit()
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/delete_comment/<int:comment_id>")
@delete_accepted
def delete_comment(comment_id):
    print(f"delete_comment function called with comment_id: {comment_id}")
    # print(comment_id)
    comment_to_delete = db.get_or_404(Comment, comment_id)
    print(comment_to_delete)
    post_id = comment_to_delete.blogpost_id
    post_id = post_id
    print(post_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5002)
