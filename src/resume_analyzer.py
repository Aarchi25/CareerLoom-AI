import io
from pypdf import PdfReader


def extract_text_from_pdf(uploaded_file):

    """
    Extract text from an uploaded PDF resume.
    """

    try:

        # Read uploaded PDF
        pdf_reader = PdfReader(
            io.BytesIO(uploaded_file.read())
        )

        # Store extracted text
        text = ""

        # Extract text from every page
        for page in pdf_reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text.strip()

    except Exception as e:

        return f"Error extracting resume: {str(e)}"