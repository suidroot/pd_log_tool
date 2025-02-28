
"""
URL configuration for log_site project.

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
from django.urls import path, include
from log_query_site import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about_page, name='about_page'),
    path('about/', views.about_page, name='about_page'),
    path('admin/', admin.site.urls),
    path('add/arrest/', views.add_arrest, name='add_arrest_log'),
    path('add/dispatch/', views.add_dispatch, name='add_dispatch'),
    path('search', views.search_records, name='search_records'),
    path('search/', views.search_records, name='search_records'),
    path('results', views.search_results, name='results'),
    path('results/', views.search_results, name='results'),
    path('logout/', views.logout_page, name='results'),
    path('logout/', views.logout_page, name='results'),
    path("accounts/", include("django.contrib.auth.urls")),
]

