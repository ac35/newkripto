from datetime import datetime
from time import time
from hashlib import md5
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, login
from flask_login import UserMixin
from kripto_core.rsa.make_rsa_keys import generate_key


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    public_key = db.Column(db.Text)
    private_key = db.Column(db.Text)
    confirmed = db.Column(db.Boolean, default=False)   # ketika sudah konfirmasi jadi True
    confirmed_timestamp = db.Column(db.DateTime)    # mencatat waktu id berhasil dikonfirmasi
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # ikutin normalnya db.relationship didefine di sisi "one"
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=robohash&s={}'.format(digest, size)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    def get_confirm_email_token(self, expires_in=3600):
        return jwt.encode(
            {'email_confirmation': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    @staticmethod
    def verify_confirm_email_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['email_confirmation']
        except:
            return
        return User.query.get(id)

    def make_rsa_keys(self, keysize=1024):
        # membuat kunci publik dan privat rsa dengan tipe Text
        pubkey, privkey = generate_key(keysize)
        self.public_key = '{},{},{}'.format(keysize, pubkey[0], pubkey[1])
        self.private_key = '{},{},{}'.format(keysize, privkey[0], privkey[1])

    def get_public_key(self):
        keysize, n, e = self.public_key.split(',')
        return int(keysize), int(n), int(e)

    def get_private_key(self):
        keysize, n, d = self.private_key.split(',')
        return int(keysize), int(n), int(d)


class Message(db.Model):
    s = {'default': 1, 'has_been_deleted': 0}
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cipherfile_id = db.Column(db.Integer, db.ForeignKey('cipherfile.id'), unique=True)  # saya coba set unique
    cipherfile = db.relationship('Cipherfile', backref='message', uselist=False)
    status = db.Column(db.Integer, default=s['default'])
    comment = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        # return '<Message {}>'.format(Cipherfile.query.get(self.cipherfile_id))
        return '<Message {}>'.format(self.id)


class Cipherfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(80))
    file_type = db.Column(db.String(50))
    file_length = db.Column(db.Integer)
    content = db.Column(db.LargeBinary)
    encrypted_s20_key = db.Column(db.Text)
    signed_digest = db.Column(db.Text)

    def __repr__(self):
        return '<Cipherfile {}>'.format(self.filename)
