from django.shortcuts import render, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.utils.datastructures import MultiValueDictKeyError
from django.contrib.auth.forms import UserCreationForm

from .models import Company, Device, CompanyUser
from .forms import CompanyForm, AddIDForm, AddSystemUserForm, DeviceForm


@user_passes_test(lambda u: u.is_superuser)
def device_list(request):
    cur_user = request.user.username
    devs = Device.objects.all()
    return render(request, 'local_admin/devices_list.html', {'devices': devs, 'cur_user': cur_user})


@user_passes_test(lambda u: u.is_superuser)
def edit_device(request, dev_id):
    cur_user = request.user.username
    cur_dev = Device.objects.get(id=dev_id)
    if request.method == 'POST':
        edit_form = DeviceForm(request.POST, instance=cur_dev)
        if edit_form.is_valid():
            edit_form.save()
    else:
        edit_form = DeviceForm(instance=cur_dev)
    return render(request, 'local_admin/device_edit.html', {'edit_form': edit_form, 'cur_user': cur_user})



@user_passes_test(lambda u: u.is_superuser)
def companies_list(request):
    cur_user = request.user.username
    company_name = ''
    if request.GET.get('company'):
        company_name = request.GET.get('company')
    companies = Company.objects.filter(name__icontains=company_name)
    c_active = request.POST.get('company_stop')
    if c_active:
        c = Company.objects.get(id=c_active)
        c.active = not c.active
        c.save()
    return render(request, 'local_admin/companies_list.html', {'companies': companies, 'cur_user': cur_user})


@user_passes_test(lambda u: u.is_superuser)
def add_company_view(request):
    cur_user = request.user.username
    if request.method == 'POST':
        add_company = CompanyForm(request.POST)
        add_devs = AddIDForm(request.POST, request.FILES)
        if add_company.is_valid():
            new_company = add_company.save()
            messages.add_message(request, messages.SUCCESS, 'Компания успешно зарегистрирована.')
            try:
                dev_doc = request.FILES['key_file'].read().decode().split()
                dev_disc = {}
                for i in range(len(dev_doc) - 1):
                    if i % 2 == 1:
                        continue
                    dev_disc[dev_doc[i]] = int(dev_doc[i + 1])
                dev_counter = 0
                for dev in dev_disc:
                    new_dev, created = Device.objects.get_or_create(dev_id=dev, port=dev_disc.get(dev), defaults={'company': new_company})
                    if created:
                        dev_counter += 1
                    else:
                        messages.add_message(request, messages.ERROR, 'Устройство ' + dev + ' уже существует в БД.')
                messages.add_message(request, messages.INFO,
                                     'Добавлено ' + str(dev_counter) + ' устройств из ' + str(len(dev_doc)) + '.')
            except MultiValueDictKeyError:
                add_devs = AddIDForm()
    else:
        add_company = CompanyForm()
        add_devs = AddIDForm()
    return render(request, 'local_admin/company_add.html',
                  {'cur_user': cur_user, 'add_company': add_company, 'add_devs': add_devs})


@user_passes_test(lambda u: u.is_superuser)
def edit_company_view(request, company_id):
    cur_user = request.user.username
    cur_com = Company.objects.get(id=company_id)
    if request.method == 'POST':
        edit_company = CompanyForm(request.POST, instance=cur_com)
        add_devs = AddIDForm(request.POST, request.FILES)
        if edit_company.is_valid():
            try:
                dev_doc = request.FILES['key_file'].read().decode().split()
                dev_disc = {}
                for i in range(len(dev_doc) - 1):
                    if i % 2 == 1:
                        continue
                    dev_disc[dev_doc[i]] = int(dev_doc[i + 1])
                dev_counter = 0
                for dev in dev_disc:
                    new_dev, created = Device.objects.get_or_create(dev_id=dev, port=dev_disc.get(dev), defaults={'company': cur_com})
                    if created:
                        dev_counter += 1
                    else:
                        messages.add_message(request, messages.ERROR, 'Устройство ' + dev + ' уже существует в БД.')
                messages.add_message(request, messages.INFO,
                                     'Добавлено ' + str(dev_counter) + ' устройств из ' + str(len(dev_doc)) + '.')
            except MultiValueDictKeyError:
                add_devs = AddIDForm()
            if edit_company.cleaned_data['comment']:
                cur_com.comment = edit_company.cleaned_data['comment']
                messages.add_message(request, messages.SUCCESS, 'Комментарий успешно изменен.')
        cur_com.save()
    else:
        edit_company = CompanyForm(instance=cur_com)
        add_devs = AddIDForm()
    return render(request, 'local_admin/company_edit.html',
                  {'cur_user': cur_user, 'edit_company': edit_company, 'add_devs': add_devs, 'company': cur_com.name})


@user_passes_test(lambda u: u.is_superuser)
def add_local_admin(request, company_id):
    cur_com = Company.objects.get(id=company_id)
    if request.method == 'POST':
        general = UserCreationForm(request.POST)
        additional = AddSystemUserForm(request.POST)
        if general.is_valid() and additional.is_valid():
            e_mail = additional.cleaned_data['email']
            try:
                User.objects.get(email=e_mail)
                messages.add_message(request, messages.ERROR,
                                     'Пользователь с почтовым ящиком ' + e_mail + ' уже зарегистрирован')
            except User.DoesNotExist:
                user = general.save()
                user.first_name = additional.cleaned_data['first_name']
                user.last_name = additional.cleaned_data['last_name']
                user.email = e_mail
                user.is_staff = True
                user.save()
                CompanyUser.objects.create(user=user, company=cur_com)
                messages.add_message(request, messages.SUCCESS,
                                     'Пользователь успешно зарегистрирован')
                return HttpResponseRedirect('/admin/local-admins/')
    else:
        general = UserCreationForm()
        additional = AddSystemUserForm()
    return render(request, 'local_admin/la_add.html',
                  {'general': general, 'additional': additional, 'cur_user': request.user.username,
                   'company': cur_com.name})


@user_passes_test(lambda u: u.is_superuser)
def local_admin_list(request):
    cur_user = request.user.username
    last_name = ''
    company = ''
    if request.GET.get('last_name'):
        last_name = request.GET.get('last_name')
    if request.GET.get('company'):
        company = request.GET.get('company')
    local_admins = CompanyUser.objects.filter(user__last_name__icontains=last_name,
                                              company__name__icontains=company,
                                              user__is_staff=True)
    disable = request.POST.get('la_name')
    if disable:
        dis_la = User.objects.get(username=disable)
        dis_la.is_active = False
        dis_la.save()
        return HttpResponseRedirect('/admin/')
    return render(request, 'local_admin/la_list.html', {'admins': local_admins, 'cur_user': cur_user})