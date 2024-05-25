from . import schemas
from ..UserDashboard.register_page import upload_client_data_to_firebase


def register_user(user_detail:schemas.UserDetails):
    user_detail = dict(user_detail)
    upload_client_data_to_firebase(user_detail)