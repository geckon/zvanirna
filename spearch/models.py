from django.db import models

class Institution(models.Model):
    name = models.CharField(max_length=100)

class Speaker(models.Model):
    name = models.CharField(max_length=100)
    url_psp = models.URLField(null=True)

class Speech(models.Model):
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE, blank=False)
    speaker = models.ForeignKey('Speaker', on_delete=models.CASCADE)
    speaker_title = models.CharField(max_length=100)
    #date = models.DateField()
    speech = models.TextField()

