from django.contrib import admin
from post.models import Post, Tag, Follow, Stream,PostFileContent, LostPost, FoundPost, Likes

# Register your models here.
admin.site.register(Tag)
admin.site.register(Post)
admin.site.register(Follow)
admin.site.register(Stream)
admin.site.register(PostFileContent)
admin.site.register(LostPost)
admin.site.register(FoundPost)
admin.site.register(Likes)
