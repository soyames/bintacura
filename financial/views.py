from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal

from .models import (
    FiscalYear, FiscalPeriod, ChartOfAccounts, JournalEntry, JournalEntryLine,
    BankAccount, Budget, BudgetLine, Tax, ProjectManagement
)
from core.serializers import ParticipantSerializer
from .serializers import (
    FiscalYearSerializer, FiscalPeriodSerializer, ChartOfAccountsSerializer,
    JournalEntrySerializer, JournalEntryLineSerializer, BankAccountSerializer,
    BudgetSerializer, BudgetLineSerializer, TaxSerializer, ProjectManagementSerializer
)


class FinancialBaseViewSet(viewsets.ModelViewSet):
    """Base viewset for financial modules with organization filtering"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['hospital', 'pharmacy', 'insurance_company']:
            return self.queryset.filter(organization=user)
        return self.queryset.none()


class FiscalYearViewSet(FinancialBaseViewSet):
    queryset = FiscalYear.objects.all()
    serializer_class = FiscalYearSerializer

    @action(detail=True, methods=['post'])
    def close_year(self, request, pk=None):
        """Close a fiscal year"""
        fiscal_year = self.get_object()
        if fiscal_year.is_closed:
            return Response({'error': 'Fiscal year already closed'}, status=status.HTTP_400_BAD_REQUEST)

        fiscal_year.is_closed = True
        fiscal_year.closed_by = request.user
        fiscal_year.closed_at = timezone.now()
        fiscal_year.save()

        return Response({'message': 'Fiscal year closed successfully'})

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current fiscal year"""
        today = timezone.now().date()
        fiscal_year = FiscalYear.objects.filter(
            organization=request.user,
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if fiscal_year:
            serializer = self.get_serializer(fiscal_year)
            return Response(serializer.data)
        return Response({'error': 'No current fiscal year found'}, status=status.HTTP_404_NOT_FOUND)


class FiscalPeriodViewSet(FinancialBaseViewSet):
    queryset = FiscalPeriod.objects.all()
    serializer_class = FiscalPeriodSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        fiscal_year_id = self.request.query_params.get('fiscal_year')
        if fiscal_year_id:
            queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
        return queryset

    @action(detail=True, methods=['post'])
    def close_period(self, request, pk=None):
        """Close a fiscal period"""
        period = self.get_object()
        if period.is_closed:
            return Response({'error': 'Period already closed'}, status=status.HTTP_400_BAD_REQUEST)

        period.is_closed = True
        period.closed_by = request.user
        period.closed_at = timezone.now()
        period.save()

        return Response({'message': 'Period closed successfully'})


class ChartOfAccountsViewSet(FinancialBaseViewSet):
    queryset = ChartOfAccounts.objects.all()
    serializer_class = ChartOfAccountsSerializer

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get accounts grouped by type"""
        account_type = request.query_params.get('type')
        queryset = self.get_queryset()

        if account_type:
            queryset = queryset.filter(account_type=account_type)

        queryset = queryset.filter(is_active=True).order_by('account_code')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get account balance"""
        account = self.get_object()
        as_of_date = request.query_params.get('as_of_date')

        if as_of_date:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

        balance = account.get_balance(as_of_date)

        return Response({
            'account_code': account.account_code,
            'account_name': account.account_name,
            'balance': float(balance),
            'as_of_date': as_of_date or date.today()
        })


class JournalEntryViewSet(FinancialBaseViewSet):
    queryset = JournalEntry.objects.all().prefetch_related('line_items')
    serializer_class = JournalEntrySerializer

    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        """Post a journal entry"""
        entry = self.get_object()
        try:
            entry.post(request.user)
            serializer = self.get_serializer(entry)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def void_entry(self, request, pk=None):
        """Void a journal entry"""
        entry = self.get_object()
        if entry.status != 'posted':
            return Response({'error': 'Only posted entries can be voided'}, status=status.HTTP_400_BAD_REQUEST)

        entry.status = 'void'
        entry.save()

        return Response({'message': 'Entry voided successfully'})

    @action(detail=False, methods=['post'])
    def create_with_lines(self, request):
        """Create journal entry with line items in one transaction"""
        data = request.data
        lines_data = data.pop('lines', [])

        # Create journal entry
        entry_data = data.copy()
        entry_data['organization'] = request.user.id
        entry_data['created_by'] = request.user.id
        entry_serializer = self.get_serializer(data=entry_data)
        entry_serializer.is_valid(raise_exception=True)
        entry = entry_serializer.save()

        # Create line items
        for line_data in lines_data:
            line_data['journal_entry'] = entry.id
            line_serializer = JournalEntryLineSerializer(data=line_data)
            line_serializer.is_valid(raise_exception=True)
            line_serializer.save()

        # Return full entry with lines
        entry.refresh_from_db()
        serializer = self.get_serializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BankAccountViewSet(FinancialBaseViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer

    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark bank account as reconciled"""
        bank_account = self.get_object()
        reconciled_balance = request.data.get('reconciled_balance')
        reconciled_date = request.data.get('reconciled_date')

        if not reconciled_balance or not reconciled_date:
            return Response({'error': 'reconciled_balance and reconciled_date required'}, status=status.HTTP_400_BAD_REQUEST)

        bank_account.last_reconciled_balance = Decimal(reconciled_balance)
        bank_account.last_reconciled_date = reconciled_date
        bank_account.save()

        return Response({'message': 'Bank account reconciled successfully'})


class BudgetViewSet(FinancialBaseViewSet):
    queryset = Budget.objects.all().prefetch_related('line_items')
    serializer_class = BudgetSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a budget"""
        budget = self.get_object()
        if budget.status != 'draft':
            return Response({'error': 'Only draft budgets can be approved'}, status=status.HTTP_400_BAD_REQUEST)

        budget.status = 'approved'
        budget.approved_by = request.user
        budget.approved_at = timezone.now()
        budget.save()

        return Response({'message': 'Budget approved successfully'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an approved budget"""
        budget = self.get_object()
        if budget.status != 'approved':
            return Response({'error': 'Only approved budgets can be activated'}, status=status.HTTP_400_BAD_REQUEST)

        budget.status = 'active'
        budget.save()

        return Response({'message': 'Budget activated successfully'})

    @action(detail=True, methods=['get'])
    def variance_report(self, request, pk=None):
        """Get budget vs actual variance report"""
        budget = self.get_object()
        variances = []

        for line in budget.line_items.all():
            # Calculate actual spend
            actual = JournalEntryLine.objects.filter(
                account=line.account,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=budget.fiscal_year.start_date,
                journal_entry__posting_date__lte=budget.fiscal_year.end_date
            ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')

            variance = line.annual_amount - actual
            variance_pct = (variance / line.annual_amount * 100) if line.annual_amount > 0 else 0

            variances.append({
                'account_code': line.account.account_code,
                'account_name': line.account.account_name,
                'budgeted': float(line.annual_amount),
                'actual': float(actual),
                'variance': float(variance),
                'variance_percentage': float(variance_pct)
            })

        return Response(variances)


class TaxViewSet(FinancialBaseViewSet):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer

    @action(detail=False, methods=['get'])
    def active_taxes(self, request):
        """Get all active taxes"""
        today = date.today()
        taxes = self.get_queryset().filter(
            is_active=True,
            effective_date__lte=today
        ).filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)
        )
        serializer = self.get_serializer(taxes, many=True)
        return Response(serializer.data)


class ProjectManagementViewSet(FinancialBaseViewSet):
    queryset = ProjectManagement.objects.all()
    serializer_class = ProjectManagementSerializer

    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        """Get all expenses for a project"""
        project = self.get_object()
        expenses = JournalEntryLine.objects.filter(
            project=project,
            journal_entry__status='posted'
        ).select_related('account', 'journal_entry').order_by('-journal_entry__posting_date')

        data = [{
            'date': exp.journal_entry.posting_date,
            'entry_number': exp.journal_entry.entry_number,
            'account_code': exp.account.account_code,
            'account_name': exp.account.account_name,
            'description': exp.description,
            'amount': float(exp.debit_amount)
        } for exp in expenses]

        return Response(data)


@extend_schema(tags=['Financial Reports'])
class FinancialReportsViewSet(viewsets.ViewSet):
    """Financial reports: P&L, Balance Sheet, Cash Flow, etc."""
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(summary="Generate Profit & Loss statement", responses={200: OpenApiResponse(description="P&L report")})
    @action(detail=False, methods=['get'])
    def profit_and_loss(self, request):
        """Generate Profit & Loss statement"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date required'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get revenue accounts
        revenue_accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            account_type='revenue',
            is_active=True
        )

        revenue_data = []
        total_revenue = Decimal('0')

        for account in revenue_accounts:
            # Calculate revenue (credits - debits)
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=start_date,
                journal_entry__posting_date__lte=end_date
            )
            credits = entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or Decimal('0')
            debits = entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or Decimal('0')
            amount = credits - debits
            total_revenue += amount

            revenue_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'amount': float(amount)
            })

        # Get expense accounts
        expense_accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            account_type='expense',
            is_active=True
        )

        expense_data = []
        total_expense = Decimal('0')

        for account in expense_accounts:
            # Calculate expense (debits - credits)
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=start_date,
                journal_entry__posting_date__lte=end_date
            )
            debits = entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or Decimal('0')
            credits = entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or Decimal('0')
            amount = debits - credits
            total_expense += amount

            expense_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'amount': float(amount)
            })

        net_income = total_revenue - total_expense

        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'revenue': {
                'accounts': revenue_data,
                'total': float(total_revenue)
            },
            'expenses': {
                'accounts': expense_data,
                'total': float(total_expense)
            },
            'net_income': float(net_income)
        })

    @action(detail=False, methods=['get'])
    def balance_sheet(self, request):
        """Generate Balance Sheet"""
        as_of_date = request.query_params.get('as_of_date')

        if not as_of_date:
            as_of_date = date.today()
        else:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

        # Assets
        asset_accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            account_type='asset',
            is_active=True
        )

        assets_data = []
        total_assets = Decimal('0')

        for account in asset_accounts:
            balance = account.get_balance(as_of_date)
            total_assets += balance
            assets_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'balance': float(balance)
            })

        # Liabilities
        liability_accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            account_type='liability',
            is_active=True
        )

        liabilities_data = []
        total_liabilities = Decimal('0')

        for account in liability_accounts:
            balance = account.get_balance(as_of_date)
            total_liabilities += balance
            liabilities_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'balance': float(balance)
            })

        # Equity
        equity_accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            account_type='equity',
            is_active=True
        )

        equity_data = []
        total_equity = Decimal('0')

        for account in equity_accounts:
            balance = account.get_balance(as_of_date)
            total_equity += balance
            equity_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'balance': float(balance)
            })

        return Response({
            'as_of_date': as_of_date,
            'assets': {
                'accounts': assets_data,
                'total': float(total_assets)
            },
            'liabilities': {
                'accounts': liabilities_data,
                'total': float(total_liabilities)
            },
            'equity': {
                'accounts': equity_data,
                'total': float(total_equity)
            },
            'total_liabilities_and_equity': float(total_liabilities + total_equity)
        })

    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """Generate Trial Balance"""
        as_of_date = request.query_params.get('as_of_date')

        if not as_of_date:
            as_of_date = date.today()
        else:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

        accounts = ChartOfAccounts.objects.filter(
            organization=request.user,
            is_active=True
        ).order_by('account_code')

        trial_balance_data = []
        total_debits = Decimal('0')
        total_credits = Decimal('0')

        for account in accounts:
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__status='posted',
                journal_entry__posting_date__lte=as_of_date
            )

            debits = entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or Decimal('0')
            credits = entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or Decimal('0')

            if debits > 0 or credits > 0:
                total_debits += debits
                total_credits += credits

                trial_balance_data.append({
                    'account_code': account.account_code,
                    'account_name': account.account_name,
                    'account_type': account.account_type,
                    'debit': float(debits),
                    'credit': float(credits)
                })

        return Response({
            'as_of_date': as_of_date,
            'accounts': trial_balance_data,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'is_balanced': total_debits == total_credits
        })

    @action(detail=False, methods=['get'])
    def ai_budget_variance(self, request):
        """AI-powered budget variance analysis with critical alerts"""
        from .ai_insights import FinancialAI

        organization = request.user
        fiscal_year_id = request.query_params.get('fiscal_year')
        department_id = request.query_params.get('department')

        fiscal_year = None
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id, organization=organization)
            except FiscalYear.DoesNotExist:
                return Response({'error': 'Fiscal year not found'}, status=status.HTTP_404_NOT_FOUND)

        from core.models import Department
        department = None
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
            except Department.DoesNotExist:
                return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

        analysis = FinancialAI.analyze_budget_variance(
            organization=organization,
            fiscal_year=fiscal_year,
            department=department
        )

        return Response(analysis)

    @action(detail=False, methods=['get'])
    def ai_cash_flow_forecast(self, request):
        """AI-powered cash flow forecasting"""
        from .ai_insights import FinancialAI

        organization = request.user
        days_forward = int(request.query_params.get('days', 30))

        if days_forward > 90:
            return Response({'error': 'Maximum forecast period is 90 days'}, status=status.HTTP_400_BAD_REQUEST)

        forecast = FinancialAI.forecast_cash_flow(organization, days_forward=days_forward)

        return Response(forecast)

    @action(detail=False, methods=['get'])
    def ai_transaction_anomalies(self, request):
        """AI-powered transaction anomaly detection"""
        from .ai_insights import FinancialAI

        organization = request.user
        days = int(request.query_params.get('days', 30))
        threshold = float(request.query_params.get('threshold', 2.5))

        if days > 90:
            return Response({'error': 'Maximum analysis period is 90 days'}, status=status.HTTP_400_BAD_REQUEST)

        anomalies = FinancialAI.detect_transaction_anomalies(
            organization=organization,
            days=days,
            std_dev_threshold=threshold
        )

        return Response(anomalies)

    @action(detail=False, methods=['get'])
    def ai_financial_health(self, request):
        """AI-powered financial health score"""
        from .ai_insights import FinancialAI

        organization = request.user

        health_score = FinancialAI.calculate_financial_health_score(organization)

        return Response(health_score)

    @action(detail=False, methods=['get'])
    def ai_insights_overview(self, request):
        """Get all financial AI insights in one response"""
        from .ai_insights import FinancialAI

        organization = request.user

        insights = FinancialAI.get_financial_insights(organization)

        return Response({
            'organization': organization.full_name,
            'total_insights': len(insights),
            'high_priority_count': len([i for i in insights if i['priority'] == 'high']),
            'medium_priority_count': len([i for i in insights if i['priority'] == 'medium']),
            'insights': insights,
            'generated_at': timezone.now()
        })
