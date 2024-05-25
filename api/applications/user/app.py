from . import schemas


def login_user(login_credentials:schemas.LoginCredentials):
    random_value = login_credentials.userid[-1]
    random_value = ord(random_value)
    if random_value%2 == 0:
        return {"result":"user validated"}
    else:
        return {"result":"invalid user"}