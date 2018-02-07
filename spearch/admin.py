from django.contrib import admin

# Register your models here.
from spearch.models import Institution, Speaker, Speech

admin.site.register(Institution)
admin.site.register(Speaker)
admin.site.register(Speech)
