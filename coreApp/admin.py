from django.contrib import admin
from .models import HospitalName, BedStatus, BedReservation, PatientProfile


admin.site.register(HospitalName)
admin.site.register(BedStatus)
admin.site.register(BedReservation)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    
    list_display = ('get_username', 'blood_group', 'emergency_contact', 'has_image')
    
    
    search_fields = ('user__username', 'emergency_contact')
    
   
    list_filter = ('blood_group',)

    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'User Name' 

    
    def has_image(self, obj):
        return "Yes" if obj.image else "No"
    has_image.short_description = 'Avatar Uploaded'