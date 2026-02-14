from decimal import Decimal
from pydantic import BaseModel


class TodayAnalytics(BaseModel):
    total_revenue: Decimal
    state_duty_total: Decimal
    income_pavilion1: Decimal
    income_pavilion2: Decimal
    orders_count: int
    average_cheque: Decimal


class MonthAnalytics(BaseModel):
    total_revenue: Decimal
    state_duty_total: Decimal
    income_pavilion1: Decimal
    income_pavilion2: Decimal
    orders_count: int
    average_cheque: Decimal


class EmployeeStat(BaseModel):
    employee_id: int
    employee_name: str
    orders_count: int
    total_amount: Decimal


class EmployeesAnalytics(BaseModel):
    period: str  # "day" | "month"
    employees: list[EmployeeStat]
