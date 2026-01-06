from django.db import models


class FXRatePeriod(models.Model):
    """
    환율 기간(수동 설정).
    - 거래 생성 시점에 이 기간의 환율을 찾아 '스냅샷'으로 복사한다.
    - 기간 자체를 나중에 바꾸더라도, 이미 생성된 거래에는 영향이 없게 설계한다.
    """

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # 비워두면 '끝이 없는 기간(open-ended)'

    # KRW -> PHP (예: 0.045 같은 값이 들어갈 수 있음)
    krw_to_php = models.DecimalField(max_digits=12, decimal_places=6)

    memo = models.CharField(max_length=200, blank=True)
    is_locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        end = self.end_date.isoformat() if self.end_date else "open"
        return f"FX {self.start_date.isoformat()} ~ {end} : {self.krw_to_php}"

    def contains(self, date_value) -> bool:
        """특정 날짜가 이 기간에 포함되는지 확인"""
        if self.end_date is None:
            return self.start_date <= date_value
        return self.start_date <= date_value <= self.end_date
