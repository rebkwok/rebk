from django import forms
from django.forms.models import modelformset_factory, BaseModelFormSet, \
    inlineformset_factory, formset_factory, BaseFormSet, BaseInlineFormSet

from floppyforms import ClearableFileInput

from gallery.models import Category, Image


class ImageThumbnailFileInput(ClearableFileInput):
    template_name = 'gallery/image_thumbnail.html'


class CategoriesBaseFormSet(BaseModelFormSet):

    def add_fields(self, form, index):
        super(CategoriesBaseFormSet, self).add_fields(form, index)

        if form.instance.id:
            delete_class = 'delete-checkbox'
        else:
            delete_class = 'hide'

        form.fields['DELETE'] = forms.BooleanField(
            widget=forms.CheckboxInput(attrs={
                'class': delete_class,
                'id': 'DELETE_{}'.format(index)
            }),
            required=False
        )
        form.DELETE_id = 'DELETE_{}'.format(index)

        form.image_count = form.instance.images.count()

        form.fields['name'] = forms.CharField(
            widget=forms.TextInput(
                attrs={'class': 'form-control'}
            )
        )


        form.fields['description'] = forms.CharField(
            widget=forms.Textarea(
                attrs={'class': 'form-control', 'rows': 1}
            ),
            required=False
        )

CategoriesFormset = modelformset_factory(
    Category,
    fields=('id', 'name', 'description'),
    formset=CategoriesBaseFormSet,
    extra=1,
    can_delete=True
)

class ImageBaseFormset(BaseInlineFormSet):

    def add_fields(self, form, index):
        super(ImageBaseFormset, self).add_fields(form, index)

        if form.instance.id:
            form.fields['DELETE'] = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={
                    'class': 'delete-checkbox',
                    'id': 'DELETE_{}'.format(index)
                }),
                required=False,
                help_text="Tick box and click Save to delete this image"
            )
            form.DELETE_id = 'DELETE_{}'.format(index)

        form.fields['photo'] = forms.ImageField(
            label='',
            error_messages={'invalid': "Image files only"},
            widget=ImageThumbnailFileInput,
            required=False
        )

        form.fields['caption'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            required=False
        )


ImageFormset = inlineformset_factory(
    Category,
    Image,
    formset=ImageBaseFormset,
    fields=('photo', 'caption'),
    can_delete=True,
    extra=3,
)


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = ('name', 'description')

