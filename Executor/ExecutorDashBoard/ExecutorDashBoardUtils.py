

class SessionState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


#Function to provide connection to firebase to all streamlit pages
def get_firebase_conn_for_page(page_name):
    pass