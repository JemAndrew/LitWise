import re

from django import forms


class DOIImportForm(forms.Form):
    doi = forms.CharField(
        max_length=200,
        label='DOI',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 10.1038/nature12373',
            'class': 'w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500',
        }),
    )

    def clean_doi(self):
        doi = self.cleaned_data['doi'].strip()
        if not re.match(r'^10\.\d{4,}/', doi):
            raise forms.ValidationError('Enter a valid DOI (e.g. 10.1038/nature12373).')
        return doi


class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label='PDF file',
        widget=forms.ClearableFileInput(attrs={
            'accept': '.pdf',
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
        }),
    )

    def clean_pdf_file(self):
        pdf = self.cleaned_data['pdf_file']
        if not pdf.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Only PDF files are accepted.')
        if pdf.size > 50 * 1024 * 1024:
            raise forms.ValidationError('File size must be under 50 MB.')
        return pdf


class SearchForm(forms.Form):
    q = forms.CharField(
        min_length=2,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search papers...',
            'class': 'w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500',
        }),
    )
