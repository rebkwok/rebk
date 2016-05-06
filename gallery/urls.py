from django.conf import settings
from django.conf.urls import url
from gallery.views import category_detail_view, CategoryListView, \
    CategoryUpdateView, gallery_menu_view, view_gallery

urlpatterns = [
    url(r'^$', gallery_menu_view, name='gallery'),
    url(r'^album/(?P<slug>[\w-]+)$', category_detail_view, name='category'),
    ##### VIEWS FOR STAFF USER ONLY #####
    # Category list view, show all categories in list, allow  for edit of
    # name and delete of entire category, add new category, links to category
    # detail views
    url(r'^albums/$', CategoryListView.as_view(), name='categories'),
    # Category detail view, show all images for edit/delete/add
    url(
        r'^albums/(?P<pk>\d+)$', CategoryUpdateView.as_view(),
        name='edit_category'
    ),
]


if settings.TESTING:
    urlpatterns.append(url(r'^alternative_view$', view_gallery, name='alternative'))
