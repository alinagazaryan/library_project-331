from flask import Blueprint, render_template, request, Response,send_file
from flask_login import login_required
from app import db, app
from models import AllBookVisits, Book
from auth import check_rights
import io
import csv
from datetime import datetime

PER_PAGE = 10

bp = Blueprint('visits', __name__, url_prefix='/visits')



@bp.route('/users_visits')
@login_required
@check_rights("get_logs")
def users_visits():
    page = request.args.get('page', 1, type=int)
    export_csv = request.args.get('export_csv', False, type=bool)

    # Базовый запрос
    query = AllBookVisits.query

    # Сортировка и пагинация
    books = query.order_by(AllBookVisits.created_at.desc())
    pagination = books.paginate(page=page, per_page=app.config['PER_PAGE'])
    books = pagination.items

    if export_csv:
        # Извлекаем все записи для экспорта в CSV
        all_books_data = query.order_by(AllBookVisits.created_at.desc()).all()

        # Создаем CSV файл в памяти
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User ID', 'Book ID', 'Visit Date'])
        
        for book_visit in all_books_data:
            writer.writerow([book_visit.user_id, book_visit.book_id, book_visit.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        
        # Перематываем указатель в начало
        output.seek(0)

        # Конвертируем строку в байты
        csv_data = output.getvalue().encode('utf-8')

        return Response(csv_data, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=users_visits.csv"})

    return render_template('visits/users_visits.html',
                           pagination=pagination,
                           books=books)


@bp.route('/books_visits')
@login_required
@check_rights("get_logs")
def books_visits():
    page = request.args.get('page', 1, type=int)
    export_csv = request.args.get('export_csv', False, type=bool)

    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    # Преобразуем строки в объекты datetime, если они предоставлены
    date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
    date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
    
    # Базовый запрос
    each_book_data = db.session.query(AllBookVisits.book_id, db.func.count(AllBookVisits.book_id))

    # Добавляем фильтрацию по датам, если они предоставлены
    if date_from:
        each_book_data = each_book_data.filter(AllBookVisits.created_at >= date_from)
    if date_to:
        each_book_data = each_book_data.filter(AllBookVisits.created_at <= date_to)

    # Продолжаем с группировкой и сортировкой
    each_book_data = each_book_data.filter(AllBookVisits.user_id.isnot(None)).group_by(AllBookVisits.book_id).order_by(db.func.count(AllBookVisits.id).desc())

    if export_csv:
        # Извлекаем все записи для экспорта в CSV, учитывая фильтрацию и сортировку
        all_books_data = each_book_data.all()
        
        # Создаем CSV файл в памяти
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Book ID', 'Book Title', 'Visit Count'])
        
        for book_id, amount in all_books_data:
            book = Book.query.get(book_id)
            writer.writerow([book_id, book.name, amount])
        
        # Перематываем указатель в начало
        output.seek(0)

        # Конвертируем строку в байты
        csv_data = output.getvalue().encode('utf-8')

        return Response(csv_data, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=books_visits.csv"})

    # Пагинация
    pagination = each_book_data.paginate(page=page, per_page=app.config['PER_PAGE'])
    books = pagination.items

    # Формирование результата
    result = []
    for book_id, amount in books:
        result.append((Book.query.get(book_id), amount))

    return render_template('visits/books_visits.html', pagination=pagination, books=result, date_from=date_from_str, date_to=date_to_str)