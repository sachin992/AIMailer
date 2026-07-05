"""
Monitoring and analytics module for AIMailer
Tracks metrics, performance, and generates reports
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

from logger import get_logger
from database import Database

logger = get_logger("monitoring")


@dataclass
class EmailMetrics:
    """Metrics for a single email processing"""
    email_id: str
    processing_time_ms: int
    confidence_score: float
    status: str
    requires_review: bool
    faq_matches_count: int
    timestamp: datetime


class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize metrics collector"""
        self.db = db
        self.current_batch_metrics: List[EmailMetrics] = []
        self.session_start_time = time.time()
    
    def record_email_metrics(
        self,
        email_id: str,
        processing_time_ms: int,
        confidence_score: float,
        status: str,
        requires_review: bool,
        faq_matches_count: int
    ):
        """Record metrics for a processed email"""
        metrics = EmailMetrics(
            email_id=email_id,
            processing_time_ms=processing_time_ms,
            confidence_score=confidence_score,
            status=status,
            requires_review=requires_review,
            faq_matches_count=faq_matches_count,
            timestamp=datetime.now()
        )
        
        self.current_batch_metrics.append(metrics)
        logger.debug(f"Recorded metrics for email {email_id}")
    
    def get_batch_summary(self) -> Dict:
        """Get summary of current batch"""
        if not self.current_batch_metrics:
            return {}
        
        total_emails = len(self.current_batch_metrics)
        auto_replied = sum(
            1 for m in self.current_batch_metrics 
            if m.status == "success" and not m.requires_review
        )
        manual_review = sum(
            1 for m in self.current_batch_metrics 
            if m.requires_review
        )
        failed = sum(
            1 for m in self.current_batch_metrics 
            if m.status == "failed"
        )
        
        avg_confidence = sum(
            m.confidence_score for m in self.current_batch_metrics
        ) / total_emails
        
        avg_processing_time = sum(
            m.processing_time_ms for m in self.current_batch_metrics
        ) / total_emails
        
        return {
            "total_emails": total_emails,
            "auto_replied": auto_replied,
            "manual_review": manual_review,
            "failed": failed,
            "avg_confidence": round(avg_confidence, 3),
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "success_rate": round((auto_replied / total_emails) * 100, 2) if total_emails > 0 else 0
        }
    
    def clear_batch_metrics(self):
        """Clear current batch metrics"""
        self.current_batch_metrics.clear()
        logger.debug("Cleared batch metrics")


class AnalyticsEngine:
    """Generates analytics reports from database"""
    
    def __init__(self, db: Database):
        """Initialize analytics engine"""
        self.db = db
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict:
        """Get summary for a specific day"""
        target_date = date or datetime.now()
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        summary = self.db.get_analytics_summary(start_of_day, end_of_day)
        summary["date"] = start_of_day.strftime("%Y-%m-%d")
        
        return summary
    
    def get_weekly_summary(self) -> Dict:
        """Get summary for the past 7 days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        summary = self.db.get_analytics_summary(start_date, end_date)
        summary["period"] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        return summary
    
    def get_monthly_summary(self) -> Dict:
        """Get summary for the past 30 days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        summary = self.db.get_analytics_summary(start_date, end_date)
        summary["period"] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        return summary
    
    def get_performance_insights(self) -> Dict:
        """Get performance insights and recommendations"""
        weekly = self.get_weekly_summary()
        
        insights = {
            "total_emails_processed": weekly.get("total_emails", 0) or 0,
            "automation_rate": 0,
            "avg_confidence": weekly.get("avg_confidence", 0) or 0,
            "avg_processing_time_seconds": (
                (weekly.get("avg_processing_time_ms") or 0) / 1000
            ),
            "recommendations": []
        }
        
        # Calculate automation rate
        total = weekly.get("total_emails") or 0
        auto = weekly.get("auto_replied") or 0
        if total > 0:
            insights["automation_rate"] = round((auto / total) * 100, 2)
        
        # Generate recommendations
        if insights["automation_rate"] < 50:
            insights["recommendations"].append(
                "Low automation rate. Consider expanding FAQ database or adjusting similarity threshold."
            )
        
        if insights["avg_confidence"] < 0.5:
            insights["recommendations"].append(
                "Low average confidence. Review FAQ quality and similarity threshold settings."
            )
        
        if insights["avg_processing_time_seconds"] > 5:
            insights["recommendations"].append(
                "High processing time. Consider optimizing API calls or implementing caching."
            )
        
        return insights
    
    def export_analytics_report(self, output_file: str = "analytics_report.json"):
        """Export comprehensive analytics report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "daily_summary": self.get_daily_summary(),
            "weekly_summary": self.get_weekly_summary(),
            "monthly_summary": self.get_monthly_summary(),
            "performance_insights": self.get_performance_insights(),
            "recent_emails": self.db.get_recent_emails(limit=20)
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Exported analytics report to {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            return None
