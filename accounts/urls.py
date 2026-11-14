"""Website URL routes for accounts (signup, login, logout, profile)."""

from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views
from accounts.forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            # Already logged in? Skip the form and go to My Shelf.
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    # Django's LogoutView only accepts POST, so logging out can't be triggered by a link.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
]
