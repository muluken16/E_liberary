from rest_framework import serializers
from django.conf import settings
from .models import (AboutUs, Book, BookCatagory, BookTag, Payment, Project, SignWord, 
                    SubBookCategory, Subject, Questions, Quiz, QCategory, SignWord, 
                    TeamMember, Testimonial, UploadedPDF, UserPurchase, UserSubjectProgress)
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
import random
import string


User = get_user_model()

def generate_password_from_lastname_phone(last_name, phone_number, extra_length=3):
    name_part = last_name[:3].capitalize() if last_name else "Usr"
    phone_part = phone_number[-4:] if phone_number else "0000"
    return f"{name_part}{phone_part}"

# ================================
# Enhanced Book Serializers
# ================================

class EnhancedBookSerializer(serializers.ModelSerializer):
    """Enhanced book serializer with hard/soft book support"""
    price_by_type = serializers.SerializerMethodField()
    display_price = serializers.ReadOnlyField()
    available_for_hard = serializers.ReadOnlyField()
    available_for_soft = serializers.ReadOnlyField()
    available_for_rent = serializers.ReadOnlyField()
    cover_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'category', 'category_name', 
            'sub_category', 'sub_category_name', 'book_type', 'delivery_method', 
            'cover_url', 'pdf_url', 'published_date', 'page_count', 'language', 
            'grade_level', 'hard_price', 'soft_price', 'rental_price_per_week',
            'price', 'is_for_sale', 'is_for_rent', 'is_free', 'is_premium',
            'is_featured', 'is_active', 'rating', 'views', 'downloads',
            'tags', 'created_at', 'updated_at', 'price_by_type', 'display_price', 
            'available_for_hard', 'available_for_soft', 'available_for_rent'
        ]
        read_only_fields = ['created_at', 'updated_at', 'views', 'downloads']
    
    def get_cover_url(self, obj):
        return obj.get_cover_url()
    
    def get_pdf_url(self, obj):
        return obj.get_pdf_url()
    
    def get_price_by_type(self, obj):
        return obj.price_by_type


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating books with validation"""
    
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'category', 'sub_category',
            'book_type', 'delivery_method', 'pdf_file', 'cover_image',
            'published_date', 'page_count', 'language', 'grade_level',
            'hard_price', 'soft_price', 'rental_price_per_week',
            'is_for_sale', 'is_for_rent', 'is_free', 'is_premium',
            'is_featured', 'is_active', 'tags'
        ]
    
    def validate(self, data):
        """Custom validation for book data"""
        hard_price = data.get('hard_price', 0)
        soft_price = data.get('soft_price', 0)
        rental_price = data.get('rental_price_per_week', 0)
        book_type = data.get('book_type', 'both')
        
        # Validate pricing based on book type
        if book_type == 'hard' and hard_price <= 0:
            raise serializers.ValidationError({
                'hard_price': 'Hard copy must have a price greater than 0'
            })
        
        if book_type == 'soft' and soft_price <= 0:
            raise serializers.ValidationError({
                'soft_price': 'Soft copy must have a price greater than 0'
            })
        
        if data.get('is_for_rent') and rental_price <= 0:
            raise serializers.ValidationError({
                'rental_price_per_week': 'Rental books must have a weekly price'
            })
        
        # Validate file requirements
        book_type = data.get('book_type')
        if book_type == 'soft' and not data.get('pdf_file'):
            raise serializers.ValidationError({
                'pdf_file': 'Soft copies require a PDF file'
            })
        
        return data


class HardSoftBookSerializer(serializers.ModelSerializer):
    """Simplified serializer for displaying books by type"""
    cover_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'cover_url',
            'hard_price', 'soft_price', 'rental_price_per_week',
            'available_for_hard', 'available_for_soft', 'available_for_rent',
            'delivery_method', 'book_type'
        ]
    
    def get_cover_url(self, obj):
        return obj.get_cover_url()


# ================================
# Enhanced Payment Serializers
# ================================

class EnhancedPaymentSerializer(serializers.ModelSerializer):
    """Enhanced payment serializer supporting different book types"""
    book_details = serializers.SerializerMethodField()
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_cover = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'book', 'book_title', 'book_cover', 
            'payment_type', 'amount', 'currency', 'local_amount', 'local_currency', 
            'payment_method', 'transaction_id', 'status', 'rental_duration_weeks',
            'rental_start_date', 'rental_end_date', 'created_at', 'updated_at', 'book_details'
        ]
        read_only_fields = ['transaction_id', 'created_at', 'updated_at']
    
    def get_book_details(self, obj):
        return {
            'title': obj.book.title,
            'author': obj.book.author,
            'book_type': obj.book.get_book_type_display(),
            'delivery_method': obj.book.get_delivery_method_display()
        }
    
    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book.cover_image:
            return request.build_absolute_uri(obj.book.cover_image.url) if request else obj.book.cover_image.url
        return None


class EnhancedPaymentRequestSerializer(serializers.Serializer):
    """Serializer for payment requests"""
    book_id = serializers.IntegerField()
    payment_type = serializers.ChoiceField(choices=[
        'purchase_hard', 'purchase_soft', 'rental'
    ])
    payment_method = serializers.ChoiceField(choices=[
        'telebir', 'cbe_bir', 'hellocash', 'dashen', 'awash', 'amole', 'stripe', 'paypal', 'chapa'
    ])
    phone_number = serializers.CharField(max_length=20, required=False)
    transaction_id = serializers.CharField(max_length=100, required=False)
    rental_duration_weeks = serializers.IntegerField(required=False, min_value=1)
    
    def validate(self, data):
        """Validate payment request data"""
        payment_type = data.get('payment_type')
        phone_number = data.get('phone_number')
        
        # Require phone number for mobile payments
        if payment_type != 'rental' and phone_number and not phone_number.startswith('09'):
            raise serializers.ValidationError({
                'phone_number': 'Phone number must start with 09'
            })
        
        return data


class EnhancedUserPurchaseSerializer(serializers.ModelSerializer):
    """Enhanced user purchase serializer"""
    book_details = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    book_cover = serializers.SerializerMethodField()
    book_pdf = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPurchase
        fields = [
            'id', 'user', 'book', 'book_title', 'book_author', 'book_cover',
            'book_pdf', 'payment', 'purchase_type', 'purchased_at', 'expires_at',
            'book_details', 'payment_details'
        ]
        read_only_fields = ['purchased_at']
    
    def get_book_details(self, obj):
        return {
            'title': obj.book.title,
            'author': obj.book.author,
            'book_type': obj.book.get_book_type_display(),
            'cover_url': obj.book.get_cover_url()
        }
    
    def get_payment_details(self, obj):
        if obj.payment:
            return {
                'amount': obj.payment.amount,
                'currency': obj.payment.currency,
                'payment_method': obj.payment.get_payment_method_display(),
                'transaction_id': obj.payment.transaction_id,
                'payment_type': obj.payment.get_payment_type_display()
            }
        return None
    
    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book.cover_image:
            return request.build_absolute_uri(obj.book.cover_image.url) if request else obj.book.cover_image.url
        return None
    
    def get_book_pdf(self, obj):
        request = self.context.get('request')
        if obj.book.pdf_file:
            return request.build_absolute_uri(obj.book.pdf_file.url) if request else obj.book.pdf_file.url
        return None


# ================================
# Original/Backward Compatible Serializers
# ================================

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'phone_number',
            'phone',
            'address',
            'business_name',
            'business_type',
            'subscription_plan',
            'role',
            'sex',
            'age',
            'grade',
            'emergency_contact_name',
            'emergency_contact_phone',
            'profile_image',
            'student_admin_id',
            'user_type',
        ]
        read_only_fields = ['student_admin_id', 'id']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'username': {'required': False},
            'phone': {'required': False},
            'address': {'required': False},
            'business_name': {'required': False},
            'business_type': {'required': False},
        }

    def create(self, validated_data):
        # Extract password
        password = validated_data.pop('password', None)
        
        # Set default values
        if 'user_type' not in validated_data:
            validated_data['user_type'] = 'buyer'
        if 'role' not in validated_data:
            # Map user_type to role
            user_type = validated_data.get('user_type', 'buyer')
            if user_type == 'seller':
                validated_data['role'] = 'Seller'
            else:
                validated_data['role'] = 'Buyer'
        if 'subscription_plan' not in validated_data:
            validated_data['subscription_plan'] = 'monthly'

        # Generate password if not provided
        if not password:
            last_name = validated_data.get('last_name', '')
            phone_number = validated_data.get('phone_number', '') or validated_data.get('phone', '')
            password = generate_password_from_lastname_phone(last_name, phone_number)

        # Create user and set hashed password
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Optional: log or return generated password (dev only)
        print(f"[DEBUG] Password for {user.username}: {password}")
        return user


class BookSerializer(serializers.ModelSerializer):
    """Backward compatible book serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    pdf_file_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    display_categories = serializers.SerializerMethodField()
    # Enhanced fields
    price_by_type = serializers.SerializerMethodField()
    available_for_hard = serializers.ReadOnlyField()
    available_for_soft = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description',
            'category', 'category_name',
            'sub_category', 'sub_category_name',
            'pdf_file', 'pdf_file_url',
            'cover_image', 'cover_image_url',
            'published_date', 'page_count',
            'language', 'grade_level', 'price',
            'hard_price', 'soft_price', 'rental_price_per_week',
            'book_type', 'delivery_method',
            'is_free', 'is_premium', 'is_featured', 'is_for_sale', 'is_for_rent',
            'rating', 'views', 'downloads',
            'tags', 'is_active',
            'created_at', 'updated_at',
            'display_categories',
            'price_by_type', 'available_for_hard', 'available_for_soft',
        ]

    def get_pdf_file_url(self, obj):
        """Returns absolute URL for PDF file if available."""
        request = self.context.get('request')
        if obj.pdf_file:
            return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url
        return None

    def get_cover_image_url(self, obj):
        """Returns absolute URL for cover image if available."""
        request = self.context.get('request')
        if obj.cover_image:
            return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url
        return None

    def get_display_categories(self, obj):
        """Returns list of category and sub-category names."""
        return obj.display_categories
    
    def get_price_by_type(self, obj):
        return obj.price_by_type


# Questions and Subjects
class QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questions
        fields = ['id', 'subject', 'question_text', 'options', 'correct_option', 'explain']

    def validate_options(self, value):
        if not isinstance(value, list) or len(value) < 2:
            raise serializers.ValidationError("Options must be a list with at least 2 items.")
        return value


class BulkQuestionSerializer(serializers.Serializer):
    questions = QuestionsSerializer(many=True)

    def create(self, validated_data):
        questions_data = validated_data['questions']
        question_objs = [Questions(**question_data) for question_data in questions_data]
        return Questions.objects.bulk_create(question_objs)
    

class SubjectSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='QCategory.name', read_only=True)
    category_color = serializers.CharField(source='QCategory.color', read_only=True)
    category_icon = serializers.CharField(source='QCategory.icon', read_only=True)
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['name', 'QCategory', 'desc', 'questions', 'category_name', 'category_color', 'category_icon', 'questions_count']

    def get_questions_count(self, obj):
        return obj.questions.count()


class QCategorySerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = QCategory
        fields = ['id', 'name', 'description', 'icon', 'cover_image', 'enrolled', 
                  'created_at', 'updated_at', 'subjects', 'total_questions']

    def get_subjects(self, obj):
        subjects = obj.general.all()
        serializer = SubjectWithProgressSerializer(subjects, many=True, context=self.context)
        return serializer.data

    def get_total_questions(self, obj):
        # Total questions across all subjects in this category
        return sum(sub.questions.count() for sub in obj.general.all())


class UserSubjectProgressSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_time = serializers.IntegerField(source='subject.time', read_only=True)

    class Meta:
        model = UserSubjectProgress
        fields = [
            'id', 'subject', 'subject_name', 'subject_time', 
            'progress', 'status', 'score', 'time_spent',
            'completed_at', 'last_accessed', 'created_at'
        ]
        read_only_fields = ['user', 'session_key', 'last_accessed', 'created_at']


class SubjectWithProgressSerializer(SubjectSerializer):
    user_progress = serializers.SerializerMethodField()
    difficulty = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    popularity = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()

    class Meta(SubjectSerializer.Meta):
        fields = SubjectSerializer.Meta.fields + [
            'user_progress', 'difficulty', 'rating', 'popularity', 
            'questions_count', 'pass_rate'
        ]

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if not request:
            return None
            
        # Try to get progress for authenticated user
        if request.user.is_authenticated:
            try:
                progress = UserSubjectProgress.objects.get(
                    user=request.user, 
                    subject=obj
                )
                return UserSubjectProgressSerializer(progress).data
            except UserSubjectProgress.DoesNotExist:
                return None
        # Try to get progress for session user
        else:
            session_key = request.session.session_key
            if session_key:
                try:
                    progress = UserSubjectProgress.objects.get(
                        session_key=session_key, 
                        subject=obj
                    )
                    return UserSubjectProgressSerializer(progress).data
                except UserSubjectProgress.DoesNotExist:
                    return None
        return None

    def get_difficulty(self, obj):
        # Mock difficulty based on subject ID
        difficulties = ["Beginner", "Intermediate", "Advanced", "Expert"]
        return difficulties[obj.id % len(difficulties)]

    def get_rating(self, obj):
        # Mock rating
        return round(3.5 + (obj.id % 15) / 10, 1)

    def get_popularity(self, obj):
        # Mock popularity
        return (obj.id % 1000) + 500

    def get_questions_count(self, obj):
        # Mock questions count
        return [20, 25, 30, 40, 50][obj.id % 5]

    def get_pass_rate(self, obj):
        # Mock pass rate
        return [65, 72, 78, 85, 92][obj.id % 5]


# Categories
class SubBookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubBookCategory
        fields = ['name','id']
        
class BookTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookTag
        fields = '__all__'
        

class BookCatagorySerializer(serializers.ModelSerializer):
    image_path = serializers.SerializerMethodField()

    class Meta:
        model = BookCatagory
        fields = ['name', 'image_path','id']

    def get_image_path(self, obj):
        request = self.context.get('request')
        if obj.image_path and hasattr(obj.image_path, 'url'):
            return request.build_absolute_uri(obj.image_path.url)
        return ''


class ProjectSerializer(serializers.ModelSerializer):
    profile_username = serializers.CharField(source='profile.username', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'summary', 'full_description',
            'profile', 'profile_username', 'date', 'badge',
            'image', 'pdf', 'views', 'rating',
            'tags', 'is_pro' ,'created_at', 'updated_at'
        ]
        read_only_fields = ['views', 'created_at', 'updated_at']


class SignWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignWord
        fields = ['id', 'word', 'video', 'image']


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise serializers.ValidationError("Invalid username or password.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
        else:
            raise serializers.ValidationError("Must include username and password.")
        
        data["user"] = user
        return data


class QuizCreateSerializer(serializers.ModelSerializer):
    question_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )

    class Meta:
        model = Quiz
        fields = ['title', 'subject', 'time_limit_minutes', 'question_ids']

    def create(self, validated_data):
        question_ids = validated_data.pop('question_ids')
        quiz = Quiz.objects.create(**validated_data)
        quiz.questions.set(Questions.objects.filter(id__in=question_ids))
        return quiz


class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = '__all__'


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = '__all__'


# Payment related serializers (enhanced)
class PaymentSerializer(serializers.ModelSerializer):
    """Original payment serializer - kept for backward compatibility"""
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_cover = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'book', 'book_title', 'book_cover',
            'amount', 'currency', 'local_amount', 'local_currency',
            'payment_method', 'transaction_id', 'phone_number', 
            'account_number', 'status', 'payment_details', 'created_at',
            'payment_type', 'rental_duration_weeks', 'rental_start_date', 'rental_end_date'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book.cover_image:
            return request.build_absolute_uri(obj.book.cover_image.url) if request else obj.book.cover_image.url
        return None


class UserPurchaseSerializer(serializers.ModelSerializer):
    """Original user purchase serializer - kept for backward compatibility"""
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    book_cover = serializers.SerializerMethodField()
    book_pdf = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserPurchase
        fields = [
            'id', 'user', 'book', 'book_title', 'book_author', 'book_cover',
            'book_pdf', 'payment', 'purchased_at', 'expires_at', 'purchase_type', 'is_active'
        ]
        read_only_fields = ['id', 'purchased_at']

    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book.cover_image:
            return request.build_absolute_uri(obj.book.cover_image.url) if request else obj.book.cover_image.url
        return None

    def get_book_pdf(self, obj):
        request = self.context.get('request')
        if obj.book.pdf_file:
            return request.build_absolute_uri(obj.book.pdf_file.url) if request else obj.book.pdf_file.url
        return None


class PaymentRequestSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    payment_method = serializers.CharField()
    phone_number = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    # Enhanced fields
    payment_type = serializers.ChoiceField(choices=['purchase_hard', 'purchase_soft', 'rental'], required=False)
    rental_duration_weeks = serializers.IntegerField(required=False, min_value=1)


class PaymentVerificationSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    transaction_id = serializers.CharField()


class UploadedPDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedPDF
        fields = ['id', 'user', 'document', 'uploaded_at']


# Chapa-specific serializers
class ChapaPaymentRequestSerializer(serializers.Serializer):
    """Serializer for Chapa payment requests"""
    book_id = serializers.IntegerField()
    payment_type = serializers.ChoiceField(choices=[
        'purchase_hard', 'purchase_soft', 'rental'
    ])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default='ETB')
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=20, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    rental_duration_weeks = serializers.IntegerField(required=False, min_value=1)
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class ChapaCheckoutSerializer(serializers.Serializer):
    """Serializer for Chapa checkout response"""
    success = serializers.BooleanField()
    checkout_url = serializers.URLField(required=False)
    tx_ref = serializers.CharField(required=False)
    payment_id = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    status_code = serializers.IntegerField(required=False)


class ChapaWebhookSerializer(serializers.Serializer):
    """Serializer for Chapa webhook data"""
    event = serializers.CharField()
    event_time = serializers.DateTimeField()
    tx_ref = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.CharField()
    reference = serializers.CharField()
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField()
    customer_phone_number = serializers.CharField()
    meta = serializers.DictField(required=False)
    
    def validate_status(self, value):
        """Validate payment status"""
        valid_statuses = ['success', 'failed', 'pending', 'cancelled', 'timeout']
        if value.lower() not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        return value.lower()


class ChapaVerificationSerializer(serializers.Serializer):
    """Serializer for Chapa payment verification requests"""
    tx_ref = serializers.CharField(max_length=255)