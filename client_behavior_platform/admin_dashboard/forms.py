from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField(
        label='Select a file',
        help_text='Max. 500 megabytes',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-red-50 file:text-red-700 hover:file:bg-red-100',
            'accept': '.csv,.json'
        })
    )

class RunJobForm(forms.Form):
    JOB_TYPES = [
        ('batch', 'Batch Processing'),
        ('streaming', 'Streaming Processing')
    ]
    
    job_type = forms.ChoiceField(
        choices=JOB_TYPES,
        label='Job Type',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500'
        })
    )
