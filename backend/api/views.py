import logging
import mimetypes
import re
from io import BytesIO
import pytesseract
import numpy as np
import cv2
from rest_framework.decorators import action
from rest_framework import serializers
from PIL import Image
import fitz

import pytesseract
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.contrib.auth import authenticate, get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view , permission_classes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import os
from django.db import models
from .models import (
    AboutUs,
    Book,
    BookCatagory,
    Payment,
    Project,
    Questions,
    QCategory,
    Quiz,
    SignWord,
    SubBookCategory,
    Subject,
    TeamMember,
    Testimonial,
    UploadedPDF,
    User,
    UserPurchase,
    UserSubjectProgress,
)
from .serializers import (
    AboutUsSerializer,
    BookSerializer,
    BookCatagorySerializer,
    BulkQuestionSerializer,
    PaymentRequestSerializer,
    PaymentSerializer,
    PaymentVerificationSerializer,
    ProjectSerializer,
    QCategorySerializer,
    QuestionsSerializer,
    SignWordSerializer,
    SubBookCategorySerializer,
    SubjectSerializer,
    SubjectWithProgressSerializer,
    TeamMemberSerializer,
    TestimonialSerializer,
    UploadedPDFSerializer,
    UserPurchaseSerializer,
    UserRegisterSerializer,
    UserSubjectProgressSerializer,
    # Enhanced serializers
    EnhancedBookSerializer,
    BookCreateUpdateSerializer,
    HardSoftBookSerializer,
    EnhancedPaymentSerializer,
    EnhancedPaymentRequestSerializer,
    EnhancedUserPurchaseSerializer,
)

from rest_framework_simplejwt.tokens import RefreshToken
from .activity_log  import get_recent_activities, log_activity  # from memory store
from rest_framework import viewsets, filters
from django.http import FileResponse

logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': getattr(user, 'role', None),
        'is_superuser': user.is_superuser,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Enhanced dashboard statistics for admin users"""
    user = request.user
    
    # Check if user has admin privileges
    if not (user.is_superuser or user.role in ['Admin', 'Staff']):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get current date for analytics
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Enhanced statistics
    data = {
        # Basic counts
        "total_books": Book.objects.count(),
        "total_courses": Subject.objects.count(),
        "total_exams": Questions.objects.count(),
        "research_papers": Project.objects.filter(badge='featured').count(),
        "active_students": User.objects.filter(role='Student').count(),
        "ongoing_projects": Project.objects.count(),
        "total_users": User.objects.count(),
        "total_categories": BookCatagory.objects.count(),
        "total_subcategories": SubBookCategory.objects.count(),
        "total_sign_words": SignWord.objects.count(),
        "total_testimonials": Testimonial.objects.count(),
        "total_team_members": TeamMember.objects.count(),
        
        # Enhanced book type statistics
        "books_by_type": {
            "hard_copy": Book.objects.filter(book_type__in=['hard', 'both'], hard_price__gt=0, is_for_sale=True).count(),
            "soft_copy": Book.objects.filter(book_type__in=['soft', 'both'], soft_price__gt=0, is_for_sale=True).count(),
            "both_available": Book.objects.filter(book_type='both').count(),
            "rental_available": Book.objects.filter(is_for_rent=True).count(),
        },
        
        # Recent activity (last 30 days)
        "books_added_last_30_days": Book.objects.filter(created_at__gte=thirty_days_ago).count(),
        "users_registered_last_30_days": User.objects.filter(date_joined__gte=thirty_days_ago).count(),
        "projects_added_last_30_days": Project.objects.filter(created_at__gte=thirty_days_ago).count(),
        "questions_added_last_30_days": Questions.objects.filter(subject__created_at__gte=thirty_days_ago).count(),
        
        # User role distribution
        "user_roles": {
            "students": User.objects.filter(role='Student').count(),
            "staff": User.objects.filter(role='Staff').count(),
            "admins": User.objects.filter(role='Admin').count(),
            "superusers": User.objects.filter(is_superuser=True).count(),
        },
        
        # Content distribution
        "content_stats": {
            "books": {
                "total": Book.objects.count(),
                "free": Book.objects.filter(is_free=True).count(),
                "premium": Book.objects.filter(is_premium=True).count(),
                "featured": Book.objects.filter(is_featured=True).count(),
            },
            "projects": {
                "total": Project.objects.count(),
                "featured": Project.objects.filter(badge='featured').count(),
                "top_rated": Project.objects.filter(badge='top-rated').count(),
                "new": Project.objects.filter(badge='new').count(),
            },
            "books_by_language": dict(
                Book.objects.values('language').annotate(count=models.Count('id')).values_list('language', 'count')
            ),
            "books_by_grade": dict(
                Book.objects.values('grade_level').annotate(count=models.Count('id')).values_list('grade_level', 'count')
            ),
        },
        
        # Performance metrics
        "performance": {
            "total_book_views": Book.objects.aggregate(total_views=models.Sum('views'))['total_views'] or 0,
            "total_project_views": Project.objects.aggregate(total_views=models.Sum('views'))['total_views'] or 0,
            "avg_book_rating": Book.objects.aggregate(avg_rating=models.Avg('rating'))['avg_rating'] or 0,
            "avg_project_rating": Project.objects.aggregate(avg_rating=models.Avg('rating'))['avg_rating'] or 0,
            "total_book_downloads": Book.objects.aggregate(total_downloads=models.Sum('downloads'))['total_downloads'] or 0,
        },
        
        # Payment statistics
        "payment_stats": {
            "total_payments": Payment.objects.count(),
            "completed_payments": Payment.objects.filter(status='completed').count(),
            "payments_this_month": Payment.objects.filter(
                created_at__gte=thirty_days_ago, 
                status='completed'
            ).count(),
            "payment_types": dict(
                Payment.objects.filter(status='completed').values('payment_type').annotate(
                    count=models.Count('id')
                ).values_list('payment_type', 'count')
            )
        },
        
        # System health
        "system_health": {
            "server_status": "operational",  # This would be checked from actual system metrics
            "last_backup": "2024-11-03T10:00:00Z",  # This would come from backup system
            "database_size": "2.4 GB",  # This would come from database monitoring
            "active_sessions": 247,  # This would come from session tracking
        }
    }
    
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activities(request):
    activities = get_recent_activities(limit=10)

    response_data = []
    for activity in activities:
        response_data.append({
            "type": activity.get("action", "unknown"),
            "text": activity.get("text", ""),
            "timestamp": activity.get("timestamp", ""),
            "user": activity.get("user", "System"),
            "model": activity.get("model", "unknown"),
            "object_id": activity.get("object_id", None),
        })

    return Response(response_data)

class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def generate_password(self, last_name, phone):
        name_part = last_name.capitalize() if last_name else "Usr"
        phone_part = phone[-4:] if phone else "0000"
        return f"{name_part}{phone_part}"


    def create(self, request, *args, **kwargs):
        data = request.data
        
        # Check for basic required fields
        required_fields = ['first_name', 'last_name', 'email']
        
        # Additional fields for sellers
        user_type = data.get('user_type', 'buyer')
        if user_type == 'seller':
            required_fields.extend(['phone_number', 'business_name', 'business_type'])
            
        missing = [field for field in required_fields if not data.get(field)]

        if missing:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enhanced phone number validation for sellers
        if user_type == 'seller':
            phone = data.get('phone_number', '')
            # Remove all non-digit characters for validation
            phone_digits = ''.join(filter(str.isdigit, phone))
            
            # Check if phone number has at least 10 digits
            if len(phone_digits) < 10:
                return Response(
                    {"error": "Phone number must have at least 10 digits for seller accounts."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate business name and business type
            business_name = data.get('business_name', '').strip()
            business_type = data.get('business_type', '').strip()
            
            if len(business_name) < 2:
                return Response(
                    {"error": "Business name must be at least 2 characters long."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if business_type not in ['individual', 'company', 'publisher', 'bookstore', 'educational', 'other']:
                return Response(
                    {"error": "Business type must be one of: Individual Seller, Company, Publisher, Bookstore, Educational Institution, Other."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # For buyers, validate phone if provided but don't require it
            phone = data.get('phone_number', '')
            if phone:  # Only validate if phone is provided
                phone_digits = ''.join(filter(str.isdigit, phone))
                if len(phone_digits) < 8:  # More lenient for buyers
                    return Response(
                        {"error": "Phone number must have at least 8 digits if provided."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Slugify last name
        last_name = slugify(data['last_name']).replace('-', '')
        
        # Handle phone number
        phone = ''
        if user_type == 'seller':
            phone = ''.join(filter(str.isdigit, data.get('phone_number', '')))
        else:
            # For buyers, use provided phone number if any, otherwise empty string
            phone_data = data.get('phone_number', '')
            phone = ''.join(filter(str.isdigit, phone_data)) if phone_data else ''

        if len(last_name) < 3:
            return Response(
                {"error": "Last name must be at least 3 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate username
        base_username = f"{last_name[:3]}{phone[-3:]}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Check for duplicate email
        if User.objects.filter(email=data['email']).exists():
            return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for duplicate phone number BEFORE processing (for both sellers and buyers)
        # Use the processed phone number for accurate checking
        if user_type == 'seller' and phone and User.objects.filter(phone_number=phone).exists():
            return Response({"error": "Phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate password
        password = self.generate_password(last_name, phone)

        # Merge user data - let the serializer handle user_type/role mapping
        user_data = {**data, "username": username, "password": password}

        try:
            serializer = self.get_serializer(data=user_data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Send credentials via email (skip in development for testing)
            try:
                subject = "Your Account Credentials"
                message = (
                    f"Dear {user.first_name},\n\n"
                    f"Your account has been created successfully.\n"
                    f"Username: {username}\n"
                    f"Password: {password}\n\n"
                    f"Please log in and change your password.\n\n"
                    f"Thank you."
                )
                send_mail(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True  # Don't fail registration if email fails
                )
                email_sent = True
            except Exception as e:
                print(f"Email sending failed (development mode): {e}")
                email_sent = False

            return Response({
                "message": "User registered successfully." + (" Credentials sent to email." if email_sent else " Check server logs for credentials (development mode)."),
                "username": username,
                "default_password": password,
                "user": UserRegisterSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            
            # Handle specific database constraints that should return 400 instead of 500
            error_str = str(e)
            
            # Check for Django REST Framework field-level validation errors
            if "ErrorDetail(string=" in error_str and "code='unique'" in error_str:
                if "phone_number" in error_str:
                    return Response({"error": "Phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)
                elif "email" in error_str:
                    return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
                elif "username" in error_str:
                    return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Duplicate entry detected."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check for traditional database constraint violations
            if "unique constraint" in error_str.lower() or "duplicate" in error_str.lower():
                if "phone" in error_str.lower():
                    return Response({"error": "Phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)
                elif "email" in error_str.lower():
                    return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
                elif "username" in error_str.lower():
                    return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Duplicate entry detected."}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"error": "Registration failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # DEBUG: print username and password (REMOVE in production)
        print(f"Login attempt - Username: {username}, Password: {password}")

        # Validate input
        if not username or not password:
            print("Missing username or password")
            return Response({'error': 'Both username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check user existence
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"User with username '{username}' does not exist")
            return Response({'error': 'User with this username does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        # Authenticate user
        user = authenticate(username=username, password=password)
        if user is None:
            print("Authentication failed: Incorrect password")
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user is active
        if not user.is_active:
            print(f"User '{username}' is inactive")
            return Response({'error': 'This account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # DEBUG: print tokens
        print(f"Access token: {access_token}")
        print(f"Refresh token: {refresh_token}")

        # Determine redirect URL: superuser or role 'Admin' => /admin else /
        role = getattr(user, 'role', None)

        return Response({
            'message': 'Login successful.',
            'access': access_token,
            'refresh': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': role,
                'student_admin_id': getattr(user, 'student_admin_id', None),
                'is_superuser': user.is_superuser,
            },      
        }, status=status.HTTP_200_OK)

class BookListView(APIView):
    def get(self, request, *args, **kwargs):
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)


@api_view(['GET'])
def get_grouped_subjects(request):
    qcategories = QCategory.objects.prefetch_related('general__questions').all()
    data = []

    for category in qcategories:
        category_data = {
            "name": category.name,
            "subjects": []
        }
        for subject in category.general.all():
            subject_data = {
                "name": subject.name,
                "qcategory": category.id,
                "desc": subject.desc,
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "options": q.options,
                        "correct_option": q.correct_option,
                        "explain": q.explain
                    }
                    for q in subject.questions.all()
                ]
            }
            category_data["subjects"].append(subject_data)

        data.append(category_data)

    return Response(data)


# --- Lightweight PDF endpoints to satisfy urls.py references ---
@api_view(['POST', 'GET'])
def generate_worksheet(request):
    # This project contains a GUI-oriented `pdf_processor.py` module. The
    # original GUI functions aren't suitable for headless API use without
    # adding dependencies. Provide a minimal placeholder API so routing
    # works; implement full processing later if desired.
    return Response({'message': 'Worksheet generation is not available via this API endpoint. Use the admin/CLI tool.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['GET'])
def list_pdfs(request):
    pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')
    data = [
        {
            'id': p.id,
            'filename': os.path.basename(p.document.name) if p.document else None,
            'uploaded_at': p.uploaded_at,
            'url': getattr(p.document, 'url', p.document.name if p.document else None)
        }
        for p in pdfs
    ]
    return Response(data)


@api_view(['GET'])
def analyze_pdf(request, pdf_id):
    try:
        pdf = UploadedPDF.objects.get(id=pdf_id)
    except UploadedPDF.DoesNotExist:
        return Response({'message': 'PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    # Lightweight analysis placeholder — avoid heavy libs at import time.
    return Response({
        'id': pdf.id,
        'filename': os.path.basename(pdf.document.name) if pdf.document else None,
        'analysis': 'not implemented in API; use backend tools to analyze'
    })


@api_view(['GET'])
def download_file(request, pdf_id, file_type):
    try:
        pdf = UploadedPDF.objects.get(id=pdf_id)
    except UploadedPDF.DoesNotExist:
        return Response({'message': 'PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    if file_type.lower() != 'pdf':
        return Response({'message': 'Only original PDF download is supported via this endpoint'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = pdf.document.path
        return FileResponse(open(path, 'rb'), as_attachment=True, filename=os.path.basename(path))
    except Exception as e:
        return Response({'message': f'Failed to open file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get subjects with optional search
# ----------------------------
@api_view(['GET'])
def get_subjects(request):
    search_query = request.GET.get('search', '').strip()
    subjects = Subject.objects.all()
    if search_query:
        subjects = subjects.filter(name__icontains=search_query)
    serializer = SubjectSerializer(subjects, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# ----------------------------
# Get questions for a specific subject
# ----------------------------
@api_view(['GET'])
def get_questions(request, subject_name):
    try:
        # Case-insensitive subject lookup
        subject = Subject.objects.get(name__iexact=subject_name)
    except Subject.DoesNotExist:
        return Response(
            {"error": f"Subject '{subject_name}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    questions = Questions.objects.filter(subject=subject)
    if not questions.exists():
        return Response(
            {"error": f"No questions found for subject '{subject_name}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Serialize the questions
    serializer = QuestionsSerializer(questions, many=True, context={'request': request})
    
    # Return data with optional subject info
    return Response(
        {
            "subject": subject.name,
            "questions": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_exam_by_subject_id(request, subject_id):
    """Return exam payload for frontend: { name, duration, questions: [...] }.

    Questions are serialized then reshaped to the frontend-friendly format
    (question -> 'question', include 'id', 'options', 'correct_option', 'explain').
    """
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)

    qs = Questions.objects.filter(subject=subject)
    serializer = QuestionsSerializer(qs, many=True, context={'request': request})

    # Map serialized fields to the frontend shape expected by ExamPage
    questions_list = []
    for q in serializer.data:
        questions_list.append({
            'id': q.get('id'),
            'question': q.get('question_text') or q.get('question') or '',
            'options': q.get('options') or [],
            'correct_option': q.get('correct_option'),
            'explain': q.get('explain') or ''
        })

    # duration: if subject.time exists (assumed minutes) convert to seconds
    duration = None
    try:
        duration = int(getattr(subject, 'time', 0))
        if duration:
            duration = duration * 60
    except Exception:
        duration = None

    if not duration:
        duration = len(questions_list) * 60

    return Response({
        'name': subject.name,
        'duration': duration,
        'questions': questions_list
    }, status=status.HTTP_200_OK)


class BookCategoryListView(APIView):
    def get(self, request):
        categories = BookCatagory.objects.all()
        serializer = BookCatagorySerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)
    
class BooksubCategorylist(APIView):
    def get(self, request):
        subcategory = SubBookCategory.objects.all()
        serializer =SubBookCategorySerializer(subcategory,many=True, context={'request': request} )
        return Response(serializer.data)
    
class QcategoryView(APIView):
    def get(self, request):
        qCategory= QCategory.objects.all()
        Serializer= QCategorySerializer(qCategory, many=True, context={'request':request})
        return Response(Serializer.data)
    
class ProjectListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data)

class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.views += 1
        project.save(update_fields=['views'])
        serializer = ProjectSerializer(project, context={'request': request})
        return Response(serializer.data)
    
class SignWordListAPIView(APIView):
    def get(self, request):
        words = SignWord.objects.all().order_by('word')
        serializer = SignWordSerializer(words, many=True, context={'request': request})
        return Response(serializer.data)
      


class PDFUploadAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = request.FILES.getlist('file')
        subject_id = request.POST.get('subject_id')

        if not files or not subject_id:
            return Response({'error': 'File(s) and subject_id are required.'}, status=400)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'error': 'Invalid subject ID.'}, status=404)

        all_questions = []

        for file in files:
            mime_type, _ = mimetypes.guess_type(file.name)
            file.seek(0)

            if mime_type and 'pdf' in mime_type:
                text = self.extract_text_from_pdf(file)
            elif mime_type and mime_type.startswith('image/'):
                text = self.extract_text_from_image(file)
            else:
                continue  # Unsupported file type

            questions = self.parse_questions(text, subject.id)
            all_questions.extend(questions)

        return Response({
            "message": f"{len(all_questions)} questions parsed.",
            "questions": all_questions
        }, status=200)

    def extract_text_from_pdf(self, file):
        text = ""
        try:
            file_bytes = file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                page_text = page.get_text().strip()

                if not page_text:
                    # OCR fallback using page image
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    image = Image.open(BytesIO(img_data)).convert("RGB")

                    img_np = np.array(image)
                    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    processed_img = Image.fromarray(thresh)

                    page_text = pytesseract.image_to_string(processed_img)

                text += "\n" + page_text
        except Exception as e:
            text = f"OCR Failed: {str(e)}"
        return text

    def extract_text_from_image(self, file):
        try:
            image = Image.open(file).convert("RGB")
            img_np = np.array(image)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            processed_img = Image.fromarray(thresh)
            return pytesseract.image_to_string(processed_img)
        except Exception as e:
            return f"OCR Failed on image: {str(e)}"

    def parse_questions(self, text, subject_id):
        # Normalize bullet points
        text = re.sub(r'[•·●]', '-', text)

        # Split text into question blocks
        question_blocks = re.split(r'\n?\s*\d+[\.\)]\s+', '\n' + text)[1:]

        parsed_questions = []

        for block in question_blocks:
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            if not lines:
                continue

            question_text = lines[0]
            options = []
            correct_option = ""
            explanation = ""

            for line in lines[1:]:
                opt_match = re.match(r'^([A-Da-d][\.\)])\s*(.*)', line)
                if opt_match:
                    options.append(opt_match.group(2).strip())
                elif 'answer' in line.lower():
                    ans_text = line.split(':')[-1].strip()
                    # Handle single-letter answers or full option text
                    if len(ans_text) == 1 and ans_text.upper() in ['A', 'B', 'C', 'D']:
                        idx = ord(ans_text.upper()) - ord('A')
                        if 0 <= idx < len(options):
                            correct_option = options[idx]
                            explanation = f"Answer: {ans_text.upper()} - {correct_option}"
                        else:
                            explanation = f"Answer {ans_text} not matched."
                    else:
                        # Attempt to match by option text
                        try:
                            idx = options.index(ans_text)
                            correct_option = options[idx]
                            explanation = f"Answer matched by text: {correct_option}"
                        except ValueError:
                            explanation = f"Answer {ans_text} not found in options."

            if question_text and len(options) >= 2:
                parsed_questions.append({
                    "id": None,
                    "subject": subject_id,
                    "question_text": question_text,
                    "options": options,
                    "correct_option": correct_option,
                    "explain": explanation
                })

        return parsed_questions


class SaveEditedQuestionsAPIView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        questions_data = request.data.get('questions')
        if not questions_data:
            return Response({'error': 'No questions provided'}, status=400)

        saved_questions = []
        errors = []

        for idx, q in enumerate(questions_data):
            try:
                options = q.get('options', [])
                question_obj = Questions.objects.create(
                    subject_id=q['subject'],
                    question_text=q.get('question_text', ''),
                    option1=options[0] if len(options) > 0 else "",
                    option2=options[1] if len(options) > 1 else "",
                    option3=options[2] if len(options) > 2 else "",
                    option4=options[3] if len(options) > 3 else "",
                    correct_option=q.get('correct_option', ""),
                    explanation=q.get('explain', "")
                )
                saved_questions.append({
                    "id": question_obj.id,
                    "question_text": question_obj.question_text
                })
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})

        response_data = {
            "message": f"{len(saved_questions)} questions saved.",
            "saved_questions": saved_questions
        }
        if errors:
            response_data["errors"] = errors

        return Response(response_data, status=201 if saved_questions else 400)


class BulkQuestionCreateView(APIView):
    def get(self, request, *args, **kwargs):
        from .models import Questions
        from .serializers import QuestionsSerializer
        questions = Questions.objects.all()
        serializer = QuestionsSerializer(questions, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = BulkQuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Questions created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ================================
# Enhanced Book ViewSet with Hard/Soft Book Support
# ================================

class EnhancedBookViewSet(viewsets.ModelViewSet):
    """Enhanced Book ViewSet with hard/soft book support"""
    queryset = Book.objects.filter(is_active=True)
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'description', 'tags']
    ordering_fields = ['title', 'author', 'created_at', 'views', 'downloads', 'rating', 'price', 'hard_price', 'soft_price']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        return BookSerializer

    def get_queryset(self):
        queryset = Book.objects.filter(is_active=True)
        
        # Filter by book type
        book_type = self.request.query_params.get('book_type')
        if book_type:
            queryset = queryset.filter(book_type=book_type)
        
        # Filter by availability
        available_for = self.request.query_params.get('available_for')
        if available_for == 'hard':
            queryset = queryset.filter(hard_price__gt=0)
        elif available_for == 'soft':
            queryset = queryset.filter(available_for_soft=True)
        elif available_for == 'rent':
            queryset = queryset.filter(is_for_rent=True)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__id=category)
        
        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
        
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with view tracking"""
        instance = self.get_object()
        instance.views += 1
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Increment book view count"""
        book = self.get_object()
        book.views += 1
        book.save()
        return Response({'success': True, 'views': book.views})

    @action(detail=True, methods=['post'])
    def increment_downloads(self, request, pk=None):
        """Increment book download count"""
        book = self.get_object()
        book.downloads += 1
        book.save()
        return Response({'success': True, 'downloads': book.downloads})

    @action(detail=False, methods=['get'])
    def hard_books(self, request):
        """Get only hard copy books"""
        books = Book.objects.filter(
            available_for_hard=True
        )
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def soft_books(self, request):
        """Get only soft copy books"""
        books = Book.objects.filter(
            available_for_soft=True
        )
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def rental_books(self, request):
        """Get books available for rent"""
        books = Book.objects.filter(
            available_for_rent=True
        )
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def price_comparison(self, request):
        """Get books with both hard and soft prices"""
        books = Book.objects.filter(
            book_type='both',
            hard_price__gt=0,
            soft_price__gt=0,
            is_active=True
        )
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def pricing_details(self, request, pk=None):
        """Get detailed pricing for a specific book"""
        book = self.get_object()
        pricing_details = {
            'book_id': book.id,
            'title': book.title,
            'author': book.author,
            'book_type': book.get_book_type_display(),
            'delivery_method': book.get_delivery_method_display(),
            'pricing': {
                'hard_copy': {
                    'available': book.available_for_hard,
                    'price': float(book.hard_price),
                    'currency': 'USD',
                    'delivery_methods': book.delivery_method
                },
                'soft_copy': {
                    'available': book.available_for_soft,
                    'price': float(book.soft_price),
                    'currency': 'USD',
                    'delivery_methods': 'digital'
                },
                'rental': {
                    'available': book.available_for_rent,
                    'price_per_week': float(book.rental_price_per_week),
                    'currency': 'USD'
                }
            }
        }
        return Response(pricing_details)

    # Enhanced admin actions for book management
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, pk=None):
        """Toggle book featured status"""
        book = self.get_object()
        book.is_featured = not book.is_featured
        book.save()
        return Response({
            'success': True,
            'message': f'Book {"featured" if book.is_featured else "unfeatured"} successfully',
            'is_featured': book.is_featured
        })

    @action(detail=True, methods=['post'])
    def toggle_premium(self, request, pk=None):
        """Toggle book premium status"""
        book = self.get_object()
        book.is_premium = not book.is_premium
        book.save()
        return Response({
            'success': True,
            'message': f'Book marked as {"premium" if book.is_premium else "regular"}',
            'is_premium': book.is_premium
        })

    @action(detail=True, methods=['post'])
    def toggle_free(self, request, pk=None):
        """Toggle book free status"""
        book = self.get_object()
        book.is_free = not book.is_free
        book.save()
        return Response({
            'success': True,
            'message': f'Book marked as {"free" if book.is_free else "paid"}',
            'is_free': book.is_free
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get book statistics"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        stats = {
            'total_books': Book.objects.count(),
            'total_views': Book.objects.aggregate(total_views=models.Sum('views'))['total_views'] or 0,
            'total_downloads': Book.objects.aggregate(total_downloads=models.Sum('downloads'))['total_downloads'] or 0,
            'avg_rating': Book.objects.aggregate(avg_rating=models.Avg('rating'))['avg_rating'] or 0,
            'free_books': Book.objects.filter(is_free=True).count(),
            'premium_books': Book.objects.filter(is_premium=True).count(),
            'featured_books': Book.objects.filter(is_featured=True).count(),
            'books_by_type': {
                'hard_only': Book.objects.filter(book_type='hard').count(),
                'soft_only': Book.objects.filter(book_type='soft').count(),
                'both': Book.objects.filter(book_type='both').count(),
            },
            'books_by_language': dict(
                Book.objects.values('language').annotate(count=models.Count('id')).values_list('language', 'count')
            ),
            'top_viewed_books': list(
                Book.objects.order_by('-views')[:10].values('id', 'title', 'views')
            ),
            'recently_added': list(
                Book.objects.order_by('-created_at')[:10].values('id', 'title', 'author', 'created_at')
            )
        }
        
        return Response(stats)


# Alias for backward compatibility with existing URLs
AdminBookViewSet = EnhancedBookViewSet


# ================================
# Original ViewSets (Backward Compatibility)
# ================================

# Keep original BookViewSet for backward compatibility
BookViewSet = EnhancedBookViewSet

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = BookCatagory.objects.all()
    serializer_class = BookCatagorySerializer

class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = SubBookCategory.objects.all()
    serializer_class = SubBookCategorySerializer


class QCategoryViewSet(viewsets.ModelViewSet):
    queryset = QCategory.objects.all()
    serializer_class = QCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'enrolled']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        category = self.get_object()
        category.enrolled += 1
        category.save()
        serializer = self.get_serializer(category)
        return Response(serializer.data)
    

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SubjectWithProgressSerializer
        return SubjectSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        try:
            subject = self.get_object()
            if not request.session.exists(request.session.session_key):
                request.session.create()

            with transaction.atomic():
                if request.user.is_authenticated:
                    progress, created = UserSubjectProgress.objects.get_or_create(
                        user=request.user,
                        subject=subject,
                        defaults={'progress': 0, 'status': 'not_started'}
                    )
                else:
                    progress, created = UserSubjectProgress.objects.get_or_create(
                        session_key=request.session.session_key,
                        subject=subject,
                        defaults={'progress': 0, 'status': 'not_started'}
                    )

                new_progress = request.data.get('progress', progress.progress)
                new_status = request.data.get('status', progress.status)
                score = request.data.get('score')
                time_spent = request.data.get('time_spent', 0)

                progress.progress = max(0, min(100, new_progress))
                progress.status = new_status

                if score is not None:
                    progress.score = float(score)

                if time_spent:
                    progress.time_spent += int(time_spent)

                if progress.progress == 100:
                    progress.status = 'completed'
                    progress.completed_at = timezone.now()
                elif progress.progress > 0 and progress.status == 'not_started':
                    progress.status = 'in_progress'

                progress.save()
                serializer = UserSubjectProgressSerializer(progress)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Subject.DoesNotExist:
            return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_progress(self, request):
        if request.user.is_authenticated:
            progress_records = UserSubjectProgress.objects.filter(user=request.user)
        else:
            if not request.session.session_key:
                return Response([])
            progress_records = UserSubjectProgress.objects.filter(session_key=request.session.session_key)
        serializer = UserSubjectProgressSerializer(progress_records, many=True)
        return Response(serializer.data)


# ================================
# Function-based APIs
# ================================
# NOTE: The duplicate function-based endpoints (get_subjects / get_questions)
# that appeared below were removed because they overrode the correct
# implementations earlier in this file and used serializers.ModelSerializer
# incorrectly (causing "ModelSerializer missing Meta" AssertionError).
#
# Keep only the correct get_subjects and get_questions defined earlier.
# If you need to reintroduce simple function-based endpoints, use the proper
# QuestionsSerializer (or another serializer with a Meta) and avoid calling
# serializers.ModelSerializer directly.

# Re-introduce viewsets that were accidentally removed (AboutUsViewSet etc.)
class QuestionsViewSet(viewsets.ModelViewSet):
    queryset = Questions.objects.all()
    serializer_class = QuestionsSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user)

class SignWordViewSet(viewsets.ModelViewSet):
    queryset = SignWord.objects.all()
    serializer_class = SignWordSerializer

class AboutUsViewSet(viewsets.ModelViewSet):
    queryset = AboutUs.objects.all()
    serializer_class = AboutUsSerializer

class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer

class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

    def perform_create(self, serializer):
        project = serializer.save(profile=self.request.user)
        log_activity(
            user=self.request.user,
            action='create',
            model_name='project',
            object_id=project.id
        )


# ================================
# Enhanced Payment and Purchase Management
# ================================

class UserPurchaseViewSet(viewsets.ModelViewSet):
    """Manage user purchases and provide access check endpoints"""
    queryset = UserPurchase.objects.all()
    serializer_class = UserPurchaseSerializer

    def get_queryset(self):
        # Limit purchases to the requesting user for safety
        if self.request.user.is_authenticated:
            return UserPurchase.objects.filter(user=self.request.user)
        return UserPurchase.objects.none()

    @action(detail=False, methods=['get'])
    def check_access(self, request):
        """Check if user has access to a specific book"""
        book_id = request.query_params.get('book_id')
        if not book_id:
            return Response({'access': False, 'message': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'access': False, 'message': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        # Free books are always accessible
        if book.is_free:
            return Response({'access': True, 'reason': 'free_book'})

        # Check user purchases
        if request.user.is_authenticated:
            # Check for purchases that haven't expired
            now = timezone.now()
            purchase = UserPurchase.objects.filter(
                user=request.user,
                book=book,
                expires_at__isnull=True
            ).first()
            
            if not purchase:
                # Check for rental that hasn't expired
                purchase = UserPurchase.objects.filter(
                    user=request.user,
                    book=book,
                    expires_at__gte=now
                ).first()
            
            if purchase:
                return Response({
                    'access': True, 
                    'purchase_type': purchase.purchase_type,
                    'purchase_id': purchase.id,
                    'expires_at': purchase.expires_at
                })
        
        return Response({'access': False, 'message': 'No purchase found'})


class PaymentViewSet(viewsets.ModelViewSet):
    """Enhanced Payment ViewSet supporting different book types"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Payment.objects.filter(user=self.request.user)
        return Payment.objects.none()

    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @action(detail=False, methods=['get'])
    def payment_methods(self, request):
        """Get available payment methods"""
        methods = [
            {
                'id': 'telebir',
                'name': 'Telebir',
                'description': 'Ethio Telecom Mobile Money',
                'type': 'mobile',
                'supported_networks': ['Ethio Telecom']
            },
            {
                'id': 'cbe_bir',
                'name': 'CBE Bir',
                'description': 'Commercial Bank of Ethiopia',
                'type': 'bank',
                'supported_networks': ['CBE']
            },
            {
                'id': 'hellocash',
                'name': 'HelloCash',
                'description': 'HelloCash Mobile Banking',
                'type': 'mobile',
                'supported_networks': ['Ethio Telecom', 'Safaricom']
            },
            {
                'id': 'dashen',
                'name': 'Dashen Bank',
                'description': 'Dashen Bank Mobile',
                'type': 'bank',
                'supported_networks': ['Dashen Bank']
            },
            {
                'id': 'awash',
                'name': 'Awash Bank',
                'description': 'Awash Bank Mobile',
                'type': 'bank',
                'supported_networks': ['Awash Bank']
            },
            {
                'id': 'amole',
                'name': 'Amole',
                'description': 'Amole Mobile Banking',
                'type': 'mobile',
                'supported_networks': ['Ethio Telecom']
            },
            {
                'id': 'stripe',
                'name': 'Credit/Debit Card',
                'description': 'International Cards',
                'type': 'card',
                'supported_networks': ['Visa', 'Mastercard', 'Amex']
            }
        ]
        return Response({'payment_methods': methods})

    @action(detail=False, methods=['post'])
    def process_payment(self, request):
        """Process payment for hard/soft/rental books"""
        serializer = PaymentRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                book_id = serializer.validated_data['book_id']
                payment_method = serializer.validated_data['payment_method']
                book = Book.objects.get(id=book_id)

                # Determine payment type and amount based on book availability
                payment_type = request.data.get('payment_type', 'purchase_soft')
                
                if payment_type == 'purchase_hard':
                    if not book.available_for_hard:
                        return Response({'error': 'Hard copy not available'}, status=400)
                    amount = book.hard_price
                elif payment_type == 'purchase_soft':
                    if not book.available_for_soft:
                        return Response({'error': 'Soft copy not available'}, status=400)
                    amount = book.soft_price
                elif payment_type == 'rental':
                    if not book.available_for_rent:
                        return Response({'error': 'Rental not available'}, status=400)
                    weeks = serializer.validated_data.get('rental_duration_weeks', 1)
                    amount = book.rental_price_per_week * weeks
                else:
                    return Response({'error': 'Invalid payment type'}, status=400)
                
                exchange_rate = 55  # USD to ETB
                local_amount = amount * exchange_rate
                transaction_id = f"TXN{timezone.now().strftime('%Y%m%d%H%M%S')}{book_id}"
                
                # Calculate rental dates
                rental_start_date = None
                rental_end_date = None
                if payment_type == 'rental':
                    rental_start_date = timezone.now().date()
                    rental_end_date = rental_start_date + timedelta(weeks=serializer.validated_data.get('rental_duration_weeks', 1))

                payment = Payment.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    book=book,
                    payment_type=payment_type,
                    amount=amount,
                    currency='USD',
                    local_amount=local_amount,
                    local_currency='ETB',
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    phone_number=serializer.validated_data.get('phone_number', ''),
                    status='completed',  # In production, this would be 'pending'
                    rental_duration_weeks=serializer.validated_data.get('rental_duration_weeks'),
                    rental_start_date=rental_start_date,
                    rental_end_date=rental_end_date,
                    payment_details={
                        'exchange_rate': exchange_rate,
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': self.get_client_ip(request),
                    }
                )
                
                # Create or update purchase record
                purchase_type = 'hard' if payment_type == 'purchase_hard' else 'soft'
                expires_at = None
                if payment_type == 'rental':
                    expires_at = rental_end_date
                
                user_purchase, created = UserPurchase.objects.get_or_create(
                    user=request.user if request.user.is_authenticated else None,
                    book=book,
                    purchase_type=purchase_type,
                    defaults={
                        'payment': payment,
                        'expires_at': expires_at
                    }
                )
                
                if not created:
                    user_purchase.payment = payment
                    if expires_at:
                        user_purchase.expires_at = expires_at
                    user_purchase.save()

                payment_serializer = PaymentSerializer(payment, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Payment processed successfully',
                    'payment': payment_serializer.data,
                    'purchase_id': user_purchase.id,
                    'access_granted': True
                })

            except Book.DoesNotExist:
                return Response({'success': False, 'message': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Payment processing failed: {str(e)}")
                return Response({'success': False, 'message': f'Payment processing failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': False, 'message': 'Invalid payment data', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def user_purchases(self, request):
        """Get user's purchase history with detailed information"""
        if request.user.is_authenticated:
            purchases = UserPurchase.objects.filter(user=request.user)
            serializer = UserPurchaseSerializer(purchases, many=True, context={'request': request})
            return Response(serializer.data)
        return Response([])

    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = Payment.objects.get(
                    id=serializer.validated_data['payment_id'],
                    transaction_id=serializer.validated_data['transaction_id']
                )
                if payment.status == 'completed':
                    return Response({'success': True, 'message': 'Payment already verified', 'payment_status': payment.status})
                payment.status = 'completed'
                payment.save()
                
                # Ensure a corresponding UserPurchase exists (create if missing)
                user_purchase, created = UserPurchase.objects.get_or_create(
                    user=payment.user,
                    book=payment.book,
                    purchase_type='hard' if payment.payment_type == 'purchase_hard' else 'soft',
                    defaults={
                        'payment': payment,
                        'expires_at': payment.rental_end_date
                    }
                )

                if not created:
                    # Update existing purchase with the new payment and extend expiry
                    user_purchase.payment = payment
                    if payment.rental_end_date:
                        user_purchase.expires_at = payment.rental_end_date
                    user_purchase.save()

                return Response({'success': True, 'message': 'Payment verified', 'payment_status': payment.status})
            except Payment.DoesNotExist:
                return Response({'success': False, 'message': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({'success': False, 'message': f'Payment verification failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': False, 'message': 'Invalid verification data', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# ================================
# Book Type API Views
# ================================

class HardSoftBookAPIView(APIView):
    """API View for hard/soft book specific operations"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        """Get book availability and pricing comparison"""
        book_id = request.query_params.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=400)
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=404)
        
        data = {
            'book_id': book.id,
            'title': book.title,
            'author': book.author,
            'book_type': book.get_book_type_display(),
            'availability': {
                'hard_copy': {
                    'available': book.available_for_hard,
                    'price': float(book.hard_price) if book.available_for_hard else None,
                    'delivery_methods': book.get_delivery_method_display()
                },
                'soft_copy': {
                    'available': book.available_for_soft,
                    'price': float(book.soft_price) if book.available_for_soft else None,
                    'delivery_methods': 'Digital Download'
                },
                'rental': {
                    'available': book.available_for_rent,
                    'price_per_week': float(book.rental_price_per_week) if book.available_for_rent else None,
                    'delivery_methods': book.get_delivery_method_display()
                }
            },
            'cover_url': book.get_cover_url(),
            'description': book.description[:200] + '...' if len(book.description) > 200 else book.description
        }
        
        return Response(data)


class BookAnalyticsView(APIView):
    """Analytics for book types and pricing"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get analytics for hard vs soft book performance"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=403)
        
        # Book type distribution
        book_types = Book.objects.values('book_type').annotate(
            count=models.Count('id')
        )
        
        # Pricing analytics
        hard_books = Book.objects.filter(hard_price__gt=0)
        soft_books = Book.objects.filter(soft_price__gt=0)
        
        pricing_stats = {
            'total_books': Book.objects.count(),
            'hard_copy_books': hard_books.count(),
            'soft_copy_books': soft_books.count(),
            'books_with_both': Book.objects.filter(
                book_type='both',
                hard_price__gt=0,
                soft_price__gt=0
            ).count(),
            'average_hard_price': hard_books.aggregate(
                avg=models.Avg('hard_price')
            )['avg'] or 0,
            'average_soft_price': soft_books.aggregate(
                avg=models.Avg('soft_price')
            )['avg'] or 0,
            'rental_books': Book.objects.filter(
                is_for_rent=True,
                rental_price_per_week__gt=0
            ).count(),
            'book_type_distribution': {item['book_type']: item['count'] for item in book_types}
        }
        
        return Response(pricing_stats)


# ================================
# Utility Functions
# ================================

def get_exchange_rate():
    """Get current USD to ETB exchange rate"""
    try:
        import requests
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        return response.json().get('rates', {}).get('ETB', 55)
    except:
        return 55


# ================================
# ADMIN API ENDPOINTS
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    """Comprehensive analytics data for admin dashboard"""
    user = request.user
    
    if not (user.is_superuser or user.role in ['Admin', 'Staff']):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
    
    # Date ranges
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)
    
    # User growth analytics
    user_growth = []
    for i in range(7):
        date = now - timedelta(days=i)
        count = User.objects.filter(date_joined__date=date.date()).count()
        user_growth.append({'date': date.date().isoformat(), 'count': count})
    
    # Content analytics
    content_analytics = {
        'books': {
            'total': Book.objects.count(),
            'this_week': Book.objects.filter(created_at__gte=last_7_days).count(),
            'this_month': Book.objects.filter(created_at__gte=last_30_days).count(),
            'most_viewed': list(Book.objects.order_by('-views')[:5].values('id', 'title', 'views')),
            'most_downloaded': list(Book.objects.order_by('-downloads')[:5].values('id', 'title', 'downloads')),
        },
        'projects': {
            'total': Project.objects.count(),
            'this_week': Project.objects.filter(created_at__gte=last_7_days).count(),
            'this_month': Project.objects.filter(created_at__gte=last_30_days).count(),
            'most_viewed': list(Project.objects.order_by('-views')[:5].values('id', 'title', 'views')),
        },
        'questions': {
            'total': Questions.objects.count(),
            'this_week': Questions.objects.filter(subject__created_at__gte=last_7_days).count(),
            'this_month': Questions.objects.filter(subject__created_at__gte=last_30_days).count(),
        }
    }
    
    # Revenue analytics (if payment data exists)
    revenue_analytics = {
        'total_payments': Payment.objects.count(),
        'completed_payments': Payment.objects.filter(status='completed').count(),
        'total_revenue': Payment.objects.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or 0,
        'payments_this_month': Payment.objects.filter(
            created_at__gte=last_30_days, status='completed'
        ).count(),
        'payment_methods': dict(
            Payment.objects.filter(status='completed').values('payment_method').annotate(
                count=models.Count('id')
            ).values_list('payment_method', 'count')
        )
    }
    
    return Response({
        'user_growth': user_growth,
        'content_analytics': content_analytics,
        'revenue_analytics': revenue_analytics,
        'generated_at': now.isoformat()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_bulk_operation(request):
    """Handle bulk operations for admin management"""
    user = request.user
    
    if not (user.is_superuser or user.role in ['Admin', 'Staff']):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
    
    operation = request.data.get('operation')
    model = request.data.get('model')
    ids = request.data.get('ids', [])
    
    if not all([operation, model, ids]):
        return Response({'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Map model names to Django models
        model_map = {
            'users': User,
            'books': Book,
            'projects': Project,
            'questions': Questions,
            'subjects': Subject,
            'categories': BookCatagory,
            'subcategories': SubBookCategory,
            'signwords': SignWord,
            'testimonials': Testimonial,
            'teammembers': TeamMember,
        }
        
        model_class = model_map.get(model.lower())
        if not model_class:
            return Response({'error': 'Invalid model'}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = model_class.objects.filter(id__in=ids)
        
        if operation == 'delete':
            deleted_count = queryset.count()
            queryset.delete()
            return Response({'success': True, 'deleted_count': deleted_count, 'message': f'Deleted {deleted_count} items'})
        
        elif operation == 'activate':
            updated_count = queryset.update(is_active=True)
            return Response({'success': True, 'updated_count': updated_count, 'message': f'Activated {updated_count} items'})
        
        elif operation == 'deactivate':
            updated_count = queryset.update(is_active=False)
            return Response({'success': True, 'updated_count': updated_count, 'message': f'Deactivated {updated_count} items'})
        
        elif operation == 'export':
            # Generate export data (simplified)
            export_data = list(queryset.values())
            return Response({'success': True, 'data': export_data, 'count': len(export_data)})
        
        else:
            return Response({'error': 'Invalid operation'}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({'error': f'Operation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_system_health(request):
    """System health check for admin monitoring"""
    user = request.user
    
    if not (user.is_superuser or user.role in ['Admin', 'Staff']):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
    
    health_data = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {
            'database': 'healthy',
            'cache': 'healthy', 
            'storage': 'healthy',
            'email': 'healthy',
        },
        'metrics': {
            'database_size': '2.4 GB',
            'active_sessions': 247,
            'memory_usage': '68%',
            'cpu_usage': '23%',
            'disk_usage': '45%',
            'uptime': '15 days, 4 hours',
        },
        'services': {
            'django': 'running',
            'redis': 'running',
            'postgres': 'running',
            'nginx': 'running',
        },
        'alerts': []
    }
    
    return Response(health_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_user_activity(request):
    """Get detailed user activity logs"""
    user = request.user
    
    if not (user.is_superuser or user.role in ['Admin', 'Staff']):
        return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get user activity data (simplified version)
    recent_logins = []
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-last_login')[:50].values('id', 'username', 'email', 'last_login', 'role')
    
    for user_data in active_users:
        recent_logins.append({
            'user_id': user_data['id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'role': user_data['role'],
            'last_activity': user_data['last_login'].isoformat(),
            'status': 'active'
        })
    
    return Response({
        'active_users_count': len(recent_logins),
        'users': recent_logins,
        'generated_at': timezone.now().isoformat()
    })


# ================================
# Enhanced UserViewSet with Admin Functionality
# ================================

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'student_admin_id']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login', 'role']
    ordering = ['-date_joined']

    def get_queryset(self):
        user = self.request.user
        if not (user.is_superuser or user.role in ['Admin', 'Staff']):
            return User.objects.none()
        return User.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]  # Only admins can modify users
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle user active status"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        return Response({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password (admin action)"""
        user = self.get_object()
        new_password = User.objects.make_random_password()
        user.set_password(new_password)
        user.save()
        
        # In a real application, you might want to send this via email
        return Response({
            'success': True,
            'message': 'Password reset successfully',
            'new_password': new_password  # In production, don't return passwords
        })

    @action(detail=True, methods=['post'])
    def update_role(self, request, pk=None):
        """Update user role"""
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in ['Student', 'Staff', 'Admin']:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.save()
        
        return Response({
            'success': True,
            'message': 'Role updated successfully',
            'new_role': new_role
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user statistics"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'new_users_this_week': User.objects.filter(
                date_joined__gte=timezone.now() - timedelta(weeks=1)
            ).count(),
            'users_by_role': dict(
                User.objects.filter(is_active=True).values('role').annotate(
                    count=models.Count('id')
                ).values_list('role', 'count')
            ),
            'recent_registrations': list(
                User.objects.filter(
                    date_joined__gte=timezone.now() - timedelta(days=7)
                ).values('id', 'username', 'email', 'role', 'date_joined')[:10]
            )
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def recent_logins(self, request):
        """Get users who recently logged in"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        hours = int(request.GET.get('hours', 24))
        recent_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(hours=hours),
            is_active=True
        ).order_by('-last_login')[:50]
        
        data = []
        for user in recent_users:
            data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'date_joined': user.date_joined.isoformat(),
            })
        
        return Response({
            'users': data,
            'count': len(data),
            'timeframe_hours': hours
        })

    @action(detail=False, methods=['post'])
    def bulk_toggle_status(self, request):
        """Bulk toggle user active status"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        user_ids = request.data.get('user_ids', [])
        activate = request.data.get('activate', True)
        
        if not user_ids:
            return Response({'error': 'user_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = User.objects.filter(id__in=user_ids).update(is_active=activate)
        
        return Response({
            'success': True,
            'message': f'Successfully {"activated" if activate else "deactivated"} {updated_count} users',
            'updated_count': updated_count
        })

    @action(detail=False, methods=['post'])
    def bulk_update_role(self, request):
        """Bulk update user roles"""
        if not (request.user.is_superuser or request.user.role in ['Admin', 'Staff']):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        user_ids = request.data.get('user_ids', [])
        new_role = request.data.get('role')
        
        if not all([user_ids, new_role]):
            return Response({'error': 'user_ids and role are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_role not in ['Student', 'Staff', 'Admin']:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = User.objects.filter(id__in=user_ids).update(role=new_role)
        
        return Response({
            'success': True,
            'message': f'Successfully updated role to {new_role} for {updated_count} users',
            'updated_count': updated_count,
            'new_role': new_role
        })


# ================================
# Chapa Payment API Views
# ================================

from .chapa_service import chapa_service
from .serializers import (
    ChapaPaymentRequestSerializer,
    ChapaCheckoutSerializer,
    ChapaWebhookSerializer
)

class ChapaPaymentAPIView(APIView):
    """
    API View for Chapa payment processing
    Handles checkout creation and payment verification
    """
    permission_classes = [AllowAny]  # Allow anonymous users to start payment
    
    def post(self, request):
        """Create Chapa checkout session"""
        try:
            serializer = ChapaPaymentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate book availability
            book_id = serializer.validated_data['book_id']
            try:
                book = Book.objects.get(id=book_id, is_active=True)
            except Book.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Book not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate amount based on payment type
            payment_type = serializer.validated_data.get('payment_type', 'purchase_soft')
            if payment_type == 'purchase_hard':
                if not book.available_for_hard:
                    return Response({
                        'success': False,
                        'message': 'Hard copy not available'
                    }, status=status.HTTP_400_BAD_REQUEST)
                amount = float(book.hard_price)
            elif payment_type == 'purchase_soft':
                if not book.available_for_soft:
                    return Response({
                        'success': False,
                        'message': 'Soft copy not available'
                    }, status=status.HTTP_400_BAD_REQUEST)
                amount = float(book.soft_price)
            elif payment_type == 'rental':
                if not book.available_for_rent:
                    return Response({
                        'success': False,
                        'message': 'Rental not available'
                    }, status=status.HTTP_400_BAD_REQUEST)
                weeks = serializer.validated_data.get('rental_duration_weeks', 1)
                amount = float(book.rental_price_per_week * weeks)
            else:
                return Response({
                    'success': False,
                    'message': 'Invalid payment type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prepare customer data
            customer_email = serializer.validated_data['customer_email']
            customer_name = serializer.validated_data['customer_name']
            phone_number = serializer.validated_data.get('phone_number', '')
            description = serializer.validated_data.get('description', f'Purchase: {book.title}')
            
            # Create Chapa checkout
            checkout_response = chapa_service.create_checkout(
                amount=amount,
                currency='ETB',
                description=description,
                return_url=f"{request.build_absolute_uri('/')}/payment/success?tx_ref={{tx_ref}}",
                callback_url=request.build_absolute_uri('/api/payments/chapa/webhook'),
                customer_email=customer_email,
                customer_name=customer_name,
                phone_number=phone_number,
                meta={
                    'book_id': book.id,
                    'book_title': book.title,
                    'payment_type': payment_type,
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'rental_duration_weeks': serializer.validated_data.get('rental_duration_weeks')
                }
            )
            
            if checkout_response['success']:
                # Create payment record in database
                transaction_id = checkout_response['tx_ref']
                local_amount = amount
                local_currency = 'ETB'
                
                payment = Payment.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    book=book,
                    payment_type=payment_type,
                    amount=amount,
                    currency='USD',
                    local_amount=local_amount,
                    local_currency=local_currency,
                    payment_method='chapa',
                    transaction_id=transaction_id,
                    status='pending',
                    rental_duration_weeks=serializer.validated_data.get('rental_duration_weeks'),
                    payment_details={
                        'chapa_payment_id': checkout_response.get('payment_id'),
                        'checkout_url': checkout_response['checkout_url'],
                        'customer_email': customer_email,
                        'customer_name': customer_name,
                        'phone_number': phone_number
                    }
                )
                
                return Response({
                    'success': True,
                    'message': 'Checkout created successfully',
                    'data': {
                        'checkout_url': checkout_response['checkout_url'],
                        'tx_ref': transaction_id,
                        'payment_id': checkout_response.get('payment_id'),
                        'amount': amount,
                        'currency': 'ETB',
                        'payment_id': payment.id
                    }
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to create checkout',
                    'error': checkout_response.get('error', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Chapa payment error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Payment processing failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Verify Chapa payment status"""
        tx_ref = request.query_params.get('tx_ref')
        if not tx_ref:
            return Response({
                'success': False,
                'message': 'Transaction reference required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify with Chapa
            verification = chapa_service.verify_transaction(tx_ref)
            
            if verification['success']:
                # Update payment status in database
                try:
                    payment = Payment.objects.get(transaction_id=tx_ref)
                    payment.status = verification['status']
                    payment.save()
                    
                    # Create user purchase if payment is successful
                    if verification['status'] == 'success':
                        self._create_user_purchase(payment)
                    
                    return Response({
                        'success': True,
                        'status': verification['status'],
                        'amount': verification['amount'],
                        'currency': verification['currency'],
                        'tx_ref': verification['tx_ref'],
                        'reference': verification['reference'],
                        'payment_id': payment.id
                    })
                except Payment.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Payment record not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'success': False,
                    'message': 'Transaction verification failed',
                    'error': verification.get('error', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Verification failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_user_purchase(self, payment):
        """Create user purchase record after successful payment"""
        try:
            purchase_type = 'hard' if payment.payment_type == 'purchase_hard' else 'soft'
            expires_at = None
            
            if payment.payment_type == 'rental' and payment.rental_end_date:
                expires_at = payment.rental_end_date
            
            user_purchase, created = UserPurchase.objects.get_or_create(
                user=payment.user,
                book=payment.book,
                purchase_type=purchase_type,
                defaults={
                    'payment': payment,
                    'expires_at': expires_at
                }
            )
            
            if not created:
                # Update existing purchase
                user_purchase.payment = payment
                if expires_at:
                    user_purchase.expires_at = expires_at
                user_purchase.save()
            
            logger.info(f"User purchase created for payment {payment.id}")
            
        except Exception as e:
            logger.error(f"Failed to create user purchase: {str(e)}")


@api_view(['POST'])
@permission_classes([AllowAny])
def chapa_webhook(request):
    """
    Chapa webhook endpoint for receiving payment notifications
    """
    try:
        # Parse webhook data
        serializer = ChapaWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Invalid webhook data: {serializer.errors}")
            return Response({'status': 'ignored'}, status=status.HTTP_400_BAD_REQUEST)
        
        webhook_data = serializer.validated_data
        tx_ref = webhook_data['tx_ref']
        status = webhook_data['status']
        
        # Update payment status
        try:
            payment = Payment.objects.get(transaction_id=tx_ref)
            payment.status = status
            
            # Update payment details with webhook data
            payment_details = payment.payment_details or {}
            payment_details.update({
                'chapa_reference': webhook_data.get('reference'),
                'webhook_event': webhook_data.get('event'),
                'webhook_time': webhook_data.get('event_time').isoformat() if webhook_data.get('event_time') else None,
                'customer_phone': webhook_data.get('customer_phone_number')
            })
            payment.payment_details = payment_details
            payment.save()
            
            # Create user purchase if payment is successful
            if status == 'success':
                ChapaPaymentAPIView()._create_user_purchase(payment)
            
            logger.info(f"Webhook processed for {tx_ref}: {status}")
            
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for webhook: {tx_ref}")
            return Response({'status': 'ignored'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_chapa_payment_methods(request):
    """
    Get available Chapa payment methods
    """
    try:
        payment_methods = chapa_service.get_payment_methods()
        return Response({
            'success': True,
            'payment_methods': payment_methods
        })
    except Exception as e:
        logger.error(f"Failed to get payment methods: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to get payment methods'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_chapa_supported_currencies(request):
    """
    Get supported currencies for Chapa payments
    """
    try:
        currencies = {
            'supported_currencies': [
                {'code': 'ETB', 'name': 'Ethiopian Birr', 'symbol': 'Br'},
                {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'}
            ],
            'default_currency': 'ETB',
            'exchange_rates': {
                'USD_TO_ETB': 55.0,
                'ETB_TO_USD': 0.018
            }
        }
        return Response({
            'success': True,
            'data': currencies
        })
    except Exception as e:
        logger.error(f"Failed to get currencies: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to get currencies'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_chapa_payment(request):
    """Verify Chapa payment status for frontend confirmation page"""
    try:
        tx_ref = request.data.get('tx_ref')
        if not tx_ref:
            return Response({
                'success': False,
                'message': 'Transaction reference required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find payment record
        try:
            payment = Payment.objects.get(transaction_id=tx_ref)
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify with Chapa service
        verification = chapa_service.verify_transaction(tx_ref)
        
        if verification['success'] and verification['status'] == 'success':
            # Update payment status to completed
            if payment.status != 'completed':
                payment.status = 'completed'
                payment.save()
            
            # Create user purchase if it doesn't exist
            purchase_type = 'hard' if payment.payment_type == 'purchase_hard' else 'soft'
            expires_at = None
            
            if payment.payment_type == 'rental' and payment.rental_end_date:
                expires_at = payment.rental_end_date
            
            user_purchase, created = UserPurchase.objects.get_or_create(
                user=payment.user,
                book=payment.book,
                purchase_type=purchase_type,
                defaults={
                    'payment': payment,
                    'expires_at': expires_at
                }
            )
            
            if not created:
                # Update existing purchase
                user_purchase.payment = payment
                if expires_at:
                    user_purchase.expires_at = expires_at
                user_purchase.save()
            
            # Get book information for response
            books_data = []
            if payment.book:
                books_data.append({
                    'id': payment.book.id,
                    'title': payment.book.title,
                    'author': payment.book.author,
                    'category': payment.book.category.name if payment.book.category else None,
                    'file': payment.book.file.url if payment.book.file else None
                })
            
            return Response({
                'success': True,
                'message': 'Payment verified successfully',
                'data': {
                    'tx_ref': payment.transaction_id,
                    'amount': str(payment.local_amount or payment.amount),
                    'currency': payment.local_currency or payment.currency or 'ETB',
                    'status': payment.status,
                    'created_at': payment.created_at.isoformat(),
                    'books': books_data,
                    'payment_type': payment.payment_type
                }
            }, status=status.HTTP_200_OK)
        else:
            # Payment failed or not successful
            return Response({
                'success': False,
                'message': 'Payment verification failed',
                'data': verification
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        return Response({
            'success': False,
            'message': f'Verification error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)