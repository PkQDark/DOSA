from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.forms.formsets import BaseFormSet

from .models import KeyOwner, Cistern


class EditKeyOwnerForm(ModelForm):
    class Meta:
        model = KeyOwner
        fields = {'name', 'car', 'keys', 'comment'}
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 40}),
                   'car': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 40}),
                   'keys': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 16, 'readonly': True}),
                   'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'cols': 50})}

    def __init__(self, *args, **kwargs):
        super(EditKeyOwnerForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = False
        self.fields['car'].required = False
        self.fields['comment'].required = False


class EditDjangoUserForm(ModelForm):
    class Meta:
        model = User
        fields = {'first_name', 'last_name', 'email'}
        widgets = {'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                   'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                   'email': forms.EmailInput(attrs={'class': 'form-control'})}


class FuelForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': 40,
                                                         'placeholder': 'Тип'}),
                           max_length=40)
    comment = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Комментарий',
                                                           'rows': 2}),
                              required=False)


class BaseFuelFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        types = []
        duplicates = False
        for form in self.forms:
            if form.cleaned_data:
                name = form.cleaned_data['name']
                if name in types:
                    duplicates = True
                types.append(name)
                if duplicates:
                    raise forms.ValidationError(
                        'Типы топлива должны быть уникальны',
                        code='duplicate_types'
                    )


class CisternForm(ModelForm):
    class Meta:
        model = Cistern
        fields = {'start_volume', 'max_volume', 'cistern_type', 'name'}
        widgets = {'start_volume': forms.NumberInput(attrs={'class': 'form-control'}),
                   'max_volume': forms.NumberInput(attrs={'class': 'form-control'}),
                   'cistern_type': forms.Select(attrs={'class': 'form-control'}),
                   'name': forms.TextInput(attrs={'class': 'form-control'})}


class AddUpDosedForm(forms.Form):
    volume = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
                                max_digits=7, decimal_places=2, required=False)
    comment = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control'}), required=False)


class DateFilter(forms.Form):
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker form-control',
                                                               'placeholder': 'с даты'}),
                                 input_formats=('%d.%m.%Y', '%Y-%m-%d'), required=False)
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker form-control',
                                                             'placeholder': 'по дату'}),
                               input_formats=('%d.%m.%Y', '%Y-%m-%d'), required=False)


class LimitsForm(forms.Form):
    day_limit = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}),
                                   max_digits=7, decimal_places=2, min_value=0.0, required=False)
    week_limit = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}),
                                    max_digits=7, decimal_places=2, min_value=0.0, required=False)
    month_limit = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}),
                                     max_digits=7, decimal_places=2, min_value=0.0, required=False)
