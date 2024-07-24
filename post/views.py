from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from post.models import Stream, Post, Tag, Likes, PostFileContent, LostPost, FoundPost, CandidateMatch
from post.forms import NewPostForm, NewLostPostForm, NewFoundPostForm,PostCreateWithImagesForm
from stories.models import Story, StoryStream

from comment.models import Comment
from comment.forms import CommentForm
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from django.contrib.auth.decorators import login_required

from django.urls import reverse
from authy.models import Profile
from .tasks import createEmbedding, matchCat
from django.core.cache import cache
from celery.result import AsyncResult
import time
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime
from django.contrib import messages
from django.utils.text import slugify

# Create your views here.
@login_required(login_url='authy:login')
def index(request):
	user = request.user
	posts = Stream.objects.filter(user=user)

	stories = StoryStream.objects.filter(user=user)

	profile = get_object_or_404(Profile,user=user)
	group_ids = []

	for post in posts:
		group_ids.append(post.post_id)
		
	post_items = Post.objects.filter(id__in=group_ids).all().order_by('-posted')		

	template = loader.get_template('index.html')

	context = {
		'post_items': post_items,
		'stories': stories,
		'requesting_profile':profile

	}

	return HttpResponse(template.render(context, request))

def PostDetails(request, post_id):
	post = get_object_or_404(Post, id=post_id)
	user = request.user
	profile = Profile.objects.get(user=user)
	favorited = Likes.objects.filter(user=request.user,post=post)
	if favorited:
		liked = True
	else:
		liked=False

	#comment
	comments = Comment.objects.filter(post=post).order_by('date')
	
	if request.user.is_authenticated:
		profile = Profile.objects.get(user=user)
		#For the color of the favorite button

		# if profile.favorites.filter(id=post_id).exists():
		# 	favorited = True

	#Comments Form
	if request.method == 'POST':
		form = CommentForm(request.POST)
		if form.is_valid():
			comment = form.save(commit=False)
			comment.post = post
			comment.user = user
			comment.save()
			return HttpResponseRedirect(reverse('post:postdetails', args=[post_id]))
	else:
		form = CommentForm()


	template = loader.get_template('post_detail_test.html')

	context = {
		'post':post,
		'profile':profile,
		'form':form,
		'comments':comments,
		'requesting_profile':profile,
		'status':liked
	}

	return HttpResponse(template.render(context, request))


@login_required
def NewPost(request):
	user = request.user
	profile = get_object_or_404(Profile,user=user)

	if request.method == 'POST':
		form = PostCreateWithImagesForm(request.POST, request.FILES, user=user)

		if form.is_valid():
			files = request.FILES.getlist('content')
			caption = form.cleaned_data.get('caption')
			tags_form = form.cleaned_data.get('tags')
			cats = form.cleaned_data.get('cats')
			tags_list = list(tags_form.split(','))

			post = Post.objects.create(caption=caption,user=user)

			for tag in tags_list:
				slug = slugify(tag)
				tag, created = Tag.objects.get_or_create(slug=slug)
				if created:
					tag.title = tag.strip()
				post.tags.add(tag)

			for file in files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				post.content.add(file_instance)

			if cats:
				post.cats.set(cats)

			url = reverse('profile',args=[profile.slug])
			return redirect(url)

	else:
		form = PostCreateWithImagesForm(user=user)

	context = {
		'form':form,
		'profile':profile,
		'requesting_profile':profile,
	}

	return render(request, 'newpost.html', context)

@login_required
def NewLostPost(request):
	user = request.user
	profile = get_object_or_404(Profile,user=user)
	tags_objs = []
	files_objs = []

	if request.method == 'POST':
		form = NewLostPostForm(request.POST, request.FILES)
		if form.is_valid():
			files = request.FILES.getlist('content')
			caption = form.cleaned_data.get('caption')
			geotag = form.cleaned_data.get('geotag')
			tags_form = form.cleaned_data.get('tags')

			tags_list = list(tags_form.split(','))

			for tag in tags_list:
				t, created = Tag.objects.get_or_create(title=tag.strip())
				tags_objs.append(t)

			for file in files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				files_objs.append(file_instance)

			p, created = LostPost.objects.get_or_create(caption=caption, user=user,geotag=geotag)
			p.tags.set(tags_objs)
			p.content.set(files_objs)
			p.save()
			createEmbedding.apply_async(args=[p.id],kwargs={'found':False,'field_name':'embedding'})

			## UPON CREATED, REDIRECT TO LOST POST DETAIL
			url = reverse('post:lostpostdetails',kwargs={'post_id':p.id})
			return redirect(url)
	else:
		form = NewLostPostForm()

	context = {
		'form':form,
		'profile':profile,
		'requesting_profile':profile
	}

	return render(request, 'newlostpost.html', context)


@login_required
def NewFunctionPost(request,option):
	user = request.user
	profile = get_object_or_404(Profile,user=user)

	if request.method == 'POST':
		if option=='lost':
			form = NewLostPostForm(request.POST, request.FILES)
		else:
			form = NewFoundPostForm(request.POST, request.FILES)

		if form.is_valid():
			files = request.FILES.getlist('content')
			caption = form.cleaned_data.get('caption')
			geotag = form.cleaned_data.get('geotag')
			tags_form = form.cleaned_data.get('tags')
			tags_list = list(tags_form.split(','))

			if option=='lost':
				post = LostPost.objects.create(caption=caption, user=user,geotag=geotag)
			else:
				post = FoundPost.objects.create(caption=caption, user=user,geotag=geotag)

			for tag in tags_list:
				slug = slugify(tag)
				tag, created = Tag.objects.get_or_create(slug=slug)
				if created:
					tag.title = tag.strip()
				post.tags.add(tag)

			for file in files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				post.content.add(file_instance)

			if option == 'lost':
				createEmbedding.apply_async(args=[post.id],kwargs={'found':False,'field_name':'embedding'})
				url = reverse('post:lostpostdetails',kwargs={'post_id':post.id})
			else:
				createEmbedding.apply_async(args=[post.id],kwargs={'found':True,'field_name':'embedding'})
				url = reverse('post:postdetails',kwargs={'post_id':post.id})

			## UPON CREATED, REDIRECT TO LOST POST DETAIL
			
			return redirect(url)
	else:
		form = NewLostPostForm()

	context = {
		'type':option,
		'form':form,
		'profile':profile,
		'requesting_profile':profile
	}

	return render(request, 'newlostpost.html', context)

def LostPostDetails(request, post_id):
	post = get_object_or_404(LostPost, id=post_id)
	user = request.user
	owner = post.user
	profile = get_object_or_404(Profile,user = request.user)
	#comment
	comments = Comment.objects.filter(post=post).order_by('date')
	
	if request.user.is_authenticated:
		profile = Profile.objects.get(user=request.user)
		#For the color of the favorite button

		# if profile.favorites.filter(id=post_id).exists():
		# 	favorited = True

	# ONLY OWNER OF POST ALLOW TO SEE RUN BUTTON
	if user == owner:
		check = True
	else:
		check = False
	#Comments Form
	if request.method == 'POST':
		form = CommentForm(request.POST)
		if form.is_valid():
			comment = form.save(commit=False)
			comment.post = post
			comment.user = user
			comment.save()
			return HttpResponseRedirect(reverse('lost-post-detail', args=[post_id]))
	else:
		form = CommentForm()


	template = loader.get_template('lostpost_detail.html')

	context = {
		'post':post,
		'profile':profile,
		'form':form,
		'comments':comments,
		'requesting_profile':profile,
		'check':check,
		'post_id':post_id

	}

	return HttpResponse(template.render(context, request))


@login_required
@require_GET
def findSimilar(request,post_id):
	#	ONLY USER WHO CREATED THE LOST POST IS ALLOWED TO RUN SIMILAR TASK
	post = get_object_or_404(LostPost,id=post_id)
	if request.user != post.user:
		return render(request,'test.html',{'error':"You do not have access"})


	task = matchCat.apply_async(args=[post_id],kwargs={'in_batch':False})

	while True:
		state = AsyncResult(task.id).state
		if state == 'SUCCESS':
			# Retrieve the posts with the corresponding IDs
			matched_candidate = CandidateMatch.objects.filter(user=request.user,lostpost=post).latest('created')
			similar_posts = matched_candidate.matched.all()
			return JsonResponse({
			'similar_posts':[
				{'id':post.id,'url':post.get_compare_url(post_id)} 
				for post in similar_posts
			]
		})
			# create a notification
			# CREATE A NOTIFICATION FOR USER
	
		time.sleep(1)  # Wait for a second before checking again

def tags(request, tag_slug):
	tag = get_object_or_404(Tag, slug=tag_slug)
	posts = Post.objects.filter(tags=tag).order_by('-posted')

	template = loader.get_template('tag.html')

	context = {
		'posts':posts,
		'tag':tag,
	}

	return HttpResponse(template.render(context, request))



@login_required
@require_POST
def like(request, post_id):
	"""
	When a user is already logged in, allow them to like a post
	user - user
	post_id: id of the post the user wants to like
	"""
	user = request.user
	post = Post.objects.get(id=post_id)
	current_likes = post.likes
	liked = Likes.objects.filter(user=user, post=post).count()

	if not liked:
		like = Likes.objects.create(user=user, post=post)
		#like.save()
		current_likes = current_likes + 1
		status = 'liked'

	else:
		Likes.objects.filter(user=user, post=post).delete()
		current_likes = current_likes - 1
		status = 'unliked'

	post.likes = current_likes
	post.save()

	return JsonResponse({'likes':post.likes,'status':status})

@login_required
def favorite(request, post_id):
	user = request.user
	post = Post.objects.get(id=post_id)
	profile = Profile.objects.get(user=user)

	if profile.favorites.filter(id=post_id).exists():
		profile.favorites.remove(post)

	else:
		profile.favorites.add(post)

	return HttpResponseRedirect(reverse('postdetails', args=[post_id]))



class FunctionNewFeed(TemplateView):
	template_name = "function_post.html"
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		type = self.kwargs.get('type')
		if type == 'lost':
			post_items = LostPost.objects.all().order_by('posted')
		else:
			post_items = FoundPost.objects.all().order_by('posted')
		
		profile = get_object_or_404(Profile,user=self.request.user)

		context.update({
			'post_items':post_items,
			'requesting_profile':profile
		})

		return context
	@classmethod
	def as_view(cls,**initkwargs):
		view = super().as_view(**initkwargs)
		view.initkwargs = initkwargs
		return view
    		

@login_required()
def comparison(request,lost_id,found_id):

	lost = get_object_or_404(LostPost,id=lost_id)
	found = get_object_or_404(FoundPost,id=found_id)
	posts = [lost,found]

	profile = get_object_or_404(Profile,user=request.user)

	if request.method == 'POST':
		is_matched = request.POST('is_matched')
		if is_matched == 'yes':
			lost.is_found = True
			found.is_matched = True
			messages.success(request,"Posts have been marked as matched!.")

			# redirect user to inbox to the owner of foundpost
			# system send notification to onwer of foundpost, at the same time, create a chat room for two people
			


	context = {'posts':posts, 'requesting_profile':profile}
	return render(request,'comparison.html',context)

def searchBar(request):
	# not login required
    query = request.GET.get('q', '')
    category = request.GET.get('category', 'people')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if category == 'people':
        results = Profile.objects.filter(
            Q(user__name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    elif category == 'post':
        results = Post.objects.filter(caption__icontains=query)
    elif category == 'lostpost':
        results = LostPost.objects.filter(caption__icontains=query)
    elif category == 'foundpost':
        results = FoundPost.objects.filter(caption__icontains=query)
    else:
        results = []

    if start_date and end_date and category != 'people':
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        results = results.filter(created_at__range=[start_date, end_date])

    paginator = Paginator(results, 10)  # Show 10 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'category': category,
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'explore.html', context)