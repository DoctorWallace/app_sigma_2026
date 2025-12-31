from django.contrib.auth import get_user_model

User = get_user_model()
username = 'admin'
email = 'admin@example.com'
password = 'Admin123!'

u, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'is_staff': True,
        'is_superuser': True,
    }
)
u.email = email
u.is_staff = True
u.is_superuser = True
u.set_password(password)
u.save()

print('created' if created else 'updated')

