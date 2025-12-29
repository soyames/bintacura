"""
Financial AI Analytics Module
No LLM required - Uses statistical methods, trend analysis, and pattern recognition
"""
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q, F
from datetime import timedelta
from decimal import Decimal
from .models import (
    Budget, BudgetLine, JournalEntry, JournalEntryLine,
    ChartOfAccounts, BankAccount, FiscalPeriod
)


class FinancialAI:
    """AI-powered financial analytics using statistical methods"""

    @staticmethod
    def analyze_budget_variance(organization, fiscal_year=None, department=None):
        """
        Analyze budget vs actual variance using statistical thresholds

        Returns:
            dict: Variance analysis with alerts for over/under budget items
        """
        from datetime import datetime

        # Get active budget
        budget_query = Budget.objects.filter(
            organization=organization,
            status__in=['approved', 'active']
        )

        if fiscal_year:
            budget_query = budget_query.filter(fiscal_year=fiscal_year)
        else:
            budget_query = budget_query.filter(
                fiscal_year__start_date__lte=timezone.now().date(),
                fiscal_year__end_date__gte=timezone.now().date()
            )

        budget = budget_query.first()
        if not budget:
            return {
                'status': 'no_budget',
                'message': 'No active budget found for analysis period'
            }

        # Get budget lines
        budget_lines_query = BudgetLine.objects.filter(budget=budget).select_related('account', 'department')
        if department:
            budget_lines_query = budget_lines_query.filter(department=department)

        variances = []
        critical_variances = []
        warning_variances = []

        for budget_line in budget_lines_query:
            # Get actual spending from journal entries
            actual_query = JournalEntryLine.objects.filter(
                account=budget_line.account,
                journal_entry__organization=organization,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=budget.fiscal_year.start_date,
                journal_entry__posting_date__lte=min(
                    budget.fiscal_year.end_date,
                    timezone.now().date()
                )
            )

            if budget_line.department:
                actual_query = actual_query.filter(department=budget_line.department)

            # Calculate actual amount based on account type
            if budget_line.account.account_type in ['expense', 'asset']:
                actual_amount = actual_query.aggregate(
                    total=Sum('debit_amount') - Sum('credit_amount')
                )['total'] or Decimal('0')
            else:  # revenue, liability, equity
                actual_amount = actual_query.aggregate(
                    total=Sum('credit_amount') - Sum('debit_amount')
                )['total'] or Decimal('0')

            budgeted_amount = budget_line.annual_amount
            variance = actual_amount - budgeted_amount
            variance_percentage = (variance / budgeted_amount * 100) if budgeted_amount > 0 else 0

            variance_data = {
                'account': budget_line.account.account_name,
                'account_code': budget_line.account.account_code,
                'account_type': budget_line.account.account_type,
                'department': budget_line.department.name if budget_line.department else 'General',
                'budgeted_amount': float(budgeted_amount),
                'actual_amount': float(actual_amount),
                'variance': float(variance),
                'variance_percentage': float(variance_percentage),
                'status': 'on_track'
            }

            # Determine alert level
            if budget_line.account.account_type == 'expense':
                # For expenses, over budget is bad
                if variance_percentage > 20:
                    variance_data['status'] = 'critical_overbudget'
                    variance_data['alert'] = f"CRITICAL: {variance_percentage:.1f}% over budget"
                    critical_variances.append(variance_data)
                elif variance_percentage > 10:
                    variance_data['status'] = 'warning_overbudget'
                    variance_data['alert'] = f"WARNING: {variance_percentage:.1f}% over budget"
                    warning_variances.append(variance_data)
                elif variance_percentage < -30:
                    variance_data['status'] = 'significant_underbudget'
                    variance_data['alert'] = f"Significantly under budget ({variance_percentage:.1f}%)"
                    warning_variances.append(variance_data)
            elif budget_line.account.account_type == 'revenue':
                # For revenue, under budget is bad
                if variance_percentage < -20:
                    variance_data['status'] = 'critical_underbudget'
                    variance_data['alert'] = f"CRITICAL: Revenue {-variance_percentage:.1f}% below target"
                    critical_variances.append(variance_data)
                elif variance_percentage < -10:
                    variance_data['status'] = 'warning_underbudget'
                    variance_data['alert'] = f"WARNING: Revenue {-variance_percentage:.1f}% below target"
                    warning_variances.append(variance_data)

            variances.append(variance_data)

        return {
            'status': 'analyzed',
            'budget_name': budget.name,
            'fiscal_year': budget.fiscal_year.name,
            'analysis_date': timezone.now().date(),
            'total_budget_lines': len(variances),
            'critical_count': len(critical_variances),
            'warning_count': len(warning_variances),
            'critical_variances': critical_variances,
            'warning_variances': warning_variances,
            'all_variances': variances
        }

    @staticmethod
    def forecast_cash_flow(organization, days_forward=30):
        """
        Forecast cash flow using time series analysis (moving averages)

        Args:
            organization: Organization participant
            days_forward: Number of days to forecast (default 30)

        Returns:
            dict: Cash flow forecast with predicted balance
        """
        # Get cash/bank accounts
        cash_accounts = BankAccount.objects.filter(
            organization=organization,
            is_active=True
        )

        if not cash_accounts.exists():
            return {
                'status': 'no_accounts',
                'message': 'No active bank accounts found'
            }

        # Calculate current total cash
        total_cash = cash_accounts.aggregate(
            total=Sum('current_balance')
        )['total'] or Decimal('0')

        # Analyze historical cash transactions (last 90 days)
        lookback_days = 90
        start_date = timezone.now().date() - timedelta(days=lookback_days)

        # Get cash account GL accounts
        cash_gl_accounts = [acc.gl_account_id for acc in cash_accounts]

        # Analyze daily cash inflows and outflows
        cash_entries = JournalEntryLine.objects.filter(
            account_id__in=cash_gl_accounts,
            journal_entry__status='posted',
            journal_entry__posting_date__gte=start_date
        ).select_related('journal_entry')

        # Calculate daily net cash flow
        daily_flows = {}
        for entry in cash_entries:
            date_key = entry.journal_entry.posting_date
            if date_key not in daily_flows:
                daily_flows[date_key] = {'inflow': Decimal('0'), 'outflow': Decimal('0')}

            # Debit to cash = inflow, Credit to cash = outflow
            daily_flows[date_key]['inflow'] += entry.debit_amount
            daily_flows[date_key]['outflow'] += entry.credit_amount

        # Calculate average daily net cash flow
        if daily_flows:
            total_net_flow = sum(
                (day['inflow'] - day['outflow']) for day in daily_flows.values()
            )
            avg_daily_net_flow = total_net_flow / len(daily_flows)

            # Calculate trend (last 30 days vs previous 60 days)
            recent_date = timezone.now().date() - timedelta(days=30)
            recent_flows = {k: v for k, v in daily_flows.items() if k >= recent_date}

            if recent_flows:
                recent_avg = sum(
                    (day['inflow'] - day['outflow']) for day in recent_flows.values()
                ) / len(recent_flows)

                trend = 'improving' if recent_avg > avg_daily_net_flow else 'declining'
                trend_percentage = ((recent_avg - avg_daily_net_flow) / abs(avg_daily_net_flow) * 100) if avg_daily_net_flow != 0 else 0
            else:
                recent_avg = avg_daily_net_flow
                trend = 'stable'
                trend_percentage = 0
        else:
            avg_daily_net_flow = Decimal('0')
            recent_avg = Decimal('0')
            trend = 'no_data'
            trend_percentage = 0

        # Forecast future balance
        forecasted_balance = total_cash + (recent_avg * days_forward)

        # Determine cash position health
        if forecasted_balance < 0:
            health_status = 'critical'
            recommendation = f"URGENT: Forecasted negative cash balance in {days_forward} days. Immediate action required."
        elif forecasted_balance < total_cash * Decimal('0.5'):
            health_status = 'warning'
            recommendation = f"WARNING: Cash expected to decrease by {((total_cash - forecasted_balance) / total_cash * 100):.1f}% in {days_forward} days."
        else:
            health_status = 'healthy'
            recommendation = "Cash flow forecast is healthy."

        return {
            'status': 'forecasted',
            'forecast_period_days': days_forward,
            'current_balance': float(total_cash),
            'forecasted_balance': float(forecasted_balance),
            'avg_daily_net_flow': float(avg_daily_net_flow),
            'recent_avg_daily_flow': float(recent_avg),
            'trend': trend,
            'trend_percentage': float(trend_percentage),
            'health_status': health_status,
            'recommendation': recommendation,
            'bank_accounts_count': cash_accounts.count()
        }

    @staticmethod
    def detect_transaction_anomalies(organization, days=30, std_dev_threshold=2.5):
        """
        Detect anomalous transactions using statistical outlier detection

        Args:
            organization: Organization participant
            days: Number of days to analyze (default 30)
            std_dev_threshold: Standard deviations from mean to flag (default 2.5)

        Returns:
            dict: Detected anomalies with statistical analysis
        """
        start_date = timezone.now().date() - timedelta(days=days)

        # Get all posted journal entries
        entries = JournalEntry.objects.filter(
            organization=organization,
            status='posted',
            posting_date__gte=start_date
        ).prefetch_related('line_items')

        if not entries.exists():
            return {
                'status': 'no_data',
                'message': f'No transactions found in last {days} days'
            }

        # Analyze transaction amounts by type
        anomalies = []

        for entry_type in ['sales', 'purchase', 'payment', 'receipt', 'payroll']:
            type_entries = entries.filter(entry_type=entry_type)

            if not type_entries.exists():
                continue

            # Calculate transaction amounts
            amounts = []
            entry_data = []

            for entry in type_entries:
                total = entry.line_items.aggregate(
                    total=Sum('debit_amount')
                )['total'] or Decimal('0')
                amounts.append(float(total))
                entry_data.append({
                    'entry_number': entry.entry_number,
                    'posting_date': entry.posting_date,
                    'amount': float(total),
                    'description': entry.description,
                    'reference': entry.reference_number
                })

            if len(amounts) < 3:
                continue  # Need at least 3 transactions for statistical analysis

            # Calculate mean and standard deviation
            import statistics
            mean_amount = statistics.mean(amounts)
            std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0

            # Find outliers
            for data in entry_data:
                if std_dev > 0:
                    z_score = abs((data['amount'] - mean_amount) / std_dev)

                    if z_score > std_dev_threshold:
                        anomaly_data = data.copy()
                        anomaly_data.update({
                            'entry_type': entry_type,
                            'z_score': round(z_score, 2),
                            'mean_amount': round(mean_amount, 2),
                            'std_dev': round(std_dev, 2),
                            'severity': 'high' if z_score > 3.5 else 'medium',
                            'reason': f"Amount is {z_score:.1f} standard deviations from mean"
                        })
                        anomalies.append(anomaly_data)

        # Sort by severity and z-score
        anomalies.sort(key=lambda x: (x['severity'] == 'high', x['z_score']), reverse=True)

        return {
            'status': 'analyzed',
            'analysis_period_days': days,
            'total_transactions': entries.count(),
            'anomalies_detected': len(anomalies),
            'high_severity_count': len([a for a in anomalies if a['severity'] == 'high']),
            'medium_severity_count': len([a for a in anomalies if a['severity'] == 'medium']),
            'anomalies': anomalies[:20],  # Top 20
            'threshold_used': std_dev_threshold
        }

    @staticmethod
    def calculate_financial_health_score(organization):
        """
        Calculate overall financial health score (0-100)

        Metrics considered:
        - Cash position
        - Budget adherence
        - Revenue growth
        - Expense control
        - Transaction volume health

        Returns:
            dict: Health score with breakdown by category
        """
        scores = {}
        weights = {}

        # 1. Cash Position Score (30%)
        cash_accounts = BankAccount.objects.filter(
            organization=organization,
            is_active=True
        )

        if cash_accounts.exists():
            total_cash = cash_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')

            # Cash flow forecast
            cash_forecast = FinancialAI.forecast_cash_flow(organization, days_forward=30)

            if cash_forecast['status'] == 'forecasted':
                if cash_forecast['health_status'] == 'healthy':
                    scores['cash_position'] = 90
                elif cash_forecast['health_status'] == 'warning':
                    scores['cash_position'] = 60
                else:  # critical
                    scores['cash_position'] = 30
            else:
                scores['cash_position'] = 50  # Neutral if no data

            weights['cash_position'] = 0.30

        # 2. Budget Adherence Score (25%)
        budget_analysis = FinancialAI.analyze_budget_variance(organization)

        if budget_analysis['status'] == 'analyzed':
            critical_count = budget_analysis['critical_count']
            warning_count = budget_analysis['warning_count']
            total_lines = budget_analysis['total_budget_lines']

            if total_lines > 0:
                problem_ratio = (critical_count * 2 + warning_count) / total_lines
                scores['budget_adherence'] = max(0, 100 - (problem_ratio * 100))
            else:
                scores['budget_adherence'] = 50

            weights['budget_adherence'] = 0.25

        # 3. Revenue Growth Score (20%)
        # Compare last 30 days to previous 30 days
        today = timezone.now().date()
        current_period_start = today - timedelta(days=30)
        previous_period_start = today - timedelta(days=60)

        revenue_accounts = ChartOfAccounts.objects.filter(
            organization=organization,
            account_type='revenue',
            is_active=True
        )

        if revenue_accounts.exists():
            current_revenue = JournalEntryLine.objects.filter(
                account__in=revenue_accounts,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=current_period_start,
                journal_entry__posting_date__lte=today
            ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')

            previous_revenue = JournalEntryLine.objects.filter(
                account__in=revenue_accounts,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=previous_period_start,
                journal_entry__posting_date__lt=current_period_start
            ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')

            if previous_revenue > 0:
                growth_rate = ((current_revenue - previous_revenue) / previous_revenue * 100)

                if growth_rate >= 10:
                    scores['revenue_growth'] = 95
                elif growth_rate >= 5:
                    scores['revenue_growth'] = 80
                elif growth_rate >= 0:
                    scores['revenue_growth'] = 65
                elif growth_rate >= -5:
                    scores['revenue_growth'] = 50
                else:
                    scores['revenue_growth'] = 30
            else:
                scores['revenue_growth'] = 50

            weights['revenue_growth'] = 0.20

        # 4. Expense Control Score (15%)
        expense_accounts = ChartOfAccounts.objects.filter(
            organization=organization,
            account_type='expense',
            is_active=True
        )

        if expense_accounts.exists():
            current_expenses = JournalEntryLine.objects.filter(
                account__in=expense_accounts,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=current_period_start,
                journal_entry__posting_date__lte=today
            ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')

            previous_expenses = JournalEntryLine.objects.filter(
                account__in=expense_accounts,
                journal_entry__status='posted',
                journal_entry__posting_date__gte=previous_period_start,
                journal_entry__posting_date__lt=current_period_start
            ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')

            if previous_expenses > 0:
                expense_change = ((current_expenses - previous_expenses) / previous_expenses * 100)

                # Lower expense growth is better
                if expense_change <= -5:
                    scores['expense_control'] = 95
                elif expense_change <= 0:
                    scores['expense_control'] = 80
                elif expense_change <= 5:
                    scores['expense_control'] = 65
                elif expense_change <= 10:
                    scores['expense_control'] = 50
                else:
                    scores['expense_control'] = 30
            else:
                scores['expense_control'] = 50

            weights['expense_control'] = 0.15

        # 5. Transaction Health Score (10%)
        anomalies = FinancialAI.detect_transaction_anomalies(organization, days=30)

        if anomalies['status'] == 'analyzed':
            total_transactions = anomalies['total_transactions']
            anomalies_count = anomalies['anomalies_detected']

            if total_transactions > 0:
                anomaly_rate = (anomalies_count / total_transactions * 100)

                if anomaly_rate < 2:
                    scores['transaction_health'] = 90
                elif anomaly_rate < 5:
                    scores['transaction_health'] = 70
                elif anomaly_rate < 10:
                    scores['transaction_health'] = 50
                else:
                    scores['transaction_health'] = 30
            else:
                scores['transaction_health'] = 50

            weights['transaction_health'] = 0.10

        # Calculate weighted overall score
        if scores and weights:
            overall_score = sum(scores[key] * weights[key] for key in scores.keys())
            overall_score = round(overall_score, 1)
        else:
            overall_score = 0

        # Determine overall health status
        if overall_score >= 80:
            health_status = 'excellent'
            summary = "Financial health is excellent. Continue current practices."
        elif overall_score >= 65:
            health_status = 'good'
            summary = "Financial health is good with some areas for improvement."
        elif overall_score >= 50:
            health_status = 'fair'
            summary = "Financial health is fair. Several areas need attention."
        else:
            health_status = 'poor'
            summary = "Financial health needs immediate attention."

        return {
            'overall_score': overall_score,
            'health_status': health_status,
            'summary': summary,
            'breakdown': {
                key: {
                    'score': round(scores.get(key, 0), 1),
                    'weight': f"{weights.get(key, 0) * 100:.0f}%",
                    'weighted_contribution': round(scores.get(key, 0) * weights.get(key, 0), 1)
                }
                for key in scores.keys()
            },
            'generated_at': timezone.now()
        }

    @staticmethod
    def get_financial_insights(organization):
        """
        Get all financial AI insights for unified dashboard
        Called by central AI coordinator

        Returns:
            list: All financial insights with priority levels
        """
        insights = []

        # Budget variance insights
        budget_analysis = FinancialAI.analyze_budget_variance(organization)
        if budget_analysis['status'] == 'analyzed':
            if budget_analysis['critical_count'] > 0:
                insights.append({
                    'type': 'budget_variance',
                    'priority': 'high',
                    'title': f"{budget_analysis['critical_count']} Critical Budget Variances Detected",
                    'description': f"Critical over/under budget items requiring immediate attention",
                    'data': budget_analysis['critical_variances'][:5],
                    'module': 'financial'
                })

            if budget_analysis['warning_count'] > 0:
                insights.append({
                    'type': 'budget_variance',
                    'priority': 'medium',
                    'title': f"{budget_analysis['warning_count']} Budget Items Need Review",
                    'description': f"Budget variances approaching critical thresholds",
                    'data': budget_analysis['warning_variances'][:5],
                    'module': 'financial'
                })

        # Cash flow insights
        cash_forecast = FinancialAI.forecast_cash_flow(organization, days_forward=30)
        if cash_forecast['status'] == 'forecasted':
            priority = 'high' if cash_forecast['health_status'] == 'critical' else 'medium' if cash_forecast['health_status'] == 'warning' else 'low'

            insights.append({
                'type': 'cash_flow_forecast',
                'priority': priority,
                'title': '30-Day Cash Flow Forecast',
                'description': cash_forecast['recommendation'],
                'data': cash_forecast,
                'module': 'financial'
            })

        # Transaction anomalies
        anomalies = FinancialAI.detect_transaction_anomalies(organization, days=30)
        if anomalies['status'] == 'analyzed' and anomalies['anomalies_detected'] > 0:
            priority = 'high' if anomalies['high_severity_count'] > 0 else 'medium'

            insights.append({
                'type': 'transaction_anomalies',
                'priority': priority,
                'title': f"{anomalies['anomalies_detected']} Unusual Transactions Detected",
                'description': f"Statistical anomalies requiring review ({anomalies['high_severity_count']} high severity)",
                'data': anomalies['anomalies'][:10],
                'module': 'financial'
            })

        # Financial health score
        health_score = FinancialAI.calculate_financial_health_score(organization)
        priority = 'high' if health_score['health_status'] == 'poor' else 'medium' if health_score['health_status'] == 'fair' else 'low'

        insights.append({
            'type': 'financial_health',
            'priority': priority,
            'title': f"Financial Health Score: {health_score['overall_score']}/100",
            'description': health_score['summary'],
            'data': health_score,
            'module': 'financial'
        })

        return insights
