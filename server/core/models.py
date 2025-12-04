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
    ("RENEWAL", "Renewal"),
    ("AMENDMENT", "Amendment"),
    ("NEW", "New"),
]

class WaiverDocument(models.Model):
    file_path = models.FileField(upload_to='uploads/')
    uploaded_on = models.DateTimeField(auto_now_add=True)

    year = models.IntegerField(null=True, blank=True)
    application_number = models.CharField(max_length=256, null=True, blank=True)
    program_title = models.TextField(null=True, blank=True)
    proposed_effective_date = models.DateField(null=True, blank=True)
    approved_effective_date = models.DateField(null=True, blank=True)
    amended_effective_date = models.DateField(null=True, blank=True)
    state = models.CharField(
        max_length=2,
        choices=US_STATES,
        null=True,
        blank=True,
        help_text="U.S. state (2-letter code)"
    )
    application_type = models.CharField(
        max_length=32,
        choices=POLICY_TYPES,
        default="POLICY",
        help_text="Is this a policy or an amendment?"
    )
    extra = models.JSONField(default=dict)



class Chunk(models.Model):
    document = models.ForeignKey(WaiverDocument, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    page = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=0)
    start = models.IntegerField(default=0)
    end = models.IntegerField(default=0)

class Embedding(models.Model):
    kind = models.CharField(max_length=16)  # text | image
    vector_id = models.BigIntegerField()
    chunk = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL)
    document = models.ForeignKey(WaiverDocument, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)

class ImageAsset(models.Model):
    document = models.ForeignKey(WaiverDocument, on_delete=models.CASCADE, related_name="images")
    path = models.TextField()
    page = models.IntegerField(null=True, blank=True)
    caption = models.TextField(blank=True, default="")
