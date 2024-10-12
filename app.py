from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_from_directory,abort,session
from auth import bp as auth_bp, init_login_manager, check_rights
from flask_migrate import Migrate
from models import db, Book, Genre, Image, Review, AllBookVisits, LastBookVisits
from flask_login import login_required, current_user
from tools import ImageSaver, extract_params
import os
from reviews import bp as reviews_bp

from datetime import datetime, timedelta

app = Flask(__name__)  # Создание экземпляра Flask-приложения
application = app  # Создание экземпляра приложения для WSGI-серверов

app.config.from_pyfile('config.py')  # Загрузка конфигурации приложения из файла config.py

db.init_app(app)  # Инициализация объекта базы данных SQLAlchemy для приложения
migrate = Migrate(app, db)  # Инициализация Flask-Migrate для управления миграциями

init_login_manager(app)  # Инициализация менеджера аутентификации и авторизации пользователей

from visits import bp as visits_bp  # Импорт Blueprint для обработки посещений книг

app.register_blueprint(auth_bp)  # Регистрация Blueprint для обработки аутентификации и пользователей
app.register_blueprint(reviews_bp)  # Регистрация Blueprint для обработки отзывов
app.register_blueprint(visits_bp)  # Регистрация Blueprint для обработки посещений книг


def get_top_five():
    # Функция для получения пяти наиболее популярных книг за последние 3 месяца
    start = datetime.now() - timedelta(days=3 * 30)  # Вычисление даты, предшествующей 3 месяцам назад
    # Запрос к базе данных для получения идентификаторов книг и количества их посещений за указанный период
    top_books = (db.session
                        .query(AllBookVisits.book_id, db.func.count(AllBookVisits.id))
                        .filter(start <= AllBookVisits.created_at)
                        .group_by(AllBookVisits.book_id)
                        .order_by(db.func.count(AllBookVisits.id).desc())
                        .limit(5).all())
    result = []
    # Проход по результатам запроса и получение объектов книг и количества их посещений
    for i, for_enum in enumerate(top_books):
        book = Book.query.get(top_books[i][0])  # Получение объекта книги по идентификатору
        result.append((book, top_books[i][1]))  # Добавление кортежа с книгой и количеством посещений в список
    return result  # Возврат списка пяти наиболее популярных книг

def get_last_five():
    # Функция для получения последних просмотренных книг текущего пользователя или из сессии
    if current_user.is_authenticated:
        # Запрос к базе данных для получения последних посещенных книг текущего пользователя
        last_books = (LastBookVisits.query
                            .filter_by(user_id=current_user.id)
                            .order_by(LastBookVisits.created_at.desc())
                            .limit(5)
                            .all())
    else:
        last_books = session.get('last_books')  # Получение последних просмотренных книг из сессии
    result = []
    if current_user.is_authenticated:
        for book_visit in last_books:
            result.append(Book.query.get(book_visit.book_id))  # Добавление объектов книг в список
    else:
        if last_books:
            for book_visit in last_books:
                result.append(Book.query.get(book_visit))  # Добавление объектов книг в список
    return result  # Возврат списка последних просмотренных книг


@app.route('/')
def index():
    # Основной маршрут для отображения главной страницы
    page = request.args.get('page', 1, type=int)
    top_five_books = get_top_five()  # Получение списка пяти популярных книг
    last_five_books = get_last_five()  # Получение списка последних просмотренных книг
    books = Book.query.order_by(Book.year_release.desc())  # Запрос на получение всех книг, сортировка по году выпуска
    pagination = books.paginate(page=page, per_page=app.config['PER_PAGE'])  # Пагинация результатов запроса
    genres = Genre.query.all()  # Получение всех жанров
    books = pagination.items  # Список книг для текущей страницы
    book = None  # Начальное значение для переменной книги
    return render_template("index.html", pagination=pagination, 
                           books=books, book=book, genres=genres,
                           top_books=top_five_books,
                           last_books=last_five_books)  # Рендеринг шаблона index.html с передачей данных

@app.route('/images/<image_id>')
def image(image_id):
    # Маршрут для отображения изображений книг по идентификатору изображения
    img = Image.query.get(image_id)  # Получение объекта изображения по его идентификатору
    if img is None:
        abort(404)  # В случае отсутствия изображения, вызов ошибки 404
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               img.file_name)  # Отправка файла изображения из указанной директории

BOOKS_PARAMS = [
    'name', 'author', 'publisher', 'year_release', 'pages_volume',
    'short_desc',
]

@app.route('/new', methods=["POST", "GET"])
@login_required
@check_rights('create')
def new():
    # Маршрут для создания новой книги
    if request.method == "POST":
        f = request.files.get('background_img')  # Получение файла обложки книги из формы
        if f and f.filename:
            img = ImageSaver(f).save()  # Сохранение изображения обложки книги
            params = extract_params(BOOKS_PARAMS)  # Извлечение параметров книги из формы
            if not params['year_release'].isdigit():
                flash('Год должен быть числом', 'danger')
            if not params['pages_volume'].isdigit():
                flash('Объем страниц должен быть числом', 'danger')
            else:
                genres = request.form.getlist('genres')  # Получение списка выбранных жанров книги из формы
                genres_list = []
                for i in genres:
                    genre = Genre.query.filter_by(id=i).first()  # Получение объекта жанра по его идентификатору
                    if genre:
                        genres_list.append(genre)
                    else:
                        flash(f'Жанр с id {i} не найден', 'danger')  # Вывод сообщения об ошибке, если жанр не найден

                book = Book(**params, image_id=img.id)  # Создание новой книги с передачей параметров и изображения
                book.prepare_to_save()  # Подготовка к сохранению книги
                book.genres = genres_list  # Привязка жанров к книге
                try:
                    db.session.add(book)  # Добавление книги в сессию базы данных
                    db.session.commit()  # Применение изменений в базе данных
                    flash('Книга успешно добавлена', 'success')  # Вывод сообщения об успешном добавлении книги
                    return redirect(url_for('show', book_id=book.id))  # Переадресация на страницу отображения информации о книге
                except Exception as e:
                    db.session.rollback()  # Откат изменений в случае ошибки
                    flash(f'При сохранении данных возникла ошибка: {e}', 'danger')  # Вывод сообщения об ошибке сохранения
        else:
            flash('У книги должна быть обложка', 'danger')  # Вывод сообщения о необходимости обложки у книги
    
    genres = Genre.query.all()  # Получение всех жанров для формы создания книги
    return render_template('books/new_edit.html',
                           action='create',  # Определение действия (создание)
                           genres=genres,
                           book={})  # Передача пустого словаря для объекта книги

@app.route('/edit/<int:book_id>', methods=["POST", "GET"])
@login_required
@check_rights('edit')
def edit(book_id):
    if request.method == "POST":
        # Извлечение параметров книги из формы редактирования
        params = extract_params(BOOKS_PARAMS)
        genres = request.form.getlist('genres')
        genres_list = []

        # Получение объекта книги по её идентификатору
        book = Book.query.get(book_id)
        # Обновление полей книги данными из формы
        if not params['year_release'].isdigit():
            flash('Год должен быть числом', 'danger')
        if not params['pages_volume'].isdigit():
            flash('Объем страниц должен быть числом', 'danger')
        else:
            book.name = params['name']
            book.author = params['author']
            book.publisher = params['publisher']
            book.year_release = params['year_release']
            book.pages_volume = params['pages_volume']
            book.short_desc = params['short_desc']
            # Обновление жанров книги
            for i in genres:
                genre = Genre.query.filter_by(id=i).first()
                genres_list.append(genre)
            book.genres = genres_list
            try:
                # Сохранение обновленных данных книги в базе данных
                db.session.add(book)
                db.session.commit()
                flash('Книга успешно отредактирована', 'success')
                return redirect(url_for('show', book_id=book.id))  # Перенаправление на страницу просмотра книги
            except Exception as e:
                db.session.rollback()
                flash(f'При сохранении данных возникла ошибка: {e}', 'danger')  # В случае ошибки выводим сообщение об ошибке
        
    # Получение данных книги для отображения в форме редактирования
    book = Book.query.get(book_id)
    genres = Genre.query.all()
    return render_template('books/new_edit.html',
                           action='edit',
                           genres=genres,
                           book=book)

@app.route('/<int:book_id>/delete', methods=['POST'])
@login_required
@check_rights('delete')
def delete(book_id):
    book = Book.query.get(book_id)
    # Проверка зависимости у обложки
    references = len(Book.query.filter_by(image_id=book.image.id).all())
       
    try:
         # Удаление всех зависимостей
        for item in AllBookVisits.query.filter_by(book_id=book_id):
            db.session.delete(item)
        for item in LastBookVisits.query.filter_by(book_id=book_id):
            db.session.delete(item)
        for item in Review.query.filter_by(book_id=book_id):
            db.session.delete(item)

        db.session.delete(book)
        # Если зависимость единственная, то обложку можно удалить
        if references == 1:
            image = Image.query.get(book.image.id)
            delete_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                image.file_name)
            db.session.delete(image)
            os.remove(delete_path)
        db.session.commit()
        flash('Удаление книги прошло успешно', 'success')
    except:
        db.session.rollback()
        flash('Во время удаления книги произошла ошибка', 'danger')

    return redirect(url_for('index'))


@app.route('/<int:book_id>')
def show(book_id):
    # Получение объекта книги по её идентификатору
    book = Book.query.get(book_id)
    # Подготовка данных книги для отображения на странице
    book.prepare_to_html()

    # Получение всех отзывов для данной книги
    reviews = Review.query.filter_by(book_id=book_id)
    user_review = None

    # Подготовка каждого отзыва к отображению на странице
    for review in reviews:
        review = review.prepare_to_html()

    # Проверка, авторизован ли текущий пользователь
    if current_user.is_authenticated:
        # Получение отзыва текущего пользователя для этой книги, если такой имеется
        user_review = reviews.filter_by(user_id=current_user.id).first()

    reviews.all()  # Загрузка всех отзывов из базы данных

    return render_template('books/show.html',
                           book=book,
                           user_review=user_review,
                           reviews=reviews)

def add_book_visit(book_id, user_id):
    try:
        # Добавление записи о посещении книги текущим пользователем
        visit_params = {
            'user_id': user_id,
            'book_id': book_id,
        }
        db.session.add(AllBookVisits(**visit_params))  # Добавление записи в сессию базы данных
        db.session.commit()  # Фиксация изменений в базе данных
    except:
        db.session.rollback()  # Откат изменений в случае ошибки

def last_visit_for_user(book_id, user_id):
    new_log = None
    
    # Поиск последней записи о посещении данной книги текущим пользователем
    last_log = LastBookVisits.query.filter_by(book_id=book_id).filter_by(user_id=current_user.id).first()

    if last_log:
        last_log.created_at = db.func.now()  # Обновление времени последнего посещения
    else:
        new_log = LastBookVisits(book_id=book_id, user_id=user_id)  # Создание новой записи о посещении

        if new_log:
            try:
                db.session.add(new_log)  # Добавление новой записи в сессию базы данных
                db.session.commit()  # Фиксация изменений
            except:
                db.session.rollback()  # Откат изменений в случае ошибки



def last_visit_for_anonim(book_id):
    # Получение данных о последних просмотренных книгах из сессии пользователя
    data_from_cookies = session.get('last_books')

    # Если данные уже существуют
    if data_from_cookies:
        # Если книга уже присутствует в истории, удаляем её и добавляем в начало списка
        if book_id in data_from_cookies:
            data_from_cookies.remove(book_id)
            data_from_cookies.insert(0, book_id)
        else:
            # Если книги нет в истории, добавляем её в начало списка
            data_from_cookies.insert(0, book_id)
    
    # Если в истории нет данных
    if not data_from_cookies:
        data_from_cookies = [book_id]

    # Сохраняем обновлённые данные обратно в сессию
    session['last_books'] = data_from_cookies


@app.before_request
def logger():
    # Игнорирование запросов к статическим файлам и изображениям
    if (request.endpoint == 'static'
        or request.endpoint == 'image'):
        return
    elif request.endpoint == 'show':  # Если запрос направлен на страницу отображения книги
        user_id = getattr(current_user, 'id', None)  # Получение ID текущего пользователя, если он авторизован
        book_id = request.view_args.get('book_id')  # Получение ID книги из запроса

        # Если пользователь авторизован, вызываем функцию записи последнего посещения
        if current_user.is_authenticated:
            last_visit_for_user(book_id, user_id)
        else:
            # Если пользователь не авторизован, вызываем функцию записи последнего посещения для анонимных пользователей
            last_visit_for_anonim(book_id)

        # Запись логов о посещении книги за последние 24 часа
        start = datetime.now() - timedelta(days=1)
        this_day = AllBookVisits.query.filter_by(book_id=book_id).filter(AllBookVisits.created_at >= start)

        log_params = {
            'book_id': book_id,
            'user_id': user_id,
        }

        # Фильтрация логов по пользователю, если он авторизован
        if current_user.is_authenticated:
            this_day = this_day.filter_by(user_id=current_user.get_id())
        else:
            this_day = this_day.filter(AllBookVisits.user_id.is_(None))

        # Проверка, что количество логов за день меньше 10
        if len(this_day.all()) < 10:
            db.session.add(AllBookVisits(**log_params))  # Добавление лога в сессию базы данных
            db.session.commit()  # Фиксация изменений в базе данных
        else:
            db.session.rollback()  # Откат изменений в случае превышения лимита записей
