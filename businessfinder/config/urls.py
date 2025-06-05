from django.contrib import admin
from django.urls import path, include  # This will now work
from search import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('search.urls')),
    path('send-email/', views.send_email_view, name='send_email'),
]
