from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('General', 'General'), 
        ('Tech', 'Tech'), 
        ('Finance', 'Finance'), 
        ('Life', 'Life')
    ])
    submit = SubmitField('Post')