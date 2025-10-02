from django.db import models

US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"),
]

POLICY_TYPES = [
    ("POLICY", "Policy"),
    ("AMENDMENT", "Amendment"),
]

class Document(models.Model):
    path = models.TextField(unique=True)
    doc_type = models.CharField(max_length=32, default="text")
    year = models.IntegerField(null=True, blank=True)
    group = models.CharField(max_length=128, null=True, blank=True)
    state = models.CharField(
        max_length=2,
        choices=US_STATES,
        null=True,
        blank=True,
        help_text="U.S. state (2-letter code)"
    )
    policy_type = models.CharField(
        max_length=16,
        choices=POLICY_TYPES,
        default="POLICY",
        help_text="Is this a policy or an amendment?"
    )
    extra = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    page = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=0)
    start = models.IntegerField(default=0)
    end = models.IntegerField(default=0)

class Embedding(models.Model):
    kind = models.CharField(max_length=16)  # text | image
    vector_id = models.BigIntegerField()
    chunk = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)

class ImageAsset(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="images")
    path = models.TextField()
    page = models.IntegerField(null=True, blank=True)
    caption = models.TextField(blank=True, default="")
