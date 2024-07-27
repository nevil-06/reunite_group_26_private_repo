from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, ItemForm
from .models import (
    Item,
    OrderItem,
    Order,
    BillingAddress,
    Coupon,
    Category,
)
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from .models import Item
from django.shortcuts import render
from django.views import View
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from .forms import ContactForm
from django.shortcuts import render
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class PaymentView(View):
    def get(self, *args, **kwargs):
        # order
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {"order": order, "DISPLAY_COUPON_FORM": False}
            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "u have not added a billing address")
            return redirect("core:checkout")


class HomeView(ListView):
    template_name = "index.html"
    queryset = Item.objects.filter(is_active=True)
    context_object_name = "items"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {"object": order}
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")


class ShopView(ListView):
    model = Item
    paginate_by = 6
    template_name = "shop.html"


class AboutUsView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "about.html")


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("core:login")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("core:home")  # Redirect to home page or dashboard
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("core:login")


class ContactUsView(View):
    def get(self, request, *args, **kwargs):
        form = ContactForm()
        return render(request, "contact.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            message = form.cleaned_data["message"]
            # Send email
            send_mail(
                f"Message from {name} ({email})",
                message,
                email,
                [settings.CONTACT_EMAIL],  # Replace with your email
            )
            return HttpResponseRedirect("/contact/success/")
        return render(request, "contact.html", {"form": form})


class ItemDetailView(DetailView):
    model = Item
    template_name = "product-detail.html"

    def get(self, request, *args, **kwargs):
        # Call the parent get method
        response = super().get(request, *args, **kwargs)

        # Get the existing list of viewed products from the cookie
        viewed_products = request.COOKIES.get("viewed_products")

        # If the cookie exists, load the product list from the cookie
        if viewed_products is not None:
            viewed_products = viewed_products.split()
        else:
            # If the cookie doesn't exist, start a new list
            viewed_products = []

        # Add the current product ID to the list

        viewed_products.append(self.object.id)

        # Store the updated product list in the cookie
        # response = HttpResponse("Product page")
        response.set_cookie(
            "viewed_products", " ".join(str(i) + " " for i in viewed_products)
        )

        return response


class CategoryView(View):
    def get(self, *args, **kwargs):
        category = Category.objects.get(slug=self.kwargs["slug"])
        item = Item.objects.filter(category=category, is_active=True)
        context = {
            "object_list": item,
            "category_title": category,
            "category_description": category.description,
            "category_image": category.image,
        }
        return render(self.request, "category.html", context)


def search(request):
    query = request.GET.get("q")
    sorting = request.GET.get("sorting")
    results = []

    if query:
        results = Item.objects.filter(
            Q(title__icontains=query)
            | Q(description_short__icontains=query)
            | Q(description_long__icontains=query)
            | Q(author__icontains=query)
            | Q(book_category__icontains=query)
            | Q(color__icontains=query) & ~Q(color="")
            | Q(size__icontains=query)
            | Q(category__title__icontains=query)
        ).distinct()

        if sorting == "price_asc":
            results = results.order_by("price")
        elif sorting == "price_desc":
            results = results.order_by("-price")

        print(f"Query: {query}")
        print(f"Results count: {results.count()}")

    context = {
        "results": results,
        "query": query,
        "sorting": sorting,
    }
    return render(request, "search_results.html", context)


def history_view(request):
    # Get the product list from the cookie
    viewed_products = request.COOKIES.get("viewed_products")

    if viewed_products is not None:
        # Convert the space-separated string back into a list
        viewed_products = viewed_products.split()

        # Retrieve the Item objects for the product IDs
        items = Item.objects.filter(id__in=viewed_products)
    else:
        # If the cookie doesn't exist, display a message
        items = None

    return render(request, "history.html", {"items": items})


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                "form": form,
                "couponform": CouponForm(),
                "order": order,
                "DISPLAY_COUPON_FORM": True,
            }
            return render(self.request, "checkout.html", context)

        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            print(self.request.POST)
            if form.is_valid():
                street_address = form.cleaned_data.get("street_address")
                apartment_address = form.cleaned_data.get("apartment_address")
                country = form.cleaned_data.get("country")
                zip = form.cleaned_data.get("zip")
                # add functionality for these fields
                # same_shipping_address = form.cleaned_data.get(
                #     'same_shipping_address')
                # save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get("payment_option")
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                    address_type="B",
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()

                # add redirect to the selected payment option
                if payment_option == "S":
                    return redirect("core:payment", payment_option="stripe")
                elif payment_option == "P":
                    return redirect("core:payment", payment_option="paypal")
                else:
                    messages.warning(self.request, "Invalid payment option select")
                    return redirect("core:checkout")
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("core:order-summary")


@login_required(
    login_url="/login/"
)  # Ensure user is redirected to login if not authenticated
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item, user=request.user, ordered=False
    )

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item qty was updated.")
        else:
            order.items.add(order_item)
            messages.info(request, "Item was added to your cart.")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "Item was added to your cart.")

    return redirect("core:order-summary")


@login_required(login_url="/login/")
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item, user=request.user, ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "Item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            # add a message saying the user dosent have an order
            messages.info(request, "Item was not in your cart.")
            return redirect("core:product", slug=slug)
    else:
        # add a message saying the user dosent have an order
        messages.info(request, "u don't have an active order.")
        return redirect("core:product", slug=slug)
    return redirect("core:product", slug=slug)


@login_required(login_url="/login/")
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item, user=request.user, ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item qty was updated.")
            return redirect("core:order-summary")
        else:
            # add a message saying the user dosent have an order
            messages.info(request, "Item was not in your cart.")
            return redirect("core:product", slug=slug)
    else:
        # add a message saying the user dosent have an order
        messages.info(request, "u don't have an active order.")
        return redirect("core:product", slug=slug)
    return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get("code")
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")

            except ObjectDoesNotExist:
                messages.info(request, "You do not have an active order")
                return redirect("core:checkout")


def history_view(request):
    # Get the product list from the cookie
    viewed_products = request.COOKIES.get("viewed_products")

    if viewed_products is not None:
        # Convert the space-separated string back into a list
        viewed_products = viewed_products.split()

        # Retrieve the Item objects for the product IDs
        items = Item.objects.filter(id__in=viewed_products)
    else:
        # If the cookie doesn't exist, display a message
        items = None

    # Get the user's visit history from the session
    visit_history = request.session.get("visit_history", {})

    # Get the currently logged-in user
    current_user = request.user if request.user.is_authenticated else None

    # Get the count of active users
    authenticated_users_count = User.objects.filter(is_active=True).count()

    return render(
        request,
        "history.html",
        {
            "items": items,
            "visit_history": visit_history,
            "current_user": current_user,
            "authenticated_users_count": authenticated_users_count,
        },
    )


@login_required(login_url='/login/')
def list_item(request):
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect(
                "core:success"
            )  # Redirect to a success page or wherever you want
    else:
        form = ItemForm()
    return render(request, "list_item.html", {"form": form})


def success(request):
    return render(request, "success.html")


def password_reset(request):
    if request.method == "POST":
        username = request.POST.get("username")
        new_password = request.POST.get("new_password")

        # Validate input
        if not username or not new_password:
            messages.error(request, "Please provide both username and new password.")
            return render(request, "password_reset.html")

        # Get the user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "User with this username does not exist.")
            return render(request, "password_reset.html")

        # Update password
        user.password = make_password(new_password)
        user.save()

        messages.success(request, "Your password has been successfully reset.")
        return redirect("core:login")

    return render(request, "password_reset.html")
