import os											#to get path
from flask import Flask                             #flask functions
from flask.ext.openid import OpenID                 #to define oid required as some pages are only for users logged in
from flask.ext.login import LoginManager,UserMixin  #required for authorisation to login
from flask.ext.wtf import Form                      #required for the remember me function, to remember data in the form
from wtforms import TextField, BooleanField         #required to save username (textfield) & remember me (checkbox)


""" definition of all my variables """
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
oid = OpenID(app,os.path.join(basedir,'tmp'))
lm = LoginManager()
lm.init_app(app)

SECRET_KEY = '\x17\x03\xb5\x08\xa5\xa8\x1dh\xcc\x9e(\xa2#t\x84\xb6\xed6;9\xa2m["'
DB_USER = "root"
DB_PWD = "Bchan"
DB_NAME = "uaa"
MY_EMAIL = "estellej@gmail.com"  #default recipient (email to), used in the contact form    
SERVER = 'localhost'             #mail server
PORT = 1025                      #port for mail server
URL = 'http://127.0.0.1:5000'   #web server address


""" class user to define who is authorised or not, later matching with data from database """
class User(UserMixin):
    def __init__(self, name, id, active=True):
        self.name = name
        self.id = id
        self.active = active
    
    def is_active(self):
        return self.active

    def get_id(self):
    	return self.id    


""" class form with data to save (string username and the chechbox remember me) """
class LoginForm(Form):
    username = TextField('username',default= "") 
    remember_me = BooleanField('remember_me', default = False)
