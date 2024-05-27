from . import schemas
from ..UserDashboard.user_dashboard_utils import get_next_trader_number, update_new_client_data_to_db



def register_user(user_detail:schemas.UserDetails):
    user_detail = dict(user_detail)
    print(user_detail)
    # update_new_client_data_to_db(get_next_trader_number(), user_detail)
