from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver


class HospitalName(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Hospital"


class BedStatus(models.Model):
   
    BED_TYPES = (
        ('GENERAL', 'General Bed / Ward'),
        ('CABIN_STANDARD', 'Single Cabin (Standard)'),
        ('CABIN_DELUXE', 'Deluxe / Executive Cabin'),
        ('ICU', 'Intensive Care Unit (ICU)'),
        ('CCU', 'Coronary Care Unit (CCU)'),
        ('NICU', 'Neonatal ICU (NICU)'),
    )
    
    hospital = models.ForeignKey(HospitalName, on_delete=models.CASCADE, related_name='beds')
    bed_type = models.CharField(max_length=50, choices=BED_TYPES, default='GENERAL')
    total_beds = models.IntegerField(default=0)
    available_beds = models.IntegerField(default=0)
    
   
    cost_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)

    def __str__(self):
        hospital_name = self.hospital.name if self.hospital and self.hospital.name else "Unknown Hospital"
        return f"{hospital_name} - {self.get_bed_type_display()}"


class BedReservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bed_status = models.ForeignKey(BedStatus, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='PENDING') # PENDING, APPROVED, EXPIRED, CANCELLED
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    
    medical_document = models.FileField(upload_to='medical_proofs/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.bed_status.hospital.name}"
   
    @property
    def get_booking_fee(self):
        daily_cost = float(self.bed_status.cost_per_day)
        return round(daily_cost * 0.05, 2)

  
    @property
    def get_extend_fee(self):
        daily_cost = float(self.bed_status.cost_per_day)
        return round(daily_cost * 0.025, 2)

    
    def extend_reservation_time(self):
        if self.expires_at:
            self.expires_at += timedelta(minutes=30)
        else:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        
        self.extension_count += 1
        self.save()
        
        
  


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    nid_number = models.CharField(max_length=17, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
    
    
    from django.db import models
from django.contrib.auth.models import User

class PatientProfile(models.Model):
  
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    
   
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        PatientProfile.objects.create(user=instance)