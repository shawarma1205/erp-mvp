
#from django.contrib import admin
#from .models import FXRatePeriod


#@admin.register(FXRatePeriod)
#class FXRatePeriodAdmin(admin.ModelAdmin):
    #list_display = ("start_date", "end_date", "krw_to_php", "is_locked", "created_at")
    #list_filter = ("is_locked",)
    #search_fields = ("memo",)

    #def get_readonly_fields(self, request, obj=None):
        # 잠긴 기간은 수정 못 하게(아주 단순한 MVP 안전장치)
        #if obj and obj.is_locked:
            #return ("start_date", "end_date", "krw_to_php", "memo", "is_locked", "created_at")
        #return ("created_at",)
