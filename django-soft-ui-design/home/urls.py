from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('system_check/', views.system_check, name='system_check'),
    path('login_as_guest/', views.login_as_guest, name='login_as_guest'),
    path('payment/', views.payment_page, name='payment_page'),
    path('chat/', views.chat_page, name='chat_page'),
    path('chat/send_message/', views.send_message, name='send_message'),
    path('qrmodaldisplay/', views.qrmodaldisplay, name='qrmodaldisplay'),
    path('validate_ticket/', views.validate_ticket, name='validate_ticket'),
    path('verify_transaction/', views.verify_transaction, name='verify_transaction'),
    path('process_payment/', views.process_payment, name='process_payment'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)