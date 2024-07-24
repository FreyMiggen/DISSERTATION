from django.urls import path
from post.views import index, NewPost, PostDetails, tags, like, favorite, NewLostPost, LostPostDetails, findSimilar,like, comparison,NewFunctionPost

app_name = 'post'
urlpatterns = [
   	path('', index, name='index'),
   	path('newpost/', NewPost, name='newpost'),
   	path('<uuid:post_id>', PostDetails, name='postdetails'),
   	path('<uuid:post_id>/like', like, name='postlike'),
   	path('<uuid:post_id>/favorite', favorite, name='postfavorite'),
   	path('tag/<slug:tag_slug>', tags, name='tags'),
    path('lostpost/', NewLostPost, name='newlostpost'),
    path('like/<uuid:post_id>',like,name='like-post'),
    path('compare/<uuid:lost_id>/<uuid:found_id>',comparison,name='compare'),
    path('lostpost/<uuid:post_id>', LostPostDetails, name='lostpostdetails'),
     path('find-similar/<uuid:post_id>/', findSimilar, name='find-similar-ajax'),
     path('lost-found-post/<option>/',NewFunctionPost,name='new-function-post'),
    
]