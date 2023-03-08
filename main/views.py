from re import T
from django.http import HttpResponse, HttpResponseRedirect
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import get_template, render_to_string
from django.template import Context
from django.contrib.auth.models import User
from django.core.mail import EmailMessage

from predicts.models import Predicts
from .forms import UserRegisterForm
from .token import account_activation_token
from .models import Router

# Import mimetypes module
import mimetypes
# import os module
import os
# Import HttpResponse module
# from django.http.response import HttpResponse

# Create your views here.

def resume(request):
    pdffile =  Router.objects.last()
    return render(request, 'main/pdffile.html', context={'pdffile':pdffile})

def home(response):
    return render(response, "main/home.html", {})

def about(response):
    return render(response, "main/about.html", {})

def reports(response):
    # Define Django project base directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Define the full file path
    path = BASE_DIR + '/perfreports/Files/'
    file_list = sorted(os.listdir(path))
    print('reports(): ', file_list)
    return render(response, "main/reports.html", {'items': file_list})

def volreports(response):
    # Define Django project base directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Define the full file path

    path = BASE_DIR + '/perfreports/etf_list/'
    etf_list = sorted(os.listdir(path))
    path = BASE_DIR + '/perfreports/stock_list/'
    stock_list = sorted(os.listdir(path))
    path = BASE_DIR + '/perfreports/us-cn_stock_list/'
    cn_stock_list = sorted(os.listdir(path))
    context = {"etf_list":etf_list, "stock_list":stock_list, "cn_stock_list": cn_stock_list}
    print(f'volreports:  {context}')
    return render(response, "main/volatility.html", context)

def usstockpick(response):
    plist = Predicts.objects.all()
    for item in plist:
        print(item.__str__())
    return render(response, "main/usstockpick.html", {'plist':plist})

########### register here #####################################
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)# Import mimetypes module
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            mail_subject = 'Activation link has been sent to your email id'
            message = render_to_string('main/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            ######################### mail system ####################################
            email = EmailMessage(
                mail_subject, message, to=[to_email], from_email='thomas.choi@neuralmatrixllc.com'
            )
            email.send()
            ##################################################################
            return HttpResponse('Please confirm your email address to complete the registration')
    else:
        form = UserRegisterForm()
    return render(request, 'main/register.html', {'form': form, 'title':'reqister here'})

    ################ login forms###################################################
def Login(request):
    if request.method == 'POST':

        # AuthenticationForm_can_also_be_used__
        print("In View.Login.")
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username = username, password = password)
        if user is not None:
            form = login(request, user)
            messages.success(request, f' wecome {username} !!')
            return redirect('home')
        else:
            messages.info(request, f'account done not exit plz sign in')
    form = AuthenticationForm()
    return render(request, 'main/login.html', {'form':form, 'title':'log in'})

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')

def volatility(request, filename=''):
    print(f'volatility({filename})')
    x= filename.split('-')
    if x[0] == "etf":
        return download_file(request, x[1], f'/perfreports/etf_list/')
    elif x[0] == "us":
        return download_file(request, x[1], f'/perfreports/stock_list/')
    elif x[0] == "cn":
        return download_file(request, x[1], f'/perfreports/us-cn_stock_list/')

def performance(request, filename=''):
    print(f'performance({filename})')
    return download_file(request, filename, '/perfreports/Files/')

def download_file(request, filename='', sub_folder=''):
    if filename != '':
        # Define Django project base directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Define the full file path
        filepath = BASE_DIR + sub_folder + filename
        print('Try to open: ', filepath)
        try:
            response = FileResponse(open(filepath, 'rb'), content_type='application/pdf')
        except FileNotFoundError:
            raise Http404()
        # Return the response value
        return response
    else:
        # Load the template
        return render(request, 'main/reports.html')
