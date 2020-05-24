from django.urls import path
from order.views import OrderView,CommitView
urlpatterns = [
    path(r'',OrderView.as_view(),name='order'),
    path(r'commit',CommitView.as_view(),name='commit'),
]
