from typing import Any
import uuid
from django.db import models
from django.contrib.auth import get_user_model


from django.db.models.signals import post_save, post_delete
from django.utils.text import slugify
from django.urls import reverse
from authy.models import Cat
from notifications.models import Notification

User = get_user_model()

# Create your models here.

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)


class Tag(models.Model):
	title = models.CharField(max_length=75, verbose_name='Tag')
	slug = models.SlugField(null=False, unique=True)

	class Meta:
		verbose_name='Tag'
		verbose_name_plural = 'Tags'

	def get_absolute_url(self):
		return reverse('post:tags', args=[self.slug])
		
	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		return super().save(*args, **kwargs)

class PostFileContent(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_owner')
	file = models.FileField(upload_to=user_directory_path)

POST_TYPES = (
	('n','Normal'),
	('l','Lost'),
	('f','Found'),
)
class Post(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	# type = models.CharField(max_length=1,choices=POST_TYPES)
	content =  models.ManyToManyField(PostFileContent, related_name='contents')
	caption = models.TextField(max_length=1500, verbose_name='Caption')
	posted = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	tags = models.ManyToManyField(Tag, related_name='tags',blank=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	likes = models.IntegerField(default=0)
	cats = models.ManyToManyField(Cat,related_name='posts',blank=True)


	def get_absolute_url(self):
		return reverse('post:postdetails', args=[str(self.id)])

	def __str__(self):
		return str(self.id)
	
def embedding_directory(instance,filename):
	return f'embeddings/{filename}'
	
class LostPost(Post):
	geotag = models.CharField(max_length=255,null=False,blank=False)
	search_active = models.BooleanField(default=True)
	is_found = models.BooleanField(default=False)
	embedding = models.FileField(upload_to=embedding_directory,null=True)

	def get_absolute_url(self):
		return reverse('post:lostpostdetails',args=[str(self.id)])

class FoundPost(Post):
	geotag = models.CharField(max_length=255,null=False,blank=False)
	search_active = models.BooleanField(default=True)
	is_matched = models.BooleanField(default=False)
	embedding = models.FileField(upload_to=embedding_directory,null=True)

	def get_compare_url(self,lost_id):
		return reverse('post:compare', args=[str(lost_id), str(self.id)])
	

class CandidateMatch(models.Model):
	user = models.ForeignKey(User,on_delete=models.CASCADE)
	lostpost = models.ForeignKey(LostPost,on_delete=models.CASCADE)
	matched = models.ManyToManyField(FoundPost,related_name="match",blank=True)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)



class Follow(models.Model):
	follower = models.ForeignKey(User,on_delete=models.CASCADE, null=True, related_name='follower')
	following = models.ForeignKey(User,on_delete=models.CASCADE, null=True, related_name='following')

	def user_follow(sender, instance, *args, **kwargs):
		follow = instance
		sender = follow.follower
		following = follow.following
		notify = Notification(sender=sender, user=following, notification_type=3)
		notify.save()

	def user_unfollow(sender, instance, *args, **kwargs):
		follow = instance
		sender = follow.follower
		following = follow.following

		notify = Notification.objects.filter(sender=sender, user=following, notification_type=3)
		notify.delete()

class Stream(models.Model):
	"""
	Create a Stream for each follower when the user they following
	create a post
	"""
	following = models.ForeignKey(User, on_delete=models.CASCADE,null=True, related_name='stream_following')
	user = models.ForeignKey(User, on_delete=models.CASCADE)   
	post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True)
	date = models.DateTimeField()

	def add_post(sender, instance, *args, **kwargs):
		post = instance
		user = post.user
		followers = Follow.objects.all().filter(following=user)
		for follower in followers:
			stream = Stream(post=post, user=follower.follower, date=post.posted, following=user)
			stream.save()

class Likes(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_like')
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_like')

	def user_liked_post(sender, instance, *args, **kwargs):
		like = instance
		post = like.post
		sender = like.user
		notify = Notification(post=post, sender=sender, user=post.user, notification_type=1)
		notify.save()

	def user_unlike_post(sender, instance, *args, **kwargs):
		like = instance
		post = like.post
		sender = like.user

		notify = Notification.objects.filter(post=post, sender=sender, notification_type=1)
		notify.delete()


#Stream
# when a post is created, activate callback function Stream.add_post to add
# that post to stream of users who follows the owner of that post
post_save.connect(Stream.add_post, sender=Post)

#Likes
post_save.connect(Likes.user_liked_post, sender=Likes)
post_delete.connect(Likes.user_unlike_post, sender=Likes)

#Follow
post_save.connect(Follow.user_follow, sender=Follow)
post_delete.connect(Follow.user_unfollow, sender=Follow)