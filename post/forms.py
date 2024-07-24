from django import forms
from post.models import Post, LostPost,FoundPost,PostFileContent
from authy.models import Cat


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class NewPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)
	caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'input is-medium'}), required=True)
	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	
	class Meta:
		model = Post
		fields = ('content', 'caption', 'tags')


class NewLostPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)
	caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'input is-medium'}), required=True)
	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	class Meta:
		model = LostPost
		fields = ('content', 'caption', 'tags','geotag')
            

class NewFoundPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)
	caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'input is-medium'}), required=True)
	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	class Meta:
		model = FoundPost
		fields = ('content', 'caption', 'tags','geotag')

class PostCreateWithImagesForm(forms.ModelForm):
	caption = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...'}),
		max_length=1500,
		required=True,
	)

	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
	content = MultipleFileField(
		label='Add images to your post',
		required=True
	)

    # cats = forms.ModelMultipleChoiceField(
    #     queryset = Cat.objects.none(),
    #     widget=forms.SelectMultiple(attrs={
    #         'class': 'form-control',
    #         'style': 'width: 100%; display: inline-block;'
    #     }),
    #     required=False,  # Making cats optional
    #     help_text="Optional: Select cats to associate with this post."
    # )
    
	cats = forms.ModelMultipleChoiceField(
		queryset = Cat.objects.none(),
		widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'style': 'width: 100%; display: inline-block;'
        }),
		required=False,  # Making cats optional
		help_text="Optional: Select cats to associate with this post."
	)

	class Meta:
		model = Post
		fields = ['caption', 'tags','cats','content']
    
	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user', None)
		super(PostCreateWithImagesForm, self).__init__(*args, **kwargs)
		if user is not None:
			self.fields['cats'].queryset = Cat.objects.filter(user=user)


	def clean(self):
		cleaned_data = super().clean()
		content = self.files.get('content')
		caption = cleaned_data.get('caption')
		cats = cleaned_data.get('cats')

		if not content:
			raise forms.ValidationError("Please upload at least one image.")
		
		if not caption and not cats:
			raise forms.ValidationError("Please provide either a caption or select at least one cat.")

		return cleaned_data

    # def save(self, commit=True, user=None):
    #     post = super().save(commit=False)
    #     post.user = user
    #     if commit:
    #         post.save()
    #         self.save_m2m()  # Save tags

    #     # Save images
    #     for file in self.files.getlist('images'):
    #         image_content = PostFileContent.objects.create(user=user, file=file)
    #         post.content.add(image_content)

    #     if self.cleaned_data['cats']:
    #         post.cats.set(self.cleaned_data['cats'])

    #     return post
    