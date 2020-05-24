from django.urls import path,re_path
from user import views
from user.views import RegisterView,ActiveView,LoginView,UserOrderView,UserInfoView,AddressView,LogoutView,CartView
from django.contrib.auth.decorators import login_required
urlpatterns = [
    # path("register/",views.register,name='register'),#name用于url 反向解析使用
    # path('register_handle/',views.register_handle,name="register_handle"),
    path('register/',RegisterView.as_view(),name='register'),
    re_path(r'active/(?P<token>.*)$',ActiveView.as_view(),name="active"),
    path(r'login/',LoginView.as_view(),name="login"),
    path(r'order/',login_required(UserOrderView.as_view()),name='order'),
    re_path(r'info/',UserInfoView.as_view(),name="info"),
    path(r'address/',AddressView.as_view(),name="address"),
    path(r'logout/',LogoutView.as_view(),name='logout'),
    path(r'cart/',CartView.as_view(),name="cart")
]
