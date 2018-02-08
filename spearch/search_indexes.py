from haystack import indexes

from spearch.models import Speech

class SpeechIndex(indexes.SearchIndex, indexes.Indexable):
    """Index for speeches."""

    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return Speech

    def index_queryset(self, using=None):
        """Used when the entre index is updated."""
        return self.get_model().objects.all()
