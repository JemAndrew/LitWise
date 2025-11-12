import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Paper(models.Model):
    """Core paper model - stores academic papers"""
    
    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    
    # Metadata (from APIs like Crossref)
    title = models.TextField()
    doi = models.CharField(max_length=200, blank=True, db_index=True)
    abstract = models.TextField(blank=True)
    year = models.IntegerField(null=True, blank=True)
    journal = models.CharField(max_length=500, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    paper_type = models.CharField(max_length=50, default='article')  # article, book, etc.
    
    # URLs
    url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)  # Open access PDF if available
    
    # Files
    pdf_file = models.FileField(upload_to='papers/pdfs/%Y/%m/', null=True, blank=True)
    full_text = models.TextField(blank=True)  # Extracted PDF text
    full_text_hash = models.CharField(max_length=64, blank=True)  # SHA-256 for deduplication
    
    # AI Summaries (Claude API)
    summary_overview = models.TextField(blank=True)
    summary_methods = models.TextField(blank=True)
    summary_findings = models.TextField(blank=True)
    summary_significance = models.TextField(blank=True)
    keywords_ai = models.JSONField(default=list)  # AI-extracted keywords
    summary_generated_at = models.DateTimeField(null=True, blank=True)
    
    # Organisation
    READING_STATUS_CHOICES = [
        ('to_read', 'To Read'),
        ('reading', 'Reading'),
        ('read', 'Read'),
        ('reference', 'Reference'),
    ]
    reading_status = models.CharField(
        max_length=20,
        choices=READING_STATUS_CHOICES,
        default='to_read'
    )
    priority = models.IntegerField(default=0)  # Higher = more important
    
    # Metrics
    citation_count = models.IntegerField(default=0)
    is_open_access = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Full-text search (PostgreSQL specific)
    search_vector = SearchVectorField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'reading_status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['doi']),
            GinIndex(fields=['search_vector']),
        ]
    
    def __str__(self):
        return self.title[:100]


class Author(models.Model):
    """Paper authors"""
    
    given_name = models.CharField(max_length=200)
    family_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    orcid = models.CharField(max_length=19, blank=True)  # ORCID identifier
    affiliation = models.CharField(max_length=500, blank=True)
    
    class Meta:
        unique_together = ('given_name', 'family_name')
    
    def __str__(self):
        return f"{self.given_name} {self.family_name}"
    
    @property
    def full_name(self):
        return f"{self.given_name} {self.family_name}"


class PaperAuthor(models.Model):
    """Through model for paper-author relationship with ordering"""
    
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    order = models.IntegerField()  # 1 = first author, 2 = second, etc.
    
    class Meta:
        ordering = ['order']
        unique_together = ('paper', 'author', 'order')
    
    def __str__(self):
        return f"{self.author.full_name} - {self.paper.title[:50]}"


class Tag(models.Model):
    """User-defined tags for organising papers"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    colour = models.CharField(max_length=7, default='#3B82F6')  # Hex colour
    papers = models.ManyToManyField(Paper, related_name='tags', blank=True)
    
    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Note(models.Model):
    """User notes on papers"""
    
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    page_number = models.IntegerField(null=True, blank=True)  # Which page of PDF
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note on {self.paper.title[:50]}"