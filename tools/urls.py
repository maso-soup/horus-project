from django.urls import path
from . import views

urlpatterns = [
    path('', views.summary, name='home'),
    path('<str:addr>', views.summary, name='home-param'),

    path('summary/', views.summary, name='summary'),
    path('summary/<str:addr>', views.summary, name='summary-param'),

    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/<str:addr>', views.portfolio, name='portfolio-param'),

    path('staking/', views.staking, name='staking'),
    path('staking/<str:addr>', views.staking, name='staking-param'),

    path('wallet/', views.wallet, name='wallet'),
    path('wallet/<str:addr>', views.wallet, name='wallet-param'),
]
