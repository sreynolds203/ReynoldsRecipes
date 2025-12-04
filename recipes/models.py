from django.db import models
from django.urls import reverse

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    ingredients = models.TextField(help_text="One per line")
    steps = models.TextField(help_text="Step by line or paragraphs")

    class Meta:
        ordering = ['-title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('recipes:detail', args=[str(self.id)])
