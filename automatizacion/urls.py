from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("portal.urls")),
    path("dtf/", include(("dtf.urls", "dtf"), namespace="dtf")),
    path("dtf/lab/", include(("sigmalab.urls", "sigmalab"), namespace="sigmalab")),
    path("dtf/mec/", include(("mec.urls", "mec"), namespace="mec")),
    path("dtf/dp/", include(("sigmadp.urls", "sigmadp"), namespace="sigmadp")),
    path("dtf/optics/", include(("sigmaoptics.urls", "sigmaoptics"), namespace="sigmaoptics")),
    # path("cuentas/", include(("accounts.urls", "accounts"), namespace="accounts")),#
    path("icts/", include(("icts.urls", "icts"), namespace="icts")),
    path("sigmaconf/", include(("sigmaconf.urls", "sigmaconf"), namespace="sigmaconf")),
    path("sigmaimp/", include(("sigmaimp.urls", "sigmaimp"), namespace="sigmaimp")),
    path("sigmavdg/", include(("sigmavdg.urls", "sigmavdg"), namespace="sigmavdg")),
    path(
        "sigmaoptics/",
        include(("sigmaoptics_icts.urls", "sigmaoptics_icts"), namespace="sigmaoptics_icts"),
    ),
    path(
        "sigmaprofilometer/",
        include(("sigmaprofilometer.urls", "sigmaprofilometer"), namespace="sigmaprofilometer"),
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path('accounts/', include('accounts.urls')),    # ← AÑADIR
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Django Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
