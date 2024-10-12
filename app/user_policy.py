from flask_login import current_user


class UsersPolicy:
    def __init__(self, record):
        self.record = record

    def create(self):
        return current_user.is_admin()

    def review(self):
        return (current_user.is_admin()
                or current_user.is_moderator()
                or current_user.is_user())

    def get_logs(self):
        return current_user.is_admin()

    def delete(self):
        return current_user.is_admin()

    def edit(self):
        return current_user.is_admin() or current_user.is_moderator()
