from django.urls import include, path
from .views import (
    AboutUsViewSet, AdminBookViewSet, AdminUserViewSet, BookListView, BookCategoryListView, BookViewSet, BooksubCategorylist, BulkQuestionCreateView, CategoryViewSet, LoginView,
    PDFUploadAPIView, PaymentViewSet, ProjectDetailView, ProjectListView, ProjectViewSet, QCategoryViewSet,
    QcategoryView, QuestionsViewSet, SignWordListAPIView, SignWordViewSet, SubcategoryViewSet, SubjectViewSet, TeamMemberViewSet, TestimonialViewSet,  UserPurchaseViewSet, UserRegisterView, admin_analytics, admin_bulk_operation, admin_system_health, admin_user_activity, current_user, dashboard_stats, get_questions,
    get_subjects, get_grouped_subjects, UserViewSet, recent_activities
)
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views


router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'admin-users', AdminUserViewSet, basename='admin-user')
router.register(r'adminbooks', BookViewSet, basename='book')
router.register(r'admin-books', AdminBookViewSet, basename='admin-book')
router.register(r'category', CategoryViewSet, basename='category')
router.register(r'Subcategory', SubcategoryViewSet, basename='subcategory')
router.register('qcategories', QCategoryViewSet)
router.register('subjects', SubjectViewSet)
router.register('questions', QuestionsViewSet)
router.register(r'project', ProjectViewSet)
router.register('signwords', SignWordViewSet)
router.register(r'aboutus', AboutUsViewSet)
router.register(r'testimonials', TestimonialViewSet)
router.register(r'team-members', TeamMemberViewSet)
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'user-purchases', UserPurchaseViewSet, basename='userpurchase')

urlpatterns = [
    path('current_user/', current_user, name='current_user'),
    path('dashboard/', dashboard_stats),
    path('recent-activities/' , recent_activities),
    
    # Admin-specific endpoints
    path('admin/analytics/', admin_analytics, name='admin-analytics'),
    path('admin/bulk-operation/', admin_bulk_operation, name='admin-bulk-operation'),
    path('admin/system-health/', admin_system_health, name='admin-system-health'),
    path('admin/user-activity/', admin_user_activity, name='admin-user-activity'),
    
    # Authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', UserRegisterView.as_view(), name='register'),
    
    # General API endpoints
    path('books/', BookListView.as_view(), name='book-list'),  # changed to avoid conflict with router
    path('question/<str:subject_name>/', get_questions, name='question-list'),
    path('exams/<int:subject_id>/', views.get_exam_by_subject_id, name='exam-detail'),
    path('subjects/', get_subjects, name='question-sub'),
    path('categories/', BookCategoryListView.as_view(), name='book-category-list'),
    path('subcategory/', BooksubCategorylist.as_view(), name='book-category-list'),
    path('grouped-subjects/', get_grouped_subjects, name='grouped-subjects'),
    path('qcategory/', QcategoryView.as_view(), name='qcategory'),
    path('projects/', ProjectListView.as_view(), name='project-list'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('words/', SignWordListAPIView.as_view(), name='word-list'),
    path('upload-parse/', PDFUploadAPIView.as_view()),
    path('questions/bulk/', BulkQuestionCreateView.as_view()),

    # PDF processing endpoints
    path("pdfs/upload/", views.generate_worksheet, name="generate_worksheet"),
    path("pdfs/", views.list_pdfs, name="list_pdfs"),
    path("pdfs/<int:pdf_id>/analyze/", views.analyze_pdf, name="analyze_pdf"),
    path("pdfs/<int:pdf_id>/download/<str:file_type>/", views.download_file, name="download_file"),
    
    # Payment endpoints
    path('payments/process/', PaymentViewSet.as_view({'post': 'process_payment'}), name='process-payment'),
    path('payments/verify/', PaymentViewSet.as_view({'post': 'verify_payment'}), name='verify-payment'),
    path('payments/methods/', PaymentViewSet.as_view({'get': 'payment_methods'}), name='payment-methods'),
    path('payments/user-purchases/', PaymentViewSet.as_view({'get': 'user_purchases'}), name='user-purchases-list'),
    
    # Chapa payment endpoints for Ethiopian test mode
    path('payments/chapa/', views.ChapaPaymentAPIView.as_view(), name='chapa-payment'),
    path('payments/chapa/webhook/', views.chapa_webhook, name='chapa-webhook'),
    path('payments/chapa/methods/', views.get_chapa_payment_methods, name='chapa-methods'),
    path('payments/chapa/currencies/', views.get_chapa_supported_currencies, name='chapa-currencies'),
    path('payments/chapa/verify/', views.verify_chapa_payment, name='chapa-verify'),
    
    # User purchase endpoints
    path('user-purchases/check-access/<int:book_id>/', UserPurchaseViewSet.as_view({'get': 'check_access'}), name='check-access'),
    
    # Include ViewSet router URLs
    path('', include(router.urls)),
]
