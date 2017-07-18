from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm


def login_user(request):
    if request.user.is_authenticated():
        if request.user.is_superuser:
            return HttpResponseRedirect('/admin/')
        elif request.user.is_staff:
            return HttpResponseRedirect('/local-admin/')
        else:
            return HttpResponseRedirect('/user/')
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        cur_user = authenticate(username=username, password=password)
        if cur_user is not None:
            if cur_user.is_active:
                login(request, cur_user)
                if cur_user.is_superuser:
                    return HttpResponseRedirect('/admin/')
                elif cur_user.is_staff:
                    return HttpResponseRedirect('/local-admin/')
                else:
                    return HttpResponseRedirect('/user/')
            else:
                messages.add_message(request, messages.ERROR, 'Пользователь неактивен.')
        else:
            messages.add_message(request, messages.ERROR, 'Неверный логин/пароль.')
    return render(request, 'main/index.html')


def logout_user(request):
    logout(request)
    return HttpResponseRedirect('/')


# Смена пароля
@login_required
def change_user_passwd(request):
    if request.method == 'POST':
        change_passwd = PasswordChangeForm(user=request.user, data=request.POST)
        if change_passwd.is_valid():
            change_passwd.save()
            messages.add_message(request, messages.SUCCESS, 'Ваш пароль успешно изменен.')
            return HttpResponseRedirect('/')
    else:
        change_passwd = PasswordChangeForm(user=request.user)
    return render(request, 'main/edit_pw.html', {'change_passwd': change_passwd})
