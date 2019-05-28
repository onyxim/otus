from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('hasker_accounts.urls')),
    path('', include('hasker_qa.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = \
        [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + \
        urlpatterns + \
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
