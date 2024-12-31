from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.simple import EmailField, PasswordField, HiddenField
from flask_ckeditor import CKEditorField
from wtforms.validators import DataRequired, Length, Email, URL



# WTForm for creating a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


# TODO: Create a RegisterForm to register new users

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()], render_kw={"style": "width:300px"})
    email = EmailField('Email', validators=[DataRequired(), Email(granular_message=True)], render_kw={"style": "width:300px"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)], render_kw={"style": "width:300px"})
    submit = SubmitField('Register')
    # hidden_field = HiddenField("Hidden")


# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email(granular_message=True)], render_kw={"style": "width:300px"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)], render_kw={"style": "width:300px"})
    submit = SubmitField('Login')
    hidden_field = HiddenField("Hidden")

# TODO: Create a CommentForm so users can leave comments below posts
class CommentForm(FlaskForm):
    body = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


