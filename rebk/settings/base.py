"""
Django settings for flexibeast project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import dj_database_url
import environ
import os

root = environ.Path(__file__) - 3  # two folders back (/a/b/ - 3 = /)

env = environ.Env(DEBUG=(bool, False),
                  PAYPAL_TEST=(bool, False),
                  USE_MAILCATCHER=(bool, False),
                  HEROKU=(bool, False),
                  BOOKING_ON=(bool, False)
                  )

environ.Env.read_env(root('rebk/.env'))  # reading .env file

BASE_DIR = root()
#
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')
if SECRET_KEY is None:
    print("No secret key!")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')
# when env variable is changed it will be a string, not bool
if str(DEBUG).lower() in ['true', 'on']:
    DEBUG = True
else:
    DEBUG = False

ALLOWED_HOSTS = []

if not DEBUG:
    SESSION_COOKIE_DOMAIN = ".rebk.com"

# Application definition

INSTALLED_APPS = (
    'suit',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'django_extensions',
    'crispy_forms',
    'floppyforms',
    'debug_toolbar',
    'imagekit',
    'ckeditor',
    'accounts',
    'paypal.standard.ipn',
    'payments',
    'activitylog',
    'gallery',
    'products',
    'orders',
)

INTERNAL_IPS = ('127.0.0.1', '0.0.0.0')

SITE_ID = 1

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",

    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# SOCIALACCOUNT_PROVIDERS = \
#     {'facebook': {
#         'SCOPE': ['email'],
#         # 'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
#         'METHOD': 'oauth2',
#         'VERIFIED_EMAIL': False,
#         'VERSION': 'v2.2'
#         }}

SOCIALACCOUNT_PROVIDERS = {}
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[rebkdesign]"
ACCOUNT_PASSWORD_MIN_LENGTH = 6
ACCOUNT_SIGNUP_FORM_CLASS = 'accounts.forms.SignupForm'

SOCIALACCOUNT_QUERY_EMAIL = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [root('templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                # Required by allauth template tags
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "django.core.context_processors.media",
                "website.context_processors.website_pages",
                "website.context_processors.more_menu_options",
                "website.context_processors.menu_options",
                "website.context_processors.reviews_pending",
                "website.context_processors.booking_on",
            ),
            'debug': DEBUG,
        },
    },
]

ROOT_URLCONF = 'rebk.urls'

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda o: "/users/%s/" % o.username,
}

WSGI_APPLICATION = 'flexibeast.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': env.db(),
    # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
}

if env('HEROKU'):
    DATABASES['default'] = dj_database_url.config()

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True

HEROKU = env('HEROKU')
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATICFILES_DIRS = (root('static'),)

STATIC_URL = '/static/'
STATIC_ROOT = root('collected-static')
if HEROKU:
    STATIC_ROOT = 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = root('media')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'rebk.shop@gmail.com'
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', None)
if EMAIL_HOST_PASSWORD is None:
    print("No email host password provided!")
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = 'rebk.shop@gmail.com'
DEFAULT_STUDIO_EMAIL = env('DEFAULT_STUDIO_EMAIL')
SUPPORT_EMAIL = 'rebkwok@gmail.com'

# #####LOGGING######
if not HEROKU:
    LOG_FOLDER = env('LOG_FOLDER')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[%(levelname)s] - %(asctime)s - %(name)s - '
                          '%(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            }
        },
        'handlers': {
            'file_app': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(LOG_FOLDER, 'rebk.log'),
                'maxBytes': 1024*1024*5,  # 5 MB
                'backupCount': 5,
                'formatter': 'verbose'
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            }
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file_app'],
                'level': 'WARNING',
                'propagate': True,
            },
            'gallery': {
                'handlers': ['console', 'file_app'],
                'level': 'INFO',
                'propagate': True,
            },
            'payments': {
                'handlers': ['console', 'file_app'],
                'level': 'INFO',
                'propagate': True,
            },
            'accounts': {
                'handlers': ['console', 'file_app'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    }


# ####HEROKU#######

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# DJANGO-SUIT
SUIT_CONFIG = {
    'ADMIN_NAME': "RebKDesign",
    'MENU': (
        {
            'app': 'gallery'
        },
        {
            'label': 'Accounts',
            'models': (
                'auth.user',
                'account.emailaddress',
                'account.emailconfirmation',
                'socialaccount.socialaccount'
            ),
            'icon': 'icon-user',
        },
        {
            'label': 'Payments',
            'models': ('payments.paypalbookingtransaction',
                       'payments.paypalblocktransaction',
                       'ipn.paypalipn'),
            'icon': 'icon-asterisk',
        },
        {
            'label': 'Activity Log',
            'app': 'activitylog',
            'icon': 'icon-asterisk',
        },
        {
            'label': 'Go to main site',
            'url': '/',
            'icon': 'icon-map-marker',
        },
    )
}

# CKEDITOR
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': [
         ['Source', '-', 'Bold', 'Italic', 'Underline',
          'TextColor', 'BGColor'],
         ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
          'JustifyLeft', 'JustifyCenter', 'JustifyRight', '-',
          'Table', 'HorizontalRule', 'Smiley', 'SpecialChar'],
         ['Format', 'Font', 'FontSize']
        ],
        'width': '100%',
        'AllowedContent': True,
    },
    'studioadmin': {
        'toolbar': [
         ['Source', '-', 'Bold', 'Italic', 'Underline',
          'TextColor', 'BGColor'],
         ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
          'JustifyLeft', 'JustifyCenter', 'JustifyRight', '-',
          'Table', 'HorizontalRule', 'Smiley', 'SpecialChar'],
         ['Format', 'Font', 'FontSize', 'Link']
        ],
        'width': '100%',
        'AllowedContent': True,
        'font_names': 'Arial;Book Antiqua;Comic Sans MS;Courier New;Georgia;'
                      'Lucida Sans Unicode;Tahoma,Times New Roman;'
                      'Trebuchet MS;Verdana',
    },
    'studioadmin_min': {
        'toolbar': [
            ['Bold', 'Italic', 'Underline', 'FontSize', 'Link']
        ],
        'height': 100,
        'width': '100%',
    },
    'studioadmin_extended': {
        'autoGrow_onStartup': True,
        'autoGrow_minWidth': 1200,
        'autoGrow_minHeight': 300,
        'autoGrow_maxHeight': 500,
        'extraPlugins': 'autogrow',
        'title': '',
        'width': '100%',
        'AllowedContent': True,
        'font_names': 'Arial;Book Antiqua;Comic Sans MS;Courier New;Georgia;'
                      'Lucida Sans Unicode;Tahoma,Times New Roman;'
                      'Trebuchet MS;Verdana',
        'extraAllowedContent': ['iframe[*]', '*[id]', '*(*)'],
        'toolbar': [
            ['Source', '-', 'Bold', 'Italic', 'Underline',
            'TextColor', 'BGColor', '-', 'Image', 'Iframe'],
            ['NumberedList', 'BulletedList', '-', 'Outdent',
             'Indent', '-',
            'JustifyLeft', 'JustifyCenter', 'JustifyRight', '-',
            'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'Link'],
            ['Format', 'Font', 'FontSize']
        ]
    },
}

CKEDITOR_JQUERY_URL = \
    '//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js'

# MAILCATCHER
if env('USE_MAILCATCHER'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = '127.0.0.1'
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False

# DJANGO-PAYPAL
PAYPAL_RECEIVER_EMAIL = env('PAYPAL_RECEIVER_EMAIL')
PAYPAL_TEST = env('PAYPAL_TEST')

# HEROKU logging
if HEROKU:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            }
        },
        'loggers': {
            'django.request': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'accounts': {
                'handlers': ['console'],
                'level': 'INFO',
                'propogate': True,
            },
            'gallery': {
                'handlers': ['console'],
                'level': 'INFO',
                'propogate': True,
            },
            'payments': {
                'handlers': ['console'],
                'level': 'INFO',
                'propogate': True,
            },
        },
    }

# for gallery app
PERMISSION_DENIED_URL = 'permission_denied'

TESTING = False