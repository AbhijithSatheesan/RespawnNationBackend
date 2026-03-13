from django.db import models

from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill

# Create your models here.


class GameCategory(models.Model):
    name = models.CharField(max_length= 30)
    main_category = models.BooleanField(default= False)

    def __str__(self):
        return self.name


class Games(models.Model):
    name = models.CharField(max_length= 30)
    description =  models.TextField(null = True, blank= True)
    release_year = models.IntegerField(null= True, blank = True)
    categories = models.ManyToManyField(GameCategory, related_name= 'games')
    tags = models.CharField(max_length= 100, null= True, blank = True)
    rating = models.FloatField(null = True, blank = True)
    action = models.FloatField(null=True, blank= True)
    graphics = models.FloatField(null= True, blank= True)
    story = models.FloatField(null= True, blank= True)
    gameplay = models.FloatField(null= True, blank= True)
    developer = models.CharField(max_length= 30, null= True, blank= True)
    publisher = models.CharField(max_length= 30, null= True, blank= True)
    price = models.FloatField(default= 0,null= True, blank= True)
    trailer_1 = models.URLField(null= True, blank = True)
    trailer_2 = models.URLField(null= True, blank = True)
    

    # the cover image should be resized according to screen size
    cover_image = models.ImageField( upload_to='games/',null = True, blank = True)

    cover_small = ImageSpecField(
        source='cover_image',
        processors=[ResizeToFill(400, 600)],
        format='WEBP',
        options={'quality': 60}
     )
    
    cover_medium = ImageSpecField(
        source='cover_image',
        processors=[ResizeToFill(800, 1200)],
        format='WEBP',
        options={'quality': 70}
     )
    
    cover_large = ImageSpecField(
        source='cover_image',
        processors=[ResizeToFill(1600, 2400)],
        format='WEBP',
        options={'quality': 80}
     )
    
    def __str__(self):
        return self.name