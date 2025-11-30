from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Room, UserProfile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-input'})


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'avatar': forms.FileInput(attrs={'class': 'form-input'}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'description', 'room_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Room name'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'Room description'}),
            'room_type': forms.Select(attrs={'class': 'form-input'}),
        }
