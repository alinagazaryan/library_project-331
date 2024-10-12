from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
from models import db, Book, User, Review
from auth import check_rights

# Создаем Blueprint для управления рецензиями
bp = Blueprint('reviews', __name__, url_prefix='/reviews')

# Маршрут для создания новой рецензии к книге
@bp.route('/<int:book_id>/new_review', methods=['GET', 'POST'])
@login_required  # Требуем, чтобы пользователь был авторизован для доступа к этому маршруту
@check_rights('review')  # Проверяем права доступа с помощью декоратора check_rights
def new_review(book_id):
    # Проверяем, оставлял ли пользователь уже рецензию на эту книгу
    user_review = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()

    # Если запрос пришел методом POST
    if request.method == "POST":
        # Если пользователь еще не оставлял рецензию на эту книгу
        if not user_review:
            # Получаем данные из формы
            params = {
                'book_id': book_id,
                'user_id': current_user.id,
                'rating': request.form.get('rating'),
                'text': request.form.get('text'),
            }
            # Создаем новый объект рецензии
            review = Review(**params)
            review.prepare_to_save()  # Предварительная обработка данных рецензии

            try:
                # Ищем книгу по book_id и увеличиваем счетчик рецензий и сумму рейтинга
                book = Book.query.filter_by(id=book_id).first()
                book.rating_num += 1
                book.rating_sum += int(params['rating'])

                # Добавляем объекты в сессию базы данных
                db.session.add(book)
                db.session.add(review)

                # Фиксируем изменения в базе данных
                db.session.commit()
                flash('Рецензия опубликована!', 'success')

            except:
                # В случае ошибки откатываем транзакцию
                db.session.rollback()
                flash('Возникла ошибка при обращении к БД', 'warning')
                return render_template('reviews/new_edit.html', book_id=book_id)

        else:
            # Если пользователь уже оставлял рецензию на эту книгу, выводим предупреждение
            flash('Вы уже оставили рецензию к этой книге', 'warning')
            return redirect(url_for('show', book_id=book_id))  # Перенаправляем пользователя на страницу просмотра книги

    # Отображаем шаблон для создания/редактирования рецензии
    return render_template('reviews/new_edit.html', book_id=book_id, user_review=user_review)
