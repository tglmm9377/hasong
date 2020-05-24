from django.urls import path,re_path
from cart.views import CartAddView,CartListView,CartUpdate,DeleteView
urlpatterns= [
    path(r'add',CartAddView.as_view(),name='add'),
    re_path(r'^$',CartListView.as_view(),name='show'),
    path('update',CartUpdate.as_view(),name="update"),
    path('delete',DeleteView.as_view(),name="delete")


]
