from django.db import models
from django.urls import reverse

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True, help_text="Recipe author")
    description = models.TextField(blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    cook_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    steps = models.TextField(help_text="Number each step or separate paragraphs for each instruction")
    tags = models.TextField(blank=True, help_text="Comma-separated tags")

    class Meta:
        ordering = ['-title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('recipes:detail', args=[str(self.id)])
