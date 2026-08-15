from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail

cors = CORS()
mail = Mail()
jwt = JWTManager()
