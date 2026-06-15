from django.urls import path
from . import views






urlpatterns = [
    # ==================== HOME & PROFILE ====================
    path('', views.hospital_list, name='hospital_list'),
    path('hospital/profile/<int:hospital_id>/', views.hospital_profile, name='hospital_profile'),

    # ==================== AUTH ====================
    path('register/', views.register_view, name='register'),
    path('patient/register/', views.user_register_view, name='user_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ==================== DASHBOARD ====================
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('hospital-dashboard/', views.hospital_dashboard, name='hospital_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),

    # ==================== BED CRUD ) ====================
    path('hospital/bed/create/', views.bed_create, name='bed_create'),
    path('hospital/bed/update/<int:pk>/', views.bed_update, name='bed_update'),
    path('hospital/bed/delete/<int:pk>/', views.bed_delete, name='bed_delete'),

    #  ==================== INTERACTIVE JAVASCRIPT ACTION ==================== ⚡
    path('hospital/bed/quick-update/<int:bed_id>/<str:action>/', views.update_bed_count, name='update_bed_count'),

    # ==================== PAYMENT GATEWAY ====================
    path('checkout/<int:bed_id>/', views.checkout_payment_view, name='checkout_payment'),
    path('reserve-bed-view/<int:bed_id>/', views.reserve_bed_view, name='reserve_bed_view'),
    
    # views.payment_success_view 
    path('booking-success/<int:bed_id>/', views.payment_success_view, name='booking_success'),
    path('extend-payment/<int:res_id>/', views.extend_payment_view, name='extend_payment'),
    path('payment-success-handler/', views.payment_success_view, name='payment_success'),
    path('payment-fail/<int:res_id>/', views.payment_fail_view, name='payment_fail'),
    path('cancel-reservation/<int:res_id>/', views.cancel_reservation, name='cancel_reservation'),

    path('api/update-profile/', views.update_profile_ajax, name='update_profile_ajax'),
    
    
]