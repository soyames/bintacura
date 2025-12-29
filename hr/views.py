from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    Employee, PayrollPeriod, PayrollRun, PayrollDeduction,
    LeaveType, LeaveRequest, LeaveBalance, TimeAndAttendance,
    EmployeeBenefit
)
from .serializers import (
    EmployeeSerializer, PayrollPeriodSerializer, PayrollRunSerializer,
    PayrollDeductionSerializer, LeaveTypeSerializer, LeaveRequestSerializer,
    LeaveBalanceSerializer, TimeAndAttendanceSerializer, EmployeeBenefitSerializer
)


class HRBaseViewSet(viewsets.ModelViewSet):
    """Base viewset for HR module with organization filtering"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization"""
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization if user is an organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            return queryset.filter(organization=user)

        return queryset


class EmployeeViewSet(HRBaseViewSet):
    queryset = Employee.objects.all().select_related(
        'organization', 'user', 'department', 'created_by'
    )
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by employment type
        employment_type = self.request.query_params.get('employment_type', None)
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)

        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department_id=department)

        return queryset

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate an employee"""
        employee = self.get_object()
        termination_date = request.data.get('termination_date')

        if not termination_date:
            return Response(
                {'error': 'termination_date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            termination_date = datetime.strptime(termination_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee.termination_date = termination_date
        employee.status = 'terminated'
        employee.save()

        serializer = self.get_serializer(employee)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payroll_history(self, request, pk=None):
        """Get employee's payroll history"""
        employee = self.get_object()
        payroll_runs = PayrollRun.objects.filter(employee=employee).order_by('-payroll_period__start_date')

        # Pagination
        page = self.paginate_queryset(payroll_runs)
        if page is not None:
            serializer = PayrollRunSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PayrollRunSerializer(payroll_runs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def leave_summary(self, request, pk=None):
        """Get employee's leave summary"""
        employee = self.get_object()
        year = int(request.query_params.get('year', timezone.now().year))

        balances = LeaveBalance.objects.filter(employee=employee, year=year)
        serializer = LeaveBalanceSerializer(balances, many=True)

        return Response({
            'year': year,
            'balances': serializer.data
        })

    @action(detail=False, methods=['get'])
    def active_count(self, request):
        """Get count of active employees by department"""
        user = request.user
        if user.role not in ['hospital', 'pharmacy', 'insurance_company']:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        summary = Employee.objects.filter(
            organization=user,
            status='active'
        ).values('department__name').annotate(
            count=Count('id')
        ).order_by('-count')

        return Response(summary)

    @action(detail=True, methods=['get'])
    def ai_insights(self, request, pk=None):
        """Get AI-powered insights for an employee"""
        from .ai_insights import HRAnalytics

        employee = self.get_object()

        # Get days parameter (default 30 days)
        days = int(request.query_params.get('days', 30))

        # Get all insights
        insights = HRAnalytics.get_employee_insights(employee.user, days=days)

        return Response({
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'analysis_period_days': days,
            'insights': insights,
            'generated_at': timezone.now()
        })

    @action(detail=True, methods=['get'])
    def attendance_analysis(self, request, pk=None):
        """Get detailed attendance pattern analysis"""
        from .ai_insights import HRAnalytics

        employee = self.get_object()
        days = int(request.query_params.get('days', 30))

        analysis = HRAnalytics.analyze_attendance_patterns(employee.user, days=days)

        return Response({
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'analysis_period_days': days,
            'attendance_analysis': analysis,
            'generated_at': timezone.now()
        })

    @action(detail=True, methods=['get'])
    def performance_trend(self, request, pk=None):
        """Get performance trend analysis"""
        from .ai_insights import HRAnalytics

        employee = self.get_object()
        reviews_count = int(request.query_params.get('reviews_count', 5))

        analysis = HRAnalytics.analyze_performance_trend(employee.user, reviews_count=reviews_count)

        return Response({
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'reviews_analyzed': reviews_count,
            'performance_analysis': analysis,
            'generated_at': timezone.now()
        })

    @action(detail=True, methods=['get'])
    def churn_risk(self, request, pk=None):
        """Get employee churn risk prediction"""
        from .ai_insights import HRAnalytics

        employee = self.get_object()

        risk_analysis = HRAnalytics.calculate_churn_risk(employee.user)

        return Response({
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'churn_risk': risk_analysis,
            'generated_at': timezone.now()
        })

    @action(detail=False, methods=['get'])
    def department_ai_overview(self, request):
        """Get AI insights overview for all employees in organization"""
        user = request.user
        if user.role not in ['hospital', 'pharmacy', 'insurance_company']:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        from .ai_insights import HRAnalytics

        # Get all active employees
        employees = Employee.objects.filter(
            organization=user,
            status='active'
        ).select_related('user', 'department')

        # Department filter
        department_id = request.query_params.get('department', None)
        if department_id:
            employees = employees.filter(department_id=department_id)

        # Analyze each employee
        high_risk_employees = []
        declining_performance = []
        attendance_issues = []

        for employee in employees:
            # Churn risk
            churn = HRAnalytics.calculate_churn_risk(employee.user)
            if churn['risk_level'] == 'high':
                high_risk_employees.append({
                    'employee_id': str(employee.id),
                    'name': employee.user.full_name,
                    'department': employee.department.name if employee.department else None,
                    'risk_score': churn['risk_score'],
                    'risk_factors': churn['risk_factors']
                })

            # Performance trend
            performance = HRAnalytics.analyze_performance_trend(employee.user)
            if performance and performance.get('trend') == 'declining':
                declining_performance.append({
                    'employee_id': str(employee.id),
                    'name': employee.user.full_name,
                    'department': employee.department.name if employee.department else None,
                    'latest_rating': performance.get('latest_rating'),
                    'avg_change': performance.get('avg_change')
                })

            # Attendance issues
            attendance = HRAnalytics.analyze_attendance_patterns(employee.user)
            if attendance['patterns']:
                attendance_issues.append({
                    'employee_id': str(employee.id),
                    'name': employee.user.full_name,
                    'department': employee.department.name if employee.department else None,
                    'attendance_rate': attendance['attendance_rate'],
                    'patterns': attendance['patterns']
                })

        return Response({
            'organization': user.full_name,
            'total_employees_analyzed': employees.count(),
            'summary': {
                'high_churn_risk_count': len(high_risk_employees),
                'declining_performance_count': len(declining_performance),
                'attendance_issues_count': len(attendance_issues)
            },
            'high_risk_employees': high_risk_employees[:10],  # Top 10
            'declining_performance': declining_performance[:10],  # Top 10
            'attendance_issues': attendance_issues[:10],  # Top 10
            'generated_at': timezone.now()
        })

    @action(detail=False, methods=['get'])
    def ml_churn_prediction(self, request):
        """ML-powered churn prediction using Logistic Regression (Phase 7)"""
        user = request.user
        if user.role not in ['hospital', 'pharmacy', 'insurance_company']:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        try:
            from ml_models.churn_prediction import ChurnPredictor

            # Train and predict for all employees in organization
            predictions = ChurnPredictor.train_and_predict(user)

            return Response({
                'organization': user.full_name,
                'ml_model': 'Logistic Regression',
                'predictions': predictions,
                'generated_at': timezone.now()
            })
        except ImportError:
            return Response(
                {'error': 'ML models not available. Install scikit-learn.'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {'error': f'ML prediction failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PayrollPeriodViewSet(HRBaseViewSet):
    queryset = PayrollPeriod.objects.all().select_related('organization', 'processed_by')
    serializer_class = PayrollPeriodSerializer

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process payroll for the period"""
        period = self.get_object()

        if period.status != 'open':
            return Response(
                {'error': f'Cannot process payroll. Period status is {period.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        period.status = 'processing'
        period.save()

        # Get all active employees for this organization
        employees = Employee.objects.filter(
            organization=period.organization,
            status='active'
        )

        created_count = 0
        for employee in employees:
            # Check if payroll run already exists
            if PayrollRun.objects.filter(payroll_period=period, employee=employee).exists():
                continue

            # Calculate hours and pay based on employment type
            if employee.salary_type == 'monthly':
                base_pay = employee.base_salary
                regular_hours = Decimal('0.00')
                overtime_hours = Decimal('0.00')
            elif employee.salary_type == 'hourly':
                # Get attendance records for the period
                attendance = TimeAndAttendance.objects.filter(
                    employee=employee,
                    clock_in__date__gte=period.start_date,
                    clock_in__date__lte=period.end_date,
                    is_approved=True
                )
                regular_hours = attendance.aggregate(total=Sum('regular_hours'))['total'] or Decimal('0.00')
                overtime_hours = attendance.aggregate(total=Sum('overtime_hours'))['total'] or Decimal('0.00')
                base_pay = regular_hours * employee.base_salary
                overtime_pay = overtime_hours * employee.base_salary * Decimal('1.5')
            else:
                base_pay = employee.base_salary
                regular_hours = Decimal('0.00')
                overtime_hours = Decimal('0.00')

            # Create payroll run
            payroll_run = PayrollRun.objects.create(
                payroll_period=period,
                employee=employee,
                regular_hours=regular_hours,
                overtime_hours=overtime_hours,
                base_pay=base_pay,
                overtime_pay=overtime_pay if employee.salary_type == 'hourly' else Decimal('0.00'),
                bonus=Decimal('0.00'),
                commission=Decimal('0.00'),
                allowances=Decimal('0.00'),
                gross_pay=base_pay,
                total_deductions=Decimal('0.00'),
                net_pay=base_pay
            )

            # Add standard deductions (income tax, social security, etc.)
            # Income tax (example: 10% for simplicity)
            income_tax = base_pay * Decimal('0.10')
            PayrollDeduction.objects.create(
                payroll_run=payroll_run,
                deduction_type='income_tax',
                description='Income Tax (10%)',
                amount=income_tax,
                is_mandatory=True
            )

            # Social security (example: 5%)
            social_security = base_pay * Decimal('0.05')
            PayrollDeduction.objects.create(
                payroll_run=payroll_run,
                deduction_type='social_security',
                description='Social Security (5%)',
                amount=social_security,
                is_mandatory=True
            )

            # Recalculate totals
            payroll_run.calculate_totals()
            created_count += 1

        period.status = 'processed'
        period.processed_by = request.user
        period.processed_at = timezone.now()
        period.save()

        return Response({
            'message': f'Payroll processed successfully for {created_count} employees',
            'payroll_runs_created': created_count
        })

    @action(detail=True, methods=['post'])
    def approve_all(self, request, pk=None):
        """Approve all payroll runs in the period"""
        period = self.get_object()

        if period.status != 'processed':
            return Response(
                {'error': 'Period must be processed before approval'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = PayrollRun.objects.filter(
            payroll_period=period,
            payment_status='pending'
        ).update(
            payment_status='approved',
            approved_by=request.user
        )

        return Response({
            'message': f'Approved {updated} payroll runs',
            'approved_count': updated
        })

    @action(detail=True, methods=['post'])
    def close_period(self, request, pk=None):
        """Close the payroll period"""
        period = self.get_object()

        # Check if all runs are paid
        pending_runs = PayrollRun.objects.filter(
            payroll_period=period,
            payment_status__in=['pending', 'approved']
        ).count()

        if pending_runs > 0:
            return Response(
                {'error': f'{pending_runs} payroll runs are not yet paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        period.status = 'closed'
        period.save()

        return Response({'message': 'Payroll period closed successfully'})


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.all().select_related(
        'payroll_period', 'employee', 'employee__user', 'approved_by'
    ).prefetch_related('deductions')
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            queryset = queryset.filter(payroll_period__organization=user)

        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)

        # Filter by period
        period = self.request.query_params.get('period', None)
        if period:
            queryset = queryset.filter(payroll_period_id=period)

        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a payroll run"""
        payroll_run = self.get_object()

        if payroll_run.payment_status != 'pending':
            return Response(
                {'error': f'Cannot approve. Current status is {payroll_run.payment_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payroll_run.payment_status = 'approved'
        payroll_run.approved_by = request.user
        payroll_run.save()

        serializer = self.get_serializer(payroll_run)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark payroll run as paid"""
        payroll_run = self.get_object()

        if payroll_run.payment_status != 'approved':
            return Response(
                {'error': 'Payroll run must be approved before marking as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = request.data.get('payment_method', '')
        payment_reference = request.data.get('payment_reference', '')

        payroll_run.payment_status = 'paid'
        payroll_run.payment_method = payment_method
        payroll_run.payment_reference = payment_reference
        payroll_run.paid_at = timezone.now()
        payroll_run.save()

        serializer = self.get_serializer(payroll_run)
        return Response(serializer.data)


class LeaveTypeViewSet(HRBaseViewSet):
    queryset = LeaveType.objects.all().select_related('organization')
    serializer_class = LeaveTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Only show active leave types by default
        active_only = self.request.query_params.get('active_only', 'true')
        if active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all().select_related(
        'employee', 'employee__user', 'leave_type', 'approved_by', 'handover_to'
    )
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            queryset = queryset.filter(employee__organization=user)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)

        return queryset

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit leave request for approval"""
        leave_request = self.get_object()

        if leave_request.status != 'draft':
            return Response(
                {'error': 'Only draft requests can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request.status = 'pending'
        leave_request.submitted_at = timezone.now()
        leave_request.save()

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve leave request"""
        leave_request = self.get_object()

        if leave_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check leave balance
        balance = LeaveBalance.objects.filter(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year
        ).first()

        if balance and balance.remaining_days < leave_request.days_requested:
            return Response(
                {'error': f'Insufficient leave balance. Available: {balance.remaining_days} days'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save()

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject leave request"""
        leave_request = self.get_object()

        if leave_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'rejection_reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request.status = 'rejected'
        leave_request.rejection_reason = rejection_reason
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save()

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel leave request"""
        leave_request = self.get_object()

        if leave_request.status not in ['draft', 'pending', 'approved']:
            return Response(
                {'error': f'Cannot cancel request with status {leave_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request.status = 'cancelled'
        leave_request.save()

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def ai_recommendation(self, request, pk=None):
        """Get AI-powered recommendation for leave approval"""
        from .ai_insights import HRAnalytics

        leave_request = self.get_object()

        recommendation = HRAnalytics.recommend_leave_approval(leave_request)

        return Response({
            'leave_request_id': str(leave_request.id),
            'employee_name': leave_request.employee.user.full_name,
            'leave_type': leave_request.leave_type.name,
            'days_requested': leave_request.days_requested,
            'ai_recommendation': recommendation,
            'generated_at': timezone.now()
        })


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all().select_related('employee', 'employee__user', 'leave_type')
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            queryset = queryset.filter(employee__organization=user)

        # Filter by year
        year = self.request.query_params.get('year', None)
        if year:
            queryset = queryset.filter(year=year)

        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)

        return queryset

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """Adjust leave balance"""
        balance = self.get_object()

        adjustment_days = request.data.get('adjustment_days')
        adjustment_reason = request.data.get('adjustment_reason', '')

        if adjustment_days is None:
            return Response(
                {'error': 'adjustment_days is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            adjustment_days = Decimal(str(adjustment_days))
        except:
            return Response(
                {'error': 'Invalid adjustment_days value'},
                status=status.HTTP_400_BAD_REQUEST
            )

        balance.adjustment_days += adjustment_days
        balance.adjustment_reason = adjustment_reason
        balance.calculate_remaining()

        serializer = self.get_serializer(balance)
        return Response(serializer.data)


class TimeAndAttendanceViewSet(viewsets.ModelViewSet):
    queryset = TimeAndAttendance.objects.all().select_related('employee', 'employee__user', 'approved_by')
    serializer_class = TimeAndAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            queryset = queryset.filter(employee__organization=user)

        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(
                clock_in__date__gte=start_date,
                clock_in__date__lte=end_date
            )

        return queryset

    @action(detail=True, methods=['post'])
    def clock_out_now(self, request, pk=None):
        """Clock out an attendance record"""
        attendance = self.get_object()

        if attendance.clock_out:
            return Response(
                {'error': 'Already clocked out'},
                status=status.HTTP_400_BAD_REQUEST
            )

        location = request.data.get('location', '')
        ip_address = request.META.get('REMOTE_ADDR', '')

        attendance.clock_out = timezone.now()
        attendance.clock_out_location = location
        attendance.clock_out_ip = ip_address
        attendance.calculate_hours()

        serializer = self.get_serializer(attendance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve_attendance(self, request, pk=None):
        """Approve attendance record"""
        attendance = self.get_object()

        attendance.is_approved = True
        attendance.approved_by = request.user
        attendance.save()

        serializer = self.get_serializer(attendance)
        return Response(serializer.data)


class EmployeeBenefitViewSet(viewsets.ModelViewSet):
    queryset = EmployeeBenefit.objects.all().select_related('employee', 'employee__user')
    serializer_class = EmployeeBenefitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by organization
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            queryset = queryset.filter(employee__organization=user)

        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)

        # Only show active benefits by default
        active_only = self.request.query_params.get('active_only', 'true')
        if active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset
