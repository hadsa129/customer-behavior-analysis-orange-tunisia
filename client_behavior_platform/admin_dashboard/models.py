from django.db import models

class JobSchedule(models.Model):
    job_type = models.CharField(max_length=10, choices=[('batch', 'Batch'), ('streaming', 'Streaming')])
    cron_expression = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True)

class JobHistory(models.Model):
    JOB_TYPES = [
        ('batch', 'Batch'),
        ('streaming', 'Streaming'),
    ]
    
    job_name = models.CharField(max_length=100)
    job_type = models.CharField(max_length=10, choices=JOB_TYPES)
    status = models.CharField(max_length=20)
    logs = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
class JobMetrics(models.Model):
    job = models.ForeignKey(JobHistory, on_delete=models.CASCADE)
    records_processed = models.IntegerField()
    processing_time = models.FloatField()
    error_count = models.IntegerField()

    def __str__(self):
        return f"{self.job_name} - {self.job_type} - {self.status}"
