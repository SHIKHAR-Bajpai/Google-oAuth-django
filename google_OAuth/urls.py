"""
URL configuration for google_OAuth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path , include
from . import views 

urlpatterns = [
    path('admin/', admin.site.urls),

    path( '' , views.home , name = 'home'),
    path('google/login/' , views.google_login , name = 'google_login'),
    path('google/callback/' , views.google_callback , name = 'google_callback'),
    path('google/dashboard' , views.dashboard , name = 'dashboard'),
    path('logout/' , views.logout , name ='logout'),
    
    path("drive/files/", views.list_drive_files, name="list_drive_files"),
    path('drive/upload/', views.upload_file, name='upload_file'),
    path("drive/download/<str:file_id>/", views.download_drive_file, name="download_drive_file"),

    path('chat/', include('chat_module.urls')),

]
