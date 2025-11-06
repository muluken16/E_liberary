from django.contrib import admin
from .models import AboutUs, Book, Project, SignWord, Subject, Questions, BookCatagory, SubBookCategory, Quiz, QCategory, TeamMember, User
# Register your models here.
from .forms import QuestionsForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
class QuestionsAdmin(admin.ModelAdmin):
    form = QuestionsForm
    list_display = ['subject', 'question_text']

admin.site.register(Questions, QuestionsAdmin)

admin.site.register(Book)
admin.site.register(Subject) 
admin.site.register(BookCatagory)  
admin.site.register(SubBookCategory)  
admin.site.register(Quiz) 
admin.site.register(Project)  
admin.site.register(QCategory) 
admin.site.register(SignWord) 
admin.site.register(AboutUs) 
admin.site.register(TeamMember)   
admin.site.register(User)  

