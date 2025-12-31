from django.urls import reverse


def test_mcf_routes_reverse():
    reverse("sigmaconf:mcf_dashboard")
    reverse("sigmaconf:mcf_create_session")
    reverse("sigmaconf:mcf_session_detail", args=[1])
    reverse("sigmaconf:mcf_finish_session", args=[1])
    reverse("sigmaconf:mcf_add_sample", args=[1])
    reverse("sigmaconf:mcf_notice_download", args=[1])
    reverse("sigmaconf:mcf_export_excel", args=[1])
    reverse("sigmaconf:mcf_sample_edit", args=[1])
