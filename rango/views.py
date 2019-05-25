from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views import View
from django.utils.decorators import method_decorator

from datetime import datetime

from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from rango.bing_search import run_query, read_bing_key


def index(request):
    request.session.set_test_cookie()
    # Query the database for a list of All categories currently stored.
    # Order the categores by the number of likes in descending order.
    # Retrieve the top 5 only -- or all if less than 5.
    # Place the list in our context_dict dictionary (with our boldmessage!)
    # that will be passed to the template engine
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]

    context_dict = {}
    context_dict['boldmessage'] = 'Crunch, creamy, cookie, candy, cupcake!'
    context_dict['categories'] = category_list
    context_dict['pages'] = page_list

    # Call the helper function to handle the cookies
    visitor_cookie_handler(request)
    context_dict['visits'] = request.session['visits']
    # Return the response back to the user, updating any cookies that need changed.
    return render(request, 'rango/index.html', context_dict)


def about(request):
    # Call the helper function to handle the cookies
    visitor_cookie_handler(request)
    context_dict = {}
    context_dict['visits'] = request.session['visits']
    return render(request, 'rango/about.html', context_dict)


class AboutView(View):
    def get(self, request):
        # view logic
        visitor_cookie_handler(request)
        return render(request, 'rango/about.html', context={'visits': request.session['visits']})


def show_category(request, category_name_slug):
    # Create a context dictionary which we canpass
    # to the template rendering engine
    context_dict = {}

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the get() method raises a DoesNotExist exception.
        # So the get() method returns one model instance or raises an exception
        category = Category.objects.get(slug=category_name_slug)
        context_dict['query'] = category.name
        # Retrieve all of the associated pages
        # Note that filter() will return a list of page objects or an empty list
        pages = Page.objects.filter(category=category).order_by('-views')

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
    except Category.DoesNotExist:
        # We get here if we didn't find the specified category
        # Don't do anything -
        # the template willdisplay "no category" message for us
        context_dict['category'] = None
        context_dict['pages'] = None

    if request.method == 'POST':
        context_dict['query'] = request.POST['query'].strip()
        if context_dict['query']:
            # Run our Bing function to get the results list
            context_dict['result_list'] = run_query(context_dict['query'])

    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)


@login_required
def add_category(request):
    form = CategoryForm()

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database
            form.save(commit=True)
            # Now that the category is saved
            # We could give a confirmation message
            # But since the most recent category added is on the index page
            # Then we can direct the user back to the index page.
            return index(request)
        else:
            # The supplied form contained errors -
            # jsut print them to the terminal.
            print(form.errors)
    # Will handle the bad form, new form, or no form supplied cases
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})


class AddCategoryView(View):

    @method_decorator(login_required)
    def get(self, request):
        form = CategoryForm()
        return render(request, 'rango/add_category.html', {'form': form})

    @method_decorator(login_required)
    def post(self, request):
        form = CategoryForm()
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print(form.errors)
        return render(request, 'rango/add_category.html', {'form': form})


@login_required
def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    form = PageForm()
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()
                return show_category(request, category_name_slug)
        else:
            print(form.errors)

    context_dict = {'form': form, 'category': category}
    return render(request, 'rango/add_page.html', context_dict)


@login_required
def restricted(request):
    return render(request, 'rango/restricted.html')


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    # Get the number of visits to the site.
    # WE use the COOKIES.get() function to obtain the visits cookie.
    # If the cookie exists, the value returned is casted to an integer.
    # If the cookie doesn't exist, then teh default value of 1 is used.
    visits = int(get_server_side_cookie(request, 'visits', '1'))

    last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')

    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        # Set the last visit cookie
        request.session['last_visit'] = last_visit_cookie

    # Update/set the visit cookie
    request.session['visits'] = visits


def search(request):
    result_list = []
    query = ''

    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
            # Run our Bing function to get the results list
            result_list = run_query(query)

    return render(request, 'rango/search.html', {'result_list': result_list, 'query': query})


def goto_url(request):
    page_id = None
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(pk=page_id)
                page.views += 1
                page.save()
                return redirect(page.url)
            except:
                pass
    return redirect(reverse('rango:index'))


@login_required
def register_profile(request):
    form = UserProfileForm()

    # A HTTP POST?
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()
            return redirect('rango:index')
        else:
            print(form.errors)
    return render(request, 'rango/profile_registration.html', {'form': form})


@login_required
def profile(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('index')

    userprofile = UserProfile.objects.get_or_create(user=user)[0]
    form = UserProfileForm(
        {'website': userprofile.website, 'picture': userprofile.picture})

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if form.is_valid():
            form.save(commit=True)
            return redirect('rango:profile', user.username)
        else:
            print(form.errors)

    return render(request, 'rango/profile.html',
        {'userprofile': userprofile, 'selecteduser': user, 'form': form})


class ProfileView(View):

    def get_user_details(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return redirect('index')

        userprofile = UserProfile.objects.get_or_create(user=user)[0]
        form = UserProfileForm({'website': userprofile.website, 'picture': userprofile.picture})
        return (user, userprofile, form)

    @method_decorator(login_required)
    def get(self, request, username):
        (user, userprofile, form) = self.get_user_details(username)
        return render(request, 'rango/profile.html', {'userprofile': userprofile, 'selecteduser': user, 'form': form})

    @method_decorator(login_required)
    def post(self, request, username):
        (user, userprofile, form) = self.get_user_details(username)
        form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if form.is_valid():
            form.save(commit=True)
            return redirect('profile', user.username)
        else:
            print(form.errors)
        return render(request, 'rango/profile.html', {'userprofile': userprofile, 'selecteduser': user, 'form': form})


def list_profiles(request):
    users = UserProfile.objects.all()
    return render(request, 'rango/list_profiles.html', {'users':users})
