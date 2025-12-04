# myapp/management/commands/import_waivers.py

import os
from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand
from core.models import WaiverDocument
from core.utils import extract_waiver_info, parse_effective_date, convert_date_format

class Command(BaseCommand):
    help = "Import PDF waivers from a folder and populate WaiverDocument objects"

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            type=str,
            help="Path to the folder containing PDF files (will search recursively)"
        )

    def handle(self, *args, **options):
        folder = options["folder"]
        folder_path = Path(folder)

        if not folder_path.exists():
            self.stdout.write(self.style.ERROR(f"Folder does not exist: {folder}"))
            return

        pdf_files = list(folder_path.rglob("*.pdf"))
        total = len(pdf_files)
        self.stdout.write(f"Found {total} PDF files in {folder_path}")
        WaiverDocument.objects.all().delete()

        for pdf_path in pdf_files:
            self.stdout.write(f"Processing: {pdf_path}")
            try:
                data = extract_waiver_info(str(pdf_path))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to extract info from {pdf_path}: {e}"))
                continue

            # Map full state name to 2-letter code
            state_name = data.get("State", "")
            state_code = next(
                (code for code, name in WaiverDocument._meta.get_field("state").choices
                 if name.lower() == state_name.lower()),
                None
            )

            # Create WaiverDocument object
            with open(pdf_path, "rb") as f:
                approved_date_str = data.get("Approved Effective Date of Waiver being Amended") or ""
                approved_date = parse_effective_date(approved_date_str)

                waiver_doc = WaiverDocument.objects.create(
                    file_path=File(f, name=pdf_path.name),
                    program_title=data.get("Program Title"),
                    application_number=data.get("Waiver Number"),
                    application_type="AMENDMENT" if data.get("Amendment Number") else "NEW",
                    state=state_code,
                    proposed_effective_date=parse_effective_date(
                        data.get("Proposed Effective Date of Waiver being Amended") or ""
                    ),
                    approved_effective_date=approved_date,
                    amended_effective_date=approved_date,
                    year=approved_date.year if approved_date else None,
                    extra={
                        "Amendment Number": data.get("Amendment Number"),
                        "Draft ID": data.get("Draft ID"),
                        "Type of Request": data.get("Type of Request"),
                        "Requested Approval Period": data.get("Requested Approval Period"),
                        "Type of Waiver": data.get("Type of Waiver"),
                        "PRA Disclosure Statement": data.get("PRA Disclosure Statement"),
                        "State Name": state_name,
                    }
                )
                self.stdout.write(self.style.SUCCESS(str(data)))
            self.stdout.write(self.style.SUCCESS(f"Created WaiverDocument: {waiver_doc.application_number}"))
