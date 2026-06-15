import os
import uuid
import requests
from datetime import timedelta
import urllib3

# ইনসিকিউর রিকোয়েস্ট ওয়ার্নিং পুরোপুরি ডিজেবল বা বন্ধ করার জন্য:
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage

from django.views.decorators.http import require_POST
from .models import PatientProfile

# PatientProfile মডেলটি এখান থেকে ইম্পোর্ট নিশ্চিত করা হলো
from .models import BedStatus, BedReservation, HospitalName, PatientProfile
from .forms import (
    HospitalRegisterForm,
    PatientRegisterForm,
    EmailLoginForm
)

# ==================== SMART AUTO RELEASE ====================

def check_and_release_expired_beds():
    now = timezone.now()
    expired_reservations = BedReservation.objects.filter(
        expires_at__lt=now,
        status='PENDING'
    )

    for reservation in expired_reservations:
        bed = reservation.bed_status
        if bed.available_beds < bed.total_beds:
            bed.available_beds += 1
            bed.save()

        reservation.status = 'EXPIRED'
        reservation.save()


# ==================== HOME & PORTAL ====================

@login_required
def hospital_list(request):
    check_and_release_expired_beds()
    
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    all_beds = BedStatus.objects.all()

    search_query = request.GET.get('search', '')
    selected_bed_type = request.GET.get('bed_type', '')
    sort_by = request.GET.get('sort_by', '')
    available_only = request.GET.get('available_only', '')

    if search_query:
        all_beds = all_beds.filter(
            Q(hospital__name__icontains=search_query) |
            Q(hospital__location__icontains=search_query)
        )

    if selected_bed_type:
        all_beds = all_beds.filter(bed_type=selected_bed_type)

    if available_only == 'on':
        all_beds = all_beds.filter(available_beds__gt=0)

    if sort_by == 'price_low':
        all_beds = all_beds.order_by('cost_per_day')
    elif sort_by == 'price_high':
        all_beds = all_beds.order_by('-cost_per_day')
    elif sort_by == 'vacant':
        all_beds = all_beds.order_by('-available_beds')

    processed_beds = []
    for bed in all_beds:
        distance_text = "Unknown"
        duration_text = "Unknown"
        sort_key = 999999

        if user_lat and user_lng and bed.hospital.latitude and bed.hospital.longitude:
            try:
                osrm_url = f"http://router.project-osrm.org/route/v1/driving/{user_lng},{user_lat};{bed.hospital.longitude},{bed.hospital.latitude}?overview=false"
                response = requests.get(osrm_url, timeout=3).json()
                
                if response.get('code') == 'Ok':
                    route = response['routes'][0]
                    distance_km = route['distance'] / 1000
                    distance_text = f"{round(distance_km, 1)} km"
                    
                    duration_mins = int(route['duration'] / 60)
                    duration_text = f"{duration_mins} mins"
                    sort_key = distance_km
            except Exception:
                pass

        processed_beds.append({
            'bed': bed,
            'distance': distance_text,
            'duration': duration_text,
            'sort_key': sort_key
        })

    if user_lat and user_lng and not sort_by:
        processed_beds = sorted(processed_beds, key=lambda x: x['sort_key'])

    context = {
        'beds': processed_beds,
        'search_query': search_query,
        'selected_bed_type': selected_bed_type,
        'sort_by': sort_by,
        'available_only': available_only,
    }

    return render(request, 'coreApp/hospital_list.html', context)


@login_required
def hospital_profile(request, hospital_id):
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    hospital = get_object_or_404(HospitalName, id=hospital_id)
    hospital_beds = BedStatus.objects.filter(hospital=hospital)

    context = {
        'hospital': hospital,
        'beds': hospital_beds
    }
    return render(request, 'coreApp/hospital_profile.html', context)


# ==================== AUTH ====================

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = HospitalRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            password = form.cleaned_data.get('password')

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )

            HospitalName.objects.create(
                user=user,
                name=form.cleaned_data.get('hospital_name'),
                location=form.cleaned_data.get('location'),
                contact_number=form.cleaned_data.get('contact_number')
            )

            login(request, user)
            return redirect('dashboard')
    else:
        form = HospitalRegisterForm()

    return render(request, 'coreApp/register.html', {'form': form})


def user_register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PatientRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            password = form.cleaned_data.get('password')
            full_name = form.cleaned_data.get('full_name')
            
            nid = form.cleaned_data.get('nid_number')
            dob = form.cleaned_data.get('date_of_birth')

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )
            user.first_name = full_name
            user.save()

            PatientProfile.objects.create(
                user=user,
                nid_number=nid,
                date_of_birth=dob
            )

            login(request, user)
            return redirect('dashboard')
    else:
        form = PatientRegisterForm()

    return render(request, 'coreApp/user_register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            password = form.cleaned_data.get('password')

            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password
                )

                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    form.add_error('password', 'Wrong password!')
            except User.DoesNotExist:
                form.add_error('email', 'No account found!')
    else:
        form = EmailLoginForm()

    return render(request, 'coreApp/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ==================== STRICT LOCKED DASHBOARDS ====================

@login_required
def dashboard_redirect(request):
    check_and_release_expired_beds()
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')
    else:
        return redirect('user_dashboard')


@login_required
def hospital_dashboard(request):
    check_and_release_expired_beds()

    if not HospitalName.objects.filter(user=request.user).exists():
        return redirect('user_dashboard')

    my_hospital = HospitalName.objects.get(user=request.user)
    my_beds = BedStatus.objects.filter(hospital=my_hospital)

    context = {
        'hospital': my_hospital,
        'beds': my_beds
    }
    return render(request, 'coreApp/hospital_dashboard.html', context)


@login_required
def user_dashboard(request):
    check_and_release_expired_beds()

    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    active_res = BedReservation.objects.filter(
        user=request.user,
        status='PENDING'
    ).select_related('bed_status__hospital').last()

    context = {
        'user': request.user,
        'active_reservation': active_res,
    }
    return render(request, 'coreApp/user_dashboard.html', context)


# ==================== BED INTERACTIVE & CRUD ACTIONS ====================

@login_required
def update_bed_count(request, bed_id, action):
    bed = get_object_or_404(BedStatus, id=bed_id, hospital__user=request.user)
    
    success = False
    if action == 'increase':
        if bed.available_beds < bed.total_beds:
            bed.available_beds += 1
            bed.save()
            success = True
    elif action == 'decrease':
        if bed.available_beds > 0:
            bed.available_beds -= 1
            bed.save()
            success = True
            
    return JsonResponse({
        'success': success,
        'new_count': bed.available_beds,
        'total_beds': bed.total_beds
    })


@login_required
def bed_create(request):
    my_hospital = get_object_or_404(HospitalName, user=request.user)

    if request.method == 'POST':
        BedStatus.objects.create(
            hospital=my_hospital,
            bed_type=request.POST.get('bed_type'),
            total_beds=request.POST.get('total_beds'),
            available_beds=request.POST.get('available_beds'),
            cost_per_day=request.POST.get('cost_per_day')
        )
        return redirect('dashboard')

    return render(request, 'coreApp/bed_form.html', {'hospital': my_hospital, 'title': 'Add Bed'})


@login_required
def bed_update(request, pk):
    bed = get_object_or_404(BedStatus, pk=pk, hospital__user=request.user)

    if request.method == 'POST':
        bed.bed_type = request.POST.get('bed_type')
        bed.total_beds = request.POST.get('total_beds')
        bed.available_beds = request.POST.get('available_beds')
        bed.cost_per_day = request.POST.get('cost_per_day')
        bed.save()
        return redirect('dashboard')

    return render(request, 'coreApp/bed_form.html', {'bed': bed, 'title': 'Update Bed'})


@login_required
def bed_delete(request, pk):
    bed = get_object_or_404(BedStatus, pk=pk, hospital__user=request.user)

    if request.method == 'POST':
        bed.delete()
        return redirect('dashboard')

    return render(request, 'coreApp/bed_confirm_delete.html', {'bed': bed})


# ==================== DYNAMIC SSLCOMMERZ PAYMENT GATEWAY ====================

@login_required
def checkout_payment_view(request, bed_id):
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    check_and_release_expired_beds()
    bed = get_object_or_404(BedStatus, id=bed_id)

    if bed.available_beds < 1:
        return render(request, 'coreApp/error.html', {'message': 'No bed available!'})

    dummy_reservation = BedReservation(bed_status=bed)
    dynamic_booking_fee = dummy_reservation.get_booking_fee

    context = {'bed': bed, 'fee': dynamic_booking_fee}
    return render(request, 'coreApp/checkout_payment.html', context)


@login_required
def reserve_bed_view(request, bed_id):
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    if request.method == 'POST':
        bed = get_object_or_404(BedStatus, id=bed_id)

        if bed.available_beds < 1:
            return render(request, 'coreApp/error.html', {'message': 'No bed available!'})

        if 'medical_document' in request.FILES:
            myfile = request.FILES['medical_document']
            
            if myfile.size > 2 * 1024 * 1024: 
                return render(request, 'coreApp/error.html', {'message': 'ফাইলের সাইজ ২ মেগাবাইটের (2MB) বেশি হওয়া যাবে না!'})
                
            fs = FileSystemStorage()
            filename = fs.save('medical_proofs/' + myfile.name, myfile)
            
            # সেশন ডেটা এসাইন করা এবং ফোর্স রাইট করা
            request.session['uploaded_file_path'] = filename
            request.session['booking_bed_id'] = bed.id
            request.session['booking_user_id'] = request.user.id
            request.session['payment_action'] = 'NEW_BOOKING'
            request.session.modified = True
            request.session.save()
        else:
            return render(request, 'coreApp/error.html', {'message': 'Medical document is required!'})

        # 🔑 সেশন ড্রপ ঠেকাতে ট্রানজেকশন আইডিতেই ডেটা এনকোড করা হলো: NEW_BOOKING-[BED_ID]-[USER_ID]
        tran_id = f"NEW_BOOKING-{bed.id}-{request.user.id}-{str(uuid.uuid4())[:6].upper()}"

        api_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
        ssl_settings = getattr(settings, 'SSLCOMMERZ_SETTINGS', {})
        store_id = ssl_settings.get('store_id') or ssl_settings.get('STORE_ID')
        store_pass = ssl_settings.get('store_pass') or ssl_settings.get('STORE_PASS')

        dummy_reservation = BedReservation(bed_status=bed)
        dynamic_amount = dummy_reservation.get_booking_fee

        post_data = {
            'store_id': store_id,
            'store_passwd': store_pass,
            'total_amount': float(dynamic_amount),
            'currency': 'BDT',
            'tran_id': tran_id,
            'success_url': request.build_absolute_uri('/payment-success-handler/'),
            'fail_url': request.build_absolute_uri('/payment-fail/0/'),
            'cancel_url': request.build_absolute_uri('/payment-fail/0/'),
            'ipn_url': request.build_absolute_uri('/payment-fail/0/'),
            'cus_name': request.user.get_full_name() or request.user.username,
            'cus_email': request.user.email or 'patient@carequeue.com',
            'cus_add1': 'Dhaka', 'cus_city': 'Dhaka', 'cus_country': 'Bangladesh',
            'cus_phone': '01700000000', 'shipping_method': 'NO',
            'product_name': f'Bed Booking - {bed.get_bed_type_display}', 'product_category': 'Medical', 'product_profile': 'general',
            'value_a': request.user.id,
            'value_b': filename # ব্যাকআপ হিসেবে ফাইলের পাথটি পাস করে দেওয়া হলো
        }

        try:
            api_response = requests.post(api_url, data=post_data, timeout=15, verify=False).json()
            if api_response.get('status') == 'SUCCESS' and api_response.get('GatewayPageURL'):
                return redirect(api_response['GatewayPageURL'])
            else:
                return render(request, 'coreApp/error.html', {'message': 'SSLCommerz Gateway Initialization Failed!'})
        except Exception as e:
            return render(request, 'coreApp/error.html', {'message': f"Exception: {str(e)}"})

    return redirect('hospital_list')


@csrf_exempt
def payment_success_view(request):
    """
    SSLCommerz পেমেন্ট সফল করার পর এই ভিউটি কল করবে।
    এখানে সেশন ড্রপ প্রুফ মেকানিজম যুক্ত করা হয়েছে।
    """
    if request.method == 'POST':
        # ১. প্রথমে গেটওয়ে থেকে ফেরত আসা ট্রানজেকশন আইডি ধরি
        tran_id = request.POST.get('tran_id', '')
        
        # ডিফল্ট ডেটা সেশন থেকে রিড করার চেষ্টা
        action = request.session.get('payment_action')
        bed_id = request.session.get('booking_bed_id')
        user_id = request.session.get('booking_user_id')
        file_path = request.session.get('uploaded_file_path')
        res_id = request.session.get('extend_reservation_id')
        
        # 🛡️ বুলেটপ্রুফ রিকভারি: সেশন হারিয়ে গেলেও যদি tran_id থাকে, তা পার্স করা হবে
        if tran_id and "-" in tran_id:
            parts = tran_id.split('-')
            # ট্রানজেকশন ফরমেট ১: EXTEND_TIME-[RES_ID]-[USER_ID]-XXXX
            # ট্রানজেকশন ফরমেট ২: NEW_BOOKING-[BED_ID]-[USER_ID]-XXXX
            if parts[0] == 'EXTEND_TIME':
                action = 'EXTEND_TIME'
                res_id = parts[1]
                user_id = parts[2]
            elif parts[0] == 'NEW_BOOKING':
                action = 'NEW_BOOKING'
                bed_id = parts[1]
                user_id = parts[2]
                file_path = file_path or request.POST.get('value_b') # value_b থেকে পাথ রিকভারি

        # যদি সেশন এবং ট্রানজেকশন আইডি দুটির কোথাও ইউজার বা মূল অ্যাকশন না পাওয়া যায়
        if not action:
            return render(request, 'coreApp/error.html', {'message': 'Invalid transaction flow or payment action unknown.'})

        # ⏰ ১. টাইম এক্সটেনশন বা সময় বাড়ানোর হ্যান্ডলার
        if action == 'EXTEND_TIME':
            if not res_id:
                return render(request, 'coreApp/error.html', {'message': 'Invalid extension transaction id.'})
            
            reservation = get_object_or_404(BedReservation, id=res_id)
            
            if hasattr(reservation, 'extend_reservation_time'):
                reservation.extend_reservation_time()
            else:
                reservation.expires_at = timezone.now() + timedelta(hours=1)
                reservation.status = 'PENDING'
                reservation.save()

            # সেশন ক্লিনআপ
            request.session.pop('payment_action', None)
            request.session.pop('extend_reservation_id', None)
            request.session.pop('booking_bed_id', None)
            request.session.pop('booking_user_id', None)
            return render(request, 'coreApp/payment_success.html', {'reservation': reservation})

        # 🆕 ২. সম্পূর্ণ নতুন বুকিং হ্যান্ডলার
        else:
            if not bed_id or not user_id:
                return render(request, 'coreApp/error.html', {'message': 'Session expired or invalid transaction tracking.'})

            user = get_object_or_404(User, id=user_id)
            bed = get_object_or_404(BedStatus, id=bed_id)
            
            # সেফটি ফিক্স: যদি ফাইল পাথ কোনোভাবেই না পাওয়া যায়, একটি জেনেরিক নাম ব্যবহার করবে
            if not file_path:
                file_path = "medical_proofs/uploaded_proof.pdf"

            reservation = BedReservation.objects.create(
                user=user,
                bed_status=bed,
                medical_document=file_path,
                status='PENDING',
                expires_at=timezone.now() + timedelta(hours=1)
            )

            if bed.available_beds > 0:
                bed.available_beds -= 1
                bed.save()

            # সেশন ক্লিয়ারেন্স
            request.session.pop('booking_bed_id', None)
            request.session.pop('booking_user_id', None)
            request.session.pop('uploaded_file_path', None)
            request.session.pop('payment_action', None)

            return render(request, 'coreApp/payment_success.html', {'reservation': reservation})
            
    return redirect('dashboard')


@csrf_exempt
def payment_fail_view(request, res_id):
    reservation = None
    if res_id != 0:
        reservation = get_object_or_404(BedReservation, id=res_id)
    return render(request, 'coreApp/payment_fail.html', {'reservation': reservation})


@login_required
def cancel_reservation(request, res_id):
    reservation = get_object_or_404(BedReservation, id=res_id)
    
    if reservation.user == request.user or HospitalName.objects.filter(user=request.user).exists():
        bed = reservation.bed_status
        
        if bed.available_beds < bed.total_beds:
            bed.available_beds += 1
            bed.save()
        
        reservation.status = 'CANCELLED'
        reservation.save()
        
        return redirect('dashboard')
    else:
        return render(request, 'coreApp/error.html', {'message': 'Unauthorized action.'})


@login_required
def extend_payment_view(request, res_id):
    if HospitalName.objects.filter(user=request.user).exists():
        return redirect('hospital_dashboard')

    reservation = get_object_or_404(BedReservation, id=res_id, user=request.user)
    bed = reservation.bed_status

    # সেশন সেটআপ এবং একশন ডিটেকশন ট্রাক
    request.session['booking_bed_id'] = bed.id
    request.session['booking_user_id'] = request.user.id
    request.session['extend_reservation_id'] = reservation.id
    request.session['payment_action'] = 'EXTEND_TIME'
    request.session.modified = True
    request.session.save()
    
    # 🔑 টাইম এক্সটেনশনের জন্য ইউনিক ট্রানজেকশন আইডি ফরম্যাট: EXTEND_TIME-[RES_ID]-[USER_ID]-XXXX
    tran_id = f"EXTEND_TIME-{reservation.id}-{request.user.id}-{str(uuid.uuid4())[:6].upper()}"
    
    api_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    ssl_settings = getattr(settings, 'SSLCOMMERZ_SETTINGS', {})
    store_id = ssl_settings.get('store_id') or ssl_settings.get('STORE_ID')
    store_pass = ssl_settings.get('store_pass') or ssl_settings.get('STORE_PASS')

    dynamic_amount = reservation.get_booking_fee

    post_data = {
        'store_id': store_id,
        'store_passwd': store_pass,
        'total_amount': float(dynamic_amount),
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': request.build_absolute_uri('/payment-success-handler/'),
        'fail_url': request.build_absolute_uri(f'/payment-fail/{reservation.id}/'),
        'cancel_url': request.build_absolute_uri(f'/payment-fail/{reservation.id}/'),
        'ipn_url': request.build_absolute_uri(f'/payment-fail/{reservation.id}/'),
        'cus_name': request.user.get_full_name() or request.user.username,
        'cus_email': request.user.email or 'patient@carequeue.com',
        'cus_add1': 'Dhaka', 'cus_city': 'Dhaka', 'cus_country': 'Bangladesh',
        'cus_phone': '01700000000', 'shipping_method': 'NO',
        'product_name': f'Extend Bed Booking - {bed.get_bed_type_display}', 'product_category': 'Medical', 'product_profile': 'general',
        'value_a': request.user.id
    }

    try:
        api_response = requests.post(api_url, data=post_data, timeout=15, verify=False).json()
        if api_response.get('status') == 'SUCCESS' and api_response.get('GatewayPageURL'):
            return redirect(api_response['GatewayPageURL'])
        else:
            return render(request, 'coreApp/error.html', {'message': 'SSLCommerz Gateway Initialization Failed!'})
    except Exception as e:
        return render(request, 'coreApp/error.html', {'message': f"Exception: {str(e)}"})


def verify_nid(nid_number, dob):
    """
    Porichoy বা অন্য কোনো API এর মাধ্যমে NID ভেরিফাই করার ফাংশন
    """
    api_url = "https://api.porichoy.gov.bd/api/v1/nid-verification"
    headers = {
        "Authorization": f"Bearer {settings.PORICHOY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "nid": nid_number,
        "dob": dob
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=5)
        data = response.json()
        if data.get('status') == 'YES' or data.get('pass') is True:
            return True, data.get('voter_info')
    except Exception:
        pass
        
    return False, None

@login_required
@require_POST
def update_profile_ajax(request):
    try:
        user = request.user
        # ইউজারের অলরেডি প্রোফাইল অবজেক্ট থাকলে সেটা নেওয়া হবে, না থাকলে নতুন তৈরি হবে
        profile, created = PatientProfile.objects.get_or_create(user=user)
        
        # ফ্রন্টএন্ড ফর্ম থেকে ডেটা রিসিভ করা
        blood_group = request.POST.get('blood_group')
        emergency_contact = request.POST.get('emergency_contact')
        address = request.POST.get('address')
        
        # ডেটা মডেল ফিল্ডে অ্যাসাইন করা
        if blood_group:
            profile.blood_group = blood_group
        if emergency_contact:
            profile.emergency_contact = emergency_contact
        if address:
            profile.address = address
            
        # 📸 প্রোফাইল ইমেজ (Avatar) হ্যান্ডেল করা
        if 'profile_image' in request.FILES:
            profile.image = request.FILES['profile_image']
            
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'প্রোফাইল সফলভাবে আপডেট করা হয়েছে!',
            'image_url': profile.image.url if profile.image else '/static/default-avatar.png'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'কিছু একটা সমস্যা হয়েছে: {str(e)}'
        })