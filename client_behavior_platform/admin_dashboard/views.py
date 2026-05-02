from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import os, subprocess
from django.conf import settings
from datetime import datetime
from .models import JobHistory, JobMetrics
from .forms import UploadFileForm, RunJobForm
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from users.forms import CustomUserCreationForm
from users.models import CustomUser

@login_required
def dashboard_home(request):
    # Get HDFS file count
    result = subprocess.run(['hdfs', 'dfs', '-ls', '/landing_zone/'], capture_output=True, text=True)
    hdfs_file_count = len([line for line in result.stdout.split('\n') if line.strip()]) - 1  # -1 for header

    # Get job statistics
    active_jobs = JobHistory.objects.filter(status='Running').count()
    completed_jobs = JobHistory.objects.filter(status='Success').count()
    failed_jobs = JobHistory.objects.filter(status='Failed').count()
    
    # Get recent jobs
    recent_jobs = JobHistory.objects.all().order_by('-timestamp')[:5]

    context = {
        'hdfs_file_count': hdfs_file_count,
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'failed_jobs': failed_jobs,
        'recent_jobs': recent_jobs,
    }
    return render(request, 'admin_dashboard/dashboard_home.html', context)

@login_required
def upload_file(request):
    msg = ""
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage(location='/tmp/')
            filename = fs.save(uploaded_file.name, uploaded_file)
            local_path = os.path.join('/tmp/', filename)
            
            # Upload to HDFS
            result = subprocess.run(
                ['hdfs', 'dfs', '-put', '-f', local_path, '/landing_zone/'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                msg = f"✅ File {filename} uploaded to HDFS successfully"
                
                # Create job history entry for file upload
                JobHistory.objects.create(
                    job_name=f"upload_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    job_type='upload',
                    status='Success',
                    logs=f"File uploaded to HDFS: {filename}"
                )
            else:
                msg = f"❌ HDFS Error: {result.stderr}"
                
                # Log failed upload
                JobHistory.objects.create(
                    job_name=f"upload_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    job_type='upload',
                    status='Failed',
                    logs=f"Failed to upload file: {result.stderr}"
                )
            
            # Clean up temporary file
            os.remove(local_path)
    else:
        form = UploadFileForm()
    
    return render(request, 'admin_dashboard/upload_file.html', {'form': form, 'msg': msg})

@login_required
def launch_job(request):
    log_result = ""
    if request.method == 'POST':
        form = RunJobForm(request.POST)
        if form.is_valid():
            job_type = form.cleaned_data['job_type']
            job_name = f"{job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create job history entry
            job = JobHistory.objects.create(
                job_name=job_name,
                job_type=job_type,
                status='Running',
                logs='Job started...'
            )
            
            try:
                if job_type == 'batch':
                    # Launch batch job
                    cmd = [
                        'spark-submit',
                        '--master', 'spark://spark-master:7077',
                        '--packages', 'io.delta:delta-core_2.12:2.0.0',
                        '/opt/spark/apps/etl_pipeline_project/batch/batch_pipeline.py'
                    ]
                else:
                    # Launch streaming job
                    cmd = [
                        'spark-submit',
                        '--master', 'spark://spark-master:7077',
                        '--packages', 'io.delta:delta-core_2.12:2.0.0',
                        '/opt/spark/apps/etl_pipeline_project/streaming/etl_streaming.py'
                    ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    job.status = 'Success'
                    log_result = "✅ Job launched successfully"
                else:
                    job.status = 'Failed'
                    log_result = f"❌ Error: {result.stderr}"
                
                job.logs += f"\n{result.stdout}\n{result.stderr}"
                job.save()
                
            except Exception as e:
                job.status = 'Failed'
                job.logs += f"\nError: {str(e)}"
                job.save()
                log_result = f"❌ Error: {str(e)}"
    else:
        form = RunJobForm()
    
    return render(request, 'admin_dashboard/launch_job.html', {'form': form, 'log': log_result})

@login_required
def job_history(request):
    jobs = JobHistory.objects.all().order_by('-timestamp')
    return render(request, 'admin_dashboard/job_history.html', {'jobs': jobs})

@login_required
def job_log_detail(request, job_name):
    try:
        job = JobHistory.objects.get(job_name=job_name)
        return render(request, 'admin_dashboard/job_log_detail.html', {
            'job': job,
            'log_content': job.logs
        })
    except JobHistory.DoesNotExist:
        return HttpResponse("Job not found", status=404)

def employee_management(request):
    return render(request, 'admin_dashboard/employee_management.html')
@login_required
@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = CustomUserCreationForm(instance=user)

    context = {
        'form': form,
    }
    return render(request, 'admin_dashboard/profile.html', context)


def signout_view(request):
    # Usually, you'd perform the signout operation here or redirect to a signout URL
    return render(request, 'accounts/home.html')
