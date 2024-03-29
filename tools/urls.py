from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.summary, name='home'),
    path('<str:addr>', views.summary, name='home-param'),

    path('summary/', views.summary, name='summary'),
    path('summary/<str:addr>', views.summary, name='summary-param'),

    path('wallet/', views.wallet, name='wallet'),
    path('wallet/<str:addr>', views.wallet, name='wallet-param'),

    path('faq/', views.faq, name='faq'),

    path('liqwid/', views.liqwid_current, name='liqwid'),
    path('liqwid-current/', views.liqwid_current, name='liqwid-current'),
]
