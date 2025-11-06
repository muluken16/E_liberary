import uuid
import random
import string
from django.db import models
from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


# -------------------------
# Utility function
# -------------------------
def generate_unique_id():
    while True:
        new_id = random.choice(string.ascii_uppercase) + ''.join(random.choices(string.digits, k=3))
        if not BookCatagory.objects.filter(id=new_id).exists():
            return new_id


# -------------------------
# Custom User Model
# -------------------------
class User(AbstractUser):
    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    ROLE_CHOICES = (
        ('Student', 'Student'),
        ('Staff', 'Staff'),
        ('Admin', 'Admin'),
        ('Seller', 'Seller'),
        ('Buyer', 'Buyer'),
    )
    USER_TYPE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )
    BUSINESS_TYPE_CHOICES = (
        ('individual', 'Individual Seller'),
        ('company', 'Company'),
        ('publisher', 'Publisher'),
        ('bookstore', 'Bookstore'),
        ('educational', 'Educational Institution'),
        ('other', 'Other'),
    )
    SUBSCRIPTION_PLAN_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('decade', '10-Year'),
    )

    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True, null=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    grade = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    student_admin_id = models.CharField(max_length=50, unique=True, blank=True, null=True, editable=False)
    
    # Enhanced fields for seller functionality
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='buyer')
    phone_number = models.CharField(max_length=20, blank=True, null=True)  # Enhanced from phone
    address = models.TextField(blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES, blank=True, null=True)
    subscription_plan = models.CharField(max_length=10, choices=SUBSCRIPTION_PLAN_CHOICES, default='monthly')

    def generate_custom_id(self):
        year = timezone.now().year
        role_code_map = {'Student': 'ST', 'Staff': 'SF', 'Admin': 'AD'}
        role_code = role_code_map.get(self.role, 'XX')
        number = random.randint(1000, 9999)
        grade_part = self.grade if self.role == 'Student' and self.grade else ''
        return f"{role_code}{number}/{grade_part}/{year}"

    def save(self, *args, **kwargs):
        if not self.student_admin_id:
            new_id = self.generate_custom_id()
            while User.objects.filter(student_admin_id=new_id).exists():
                new_id = self.generate_custom_id()
            self.student_admin_id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.student_admin_id})"


# -------------------------
# Book Category Models
# -------------------------
class BookCatagory(models.Model):
    id = models.CharField(primary_key=True, max_length=4, default=generate_unique_id, editable=False)
    name = models.CharField(max_length=200, null=True)
    image_path = models.ImageField(upload_to='category_covers/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.name:
            uid = uuid.uuid4().hex[:6].upper()
            self.name = f"Category-{uid}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or "Unnamed Category"


class SubBookCategory(models.Model):
    id = models.CharField(primary_key=True, max_length=4, default=generate_unique_id, editable=False)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(BookCatagory, on_delete=models.CASCADE, related_name='subcategories')

    def save(self, *args, **kwargs):
        if not self.name:
            uid = uuid.uuid4().hex[:6].upper()
            self.name = f"SubBookCategory-{uid}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or "Unnamed SubCategory"


# -------------------------
# Enhanced Book Model with Hard/Soft Book Support
# -------------------------
class Book(models.Model):
    BOOK_TYPE_CHOICES = [
        ('hard', 'Hard Copy (Physical Book)'),
        ('soft', 'Soft Copy (Digital Book)'),
        ('both', 'Both Available'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Pickup Only'),
        ('delivery', 'Delivery Only'),
        ('both', 'Pickup & Delivery'),
    ]

    GRADE_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    LANGUAGES = [
        ('english', 'English'),
        ('spanish', 'Spanish'),
        ('french', 'French'),
        ('german', 'German'),
        ('chinese', 'Chinese'),
        ('japanese', 'Japanese'),
        ('amharic', 'Amharic (አማርኛ)'),
        ('oromo', 'Oromo (Afaan Oromoo)'),
        ('tigrinya', 'Tigrinya (ትግርኛ)'),
        ('somali', 'Somali (Af-Soomaali)'),
        ('sidama', 'Sidama'),
        ('wolaytta', 'Wolaytta'),
    ]

    # Basic book information
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(BookCatagory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    sub_category = models.ForeignKey(SubBookCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    
    # Book type and availability
    book_type = models.CharField(max_length=10, choices=BOOK_TYPE_CHOICES, default='both')
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHOD_CHOICES, default='both')
    
    # Files and images
    pdf_file = models.FileField(upload_to='books/pdfs/', null=True, blank=True)
    cover_image = models.ImageField(
        upload_to='books/covers/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # Book details
    published_date = models.DateField(null=True, blank=True)
    page_count = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=20, choices=LANGUAGES, default='english')
    grade_level = models.CharField(max_length=20, choices=GRADE_LEVELS, default='beginner')
    
    # Enhanced pricing for different types
    hard_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price for hard copy")
    soft_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price for soft copy")
    rental_price_per_week = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Rental price per week")
    
    # Original price field for backward compatibility
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Availability flags
    is_for_sale = models.BooleanField(default=True, help_text="Available for purchase")
    is_for_rent = models.BooleanField(default=False, help_text="Available for rental")
    is_free = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    rating = models.FloatField(default=0.0)
    views = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title', 'author']),
            models.Index(fields=['category', 'sub_category']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['book_type']),
            models.Index(fields=['is_for_sale', 'is_for_rent']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_book_type_display()})"

    def save(self, *args, **kwargs):
        # Update is_free based on both prices
        self.is_free = (self.hard_price == 0 and self.soft_price == 0)
        
        # Backward compatibility: set price to soft price if available, otherwise hard price
        if self.soft_price > 0:
            self.price = self.soft_price
        elif self.hard_price > 0:
            self.price = self.hard_price
            
        super().save(*args, **kwargs)

    @property
    def display_categories(self):
        cats = []
        if self.category:
            cats.append(self.category.name)
        if self.sub_category:
            cats.append(self.sub_category.name)
        return cats

    def get_pdf_url(self):
        return self.pdf_file.url if self.pdf_file else None

    def get_cover_url(self):
        return self.cover_image.url if self.cover_image else None
    
    @property
    def available_for_hard(self):
        """Check if hard copy is available"""
        return self.book_type in ['hard', 'both'] and self.hard_price > 0 and self.is_for_sale
    
    @property
    def available_for_soft(self):
        """Check if soft copy is available"""
        return self.book_type in ['soft', 'both'] and self.soft_price > 0 and self.is_for_sale
    
    @property
    def available_for_rent(self):
        """Check if rental is available"""
        return self.is_for_rent and self.rental_price_per_week > 0
    
    @property
    def display_price(self):
        """Get display price based on availability"""
        if self.available_for_hard and self.available_for_soft:
            return f"H: ${self.hard_price} | S: ${self.soft_price}"
        elif self.available_for_hard:
            return f"${self.hard_price}"
        elif self.available_for_soft:
            return f"${self.soft_price}"
        else:
            return "Not Available"
    
    def get_price_for_type(self, book_type):
        """Get price for specific book type"""
        if book_type == 'hard':
            return self.hard_price
        elif book_type == 'soft':
            return self.soft_price
        else:
            return self.price  # fallback for compatibility
    
    @property
    def price_by_type(self):
        """Return dictionary with pricing for different types"""
        return {
            'hard': {
                'available': self.available_for_hard,
                'price': self.hard_price,
                'delivery_method': self.delivery_method
            },
            'soft': {
                'available': self.available_for_soft,
                'price': self.soft_price,
                'delivery_method': 'digital'
            },
            'rent': {
                'available': self.available_for_rent,
                'price': self.rental_price_per_week,
                'delivery_method': self.delivery_method
            }
        }


class BookTag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#6B7280')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


#
class QCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='📚')
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    enrolled = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
   
    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    QCategory = models.ForeignKey(QCategory, on_delete=models.CASCADE, related_name='general', default=1)
    desc = RichTextField()
    time = models.IntegerField(default=30, help_text="Exam duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserSubjectProgress(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    score = models.FloatField(null=True, blank=True)
    time_spent = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'subject'], ['session_key', 'subject']]
        verbose_name_plural = "User Subject Progress"
    
    def __str__(self):
        user_identifier = self.user.username if self.user else f"Session:{self.session_key}"
        return f"{user_identifier} - {self.subject.name} ({self.progress}%)"
    
class Questions(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    question_text = RichTextField()
    options = models.JSONField()
    correct_option = models.CharField(max_length=100, null=True, blank=True)
    explain = RichTextField(null=True, blank=True)

    def __str__(self):
        return f"{self.subject.name} > {self.question_text[:50]}"

    def clean(self):
        super().clean()
        if not isinstance(self.options, list) or len(self.options) < 2:
            raise ValidationError("Options must be a list with at least 2 items.")
        if self.correct_option and self.correct_option not in self.options:
            raise ValidationError(f"Correct option '{self.correct_option}' must be one of the options.")


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    questions = models.ManyToManyField(Questions)
    created_at = models.DateTimeField(auto_now_add=True)
    time_limit_minutes = models.IntegerField(default=30)

    def __str__(self):
        return self.title


# -------------------------
# Project Model
# -------------------------
class Project(models.Model):
    BADGE_CHOICES = [
        ('top-rated', 'Top Rated'),
        ('featured', 'Featured'),
        ('new', 'New'),
    ]

    title = models.CharField(max_length=255)
    summary = models.TextField(help_text="Brief summary for free users")
    full_description = models.TextField(help_text="Full description for Pro users")
    profile = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    date = models.DateField()
    badge = models.CharField(max_length=50, choices=BADGE_CHOICES, default='new')
    is_pro = models.BooleanField(default=False)
    image = models.ImageField(upload_to="project_images/")
    pdf = models.FileField(upload_to="project_pdfs/")
    views = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0.0)
    tags = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# -------------------------
# Sign Language Model
# -------------------------
class SignWord(models.Model):
    word = models.CharField(max_length=100)
    video = models.FileField(upload_to='videos/')
    image = models.ImageField(upload_to='images/')

    def __str__(self):
        return self.word


# -------------------------
# About Us / Team / Testimonials
# -------------------------
class AboutUs(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField()
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255, default="About Us")
    subtitle = models.TextField()
    mission = models.TextField()
    why_choose_us = models.TextField()
    description = models.TextField(blank=True)
    services = models.TextField(blank=True)
    recognition = models.TextField(blank=True)
    established_year = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

    def services_list(self):
        return [s.strip() for s in self.services.split(",") if s.strip()]


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    quote = models.TextField()
    role = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name}: {self.quote[:30]}..."


class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    photo = models.ImageField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.role}"


# Enhanced Payment Model to support different book types
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('telebir', 'Telebir'),
        ('cbe_bir', 'CBE Bir'),
        ('hellocash', 'HelloCash'),
        ('dashen', 'Dashen Bank'),
        ('awash', 'Awash Bank'),
        ('amole', 'Amole'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('chapa', 'Chapa'),
    ]

    PAYMENT_TYPES = [
        ('purchase_hard', 'Purchase Hard Copy'),
        ('purchase_soft', 'Purchase Soft Copy'),
        ('rental', 'Rental'),
        ('extension', 'Rental Extension'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='purchase_soft')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    local_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    local_currency = models.CharField(max_length=3, default='ETB')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Additional fields for rental tracking
    rental_duration_weeks = models.PositiveIntegerField(null=True, blank=True)
    rental_start_date = models.DateField(null=True, blank=True)
    rental_end_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.book.title} - {self.get_payment_type_display()} - {self.amount}"

    class Meta:
        ordering = ['-created_at']


class UserPurchase(models.Model):
    PURCHASE_TYPES = [
        ('hard', 'Hard Copy'),
        ('soft', 'Soft Copy'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    purchase_type = models.CharField(max_length=10, choices=PURCHASE_TYPES, default='soft')
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # For time-limited purchases

    class Meta:
        unique_together = ['user', 'book', 'purchase_type']

    def __str__(self):
        return f"{self.user} - {self.book.title} ({self.get_purchase_type_display()})"
    
class UploadedPDF(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    document = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.document.name