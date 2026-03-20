from django.contrib import admin
from .models import Paper, Author, PaperAuthor, Tag, Note


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    """Admin interface for Paper model"""
    
    list_display = ('title', 'year', 'reading_status', 'priority', 'created_at')
    list_filter = ('reading_status', 'year', 'is_open_access')
    search_fields = ('title', 'doi', 'abstract')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'doi', 'abstract')
        }),
        ('Publication Details', {
            'fields': ('year', 'journal', 'volume', 'issue', 'pages', 'publisher', 'paper_type')
        }),
        ('URLs & Files', {
            'fields': ('url', 'pdf_url', 'pdf_file')
        }),
        ('AI Summary', {
            'fields': ('summary_overview', 'summary_methods', 'summary_findings', 'summary_significance', 'keywords_ai', 'summary_generated_at'),
            'classes': ('collapse',)
        }),
        ('Organisation', {
            'fields': ('reading_status', 'priority')
        }),
        ('Metrics', {
            'fields': ('citation_count', 'is_open_access')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Admin interface for Author model"""
    
    list_display = ('full_name', 'email', 'orcid', 'affiliation')
    search_fields = ('given_name', 'family_name', 'email', 'orcid')
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'


@admin.register(PaperAuthor)
class PaperAuthorAdmin(admin.ModelAdmin):
    """Admin interface for PaperAuthor relationship"""
    
    list_display = ('author', 'paper_title', 'order')
    list_filter = ('order',)
    search_fields = ('author__given_name', 'author__family_name', 'paper__title')
    
    def paper_title(self, obj):
        return obj.paper.title[:50]
    paper_title.short_description = 'Paper'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for Tag model"""
    
    list_display = ('name', 'user', 'colour', 'paper_count')
    list_filter = ('user',)
    search_fields = ('name',)
    filter_horizontal = ('papers',)
    
    def paper_count(self, obj):
        return obj.papers.count()
    paper_count.short_description = 'Papers'


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin interface for Note model"""
    
    list_display = ('paper_title', 'user', 'page_number', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('content', 'paper__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def paper_title(self, obj):
        return obj.paper.title[:50]
    paper_title.short_description = 'Paper'