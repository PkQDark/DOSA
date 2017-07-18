from django import forms
from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = {'name', 'comment'}
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название', 'maxlength': 100}),
                   'comment': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Комментарий'})}


class AddIDForm(forms.Form):
    key_file = forms.FileField(label='', required=False)


class AddSystemUserForm(forms.Form):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control',
                                                               'required': True, 'maxlength': 30}),
                                 max_length=30)
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control',
                                                              'required': True, 'maxlength': 30}),
                                max_length=30)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'required': True}))