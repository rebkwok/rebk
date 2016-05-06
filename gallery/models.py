from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from django_extensions.db.fields import AutoSlugField

from imagekit.models import ProcessedImageField


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    slug = AutoSlugField(populate_from='name', max_length=40, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'categories'


class Image(models.Model):

    photo = ProcessedImageField(
        upload_to='gallery',
        format='JPEG',
        options={'quality': 70},
        null=True, blank=True,
    )

    category = models.ForeignKey(Category, related_name='images')
    caption = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return "Photo id: " + str(self.id)

    def save(self, *args, **kwargs):
        # delete old image file when replacing by updating the file
        try:
            this = Image.objects.get(id=self.id)
            if this.photo != self.photo:
                this.photo.delete(save=False)
        except Image.DoesNotExist:
            pass  # when new photo then we do nothing, normal case
        super(Image, self).save(*args, **kwargs)


@receiver(pre_delete)
def delete_image(sender, instance, **kwargs):
    if sender == Image:
        instance.photo.delete()
