#!/usr/bin/env python3
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('./backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dl.settings')

django.setup()

from api.models import Book, BookCatagory

def create_sample_books():
    print("Creating sample books...")
    
    # Create a sample category if none exists
    category, created = BookCatagory.objects.get_or_create(
        name='Education'
    )
    
    if created:
        print('[CREATED] Created Education category')
    else:
        print('[EXISTS] Education category already exists')

    # Create sample books
    books_data = [
        {
            'title': 'Advanced Mathematics',
            'author': 'John Doe',
            'price': 25.99,
            'hard_price': 30.99,
            'soft_price': 25.99,
            'rental_price_per_week': 5.99,
            'description': 'A comprehensive guide to advanced mathematics covering calculus, linear algebra, and differential equations.',
            'category': category,
            'book_type': 'both',
            'is_for_sale': True,
            'is_for_rent': True,
            'is_active': True,
            'language': 'english',
            'grade_level': 'advanced'
        },
        {
            'title': 'Physics Fundamentals',
            'author': 'Jane Smith',
            'price': 22.99,
            'hard_price': 27.99,
            'soft_price': 22.99,
            'rental_price_per_week': 4.99,
            'description': 'Basic principles of physics explained simply for students and beginners.',
            'category': category,
            'book_type': 'both',
            'is_for_sale': True,
            'is_for_rent': True,
            'is_active': True,
            'language': 'english',
            'grade_level': 'intermediate'
        },
        {
            'title': 'Chemistry for Students',
            'author': 'Mike Johnson',
            'price': 19.99,
            'hard_price': 24.99,
            'soft_price': 19.99,
            'rental_price_per_week': 3.99,
            'description': 'Essential chemistry concepts for students including organic and inorganic chemistry.',
            'category': category,
            'book_type': 'both',
            'is_for_sale': True,
            'is_for_rent': True,
            'is_active': True,
            'language': 'english',
            'grade_level': 'advanced'
        },
        {
            'title': 'Biology Essentials',
            'author': 'Sarah Wilson',
            'price': 21.99,
            'hard_price': 26.99,
            'soft_price': 21.99,
            'rental_price_per_week': 4.49,
            'description': 'Comprehensive biology textbook covering cell biology, genetics, and ecology.',
            'category': category,
            'book_type': 'both',
            'is_for_sale': True,
            'is_for_rent': True,
            'is_active': True,
            'language': 'english',
            'grade_level': 'advanced'
        },
        {
            'title': 'English Literature Guide',
            'author': 'David Brown',
            'price': 18.99,
            'hard_price': 23.99,
            'soft_price': 18.99,
            'rental_price_per_week': 3.49,
            'description': 'A comprehensive guide to English literature from classical to modern times.',
            'category': category,
            'book_type': 'both',
            'is_for_sale': True,
            'is_for_rent': True,
            'is_active': True,
            'language': 'english',
            'grade_level': 'intermediate'
        }
    ]

    created_books = []
    for book_data in books_data:
        book, created = Book.objects.get_or_create(
            title=book_data['title'],
            author=book_data['author'],
            defaults=book_data
        )
        if created:
            created_books.append(book)
            print(f'[CREATED] Created book: {book.title} (ID: {book.id})')
        else:
            print(f'[EXISTS] Book already exists: {book.title} (ID: {book.id})')

    print(f'\n[SUMMARY] Summary:')
    print(f'   Total books: {Book.objects.count()}')
    print(f'   Active books: {Book.objects.filter(is_active=True).count()}')
    print(f'   Created {len(created_books)} new books')

if __name__ == '__main__':
    create_sample_books()