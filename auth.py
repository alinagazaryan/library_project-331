from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User  # Подключение необходимых модулей и классов
from functools import wraps

bp = Blueprint('auth', __name__, url_prefix='/auth')  # Создание Blueprint для аутентификации

def init_login_manager(app):
    """Инициализация менеджера входа"""
    login_manager = LoginManager()  # Создание объекта менеджера входа
    login_manager.login_view = 'auth.login'  # Установка представления входа
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'  # Сообщение о необходимости аутентификации
    login_manager.login_message_category = 'warning'  # Категория сообщения о входе
    login_manager.user_loader(load_user)  # Установка функции загрузки пользователя
    login_manager.init_app(app)  # Инициализация менеджера входа для приложения

def load_user(user_id):
    """Функция загрузки пользователя"""
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()  # Загрузка пользователя из базы данных по ID
    return user

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Представление для входа"""
    if request.method == 'POST':
        login = request.form.get('login')  # Получение логина из формы
        password = request.form.get('password')  # Получение пароля из формы
        if login and password:
            user = db.session.execute(db.select(User).filter_by(login=login)).scalar()  # Поиск пользователя по логину в базе данных
            if user and user.check_password(password):  # Проверка пароля
                login_user(user)  # Вход пользователя
                flash('Вы успешно аутентифицированы.', 'success')  # Сообщение об успешной аутентификации
                next = request.args.get('next')  # Получение следующего URL после аутентификации
                return redirect(next or url_for('index'))  # Перенаправление на следующую страницу или главную
        flash('Введены неверные логин и/или пароль.', 'danger')  # Сообщение о неверном логине или пароле
    return render_template('auth/login.html')  # Возвращение шаблона для входа

@bp.route('/logout')
@login_required  # Требование аутентификации для выхода
def logout():
    """Представление для выхода"""
    logout_user()  # Выход пользователя
    return redirect(url_for('index'))  # Перенаправление на главную страницу

def check_rights(action):
    """Декоратор для проверки прав доступа"""
    def decor(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")  # Получение ID пользователя из аргументов функции
            user = None
            if user_id:
                user = load_user(user_id)  # Загрузка пользователя по ID
            if not current_user.can(action, user):  # Проверка прав доступа
                flash("У вас недостаточно прав для выполнения данного действия", "warning")  # Сообщение о недостаточных правах
                return redirect(url_for("index"))  # Перенаправление на главную страницу
            return function(*args, **kwargs)  # Вызов функции, если права доступа есть
        return wrapper
    return decor  # Возвращение декоратора
