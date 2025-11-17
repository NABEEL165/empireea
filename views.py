from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import WasteCollection
from .forms import WasteCollectionForm
from authentication.models import CustomUser
import base64
from django.core.files.base import ContentFile
import uuid
from customer_dashboard.models import CustomerWasteInfo



# Check if the user is a waste collector (role 1)
def is_collector(user):
    return user.is_authenticated and user.role == 1


# Waste Collector Dashboard View
@login_required
def dashboard(request):
    if not is_collector(request.user):
        return redirect('authentication:login')

    waste_entries = WasteCollection.objects.filter(collector=request.user)
    return render(request, 'waste_collector_dashboard.html', {'waste_entries': waste_entries})


# List all waste collection records for the logged-in collector
@login_required
def collection_list(request):
    if not is_collector(request.user):
        return redirect('authentication:login')

    collections = WasteCollection.objects.filter(collector=request.user)
    return render(request, 'waste_collect_list.html', {'collections': collections})


def collection_create(request):
    customer_id = request.GET.get('customer_id')

    if request.method == 'POST':
        form = WasteCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.collector = request.user
            instance.total_amount = instance.kg * 50

            # Handle base64 photo
            photo_data = request.POST.get('photo_data')
            if photo_data:
                format, imgstr = photo_data.split(';base64,')
                ext = format.split('/')[-1]
                file_name = f"{uuid.uuid4()}.{ext}"
                instance.photo.save(file_name, ContentFile(base64.b64decode(imgstr)), save=False)

            instance.save()
            return redirect('waste_collector:waste_collector_dashboard')

    else:
        form = WasteCollectionForm()
        if customer_id:
            try:
                customer_info = CustomerWasteInfo.objects.get(id=customer_id)


            except CustomerWasteInfo.DoesNotExist:
                pass

    return render(request, 'waste_collect_form.html', {'form': form})






@login_required
def collection_update(request, pk):
    if not is_collector(request.user):
        return redirect('authentication:login')

    waste = get_object_or_404(WasteCollection, pk=pk, collector=request.user)
    form = WasteCollectionForm(request.POST or None, request.FILES or None, instance=waste)
    if form.is_valid():
        form.save()
        return redirect('waste_collector:waste_collector_dashboard')
    return render(request, 'waste_collect_form.html', {'form': form})





# Delete a waste collection entry
@login_required
def collection_delete(request, pk):
    if not is_collector(request.user):
        return redirect('authentication:login')

    waste = get_object_or_404(WasteCollection, pk=pk, collector=request.user)
    if request.method == 'POST':
        waste.delete()
        return redirect('waste_collector:waste_collector_dashboard')
    return render(request, 'waste_collect_delete.html', {'waste': waste})





@login_required
def assigned_waste_customers(request):
    collector = request.user
    assigned_customers = CustomerWasteInfo.objects.filter(assigned_collector=collector)
    return render(request, 'assigned_customers_details.html', {
        'assigned_customers': assigned_customers
    })













@login_required
def billing_dashboard(request):
    """Display billing statistics and impact data"""
    # Get current month's collections
    from django.utils import timezone
    from django.db.models import Sum, Count
    import calendar

    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get this month's collections
    monthly_collections = WasteCollection.objects.filter(
        created_at__gte=start_of_month
    )

    # Calculate statistics
    total_weight = monthly_collections.aggregate(
        total=Sum('kg')
    )['total'] or 0

    total_revenue = monthly_collections.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    collection_count = monthly_collections.count()

    # Group by local body for regional analysis
    localbody_stats = monthly_collections.values(
        'localbody__name'
    ).annotate(
        total_weight=Sum('kg'),
        total_revenue=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total_revenue')

    # Prepare data for charts
    chart_data = []
    for stat in localbody_stats:
        chart_data.append({
            'localbody': stat['localbody__name'],
            'weight': float(stat['total_weight']),
            'revenue': float(stat['total_revenue']),
            'collections': stat['count']
        })

    context = {
        'total_weight': total_weight,
        'total_revenue': total_revenue,
        'collection_count': collection_count,
        'localbody_stats': localbody_stats,
        'chart_data': chart_data,
        'current_month': today.strftime('%B %Y')
    }

    return render(request, 'billing_dashboard.html', context)




